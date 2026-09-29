import contextlib
import csv
import hashlib
import io
import json
import math
import re
import sys
import tempfile
import unittest
import urllib.error
from collections import Counter
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bizhallu import decision_battery as battery  # noqa: E402
from bizhallu import evidence  # noqa: E402
from bizhallu import rule_checker as checker  # noqa: E402
from bizhallu import span_signals  # noqa: E402

CONFIG = battery.load_config()
GOLD = battery.load_gold()
ANNOTATIONS = battery.load_annotations()
SPANS = battery.load_spans()
LABELS = battery.load_labels([battery.ANNOTATIONS_PATH], "ai_provisional", CONFIG)
TEXTS, SOURCES = battery.load_generated_texts(None)
TOLERANCE = CONFIG["checker_policy"]["currency_tolerance"]
PCT_TOL = CONFIG["checker_policy"]["percentage_tolerance_points"]


def span(annotation_id):
    return next(row for row in ANNOTATIONS if row["annotation_id"] == annotation_id)


def spans_for(question_id):
    return [row for row in ANNOTATIONS if row["question_id"] == question_id]


def check(annotation_id):
    row = span(annotation_id)
    return checker.check_span(GOLD[row["question_id"]], row, TEXTS[row["question_id"]], TOLERANCE, PCT_TOL)


def find(question_id, text, fact_type=None, occurrence=0):
    hits = [row for row in spans_for(question_id) if row["span_text"] == text and (fact_type is None or row["fact_type"] == fact_type)]
    return hits[occurrence]["annotation_id"]


def import_build_prompts():
    """Import src/build_prompts.py; without pandas, use a placeholder module only for the import."""
    import types
    try:
        import build_prompts
        return build_prompts
    except ImportError:
        pass
    placeholder = types.ModuleType("pandas")
    sys.modules["pandas"] = placeholder
    try:
        import build_prompts
    finally:
        if sys.modules.get("pandas") is placeholder:
            del sys.modules["pandas"]
    return build_prompts


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
        build_prompts = import_build_prompts()
        self.assertEqual(evidence.DISPLAY_COLUMNS, build_prompts.DISPLAY_COLUMNS)
        for record in GOLD.values():
            expected, _ = build_prompts.ordered_rows(record)
            self.assertEqual(evidence.ordered_rows(record), expected)
            self.assertEqual(evidence.metric_definitions(record), build_prompts.metric_definitions(record))
            notes = build_prompts.scope_notes(record) or ["No additional scope notes."]
            self.assertEqual(evidence.scope_notes(record), notes)
            for row in expected:
                for column, value in row.items():
                    self.assertEqual(evidence.format_value(value, column), build_prompts.format_value(value, column))

    def test_dynamic_criteria_follow_table_shape(self):
        states, _ = battery.build_states(CONFIG, GOLD, ANNOTATIONS, TEXTS, SOURCES)
        for record in states:
            evidence_rows = record["state"]["evidence_rows"]
            rows = len(evidence_rows)
            questions = record["questions"]
            self.assertEqual(sorted(questions), sorted(CONFIG["questions"]))
            self.assertEqual(list(questions["source_row"]["criteria"]),
                             [row["row_id"] for row in evidence_rows] + ["n0"])
            self.assertEqual(list(questions["rank_claim"]["criteria"]),
                             [f"p{i}" for i in range(1, rows + 1)] + ["p0"])
            numeric = [c for c in evidence_rows[0] if c in battery.NUMERIC_DISPLAY_COLUMNS]
            self.assertEqual(list(questions["source_column"]["criteria"]),
                             [f"c{i}" for i in range(1, len(numeric) + 1)] + ["d1", "d2", "d3"])
            self.assertEqual(questions["source_column"]["criteria"]["c1"], f"Column {numeric[0]}.")
            self.assertEqual(questions["status"]["criteria"].keys(), {"k7", "m2", "x9"})
            self.assertEqual(questions["value_faithful"]["criteria"].keys(), {"f1", "f2", "f3", "f4"})
            for spec in questions.values():
                self.assertNotIn("gold", json.dumps(spec).lower())
            self.assertEqual(record["role"], GOLD[record["question_id"]]["split"])

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
        results = checker.run_checker(CONFIG, GOLD, SPANS, TEXTS)
        audit = checker.checker_audit(results, battery.binary_labels(LABELS))
        self.assertEqual(audit["span_count"], 70)
        self.assertEqual(audit["unlabelled_skipped"], 0)
        self.assertEqual(audit["parsed_count"], 69)
        self.assertEqual(audit["agreement_on_parsed"]["point"], 1.0)
        self.assertIn("not detection", audit["note"])
        self.assertLessEqual(audit["coverage"]["upper_95"], 1.0)


def fake_response(label, model="jev-1.13.0", flip=False):
    risk = 0.8 if label else 0.1
    return {"model": model, "answers": {
        "slot_correct": {"type": "noul", "noul": 1 - risk},
        "status": {"type": "choice", "choice": "m2" if label else "k7",
                   "probabilities": {"k7": 1 - risk, "m2": risk, "x9": 0.0}, "confidence": 0.5},
        "value_faithful": {"type": "choice", "choice": "f1",
                           "probabilities": {"f1": 0.7, "f2": 0.2, "f3": 0.1, "f4": 0.0}, "confidence": 0.7},
        "relation": {"type": "choice", "choice": "t1" if not flip else "t3", "probabilities": {}, "confidence": 0.4},
    }, "usage": {"input_tokens": 900, "output_tokens": 60}}


HOSTED_ARM = {"arm_id": "hosted_test", "kind": "hosted", "endpoint": "https://api.typesafe.ai/v1/systemone",
              "allowed_hosts": ["api.typesafe.ai"], "model": "jev-1.13.0", "auth_env": "TEST_DM_KEY",
              "repeats": {"dev": 1, "eval": 1}}
LOCAL_ARM = {"arm_id": "local_test", "kind": "local", "endpoint": "http://127.0.0.1:8791/v1/systemone",
             "allowed_hosts": ["127.0.0.1", "localhost", "::1"], "model": "open-jev-2b", "auth_env": None,
             "repeats": {"dev": 1, "eval": 1}}


def http_error(code, body=b"{}", headers=None):
    return urllib.error.HTTPError("https://api.typesafe.ai/v1/systemone", code, "error", headers or {}, io.BytesIO(body))


def full_response(questions, yes=0.9, model="jev-1.13.0"):
    """A usable response: every question answered, probabilities for every option."""
    answers = {}
    for key, spec in questions.items():
        if spec["type"] == "noul":
            answers[key] = {"type": "noul", "noul": yes}
        else:
            options = list(spec.get("criteria") or {"a": ""})
            share = 1.0 / len(options)
            answers[key] = {"type": spec["type"], "choice": options[0],
                            "probabilities": {option: share for option in options}, "confidence": share}
    return {"model": model, "answers": answers}


