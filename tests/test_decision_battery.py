import io
import json
import re
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from bizhallu import decision_battery as battery  # noqa: E402
from bizhallu import evidence  # noqa: E402
from bizhallu import rule_checker as checker  # noqa: E402

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
        results = checker.run_checker(CONFIG, GOLD, ANNOTATIONS, TEXTS)
        audit = checker.checker_audit(results, ANNOTATIONS)
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
        return states[:count]

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
            checker_results = checker.run_checker(CONFIG, GOLD, ANNOTATIONS, TEXTS)
            signals = battery.load_stored_signals()
            report, rows = battery.score_battery(CONFIG, GOLD, ANNOTATIONS, path, checker_results, signals, replicates=50, seed=1)
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
        import hashlib
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


if __name__ == "__main__":
    unittest.main()
