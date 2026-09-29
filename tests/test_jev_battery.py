import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import jev_evidence_battery as battery  # noqa: E402

CONFIG = battery.load_config()
GOLD = battery.load_gold()
ANNOTATIONS = battery.load_annotations()
TEXTS, SOURCES = battery.load_generated_texts(None)
TOLERANCE = CONFIG["checker_policy"]["currency_tolerance"]
PCT_TOL = CONFIG["checker_policy"]["percentage_tolerance_points"]


def span(annotation_id):
    return next(row for row in ANNOTATIONS if row["annotation_id"] == annotation_id)


def spans_for(question_id):
    return [row for row in ANNOTATIONS if row["question_id"] == question_id]


def check(annotation_id):
    row = span(annotation_id)
    return battery.check_span(GOLD[row["question_id"]], row, TEXTS[row["question_id"]], TOLERANCE, PCT_TOL)


def find(question_id, text, fact_type=None, occurrence=0):
    hits = [row for row in spans_for(question_id) if row["span_text"] == text and (fact_type is None or row["fact_type"] == fact_type)]
    return hits[occurrence]["annotation_id"]


class StateContractTests(unittest.TestCase):
    def test_public_demo_texts_cover_nine_cases(self):
        self.assertEqual(sorted(TEXTS), ["q_0039", "q_0054", "q_0059", "q_0063", "q_0064", "q_0068", "q_0069", "q_0093", "q_0098"])
        self.assertEqual(set(SOURCES.values()), {"public_demo_bundle"})

    def test_states_follow_contract_and_exclude_gold(self):
        states, skipped = battery.build_states(CONFIG, GOLD, ANNOTATIONS, TEXTS, SOURCES)
        self.assertEqual(len(states), 70)
        self.assertEqual(len(skipped) + len(states), len(ANNOTATIONS))
        for record in states:
            state = record["state"]
            self.assertEqual(sorted(state), sorted(CONFIG["state_contract"]["included_keys"]))
            serialized = json.dumps(state, ensure_ascii=False)
            gold = GOLD[record["question_id"]]
            self.assertNotIn(gold["gold_short_answer"], serialized)
            self.assertNotIn("share_numerator_label", serialized)
            for word in ('"label"', '"fact_type"', '"split"', "gold_reference"):
                self.assertNotIn(word, serialized)
            self.assertEqual(state["marked_answer"].count(battery.MARK_OPEN), 1)
            self.assertEqual(state["marked_answer"].replace(battery.MARK_OPEN, "").replace(battery.MARK_CLOSE, ""), state["answer"])
            self.assertEqual(state["evidence_rows"][0]["row_id"], "r1")

    def test_row_order_matches_generator_prompt(self):
        try:
            import build_prompts  # noqa: F401  (needs pandas)
        except ImportError:
            self.skipTest("pandas not installed; build_prompts cannot be imported")
        for record in GOLD.values():
            expected, _ = build_prompts.ordered_rows(record)
            self.assertEqual(battery.ordered_rows(record), expected)
            self.assertEqual(battery.metric_definitions(record), build_prompts.metric_definitions(record))
            notes = build_prompts.scope_notes(record) or ["No additional scope notes."]
            self.assertEqual(battery.scope_notes(record), notes)

    def test_dynamic_criteria_follow_table_shape(self):
        states, _ = battery.build_states(CONFIG, GOLD, ANNOTATIONS, TEXTS, SOURCES)
        for record in states:
            rows = len(record["state"]["evidence_rows"])
            questions = record["questions"]
            self.assertEqual(len(questions["source_row"]["criteria"]), rows + 1)
            self.assertIn("none", questions["source_row"]["criteria"])
            self.assertEqual(len(questions["rank_claim"]["criteria"]), rows + 1)
            self.assertIn("derived", questions["source_column"]["criteria"])
            self.assertIn("not_a_number", questions["source_column"]["criteria"])
            self.assertEqual(questions["status"]["criteria"].keys(), {"k7", "m2", "x9"})
            for spec in questions.values():
                self.assertNotIn("gold", json.dumps(spec).lower())

    def test_mismatched_offsets_are_rejected(self):
        row = dict(span(find("q_0064", "WOODEN UNION JACK BUNTING")))
        row["span_start_char"] += 1
        with self.assertRaises(ValueError):
            battery.build_state(GOLD["q_0064"], row, TEXTS["q_0064"])

    def test_forbidden_fragment_detected(self):
        row = span(find("q_0064", "WOODEN UNION JACK BUNTING"))
        state = battery.build_state(GOLD["q_0064"], row, TEXTS["q_0064"])
        state["scope_notes"] = state["scope_notes"] + [GOLD["q_0064"]["gold_short_answer"]]
        self.assertTrue(battery.check_state_contract(state, GOLD["q_0064"], row, CONFIG))