class RunnerTests(unittest.TestCase):
    """Runner hardening of plan T1.5; every test is offline with an injected sender."""

    def setUp(self):
        self.policy = battery.api_policy()
        self.sleeps = []

    def call(self, sender, key="k"):
        return battery.call_with_retry({"state": "x"}, HOSTED_ARM["endpoint"], key, policy=self.policy,
                                       sender=sender, sleeper=self.sleeps.append)

    def test_success(self):
        outcome = self.call(lambda url, payload, key: (200, {"answers": {}}))
        self.assertEqual((outcome["status"], outcome["attempts"], self.sleeps), (200, 1, []))

    def test_401_and_403_stop_the_run(self):
        for code in (401, 403):
            def refuse(url, payload, key, code=code):
                raise http_error(code)
            with self.assertRaises(SystemExit):
                self.call(refuse)

    def test_422_is_not_retried(self):
        def invalid(url, payload, key):
            raise http_error(422)
        outcome = self.call(invalid)
        self.assertEqual((outcome["status"], outcome["attempts"], self.sleeps), (422, 1, []))

    def test_429_then_200_uses_backoff(self):
        calls = []

        def flaky(url, payload, key):
            calls.append(1)
            if len(calls) == 1:
                raise http_error(429)
            return 200, {"answers": {}}
        outcome = self.call(flaky)
        self.assertEqual((outcome["status"], outcome["attempts"], self.sleeps), (200, 2, [2]))

    def test_retry_after_header_is_respected_and_capped(self):
        calls = []

        def slow(url, payload, key):
            calls.append(1)
            if len(calls) == 1:
                raise http_error(429, headers={"Retry-After": "10"})
            if len(calls) == 2:
                raise http_error(429, headers={"Retry-After": "9999"})
            return 200, {"answers": {}}
        self.call(slow)
        self.assertEqual(self.sleeps, [10.0, 300.0])

    def test_529_exhausted_and_500_retried(self):
        for code in (529, 500):
            self.sleeps.clear()

            def busy(url, payload, key, code=code):
                raise http_error(code)
            outcome = self.call(busy)
            self.assertEqual((outcome["status"], outcome["attempts"]), (code, self.policy["max_attempts"]))
            self.assertEqual(len(self.sleeps), self.policy["max_attempts"] - 1)

    def test_timeout_and_non_json_are_retried_then_recorded(self):
        for error in (TimeoutError("read timed out"), json.JSONDecodeError("bad", "doc", 0)):
            self.sleeps.clear()

            def broken(url, payload, key, error=error):
                raise error
            outcome = self.call(broken)
            self.assertIsNone(outcome["status"])
            self.assertEqual(outcome["attempts"], self.policy["max_attempts"])

    def test_key_is_redacted_from_error_bodies(self):
        def echo(url, payload, key):
            raise http_error(422, body=f"invalid key {key}".encode("utf-8"))
        outcome = self.call(echo, key="sk-secret-123")
        self.assertNotIn("sk-secret-123", json.dumps(outcome))
        self.assertIn("[REDACTED]", outcome["body"]["error"])

    def test_local_arm_sends_no_authorization_header(self):
        request = battery.build_request(LOCAL_ARM["endpoint"], {"a": 1}, None, "ua/1")
        self.assertNotIn("Authorization", request.headers)
        self.assertEqual(request.get_header("User-agent"), "ua/1")
        self.assertIsNone(battery.read_api_key(LOCAL_ARM, environ={}))
        request = battery.build_request(HOSTED_ARM["endpoint"], {"a": 1}, "k", "ua/1")
        self.assertEqual(request.get_header("Authorization"), "Bearer k")

    def test_endpoint_rules(self):
        battery.check_arm_endpoint(HOSTED_ARM)
        battery.check_arm_endpoint(LOCAL_ARM)
        for bad in ({**HOSTED_ARM, "endpoint": "http://api.typesafe.ai/v1/systemone"},
                    {**HOSTED_ARM, "endpoint": "https://example.com/v1/systemone"},
                    {**LOCAL_ARM, "endpoint": "http://10.0.0.5:8791/v1/systemone"},
                    {**LOCAL_ARM, "endpoint": None}):
            with self.assertRaises(SystemExit):
                battery.check_arm_endpoint(bad)

    def test_key_handling(self):
        self.assertEqual(battery.read_api_key(HOSTED_ARM, environ={"TEST_DM_KEY": "abc\n"}), "abc")
        for value in ("", "a b", "a\tb"):
            with self.assertRaises(SystemExit) as caught:
                battery.read_api_key(HOSTED_ARM, environ={"TEST_DM_KEY": value})
            self.assertNotIn("a b", str(caught.exception))

    def _states(self, count=2):
        states, _ = battery.build_states(CONFIG, GOLD, ANNOTATIONS, TEXTS, SOURCES)
        return [state for state in states if state["role"] == "dev"][:count]

    def test_rerun_resends_only_failed_or_unusable_calls(self):
        states = self._states()
        sent = []

        def first_pass(url, payload, key):
            sent.append(payload["state"]["marked_text"])
            if len(sent) == 1:
                return 200, {"model": "jev-1.13.0"}
            if len(sent) == 2:
                raise http_error(422)
            return 200, full_response(payload["questions"])

        def second_pass(url, payload, key):
            sent.append(payload["state"]["marked_text"])
            self.assertNotIn("gold", json.dumps(payload).lower())
            return 200, full_response(payload["questions"])

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "responses.jsonl"
            first = battery.run_battery(states, HOSTED_ARM, "k", 2, path, policy=self.policy, sender=first_pass,
                                        sleeper=lambda s: None, log=lambda *a: None)
            self.assertEqual((first["completed"], first["failed"]), (2, 2))
            self.assertEqual(first["spans_without_success"], [states[0]["annotation_id"]])
            second = battery.run_battery(states, HOSTED_ARM, "k", 2, path, policy=self.policy, sender=second_pass,
                                         sleeper=lambda s: None, log=lambda *a: None)
            self.assertEqual((second["completed"], second["failed"], second["cached_success_before_run"]), (2, 0, 2))
            self.assertEqual(len(sent), 6)
            third = battery.run_battery(states, HOSTED_ARM, "k", 2, path, policy=self.policy, sender=second_pass,
                                        sleeper=lambda s: None, log=lambda *a: None)
            self.assertEqual((third["completed"], third["cached_success_before_run"], len(sent)), (0, 4, 6))

    def test_consecutive_failures_stop_the_run(self):
        states = self._states(3)

        def always_fails(url, payload, key):
            raise http_error(422)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "responses.jsonl"
            with self.assertRaises(SystemExit):
                battery.run_battery(states, HOSTED_ARM, "k", 2, path, policy=self.policy, sender=always_fails,
                                    sleeper=lambda s: None, log=lambda *a: None)
            self.assertEqual(len(battery.read_jsonl(path)), self.policy["consecutive_failure_limit"])

    def test_truncated_last_line_is_skipped(self):
        messages = []
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "responses.jsonl"
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps({"cache_key": "a", "status": 200}) + "\n")
                handle.write('{"cache_key": "b", "sta')
            rows = battery.read_response_rows(path, log=messages.append)
        self.assertEqual([row["cache_key"] for row in rows], ["a"])
        self.assertTrue(messages)

    def test_smoke_reports_orientation_sums_and_determinism(self):
        v2 = battery.load_config(battery.V2_CONFIG_PATH)

        def answering(url, payload, key):
            wrong = "9,999.00" in payload["state"]["marked_text"]
            return 200, full_response(payload["questions"], yes=0.1 if wrong else 0.9)

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "local_test" / "smoke.json"
            report = battery.run_smoke(v2, LOCAL_ARM, None, out, policy=self.policy, sender=answering,
                                       sleeper=lambda s: None, log=lambda *a: None)
            self.assertTrue(out.exists())
        self.assertEqual(report["problems"], [])
        self.assertTrue(report["deterministic"])
        self.assertEqual(report["controls"]["control_correct"]["slot_correct_yes"], [0.9, 0.9, 0.9])

        def backwards(url, payload, key):
            wrong = "9,999.00" in payload["state"]["marked_text"]
            return 200, full_response(payload["questions"], yes=0.9 if wrong else 0.1)

        with tempfile.TemporaryDirectory() as tmp:
            report = battery.run_smoke(v2, LOCAL_ARM, None, Path(tmp) / "smoke.json", policy=self.policy,
                                       sender=backwards, sleeper=lambda s: None, log=lambda *a: None)
        self.assertEqual(len(report["problems"]), 2)


class ScoreTests(unittest.TestCase):
    def test_aggregation_means_and_flip_rates(self):
        rows = [{"annotation_id": "a", "status": 200, "response": fake_response(1)},
                {"annotation_id": "a", "status": 200, "response": fake_response(1, flip=True)},
                {"annotation_id": "b", "status": 422, "response": {"error": "bad"}}]
        aggregated = battery.aggregate_responses(rows, CONFIG)
        self.assertEqual(set(aggregated), {"a"})
        self.assertAlmostEqual(aggregated["a"]["dm_risk"], 0.8)
        self.assertAlmostEqual(aggregated["a"]["dm_unfaithful"], 0.2)
        self.assertAlmostEqual(aggregated["a"]["dm_conflict_or_undetermined"], 0.8)
        self.assertEqual(aggregated["a"]["repeats"], 2)
        self.assertEqual(aggregated["a"]["choice_flip_rate"]["relation_choice"], 0.5)
        self.assertIn("status_choice", aggregated["a"]["choice_flip_rate"])

    def test_formula_rules(self):
        answer = {"noul": 0.25, "probabilities": {"m2": 0.5, "x9": 0.1}}
        self.assertAlmostEqual(battery.evaluate_formula("1 - noul", answer), 0.75)
        self.assertAlmostEqual(battery.evaluate_formula("probabilities.m2 + probabilities.x9", answer), 0.6)
        with self.assertRaises(ValueError):
            battery.evaluate_formula("probabilities.m2 * 2", answer)
        with self.assertRaises(KeyError):
            battery.evaluate_formula("probabilities.k7", answer)

    def _rows_for(self, states, arm, labels, model_for=lambda index: "jev-1.13.0"):
        expected = battery.expected_request_hashes(states, arm)
        rows = []
        for index, record in enumerate(states):
            rows.append({"annotation_id": record["annotation_id"], "question_id": record["question_id"], "repeat": 0,
                         "cache_key": str(index), "request_sha256": expected[record["annotation_id"]], "status": 200,
                         "response": fake_response(labels[record["annotation_id"]], model=model_for(index))})
        return rows

    def test_end_to_end_score_flags_model_drift(self):
        states, _ = battery.build_states(CONFIG, GOLD, ANNOTATIONS, TEXTS, SOURCES)
        labels = {row["annotation_id"]: row["binary_label"] for row in ANNOTATIONS}
        arm = {**LOCAL_ARM, "arm_id": "local_open_jev_2b", "model": "jev-1.13.0"}
        rows = self._rows_for(states, arm, labels, lambda index: "jev-1.14.0" if index == 0 else "jev-1.13.0")
        kept, excluded = battery.select_scored_rows(rows, battery.expected_request_hashes(states, arm))
        self.assertEqual((len(kept), excluded), (70, 0))
        aggregated = battery.aggregate_responses(kept, CONFIG)
        spans = [span for span in SPANS if span["question_id"] in TEXTS]
        score_rows, _, _ = battery.assemble_rows(CONFIG, GOLD, spans, LABELS, TEXTS, SOURCES, None,
                                                      {"local_open_jev_2b": aggregated}, frozenset(), legacy=True)
        report, scored = battery.build_report(CONFIG, score_rows, {"local_open_jev_2b": arm},
                                              {"local_open_jev_2b": aggregated}, "ai_provisional", [], LABELS,
                                              "stored", set(), 50, 1)
        self.assertEqual(len(scored), 70)
        test_all = report["roles"]["test"]["sets"]["all spans"]
        for name in ("dev_span_kind_prior", "dev_question_type_prior", "dev_fact_type_prior", "one_minus_min_top2_margin"):
            self.assertIn(name, test_all["arms"])
        self.assertEqual(test_all["arms"]["dm_risk@local_open_jev_2b"]["average_precision"]["point"], 1.0)
        self.assertIn("lower_95", test_all["primary_contrast"]["average_precision"])
        self.assertEqual(test_all["primary_contrast"]["cluster"], "question_id")
        self.assertEqual(test_all["primary_contrast_sensitivity"]["cluster"], "evidence_cluster")
        self.assertEqual(report["dm_arms"]["local_open_jev_2b"]["unexpected_model_versions"], ["jev-1.14.0"])
        self.assertIn("self_consistent_wrong_selection", report["mechanism_tables"]["test"]["rows"])
        self.assertGreater(report["interval_count"], 0)
        markdown = battery.scoring.render_report(report)
        self.assertIn("label-consistency audit", markdown)
        self.assertIn("jev-1.14.0", markdown)
        self.assertNotIn("PRE-FREEZE", markdown)

    def test_rows_from_another_wording_or_arm_are_excluded(self):
        states, _ = battery.build_states(CONFIG, GOLD, ANNOTATIONS, TEXTS, SOURCES)
        labels = {row["annotation_id"]: row["binary_label"] for row in ANNOTATIONS}
        current = self._rows_for(states, HOSTED_ARM, labels)
        other_wording = json.loads(json.dumps(CONFIG))
        other_wording["questions"]["slot_correct"]["instructions"] += " Revised."
        old_states, _ = battery.build_states(other_wording, GOLD, ANNOTATIONS, TEXTS, SOURCES)
        stale = self._rows_for(old_states, HOSTED_ARM, labels)
        other_arm = self._rows_for(states, LOCAL_ARM, labels)
        kept, excluded = battery.select_scored_rows(current + stale + other_arm,
                                                    battery.expected_request_hashes(states, HOSTED_ARM))
        self.assertEqual((len(kept), excluded), (70, 140))

    def test_repeat_shortfall_is_reported(self):
        states = [{"annotation_id": "a", "role": "dev"}, {"annotation_id": "b", "role": "test"}]
        arm = {**HOSTED_ARM, "repeats": {"dev": 5, "eval": 1}}
        aggregated = {"a": {"repeats": 3}, "b": {"repeats": 1}}
        self.assertEqual(battery.repeat_shortfalls(aggregated, states, arm), ["a"])

    def test_endpoint_change_triggers_new_calls(self):
        states, _ = battery.build_states(CONFIG, GOLD, ANNOTATIONS, TEXTS, SOURCES)
        states = [state for state in states if state["role"] == "dev"][:1]
        sent = []

        def sender(url, payload, key):
            sent.append(url)
            return 200, full_response(payload["questions"])

        moved = {**LOCAL_ARM, "endpoint": "http://localhost:8791/v1/systemone"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "responses.jsonl"
            for arm in (LOCAL_ARM, LOCAL_ARM, moved):
                battery.run_battery(states, arm, None, 1, path, sender=sender, sleeper=lambda s: None,
                                    log=lambda *a: None, provenance={"battery_id": "b", "config_sha256": "c"})
            rows = battery.read_jsonl(path)
        self.assertEqual(sent, [LOCAL_ARM["endpoint"], moved["endpoint"]])
        for field in ("battery_id", "config_sha256", "arm_id", "endpoint", "requested_model", "called_at_utc", "role"):
            self.assertIn(field, rows[0])
        self.assertNotEqual(rows[0]["request_sha256"], rows[1]["request_sha256"])


class StatesFileTests(unittest.TestCase):
    """states files and their manifest (plan T1.6 items 4 to 6); synthetic files only."""

    def test_manifest_detects_a_changed_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_copy = root / "config.json"
            arms_copy = root / "arms.json"
            spans = root / "spans_full100_v1.jsonl"
            generations = root / "generations.jsonl"
            for source, target in ((battery.CONFIG_PATH, config_copy), (battery.ARMS_CONFIG_PATH, arms_copy)):
                target.write_bytes(Path(source).read_bytes())
            spans.write_text("{}\n", encoding="utf-8")
            generations.write_text("{}\n", encoding="utf-8")
            states = [{"annotation_id": "x", "role": "dev", "state": {}, "questions": {}}]
            self.assertEqual(battery.span_set_id_for(spans), "full100_205")
            battery.write_states(states, "full100_205", config_copy, arms_copy, spans, generations, root=root)
            loaded, manifest = battery.load_states("full100_205", config_copy, arms_copy, spans, generations, root=root)
            self.assertEqual(loaded, states)
            self.assertEqual(manifest["roles"], {"dev": 1})
            config_copy.write_text(config_copy.read_text(encoding="utf-8").replace("draft_wording", "draft-wording"),
                                   encoding="utf-8")
            with self.assertRaises(SystemExit) as caught:
                battery.load_states("full100_205", config_copy, arms_copy, spans, generations, root=root)
            self.assertIn("config", str(caught.exception))

    def test_unknown_span_file_name_is_refused(self):
        with self.assertRaises(SystemExit):
            battery.span_set_id_for("my_spans.jsonl")

    def test_line_endings_do_not_change_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            lf = Path(tmp) / "lf.txt"
            crlf = Path(tmp) / "crlf.txt"
            lf.write_bytes(b"a\nb\n")
            crlf.write_bytes(b"a\r\nb\r\n")
            self.assertEqual(battery.file_sha256(lf), battery.file_sha256(crlf))


class ValidateTests(unittest.TestCase):
    def test_validate_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = battery.validate(output_dir=Path(tmp))
            self.assertEqual(result["num_failures"], 0, result["failures"])
            self.assertEqual(result["states_built"], 70)
            self.assertEqual(result["span_kinds"]["month"], 37)
            self.assertEqual(result["test_non_month_spans"], 85)
            self.assertTrue((Path(tmp) / "validation.json").exists())


V2_CONFIG = battery.load_config(battery.V2_CONFIG_PATH)


def synthetic_state(record):
    answer = "The answer is X."
    row = {"annotation_id": "synthetic", "span_start_char": 14, "span_end_char": 15, "span_text": "X"}
    return battery.build_state(record, row, answer), row


class ContractRewriteTests(unittest.TestCase):
    """Contract check of plan T1.4: no false positives on 100 records, real leaks caught."""

    def test_all_gold_records_pass_with_both_question_payloads(self):
        for qid, record in GOLD.items():
            state, row = synthetic_state(record)
            for config in (CONFIG, V2_CONFIG):
                questions = battery.build_questions(config, state)
                problems = battery.check_state_contract(state, record, row, questions=questions)
                self.assertEqual(problems, [], qid)

    def _problems(self, qid, mutate, questions=None):
        record = GOLD[qid]
        state, row = synthetic_state(record)
        state = json.loads(json.dumps(state))
        mutate(state)
        return battery.check_state_contract(state, record, row, questions=questions or {})

    def test_rank_column_is_caught(self):
        def mutate(state):
            for index, row in enumerate(state["evidence_rows"], start=1):
                row["rank"] = str(index)
        self.assertTrue(self._problems("q_0064", mutate))

    def test_neutral_named_rank_column_is_caught(self):
        def mutate(state):
            for index, row in enumerate(state["evidence_rows"], start=1):
                row["c9"] = str(index)
        self.assertTrue(self._problems("q_0064", mutate))

    def test_gold_answer_dict_is_caught(self):
        def mutate(state):
            state["gold_answer"] = GOLD["q_0064"]["gold_answer"]
        self.assertTrue(self._problems("q_0064", mutate))

    def test_gold_short_answer_in_scope_notes_is_caught(self):
        def mutate(state):
            state["scope_notes"].append(GOLD["q_0064"]["gold_short_answer"])
        problems = self._problems("q_0064", mutate)
        self.assertTrue(any("forbidden fragment" in p for p in problems), problems)

    def test_annotation_reason_in_definitions_is_caught(self):
        row = next(r for r in ANNOTATIONS if r["question_id"] == "q_0064" and r.get("reason"))
        record = GOLD["q_0064"]
        state, synthetic = synthetic_state(record)
        state["metric_definitions"].append(row["reason"])
        problems = battery.check_state_contract(state, record, synthetic, label_row=row)
        self.assertTrue(any("forbidden fragment" in p for p in problems), problems)

    def test_non_string_cell_is_caught(self):
        def mutate(state):
            state["evidence_rows"][0]["net_revenue_gbp"] = 14280.9
        problems = self._problems("q_0064", mutate)
        self.assertTrue(any("not a string" in p for p in problems), problems)

    def test_label_in_question_payload_is_caught(self):
        questions = {"extra": {"type": "noul", "instructions": "Known answer: hallucinated_key_fact."}}
        problems = self._problems("q_0064", lambda state: None, questions)
        self.assertTrue(any("forbidden label string" in p for p in problems), problems)

    def test_key_containing_gold_is_caught(self):
        def mutate(state):
            state["evidence_rows"][0]["gold_rank"] = "1"
        problems = self._problems("q_0064", mutate)
        self.assertTrue(any("forbidden key" in p for p in problems), problems)

    def test_gold_number_not_shown_to_generator_is_caught(self):
        change = GOLD["q_0053"]["gold_answer"]["absolute_change"]
        questions = {"extra": {"type": "noul", "instructions": f"Hint: GBP {change:,.2f}."}}
        problems = self._problems("q_0053", lambda state: None, questions)
        self.assertTrue(any("gold number" in p for p in problems), problems)

    def test_question_must_equal_gold_question(self):
        def mutate(state):
            state["question"] = state["question"] + " Answer: top product."
        problems = self._problems("q_0064", mutate)
        self.assertTrue(any("question differs" in p for p in problems), problems)

    def test_share_label_in_question_is_not_a_false_positive(self):
        record = GOLD["q_0086"]
        state, row = synthetic_state(record)
        self.assertIn("the top 3 products", state["question"].lower())
        self.assertEqual(battery.check_state_contract(state, record, row), [])

    def test_local_package_builds_205_states(self):
        if not battery.DEFAULT_GENERATIONS.exists():
            self.skipTest("local generation file not present")
        texts, sources = battery.load_generated_texts(battery.DEFAULT_GENERATIONS, log=lambda m: None)
        states, skipped = battery.build_states(CONFIG, GOLD, ANNOTATIONS, texts, sources)
        self.assertEqual((len(states), len(skipped)), (205, 0))


def render_state_table(rows):
    """Markdown table from state evidence rows, in the layout of src/build_prompts.markdown_table."""
    columns = [column for column in rows[0] if column != "row_id"]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row[column] for column in columns) + " |")
    return "\n".join(lines)