class CheckerTests(unittest.TestCase):
    def test_wrong_rank_with_correct_pair_is_selection_error(self):
        result = check(find("q_0064", "WOODEN UNION JACK BUNTING"))
        self.assertEqual((result["verdict"], result["mechanism"]), ("contradicted", "self_consistent_wrong_selection"))
        amount = check(find("q_0064", "GBP 4,173.18"))
        self.assertEqual((amount["verdict"], amount["mechanism"]), ("contradicted", "self_consistent_wrong_selection"))
        correct = check(find("q_0064", "GBP 14,280.90"))
        self.assertEqual((correct["verdict"], correct["mechanism"]), ("supported", "cell_copy"))

    def test_direction_and_subject_entity_reversed(self):
        direction = check(find("q_0039", "generated more net revenue"))
        self.assertEqual((direction["verdict"], direction["mechanism"]), ("contradicted", "direction_reversed"))
        subject = check(find("q_0039", "France", "country"))
        self.assertEqual((subject["verdict"], subject["mechanism"]), ("contradicted", "self_consistent_wrong_selection"))
        difference = check(find("q_0039", "5,586.83 GBP"))
        self.assertEqual(difference["mechanism"], "derived_value_matches")

    def test_magnitude_and_column_errors(self):
        self.assertEqual(check(find("q_0059", "145,614.50 GBP"))["mechanism"], "magnitude_digit_error")
        self.assertEqual(check(find("q_0098", "GBP 101,759.68"))["mechanism"], "magnitude_digit_error")
        reduction = check(find("q_0093", "£44,600.65", occurrence=0))
        net = check(find("q_0093", "£44,600.65", occurrence=1))
        self.assertEqual((reduction["verdict"], reduction["mechanism"]), ("supported", "cell_copy"))
        self.assertEqual((net["verdict"], net["mechanism"]), ("contradicted", "same_row_wrong_column"))

    def test_percentage_tolerance_and_period(self):
        within = check(find("q_0054", "-4.14%"))
        self.assertEqual(within["verdict"], "supported")
        outside = check(find("q_0059", "29.75%"))
        self.assertEqual((outside["verdict"], outside["mechanism"]), ("contradicted", "derived_value_mismatch"))
        month = check(find("q_0059", "November 2011"))
        self.assertEqual(month["mechanism"], "period_in_question")

    def test_business_conclusion_is_unparsed(self):
        conclusion = next(row for row in spans_for("q_0063") if row["fact_type"] == "unsupported_business_claim")
        self.assertEqual(check(conclusion["annotation_id"])["verdict"], "unparsed")

    def test_audit_reports_agreement_not_detection(self):
        results = battery.run_checker(CONFIG, GOLD, ANNOTATIONS, TEXTS)
        audit = battery.checker_audit(results, ANNOTATIONS)
        self.assertEqual(audit["span_count"], 70)
        self.assertEqual(audit["parsed_count"], 69)
        self.assertEqual(audit["agreement_on_parsed"]["point"], 1.0)
        self.assertIn("not detection", audit["note"])
        self.assertLessEqual(audit["coverage"]["upper_95"], 1.0)


def fake_response(label, model="jev-1.13.0", flip=False):
    supported = 0.2 if label else 0.9
    return {"model": model, "answers": {
        "supported": {"type": "noul", "noul": supported},
        "present": {"type": "noul", "noul": 0.8},
        "status": {"type": "choice", "choice": "m2" if label else "k7",
                   "probabilities": {"k7": 1 - supported, "m2": supported, "x9": 0.0}, "confidence": 0.5},
        "conclusion": {"type": "noul", "noul": 0.1},
        "relation": {"type": "choice", "choice": "entity_value" if not flip else "comparison", "probabilities": {}, "confidence": 0.4},
    }, "usage": {"input_tokens": 900, "output_tokens": 60}}