class EvidenceCellTests(unittest.TestCase):
    """State evidence cells are the generator's prompt cells (plan T1.3)."""

    MONEY = re.compile(r"^-?[0-9]+[.][0-9]{2}$")

    def test_every_cell_is_a_prompt_formatted_string(self):
        for record in GOLD.values():
            rows = evidence.evidence_rows_for_state(record)
            for row in rows:
                for column, value in row.items():
                    self.assertIsInstance(value, str, (record["question_id"], column))
                    if column in ("net_revenue_gbp", "gross_positive_revenue_gbp", "cancellation_return_revenue_gbp"):
                        self.assertRegex(value, self.MONEY)

    def test_public_demo_row_order(self):
        with open(battery.DEMO_PATH, encoding="utf-8") as handle:
            demo = json.load(handle)
        for case in demo["cases"]:
            record = GOLD[case["question_id"]]
            keys = list(case["prompt_evidence_rows"][0])
            projected = [{key: row[key] for key in keys} for row in evidence.ordered_rows(record)]
            self.assertEqual(projected, case["prompt_evidence_rows"], case["question_id"])

    def test_unknown_question_type_is_rejected(self):
        record = {"question_id": "q_9999", "question_type": "new_type", "evidence": {"rows": []}}
        with self.assertRaises(ValueError):
            evidence.ordered_rows(record)

    def test_tables_match_stored_prompts_byte_for_byte(self):
        prompts_path = battery.PROJECT_ROOT / "outputs" / "qwen_input_prompts.jsonl"
        if not prompts_path.exists():
            self.skipTest("local prompt file not present")
        compared = 0
        for prompt in battery.read_jsonl(prompts_path):
            record = GOLD[prompt["question_id"]]
            table = render_state_table(evidence.evidence_rows_for_state(record))
            self.assertEqual(table, prompt["evidence_table_markdown"], prompt["question_id"])
            compared += 1
        self.assertEqual(compared, 100)


class GuardedLoaderTests(unittest.TestCase):
    """Held-out answers and traces are dropped on read (plan T1.2, red line R8)."""

    def _write_jsonl(self, path, records):
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")

    def test_generations_and_traces_drop_heldout_ids(self):
        messages = []
        with tempfile.TemporaryDirectory() as tmp:
            gen = Path(tmp) / "gen.jsonl"
            traces = Path(tmp) / "traces.jsonl"
            self._write_jsonl(gen, [{"question_id": "q_9001", "generated_text": "a"},
                                    {"question_id": "q_9002", "generated_text": "b"}])
            self._write_jsonl(traces, [{"question_id": "q_9001", "token_traces": []},
                                       {"question_id": "q_9002", "token_traces": []}])
            kept = battery.load_generations(gen, frozenset({"q_9002"}), log=messages.append)
            self.assertEqual([r["question_id"] for r in kept], ["q_9001"])
            kept = battery.load_traces(traces, frozenset({"q_9002"}), log=messages.append)
            self.assertEqual([r["question_id"] for r in kept], ["q_9001"])
        self.assertTrue(all("dropped 1 held-out" in m for m in messages), messages)

    def test_generated_texts_drop_heldout_ids_from_both_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen = Path(tmp) / "gen.jsonl"
            demo = Path(tmp) / "demo.json"
            self._write_jsonl(gen, [{"question_id": "q_9001", "generated_text": "a"},
                                    {"question_id": "q_9002", "generated_text": "b"}])
            demo.write_text(json.dumps({"cases": [{"question_id": "q_9003", "generated_text": "c"},
                                                  {"question_id": "q_9004", "generated_text": "d"}]}),
                            encoding="utf-8")
            texts, sources = battery.load_generated_texts(gen, demo, frozenset({"q_9002", "q_9004"}),
                                                          log=lambda m: None)
        self.assertEqual(sorted(texts), ["q_9001", "q_9003"])
        self.assertEqual(sources["q_9003"], "public_demo_bundle")

    def test_heldout_slice_file(self):
        with open(battery.HELDOUT_SLICE_PATH, encoding="utf-8") as handle:
            slice_cfg = json.load(handle)
        ids = slice_cfg["heldout_question_ids"]
        self.assertEqual(len(ids), 44)
        self.assertEqual(ids, sorted(ids))
        digest = hashlib.sha256(json.dumps(ids, separators=(",", ":")).encode("utf-8")).hexdigest()
        self.assertEqual(digest, slice_cfg["sha256"])
        self.assertEqual(digest, "26094d674ed7c170f2c92b67aeb3f984cb089b3afc0e613ca6e5f10edd668087")
        self.assertTrue(set(slice_cfg["exposed_in_review_question_ids"]) <= set(ids))
        self.assertEqual(len(slice_cfg["exposed_in_review_question_ids"]), 15)
        self.assertFalse(set(ids) & set(slice_cfg["excluded_pilot_question_ids"]))
        splits = {qid: GOLD[qid]["split"] for qid in ids}
        self.assertEqual(set(splits.values()), {"train"})

    def test_local_files_keep_56_and_drop_44(self):
        if not battery.DEFAULT_GENERATIONS.exists() or not battery.DEFAULT_TRACES.exists():
            self.skipTest("local generation or trace file not present")
        messages = []
        heldout = battery.load_heldout_ids()
        generations = battery.load_generations(heldout_ids=heldout, log=messages.append)
        traces = battery.load_traces(heldout_ids=heldout, log=messages.append)
        self.assertEqual(len(generations), 56)
        self.assertEqual(len(traces), 56)
        self.assertFalse({r["question_id"] for r in generations} & heldout)
        self.assertFalse({r["question_id"] for r in traces} & heldout)
        self.assertEqual(sum("dropped 44 held-out" in m for m in messages), 2)


def trace_token(position, text, entropy=0.5, margin=0.5):
    return {"position": position, "token_text": text, "token_entropy": entropy, "top2_margin": margin}


class SpanSignalTests(unittest.TestCase):
    """Span file, label mappings, trace signals, span kinds and evidence clusters (plan T1.7)."""

    def test_synthetic_trace_signals(self):
        text = "The total is £1,234."
        tokens = [trace_token(0, "The", 0.1, 0.9), trace_token(1, " total", 0.2, 0.8), trace_token(2, " is", 0.3, 0.7),
                  trace_token(3, " £", 0.4, 0.6), trace_token(4, "1", 0.5, 0.2), trace_token(5, ",", 0.6, 0.5),
                  trace_token(6, "234", 0.7, 0.4), trace_token(7, ".", 0.8, 0.3), trace_token(8, "<|im_end|>", 9.0, 0.0)]
        start = text.index("£")
        scores = span_signals.span_token_signals(tokens, text, start, start + len("£1,234"))
        self.assertEqual(scores["token_positions"], [3, 4, 5, 6])
        self.assertEqual(scores["mean_token_entropy"], math.fsum([0.4, 0.5, 0.6, 0.7]) / 4)
        self.assertEqual(scores["one_minus_min_top2_margin"], 1 - 0.2)
        with self.assertRaises(ValueError):
            span_signals.span_token_signals(tokens, "The total was £1,234.", 0, 3)

    def test_byte_fallback_pair_aligns(self):
        replacement, approx = chr(0xFFFD), chr(0x2248)
        tokens = [trace_token(0, "about "), trace_token(1, " " + replacement), trace_token(2, replacement),
                  trace_token(3, "5")]
        text = "about  " + approx + "5"
        spans, failures = span_signals.build_token_char_spans("q", text, tokens)
        self.assertEqual(failures, [])
        self.assertEqual([token["aligned_text"] for token in spans], ["about ", " ", approx, "5"])

    def test_span_kind_rules(self):
        record = {"evidence": {"rows": [{"stock_code": "85123A", "description": "WHITE HANGING HEART", "country": "France"}]}}
        rules = CONFIG["span_kind"]
        cases = {"April 2011": "month", "12.5%": "percentage", "**1.": "rank_marker", "increased": "direction_word",
                 "85123a": "code", "**White Hanging Heart**": "entity_name", "£1,234.50": "currency_or_number",
                 "strong seasonal demand": "free_text", "rose 5%": "percentage", "3 more units": "currency_or_number"}
        for text, kind in cases.items():
            self.assertEqual(span_signals.span_kind(text, record, rules), kind, text)
        broken = {**rules, "precedence": ["month"]}
        with self.assertRaises(ValueError):
            span_signals.span_kind("strong demand", record, broken)

    def test_restated_from_question(self):
        question = "Did net revenue in the United  Kingdom exceed £1,234.50 in May 2011?"
        self.assertTrue(span_signals.restated_from_question("1234.50", question))
        self.assertTrue(span_signals.restated_from_question("united kingdom", question))
        self.assertFalse(span_signals.restated_from_question("France", question))
        self.assertFalse(span_signals.restated_from_question("  ", question))

    def test_span_kind_distribution_matches_plan(self):
        attributes = battery.span_attributes(CONFIG, GOLD, SPANS)
        kinds = Counter(item["span_kind"] for item in attributes.values())
        self.assertEqual(dict(kinds), {"month": 37, "currency_or_number": 85, "entity_name": 35, "rank_marker": 16,
                                       "percentage": 15, "direction_word": 9, "code": 6, "free_text": 2})
        test_main = [span for span in SPANS if GOLD[span["question_id"]]["split"] == "test"
                     and attributes[span["annotation_id"]]["span_kind"] != "month"]
        self.assertEqual(len(test_main), 85)
        self.assertEqual(sum(LABELS[span["annotation_id"]]["binary_label"] for span in test_main), 61)
        rows = battery.span_kind_rows(attributes)
        self.assertEqual([row["annotation_id"] for row in rows], sorted(attributes))
        self.assertEqual(set(rows[0]), {"annotation_id", "span_kind", "restated_from_question"})

    def test_evidence_clusters_match_saved_scores(self):
        attributes = battery.span_attributes(CONFIG, GOLD, SPANS)
        with open(battery.SCORES_PATH, encoding="utf-8-sig", newline="") as handle:
            saved = {row["annotation_id"]: row["evidence_cluster"] for row in csv.DictReader(handle)
                     if row["arm"] == "saved_trace_precision"}
        self.assertEqual(len(saved), 205)
        self.assertEqual({aid: item["evidence_cluster"] for aid, item in attributes.items()}, saved)
        self.assertEqual(len({span["question_id"] for span in SPANS}), 35)

    def test_local_signals_equal_saved_trace_precision(self):
        if not battery.DEFAULT_GENERATIONS.exists() or not battery.DEFAULT_TRACES.exists():
            self.skipTest("local generation or trace file not present")
        texts, sources = battery.load_generated_texts(battery.DEFAULT_GENERATIONS, log=lambda m: None)
        signals, source = battery.load_signals(SPANS, texts, sources)
        self.assertEqual(source, "recomputed_from_traces")
        saved = battery.load_stored_signals()
        self.assertEqual(set(signals), set(saved))
        self.assertEqual(len(signals), 205)
        difference = max(abs(signals[aid][key] - saved[aid][key]) for aid in saved for key in battery.TRACE_SIGNALS)
        self.assertEqual(difference, 0)

    def test_span_file_is_the_six_fields_of_the_annotations(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "spans_full100_v1.jsonl"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(battery.main(["export-spans", "--spans", str(out)]), 0)
            self.assertEqual(out.read_bytes(), battery.SPANS_PATH.read_bytes().replace(b"\r\n", b"\n"))
        self.assertEqual([set(span) for span in SPANS], [set(battery.SPAN_FIELDS)] * 205)

    def test_span_only_file_builds_states_without_labels(self):
        states, skipped = battery.build_states(CONFIG, GOLD, SPANS, TEXTS, SOURCES)
        self.assertEqual(len(states), 70)
        self.assertTrue(all(item["reason"] == "generated text unavailable" for item in skipped))
        if battery.DEFAULT_GENERATIONS.exists():
            texts, sources = battery.load_generated_texts(battery.DEFAULT_GENERATIONS, log=lambda m: None)
            states, skipped = battery.build_states(CONFIG, GOLD, SPANS, texts, sources)
            self.assertEqual((len(states), len(skipped)), (205, 0))

    def test_checker_runs_without_labels_and_audit_counts_unlabelled(self):
        results = checker.run_checker(CONFIG, GOLD, SPANS, TEXTS)
        self.assertEqual(len(results), 70)
        partial = {aid: label for aid, label in battery.binary_labels(LABELS).items() if not aid.endswith("1")}
        audit = checker.checker_audit(results, partial)
        self.assertEqual(audit["span_count"] + audit["unlabelled_skipped"], 70)
        self.assertGreater(audit["unlabelled_skipped"], 0)

    def test_label_mappings(self):
        self.assertEqual(Counter(item["binary_label"] for item in LABELS.values()), Counter({1: 122, 0: 83}))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "human.jsonl"
            rows = [{"annotation_id": "a", "slot_label": "incorrect", "value_label": "faithful"},
                    {"annotation_id": "b", "slot_label": "correct"},
                    {"annotation_id": "c", "slot_label": "cannot_judge"},
                    {"annotation_id": "d"}]
            path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            slot = battery.load_labels([path], "human_v1_slot", CONFIG)
            self.assertEqual(battery.binary_labels(slot), {"a": 1, "b": 0, "c": None, "d": None})
            value = battery.load_labels([path], "human_v1_value", CONFIG)
            self.assertEqual(battery.binary_labels(value), {"a": 0, "b": None, "c": None, "d": None})
            with self.assertRaises(SystemExit):
                battery.load_labels([path, path], "human_v1_slot", CONFIG)
            with self.assertRaises(SystemExit):
                battery.load_labels([path], "value_axis_rule", CONFIG)
            path.write_text(json.dumps({"annotation_id": "a", "slot_label": "wrong"}) + "\n", encoding="utf-8")
            with self.assertRaises(SystemExit):
                battery.load_labels([path], "human_v1_slot", CONFIG)

    def test_priors_and_legacy_fact_type_prior(self):
        attributes = battery.span_attributes(CONFIG, GOLD, SPANS)
        rows = battery.base_rows(SPANS, LABELS, GOLD, attributes, battery.load_stored_signals(), [])
        self.assertEqual(len(rows), 205)
        fits = battery.attach_priors(rows, legacy=True)
        self.assertEqual(fits["dev_fact_type_prior"]["fit_size"], 102)
        self.assertEqual(fits["dev_question_type_prior"]["fit_size"], 83)
        test = [row for row in rows if row["role"] == "test"]
        prior = battery.metrics.evaluate([r["binary_label"] for r in test], [r["dev_fact_type_prior"] for r in test], 0.5)
        self.assertEqual(round(prior["auroc"], 3), 0.768)
        self.assertEqual(round(sum(r["binary_label"] for r in test) / len(test), 3), 0.592)
        fit = battery.fit_prior([{"kind": "a", "binary_label": 1}, {"kind": "a", "binary_label": 0},
                                 {"kind": "b", "binary_label": 1}], "kind")
        self.assertEqual(fit["rates"], {"a": 0.5, "b": 1.0})
        self.assertAlmostEqual(fit["fallback"], 2 / 3)
        without_legacy = battery.base_rows(SPANS, LABELS, GOLD, attributes, {}, [])
        self.assertNotIn("dev_fact_type_prior", battery.attach_priors(without_legacy))

    def test_cli_label_arguments(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                battery.main(["check", "--labels", str(battery.ANNOTATIONS_PATH)])
            with self.assertRaises(SystemExit):
                battery.main(["score", "--labels", str(battery.ANNOTATIONS_PATH), "--label-mapping", "ai_provisional"])
            with self.assertRaises(SystemExit):
                battery.main(["score", "--arms", "reference", "--public-demo"])

FREEZE_FILE_FIELDS = ["codebook_sha256", "annotation_schema_sha256", "labels_205_sha256", "preregistration_sha256",
                      "span_extractor_sha256", "generations_sha256", "token_traces_sha256"]


def synthetic_freeze(root):
    """A freeze record in `root` that matches synthetic inputs; returns (freeze_path, overrides, states_root)."""
    overrides = {}
    for field in FREEZE_FILE_FIELDS:
        path = root / f"{field}.txt"
        path.write_text(field, encoding="utf-8")
        overrides[field] = path
    states_root = root / "states"
    states_root.mkdir()
    states_path, manifest_path = battery.states_paths("full100_205", states_root)
    states = [{"annotation_id": "a", "question_id": "q_0015", "role": "test", "state": {"x": "1"}, "questions": {}},
              {"annotation_id": "b", "question_id": "q_0004", "role": "dev", "state": {"x": "2"}, "questions": {}}]
    states_path.write_text("".join(json.dumps(state) + "\n" for state in states), encoding="utf-8")
    manifest_path.write_text("{}\n", encoding="utf-8")
    record = battery.current_freeze_values(overrides, states_root=states_root)
    record.update({"freeze_id": "synthetic", "amendments": [],
                   "spans_extractor_only_devtest_sha256": None, "span_source_devtest_sha256": None})
    freeze_path = root / "decision_battery_v2_freeze.json"
    freeze_path.write_text(json.dumps(record), encoding="utf-8")
    return freeze_path, overrides, states_root


class FreezeGuardTests(unittest.TestCase):
    """Split and freeze guard (plan T1.8); synthetic freeze records in temporary folders, no network."""

    def test_synthetic_record_passes_for_test_and_heldout(self):
        with tempfile.TemporaryDirectory() as tmp:
            freeze_path, overrides, states_root = synthetic_freeze(Path(tmp))
            for role in ("test", "heldout"):
                record = battery.require_freeze(role, "t", freeze_path, overrides, states_root=states_root)
                self.assertEqual(record["freeze_id"], "synthetic")

    def test_missing_record_stops(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(SystemExit) as caught:
            battery.require_freeze("test", "run --split test", Path(tmp) / "decision_battery_v2_freeze.json")
        self.assertIn("does not exist", str(caught.exception))

    def test_mismatched_field_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            freeze_path, overrides, states_root = synthetic_freeze(Path(tmp))
            overrides["codebook_sha256"].write_text("changed", encoding="utf-8")
            with self.assertRaises(SystemExit) as caught:
                battery.require_freeze("test", "t", freeze_path, overrides, states_root=states_root)
        self.assertIn("codebook_sha256", str(caught.exception))
        self.assertNotIn("labels_205_sha256", str(caught.exception))

    def test_heldout_does_not_check_the_test_only_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            freeze_path, overrides, states_root = synthetic_freeze(Path(tmp))
            battery.states_paths("full100_205", states_root)[1].write_text('{"changed": 1}\n', encoding="utf-8")
            with self.assertRaises(SystemExit) as caught:
                battery.require_freeze("test", "t", freeze_path, overrides, states_root=states_root)
            self.assertIn("states_manifest_full100_205_sha256", str(caught.exception))
            battery.require_freeze("heldout", "t", freeze_path, overrides, states_root=states_root)

    def test_test_request_set_covers_every_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, states_root = synthetic_freeze(Path(tmp))
            states = battery.read_jsonl(battery.states_paths("full100_205", states_root)[0])
            arms = battery.load_arms()
            lines = sorted(f"{arm_id}|{digest}" for arm_id, arm in arms.items()
                           for digest in battery.expected_request_hashes(states[:1], arm).values())
            expected = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
            self.assertEqual(battery.request_set_sha256(arms, states_root), expected)
            self.assertEqual(len(lines), 2)

    def test_unrecorded_field_is_a_mismatch_but_nullable_fields_are_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            freeze_path, overrides, states_root = synthetic_freeze(Path(tmp))
            record = json.loads(freeze_path.read_text(encoding="utf-8"))
            record["preregistration_sha256"] = None
            freeze_path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaises(SystemExit) as caught:
                battery.require_freeze("heldout", "t", freeze_path, overrides, states_root=states_root)
            self.assertIn("preregistration_sha256 (not recorded)", str(caught.exception))
            self.assertNotIn("spans_extractor_only_devtest_sha256", str(caught.exception))

    def test_amendments_take_effect_in_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            freeze_path, overrides, states_root = synthetic_freeze(root)
            old = json.loads(freeze_path.read_text(encoding="utf-8"))["codebook_sha256"]
            overrides["codebook_sha256"].write_text("codebook v1.1", encoding="utf-8")
            new = battery.file_sha256(overrides["codebook_sha256"])
            amendment = root / "decision_battery_v2_freeze_amendment_1.json"
            amendment.write_text(json.dumps({"fields": {"codebook_sha256": {"old_sha256": old, "new_sha256": new}}}),
                                 encoding="utf-8")
            record = battery.require_freeze("test", "t", freeze_path, overrides, states_root=states_root)
            self.assertEqual(record["codebook_sha256"], new)
            self.assertEqual([item["file"] for item in record["amendments"]], [amendment.name])
            wrong_old = root / "decision_battery_v2_freeze_amendment_2.json"
            wrong_old.write_text(json.dumps({"fields": {"codebook_sha256": {"old_sha256": old, "new_sha256": old}}}),
                                 encoding="utf-8")
            with self.assertRaises(SystemExit) as caught:
                battery.load_freeze(freeze_path)
            self.assertIn("old hash of codebook_sha256", str(caught.exception))
            wrong_old.unlink()
            (root / "decision_battery_v2_freeze_amendment_3.json").write_text('{"fields": {}}', encoding="utf-8")
            with self.assertRaises(SystemExit) as caught:
                battery.load_freeze(freeze_path)
            self.assertIn("without gaps", str(caught.exception))

    def test_loaders_admit_heldout_ids_only_with_a_valid_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            freeze_path, overrides, states_root = synthetic_freeze(Path(tmp))
            generations = Path(tmp) / "generations.jsonl"
            generations.write_text(json.dumps({"question_id": "q_9001", "generated_text": "held out"}) + "\n"
                                   + json.dumps({"question_id": "q_9002", "generated_text": "open"}) + "\n",
                                   encoding="utf-8")
            heldout = frozenset({"q_9001"})
            before = battery.load_generations(generations, battery.readable_heldout_ids(heldout, None), log=lambda m: None)
            self.assertEqual([row["question_id"] for row in before], ["q_9002"])
            record = battery.require_freeze("heldout", "t", freeze_path, overrides, states_root=states_root)
            after = battery.load_generations(generations, battery.readable_heldout_ids(heldout, record), log=lambda m: None)
            self.assertEqual([row["question_id"] for row in after], ["q_9001", "q_9002"])

    def test_run_battery_sends_only_cleared_roles(self):
        states = [{"annotation_id": "a", "question_id": "q_0015", "role": "test", "state": {}, "questions": {}}]
        sent = []

        def sender(url, payload, key):
            sent.append(url)
            return 200, {"model": "m", "answers": {}}

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "responses.jsonl"
            with self.assertRaises(SystemExit):
                battery.run_battery(states, LOCAL_ARM, None, 1, path, sender=sender, sleeper=lambda s: None,
                                    log=lambda *a: None)
            self.assertEqual(sent, [])
            battery.run_battery(states, LOCAL_ARM, None, 1, path, sender=sender, sleeper=lambda s: None,
                                log=lambda *a: None, cleared_roles=("test",))
        self.assertEqual(len(sent), 1)

    def test_cli_run_outside_dev_needs_status_and_freeze(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                battery.main(["run", "--arm", "hosted_jev_1_13_0", "--split", "test"])
            self.assertIn("accepts only --split dev", str(caught.exception))
            final = json.loads(battery.CONFIG_PATH.read_text(encoding="utf-8"))
            final["status"] = "final_wording_not_frozen"
            config_path = Path(tmp) / "decision_battery_v2.json"
            config_path.write_text(json.dumps(final), encoding="utf-8")
            with mock.patch.object(battery, "FREEZE_PATH", Path(tmp) / "decision_battery_v2_freeze.json"):
                for split in ("test", "heldout"):
                    with self.assertRaises(SystemExit) as caught:
                        battery.main(["run", "--config", str(config_path), "--arm", "hosted_jev_1_13_0",
                                      "--split", split])
                    self.assertIn("freeze record", str(caught.exception))
                with self.assertRaises(SystemExit) as caught:
                    battery.main(["check", "--spans", str(Path(tmp) / "spans_heldout_v1.jsonl")])
                self.assertIn("freeze record", str(caught.exception))
            with self.assertRaises(SystemExit):
                battery.main(["run", "--arm", "hosted_jev_1_13_0"])
            with self.assertRaises(SystemExit):
                battery.main(["check", "--split", "dev"])

    def test_heldout_questions_get_the_heldout_role(self):
        qid = next(span["question_id"] for span in SPANS if span["question_id"] in TEXTS)
        spans = [span for span in SPANS if span["question_id"] == qid]
        states, _ = battery.build_states(CONFIG, GOLD, spans, TEXTS, SOURCES, heldout_ids=frozenset({qid}))
        self.assertEqual({state["role"] for state in states}, {"heldout"})
        states, _ = battery.build_states(CONFIG, GOLD, spans, TEXTS, SOURCES)
        self.assertEqual({state["role"] for state in states}, {GOLD[qid]["split"]})

    def test_scoring_rejects_other_roles(self):
        battery.check_response_roles([{"annotation_id": "a", "role": "dev"}, {"annotation_id": "b", "role": "heldout"}])
        for role in ("train", None):
            with self.assertRaises(SystemExit) as caught:
                battery.check_response_roles([{"annotation_id": "x_1", "role": role}])
            self.assertIn("x_1", str(caught.exception))

PRIMARY = "dm_risk@local_open_jev_2b"


def synthetic_row(index, role, label, span_set="full100_205", **extra):
    """One labelled row with every continuous column; higher scores go with label 1 but overlap."""
    base = 0.6 if label else 0.4
    jitter = ((index * 37) % 11) / 20
    row = {"annotation_id": f"s_{role}_{index:03d}", "span_set_id": span_set, "question_id": f"q_9{index % 12:03d}",
           "role": role, "span_kind": "currency_or_number", "question_type": "top_product_month",
           "restated_from_question": index % 5 == 0, "evidence_cluster": f"c{index % 9}",
           "derivation_need": "top_k", "binary_label": label, "value_binary": None, "all_positive": 1.0,
           "rule_checker_flag": label if index % 4 else 0, "rule_checker_abstain": 0 if index % 4 else 1,
           "evidence_lookup_flag": None, "evidence_lookup_abstain": None, "checker_mechanism": "cell_copy",
           "slot_label": "incorrect" if label else "correct", "value_label": "faithful",
           "mechanism": ("M1" if index % 2 else "M2") if label else None, "matched_row_id": "r1"}
    for offset, column in enumerate(["one_minus_min_top2_margin", "mean_token_entropy", "dev_span_kind_prior",
                                     "dev_question_type_prior", PRIMARY, "dm_conflict@local_open_jev_2b",
                                     "dm_conflict_or_undetermined@local_open_jev_2b"]):
        row[column] = round(min(1.0, max(0.0, base + jitter - 0.25 + offset * 0.01)), 6)
    row["slot_yes@local_open_jev_2b"] = round(1 - row[PRIMARY], 6)
    row.update(extra)
    return row


def synthetic_role_rows(role, count, span_set="full100_205"):
    return [synthetic_row(index, role, int(index % 3 != 0), span_set) for index in range(count)]


class ScoringTests(unittest.TestCase):
    """Scoring, reports and freeze (plan T1.9); synthetic data unless stated."""

    def test_threshold_rule(self):
        fit = [{"binary_label": 0, "a": value} for value in (0.1, 0.2, 0.3, 0.4, 0.5)]
        fit += [{"binary_label": 1, "a": value} for value in (0.6, 0.7, 0.8, 0.9, 0.95)]
        chosen = battery.scoring.budget_threshold(fit, "a", 0.2)
        self.assertEqual((chosen["threshold"], chosen["degenerate"]), (0.5, False))
        none_meets = [{"binary_label": 0, "a": 0.9}, {"binary_label": 0, "a": 0.9}, {"binary_label": 1, "a": 0.1}]
        result = battery.scoring.budget_threshold(none_meets, "a", 0.2)
        self.assertEqual(result["threshold"], math.inf)
        self.assertTrue(result["degenerate"])
        lowest = battery.scoring.budget_threshold([{"binary_label": 1, "a": 0.3}, {"binary_label": 1, "a": 0.7}], "a", 0.2)
        self.assertEqual((lowest["threshold"], lowest["degenerate"]), (0.3, True))
        rows = synthetic_role_rows("dev", 30)
        thresholds = battery.scoring.fit_thresholds(rows, ["one_minus_min_top2_margin"], CONFIG, "human_v1_slot")
        self.assertEqual(thresholds["for_test"]["all_positive"]["threshold"], 1.0)
        self.assertTrue(thresholds["source"].startswith("PRE-FREEZE"))
        self.assertIn("for_test fit set", thresholds["notes"][0])
        frozen = {"dev_thresholds": {"rule": "r", "for_test": {"a": {"threshold": None, "degenerate": True}},
                                     "for_heldout": {"a": {"threshold": 0.4, "degenerate": False}}}}
        read = battery.scoring.fit_thresholds(rows, ["a"], CONFIG, "human_v1_slot", frozen=frozen)
        self.assertEqual((read["source"], read["for_test"]["a"]["threshold"]), ("freeze record", math.inf))

    def test_new_bootstrap_matches_detector_metrics_point_difference(self):
        attributes = battery.span_attributes(CONFIG, GOLD, SPANS)
        rows = battery.base_rows(SPANS, LABELS, GOLD, attributes, battery.load_stored_signals(), [])
        test = [{**row, "split": "test"} for row in rows if row["role"] == "test"]
        self.assertEqual(len(test), 103)
        pair = ("one_minus_min_top2_margin", "mean_token_entropy")
        old = battery.metrics.paired_cluster_bootstrap(test, {pair[0]: 0.3, pair[1]: 0.005}, [pair], "question_id",
                                                       replicates=20, seed=3)
        old_ap = next(item for item in old["intervals"] if item["metric"] == "average_precision")
        new = battery.cb.ranking_intervals(test, list(pair), "question_id", [pair], replicates=20, seed=3)
        self.assertEqual(new["estimates"][f"{pair[0]} minus {pair[1]}|average_precision"]["point"], old_ap["point_difference"])
        self.assertEqual(new["cluster_count"], old["cluster_count"])

    def test_every_risk_score_rises_for_a_wrong_answer(self):
        wrong = {"answers": {"slot_correct": {"type": "noul", "noul": 0.1},
                             "status": {"type": "choice", "probabilities": {"k7": 0.1, "m2": 0.7, "x9": 0.2}},
                             "value_faithful": {"type": "choice", "probabilities": {"f1": 0.1, "f2": 0.8, "f3": 0.05, "f4": 0.05}}}}
        right = {"answers": {"slot_correct": {"type": "noul", "noul": 0.9},
                             "status": {"type": "choice", "probabilities": {"k7": 0.9, "m2": 0.05, "x9": 0.05}},
                             "value_faithful": {"type": "choice", "probabilities": {"f1": 0.9, "f2": 0.05, "f3": 0.05, "f4": 0.0}}}}
        high, low = battery.derived_scores(wrong, CONFIG), battery.derived_scores(right, CONFIG)
        for name in CONFIG["derived_scores"]:
            self.assertGreater(high[name], low[name], name)

    def test_invalid_scores_name_the_span(self):
        with self.assertRaises(ValueError) as caught:
            battery.scoring.rounded(float("nan"), "ann_x", "dm_risk")
        self.assertIn("ann_x", str(caught.exception))
        with self.assertRaises(ValueError):
            battery.scoring.rounded(1.5, "ann_x", "dm_risk")
        self.assertEqual(battery.scoring.rounded(0.12345678, "ann_x", "dm_risk"), 0.123457)
        bad = [{"annotation_id": "ann_y", "status": 200, "response": {"answers": {}}}]
        with self.assertRaises(ValueError) as caught:
            battery.aggregate_responses(bad, CONFIG)
        self.assertIn("ann_y", str(caught.exception))

    def test_estimand_e1_by_hand(self):
        rows = [
            {"question_id": "q1", "evidence_cluster": "c1", "binary_label": 1, "slot_label": "incorrect",
             "value_label": "faithful", "span_kind": "currency_or_number", "mechanism": "M1", "matched_row_id": "r1"},
            {"question_id": "q1", "evidence_cluster": "c1", "binary_label": 1, "slot_label": "incorrect",
             "value_label": "unfaithful", "span_kind": "currency_or_number", "mechanism": "M2", "matched_row_id": ""},
            {"question_id": "q2", "evidence_cluster": "c2", "binary_label": 1, "slot_label": "unsupported",
             "value_label": None, "span_kind": "percentage", "mechanism": "M5", "matched_row_id": ""},
            {"question_id": "q3", "evidence_cluster": "c3", "binary_label": 1, "slot_label": "incorrect",
             "value_label": "faithful", "span_kind": "entity_name", "mechanism": "M1", "matched_row_id": "r2"},
            {"question_id": "q3", "evidence_cluster": "c3", "binary_label": 0, "slot_label": "correct",
             "value_label": "faithful", "span_kind": "currency_or_number", "mechanism": None, "matched_row_id": "r2"},
        ]
        result = battery.scoring.estimand_e1(rows, 20, 1)
        self.assertEqual((result["numerator_spans"], result["wrong_spans"]), (1, 4))
        self.assertEqual(result["estimates"]["share_of_all_wrong"]["point"], 1 / 4)
        self.assertEqual(result["estimates"]["share_of_numeric_wrong"]["point"], 1 / 3)
        self.assertEqual(result["other_span_kinds"]["entity_name"], {"numerator_spans": 1, "wrong_spans_of_kind": 1})
        self.assertEqual(result["answer_level"]["share"], 1 / 3)
        self.assertEqual(result["error_events"], {"numerator": 1, "all_wrong": 4})

    def test_estimands_e2_e3_e4_by_hand(self):
        def row(role, label, mechanism, score, flag, cluster):
            return {"annotation_id": f"{role}{cluster}{score}", "role": role, "binary_label": label,
                    "mechanism": mechanism, "one_minus_min_top2_margin": score, "rule_checker_flag": flag,
                    "rule_checker_abstain": 0, "evidence_cluster": cluster, "question_id": f"q{cluster}"}
        rows = [row("test", 1, "M1", 0.9, 1, "a"), row("test", 0, None, 0.5, 0, "b"), row("test", 0, None, 0.95, 0, "c"),
                row("test", 1, "M2", 0.6, 0, "d"), row("test", 1, "M1", 0.2, 0, "e"),
                row("heldout", 1, "M1", 0.8, 1, "f"), row("heldout", 0, None, 0.1, 0, "g")]
        m1 = [r for r in rows if r["mechanism"] == "M1"]
        pooled = battery.scoring.pooled_auroc(rows, lambda r: r["mechanism"] == "M1", lambda r: r["binary_label"] == 0,
                                              "one_minus_min_top2_margin")
        self.assertAlmostEqual(pooled, 2 / 5)
        e2 = battery.scoring.estimand_e2(rows, ["one_minus_min_top2_margin"], 20, 1)
        self.assertAlmostEqual(e2["pooled"]["estimates"]["one_minus_min_top2_margin|contrast"]["point"], 2 / 5 - 1 / 2)
        self.assertAlmostEqual(e2["heldout"]["estimates"]["one_minus_min_top2_margin|m1"]["point"], 1.0)
        thresholds = {"for_test": {"one_minus_min_top2_margin": {"threshold": 0.5, "degenerate": False}},
                      "for_heldout": {"one_minus_min_top2_margin": {"threshold": 0.9, "degenerate": False}}}
        e3 = battery.scoring.estimand_e3(rows, ["one_minus_min_top2_margin"], thresholds, 20, 1)
        self.assertEqual(e3["m1_spans"], len(m1))
        self.assertAlmostEqual(e3["pooled"]["estimates"]["rule_checker"]["point"], 2 / 3)
        self.assertAlmostEqual(e3["pooled"]["estimates"]["one_minus_min_top2_margin"]["point"], 1 / 3)
        self.assertAlmostEqual(e3["pooled"]["estimates"]["rule_checker minus one_minus_min_top2_margin"]["point"], 1 / 3)
        abstained = [{"annotation_id": str(i), "role": "test", "question_id": f"q{i % 4}", "evidence_cluster": "c",
                      "rule_checker_abstain": 1, "binary_label": i % 2, PRIMARY: 0.9 if i % 2 else 0.1}
                     for i in range(12)]
        e4 = battery.scoring.estimand_e4(abstained, PRIMARY, 20, 1)
        self.assertEqual((e4["spans"], e4["auroc"]["point"]), (12, 1.0))
        self.assertEqual(battery.scoring.estimand_e4(abstained[:9], PRIMARY, 20, 1)["note"], "counts only")

    def test_funnel_by_hand(self):
        thresholds = {"for_test": {PRIMARY: {"threshold": 0.5, "degenerate": False}}, "for_heldout": {}}
        rows = [{"role": "test", "binary_label": 1, "rule_checker_flag": 1, "rule_checker_abstain": 0},
                {"role": "test", "binary_label": 0, "rule_checker_flag": 1, "rule_checker_abstain": 0},
                {"role": "test", "binary_label": 1, "rule_checker_flag": 0, "rule_checker_abstain": 1,
                 "slot_yes@local_open_jev_2b": 0.2, PRIMARY: 0.8},
                {"role": "test", "binary_label": 1, "rule_checker_flag": 0, "rule_checker_abstain": 1,
                 "slot_yes@local_open_jev_2b": 0.5, PRIMARY: 0.5}]
        result = battery.scoring.funnel(rows, "local_open_jev_2b", thresholds, minimum=10)
        self.assertEqual(result["layer_1"], {"spans": 2, "share": 0.5, "errors": 1})
        self.assertEqual(result["layer_2"], {"spans": 1, "share": 0.25, "errors": 0})
        self.assertEqual(result["layer_3"], {"spans": 1, "share": 0.25})

    def test_heldout_report_has_intervals_for_both_versions(self):
        rows = synthetic_role_rows("dev", 36) + synthetic_role_rows("test", 36)
        rows += synthetic_role_rows("heldout", 48, span_set="heldout_v1")
        rows.append({**synthetic_row(99, "heldout", None, "heldout_v1"), "binary_label": None, "slot_label": "not_a_claim"})
        labels = {row["annotation_id"]: {"binary_label": row["binary_label"],
                                         "value": row["slot_label"], "row": {}} for row in rows}
        exposed = {"q_9000", "q_9001", "q_9002"}
        dev_thresholds = {"rule": "r", "for_test": {}, "for_heldout": {}}
        for key in ("for_test", "for_heldout"):
            for column in battery.continuous_columns(CONFIG, ["local_open_jev_2b"], False):
                dev_thresholds[key][column] = {"threshold": 0.5, "degenerate": False}
        arms = {"local_open_jev_2b": {**LOCAL_ARM, "arm_id": "local_open_jev_2b", "model": "m"}}
        aggregated = {"local_open_jev_2b": {row["annotation_id"]: {"repeats": 1, "models": {"m": 1}} for row in rows}}
        report, _ = battery.build_report(CONFIG, rows, arms, aggregated, "human_v1_slot", [], labels, "stored", exposed,
                                         50, 1, frozen={"dev_thresholds": dev_thresholds})
        heldout = report["roles"]["heldout"]["sets"]
        for name in ("main set", "main set, answers not viewed during review"):
            primary = heldout[name]["primary_contrast"]
            for metric in ("average_precision", "auroc"):
                self.assertIsNotNone(heldout[name]["arms"][PRIMARY][metric]["lower_95"], name)
                self.assertIsNotNone(primary[metric]["lower_95"], name)
        self.assertLess(heldout["main set, answers not viewed during review"]["counts"]["spans"],
                        heldout["main set"]["counts"]["spans"])
        self.assertEqual(heldout["main set"]["primary_contrast"]["cluster"], "evidence_cluster")
        self.assertEqual(report["excluded_label_values"], {"not_a_claim": 1})
        self.assertEqual(report["thresholds"]["source"], "freeze record")
        self.assertIn("E1", report["estimands"])
        markdown = battery.scoring.render_report(report)
        self.assertIn(battery.scoring.HISTORICAL_REFERENCE_LINE, markdown)
        self.assertIn("rater", markdown)
        self.assertNotIn("significant", markdown.lower())

    def test_score_reference_and_the_test_response_guard(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            root = Path(tmp)
            with mock.patch.object(battery, "OUTPUT_ROOT", root), \
                    mock.patch.object(battery, "FREEZE_PATH", root / "decision_battery_v2_freeze.json"):
                labels = ["--labels", str(battery.ANNOTATIONS_PATH), "--label-mapping", "ai_provisional"]
                self.assertEqual(battery.main(["score", "--arms", "reference", "--public-demo", "--replicates", "20"]
                                              + labels), 0)
                report = json.loads((root / "report_reference.json").read_text(encoding="utf-8"))
                self.assertEqual(set(report["roles"]), {"dev", "test"})
                self.assertIn("one_minus_min_top2_margin", report["roles"]["test"]["sets"]["main set"]["arms"])
                self.assertEqual(battery.main(["build"]), 0)
                arm_dir = root / "hosted_jev_1_13_0"
                arm_dir.mkdir()
                (arm_dir / "responses.jsonl").write_text(json.dumps({"annotation_id": "x", "role": "test", "status": 200})
                                                         + "\n", encoding="utf-8")
                with self.assertRaises(SystemExit) as caught:
                    battery.main(["score", "--arms", "hosted_jev_1_13_0", "--public-demo"] + labels)
                self.assertIn("freeze record", str(caught.exception))

    def test_diagnostics_without_labels(self):
        states, _ = battery.build_states(CONFIG, GOLD, SPANS, TEXTS, SOURCES)
        states = [{**state, "span_kind": "month"} for state in states[:2]]
        rows = [{"annotation_id": state["annotation_id"], "status": 200, "response": full_response(state["questions"], yes, "m")}
                for state, yes in zip(states, (0.5, 0.9))]
        result = battery.scoring.diagnostics(rows, states, CONFIG)
        month = result["by_span_kind"]["month"]
        self.assertEqual(month["spans"], 2)
        self.assertEqual(month["questions"]["slot_correct"]["responses"], 2)
        self.assertEqual(month["questions"]["slot_correct"]["yes_between_0_45_and_0_55_share"], 0.5)
        self.assertEqual(month["questions"]["status"]["abstain_argmax_share"], 0.0)
        self.assertEqual(month["questions"]["status"]["abstain_option"], "x9")
        self.assertEqual(result["models"], {"m": 2})
        self.assertIn("relation", month["descriptive_option_counts"])
        text = battery.scoring.render_diagnostics(result, "local_test", "full100_205")
        self.assertIn("span_kind month", text)

    def test_power_notes(self):
        rows = synthetic_role_rows("dev", 30)
        notes = battery.power_notes(rows, "local_open_jev_2b", 30, 1)
        self.assertEqual(notes["dev_main_set_spans"], 30)
        self.assertAlmostEqual(notes["dev_main_set_positive_rate"], 20 / 30)
        self.assertGreaterEqual(notes["perfect_detector_gap_to_margin"]["auroc"], 0)
        self.assertGreaterEqual(notes["dev_paired_difference_interval_width"]["auroc"], 0)
        self.assertIsNone(battery.power_notes(synthetic_role_rows("test", 5), "local_open_jev_2b", 5, 1))


class FreezeCommandTests(unittest.TestCase):
    """freeze in a temporary folder, then a test run through both checks (plan T1.9 item 18)."""

    def test_build_dev_responses_freeze_then_test_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            states_root = root / "out"
            config_path = root / "decision_battery_v2.json"
            config_path.write_bytes(battery.CONFIG_PATH.read_bytes())
            arm = {**LOCAL_ARM, "arm_id": "local_open_jev_2b", "model": "open-jev-2b", "repeats": {"dev": 1, "eval": 1}}
            arms_path = root / "arms.json"
            arms_path.write_text(json.dumps({"arms": [arm]}), encoding="utf-8")
            generations, traces = root / "generations.jsonl", root / "traces.jsonl"
            generations.write_text("{}\n", encoding="utf-8")
            traces.write_text("{}\n", encoding="utf-8")
            extra = {}
            for name in ("codebook", "schema", "preregistration", "span_extractor"):
                extra[name] = root / f"{name}.txt"
                extra[name].write_text(name, encoding="utf-8")
            power = root / "power_notes.json"
            power.write_text('{"dev_main_set_positive_rate": 0.5}', encoding="utf-8")
            texts, sources = battery.load_generated_texts(generations, log=lambda m: None)
            states, _ = battery.build_states(CONFIG, GOLD, SPANS, texts, sources)
            battery.write_states(states, "full100_205", config_path, arms_path, battery.SPANS_PATH, generations,
                                 root=states_root)
            dev = [state for state in states if state["role"] == "dev"]
            labels_path = root / "labels.jsonl"
            mapping = {1: "incorrect", 0: "correct"}
            with labels_path.open("w", encoding="utf-8", newline="\n") as handle:
                for state in dev:
                    label = LABELS[state["annotation_id"]]["binary_label"]
                    handle.write(json.dumps({"annotation_id": state["annotation_id"], "slot_label": mapping[label]}) + "\n")
            expected = battery.expected_request_hashes(dev, arm)
            responses = states_root / arm["arm_id"] / "responses.jsonl"
            responses.parent.mkdir(parents=True)
            with responses.open("w", encoding="utf-8", newline="\n") as handle:
                for index, state in enumerate(dev):
                    label = LABELS[state["annotation_id"]]["binary_label"]
                    handle.write(json.dumps({"annotation_id": state["annotation_id"], "role": "dev", "status": 200,
                                             "cache_key": str(index), "request_sha256": expected[state["annotation_id"]],
                                             "response": fake_response(label)}) + "\n")
            freeze_path = root / "decision_battery_v2_freeze.json"
            overrides = {"span_extractor_sha256": extra["span_extractor"]}
            record = battery.run_freeze("2026-09-29", config_path, arms_path, labels_path, "human_v1_slot",
                                        extra["codebook"], extra["schema"], battery.HELDOUT_SLICE_PATH,
                                        extra["preregistration"], power, generations, traces, freeze_path=freeze_path,
                                        states_root=states_root, overrides=overrides,
                                        validator=lambda: {"num_failures": 0, "failures": []}, git_commit="abc",
                                        log=lambda m: None)
            self.assertTrue(set(battery.FREEZE_ENFORCED_FIELDS) <= set(record))
            self.assertEqual(json.loads(config_path.read_text(encoding="utf-8"))["status"], "frozen")
            self.assertEqual(record["battery_config_sha256"], battery.file_sha256(config_path))
            self.assertIsNone(record["spans_extractor_only_devtest_sha256"])
            self.assertIn("dm_risk@local_open_jev_2b", record["dev_thresholds"]["for_test"])
            self.assertEqual(record["power_notes"], {"dev_main_set_positive_rate": 0.5})
            with self.assertRaises(SystemExit):
                battery.run_freeze("2026-09-29", config_path, arms_path, labels_path, "human_v1_slot",
                                   extra["codebook"], extra["schema"], battery.HELDOUT_SLICE_PATH,
                                   extra["preregistration"], power, generations, traces, freeze_path=freeze_path,
                                   states_root=states_root, overrides=overrides,
                                   validator=lambda: {"num_failures": 0, "failures": []})
            run_overrides = {"battery_config_sha256": config_path, "arms_config_sha256": arms_path,
                             "generations_sha256": generations, "token_traces_sha256": traces}
            battery.require_freeze("test", "run --split test", freeze_path, run_overrides, arms_path, states_root)
            loaded, _ = battery.load_states("full100_205", config_path, arms_path, battery.SPANS_PATH, generations,
                                            root=states_root)
            test_states = [state for state in loaded if state["role"] == "test"]
            sent = []

            def sender(url, payload, key):
                sent.append(payload["model"])
                return 200, full_response(payload["questions"])

            battery.run_battery(test_states[:2], arm, None, 1, responses, sender=sender, sleeper=lambda s: None,
                                log=lambda *a: None, cleared_roles=("test",))
            self.assertEqual(sent, ["open-jev-2b", "open-jev-2b"])

    def test_freeze_refuses_missing_inputs_and_failed_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "missing.txt"
            with self.assertRaises(SystemExit) as caught:
                battery.run_freeze("d", battery.CONFIG_PATH, battery.ARMS_CONFIG_PATH, missing, "human_v1_slot",
                                   missing, missing, battery.HELDOUT_SLICE_PATH, missing, missing,
                                   freeze_path=root / "f.json", states_root=root, validator=lambda: {"num_failures": 0})
            self.assertIn("codebook_sha256", str(caught.exception))
            self.assertIn("power_notes", str(caught.exception))
            self.assertEqual(battery.config_text_with_status('{\n  "status": "draft",\n  "x": {"status": "keep"}\n}',
                                                             "frozen"),
                             '{\n  "status": "frozen",\n  "x": {"status": "keep"}\n}')

if __name__ == "__main__":
    unittest.main()