class RunnerTests(unittest.TestCase):
    def test_retry_then_success_and_401_abort(self):
        calls = []

        def flaky(url, payload, key):
            calls.append(url)
            if len(calls) == 1:
                raise urllib.error.HTTPError(url, 429, "slow down", {}, io.BytesIO(b"{}"))
            return 200, {"model": "jev-1.13.0", "answers": {}}

        sleeps = []
        outcome = battery.call_with_retry({"state": "x"}, CONFIG, "key", sender=flaky, sleeper=sleeps.append)
        self.assertEqual((outcome["status"], outcome["attempts"], sleeps), (200, 2, [2]))

        def unauthorized(url, payload, key):
            raise urllib.error.HTTPError(url, 401, "no", {}, io.BytesIO(b"{}"))

        with self.assertRaises(SystemExit):
            battery.call_with_retry({"state": "x"}, CONFIG, "bad", sender=unauthorized, sleeper=sleeps.append)

    def test_cache_skips_completed_repeats(self):
        states, _ = battery.build_states(CONFIG, GOLD, ANNOTATIONS, TEXTS, SOURCES)
        states = states[:2]
        sent = []

        def sender(url, payload, key):
            sent.append(payload["state"]["marked_text"])
            self.assertEqual(payload["model"], CONFIG["api"]["model"])
            self.assertNotIn("gold", json.dumps(payload).lower())
            return 200, fake_response(0)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "responses.jsonl"
            first = battery.run_battery(states, CONFIG, "key", 2, path, sender=sender, sleeper=lambda s: None, log=lambda *a: None)
            second = battery.run_battery(states, CONFIG, "key", 2, path, sender=sender, sleeper=lambda s: None, log=lambda *a: None)
            self.assertEqual((first["completed"], second["completed"], len(sent)), (4, 0, 4))
            rows = battery.read_jsonl(path)
            self.assertEqual(len(rows), 4)
            self.assertEqual(len({row["cache_key"] for row in rows}), 4)
            self.assertEqual(len({row["request_sha256"] for row in rows}), 2)


class ScoreTests(unittest.TestCase):
    def test_aggregation_means_and_flip_rates(self):
        rows = [{"annotation_id": "a", "status": 200, "response": fake_response(1)},
                {"annotation_id": "a", "status": 200, "response": fake_response(1, flip=True)},
                {"annotation_id": "b", "status": 422, "response": {"error": "bad"}}]
        aggregated = battery.aggregate_responses(rows)
        self.assertEqual(set(aggregated), {"a"})
        self.assertAlmostEqual(aggregated["a"]["jev_risk"], 0.8)
        self.assertEqual(aggregated["a"]["repeats"], 2)
        self.assertEqual(aggregated["a"]["choice_flip_rate"]["relation_choice"], 0.5)

    def test_end_to_end_score_flags_model_drift(self):
        states, _ = battery.build_states(CONFIG, GOLD, ANNOTATIONS, TEXTS, SOURCES)
        labels = {row["annotation_id"]: row["binary_label"] for row in ANNOTATIONS}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "responses.jsonl"
            with path.open("w", encoding="utf-8") as handle:
                for index, record in enumerate(states):
                    model = "jev-1.14.0" if index == 0 else "jev-1.13.0"
                    row = {"annotation_id": record["annotation_id"], "question_id": record["question_id"], "repeat": 0,
                           "cache_key": str(index), "request_sha256": str(index), "status": 200, "attempts": 1,
                           "elapsed_seconds": 0.1, "response": fake_response(labels[record["annotation_id"]], model=model)}
                    handle.write(json.dumps(row) + "\n")
            checker = battery.run_checker(CONFIG, GOLD, ANNOTATIONS, TEXTS)
            signals = battery.load_stored_signals()
            report, rows = battery.score_battery(CONFIG, GOLD, ANNOTATIONS, path, checker, signals, replicates=50, seed=1)
        self.assertEqual(len(rows), 70)
        self.assertEqual(report["unexpected_model_versions"], ["jev-1.14.0"])
        self.assertIn("jev_risk", report["evaluation"]["arms"])
        self.assertIn("one_minus_min_top2_margin", report["evaluation"]["arms"])
        self.assertEqual(report["evaluation"]["arms"]["jev_risk"]["test"]["average_precision"], 1.0)
        self.assertEqual(report["paired_intervals"]["cluster_field"], "question_id")
        self.assertIn("self_consistent_wrong_selection", report["mechanisms"])
        markdown = battery.render_markdown(report)
        self.assertIn("not an independent detector", markdown)


class ValidateTests(unittest.TestCase):
    def test_validate_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = battery.validate(output_dir=Path(tmp))
            self.assertEqual(result["num_failures"], 0, result["failures"])
            self.assertEqual(result["states_built"], 70)
            self.assertTrue((Path(tmp) / "validation.json").exists())


if __name__ == "__main__":
    unittest.main()
