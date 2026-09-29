"""Jev evidence-binding battery v1 for BizHallu (standard library only).

Poses each pre-identified business-fact span as typed questions to a
non-generative decision model (TypeSafe Jev) over the same evidence table the
generator saw, and compares the returned probabilities with a deterministic,
label-blind evidence checker and with the stored token-time uncertainty signals.

Subcommands (all offline unless stated):

  build     Build one state per span from committed artifacts plus the local
            generation file; write outputs/jev_battery_v1/states.jsonl.
  check     Run the deterministic checker over the states and audit it against
            the provisional labels; write checker.jsonl and checker_audit.json.
  run       Send states to the Jev API (network; needs TYPESAFE_API_KEY in the
            environment) with repeats and a response cache.
  score     Join cached responses with labels and stored signals; write
            report.json and report.md.
  validate  Public offline check of the frozen config and state contract.

The API key is read only from the environment and is never written to disk.
Nothing here reads the sealed Confirmation Set v1 manifests.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import detector_metrics as metrics  # noqa: E402
from bizhallu import evidence, rule_checker  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "jev_battery_v1.json"
GOLD_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
ANNOTATIONS_PATH = PROJECT_ROOT / "data" / "annotations" / "span_annotations_full100_draft.jsonl"
DEMO_PATH = PROJECT_ROOT / "reports" / "bizhallu_demo_v2_data.json"
SCORES_PATH = PROJECT_ROOT / "results" / "full100_statistics_v2_scores.csv"
DEFAULT_GENERATIONS = PROJECT_ROOT / "outputs" / "qwen_full100_generations.jsonl"
DEFAULT_TRACES = PROJECT_ROOT / "outputs" / "qwen_full100_token_traces.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "jev_battery_v1"
V2_CONFIG_PATH = PROJECT_ROOT / "configs" / "decision_battery_v2.json"
ARMS_CONFIG_PATH = PROJECT_ROOT / "configs" / "decision_battery_arms_v1.json"
HELDOUT_SLICE_PATH = PROJECT_ROOT / "configs" / "heldout_slice_v1.json"

MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]
POSITIVE_LABELS = {"hallucinated_key_fact", "unsupported_claim"}
NEGATIVE_LABELS = {"correct_key_fact"}
MARK_OPEN, MARK_CLOSE = "【", "】"
REFERENCE_ARMS = ["one_minus_min_top2_margin", "mean_token_entropy", "dev_fact_type_prior", "all_positive"]


# ---------------------------------------------------------------- loading ---

def read_jsonl(path):
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def load_config(path=CONFIG_PATH):
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def load_gold(path=GOLD_PATH):
    return {record["question_id"]: record for record in read_jsonl(path)}


def load_annotations(path=ANNOTATIONS_PATH):
    rows = read_jsonl(path)
    for row in rows:
        if row["label"] in POSITIVE_LABELS:
            row["binary_label"] = 1
        elif row["label"] in NEGATIVE_LABELS:
            row["binary_label"] = 0
        else:
            row["binary_label"] = None
    return rows


def load_heldout_ids(path=HELDOUT_SLICE_PATH):
    """Question ids of the label-held-out slice; membership comes only from this file."""
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return frozenset(json.load(handle)["heldout_question_ids"])


def _read_guarded_jsonl(path, heldout_ids, what, log):
    """Read JSONL records and drop held-out question ids as the first step after parsing each line."""
    records, dropped = [], 0
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            if record.get("question_id") in heldout_ids:
                dropped += 1
                continue
            records.append(record)
    log(f"{what}: dropped {dropped} held-out records, kept {len(records)}")
    return records


def _stderr(message):
    print(message, file=sys.stderr)


def load_generations(path=DEFAULT_GENERATIONS, heldout_ids=None, log=_stderr):
    """Generation records with the held-out answers removed on read."""
    if heldout_ids is None:
        heldout_ids = load_heldout_ids()
    return _read_guarded_jsonl(path, heldout_ids, "generations", log)


def load_traces(path=DEFAULT_TRACES, heldout_ids=None, log=_stderr):
    """Token-trace records with the held-out answers removed on read."""
    if heldout_ids is None:
        heldout_ids = load_heldout_ids()
    return _read_guarded_jsonl(path, heldout_ids, "token traces", log)


def load_generated_texts(generations_path=None, demo_path=DEMO_PATH, heldout_ids=None, log=_stderr):
    """Generated answers by question id: local generation file first, demo bundle as fallback.

    Held-out answers are dropped on read, from both sources.
    """
    if heldout_ids is None:
        heldout_ids = load_heldout_ids()
    texts, sources = {}, {}
    if generations_path and Path(generations_path).exists():
        for record in load_generations(generations_path, heldout_ids, log):
            text = record.get("generated_text")
            if isinstance(text, str) and record.get("question_id"):
                texts[record["question_id"]] = text
                sources[record["question_id"]] = "local_generations"
    if Path(demo_path).exists():
        with Path(demo_path).open("r", encoding="utf-8") as handle:
            demo = json.load(handle)
        for case in demo.get("cases", []):
            qid = case.get("question_id")
            if qid in heldout_ids:
                continue
            if qid and qid not in texts and isinstance(case.get("generated_text"), str):
                texts[qid] = case["generated_text"]
                sources[qid] = "public_demo_bundle"
    return texts, sources


def load_stored_signals(path=SCORES_PATH, arm="saved_trace_precision"):
    signals = {}
    if not Path(path).exists():
        return signals
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("arm") != arm:
                continue
            signals[row["annotation_id"]] = {
                "evidence_cluster": row.get("evidence_cluster"),
                "period_component": row.get("period_component"),
                **{key: float(row[key]) for key in REFERENCE_ARMS if key in row},
            }
    return signals


# ------------------------------------------------- prompt reconstruction ---

def build_state(record, span, answer_text):
    start, end = span["span_start_char"], span["span_end_char"]
    if answer_text[start:end] != span["span_text"]:
        raise ValueError(f"Span offsets do not match generated text for {span['annotation_id']}")
    return {
        "question": record["question"],
        "metric_definitions": evidence.metric_definitions(record),
        "scope_notes": evidence.scope_notes(record),
        "evidence_rows": evidence.evidence_rows_for_state(record),
        "answer": answer_text,
        "marked_answer": answer_text[:start] + MARK_OPEN + span["span_text"] + MARK_CLOSE + answer_text[end:],
        "marked_text": span["span_text"],
    }


_CONTRACT_CACHE = {}
_THOUSANDS_COMMA = re.compile(r"(?<=\d),(?=\d)")
_TEMPLATE_VALUES = {
    "format(float(evidence.metadata.total_merchandise_net_revenue), ',.2f')":
        lambda record: (None if record["evidence"].get("metadata", {}).get("total_merchandise_net_revenue") is None
                        else f"{float(record['evidence']['metadata']['total_merchandise_net_revenue']):,.2f}"),
    "', '.join(evidence.filters.exclude_countries)":
        lambda record: ", ".join(record["evidence"]["filters"].get("exclude_countries") or []),
}


def load_state_contract(path=None):
    """State-contract rules from the v2 config: whitelists, templates, forbidden names, numeric scan."""
    key = str(path or V2_CONFIG_PATH)
    if key not in _CONTRACT_CACHE:
        _CONTRACT_CACHE[key] = load_config(key)["state_contract"]
    return _CONTRACT_CACHE[key]


def normalize_for_scan(text):
    """Lower-case, drop whitespace and thousands separators, for fragment matching."""
    return _THOUSANDS_COMMA.sub("", re.sub(r"\s+", "", str(text).lower()))


def forbidden_fragments(record, span, label_row=None):
    """Strings that must never appear in the constructed fields of a state for this span.

    Sources follow state_contract.fragment_sources: the gold short answer, the share numerator
    label, and the reason, notes and gold_reference of the same annotation (gold_reference is
    serialised once, never split into its values).
    """
    fragments = [record["gold_short_answer"]]
    share_label = record["evidence"].get("metadata", {}).get("share_numerator_label")
    if share_label:
        fragments.append(share_label)
    source = label_row if label_row is not None else span
    for key in ("reason", "notes"):
        if source.get(key):
            fragments.append(str(source[key]))
    if source.get("gold_reference"):
        fragments.append(json.dumps(source["gold_reference"], sort_keys=True))
    return [fragment for fragment in fragments if fragment]


def _string_leaves(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _string_leaves(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _string_leaves(item)


def _all_keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _all_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _all_keys(item)


def _float_leaves(value):
    if isinstance(value, bool):
        return
    if isinstance(value, float):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _float_leaves(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _float_leaves(item)


def _template_ok(line, templates, record):
    if line in templates["fixed"]:
        return True
    for pattern in templates["patterns"]:
        match = re.match(pattern["regex"], line)
        if match:
            expected = _TEMPLATE_VALUES[pattern["captured_value_must_equal"]](record)
            if expected is not None and match.group(1) == expected:
                return True
    return False


def _scan_number(token):
    return round(abs(float(token.replace(",", ""))), 2)


def numeric_scan_hits(texts, record, scan):
    """Gold numbers that appear in constructed text although the generator prompt did not show them."""
    tokenizer = re.compile(scan["tokenizer_regex"])
    exempt = set()
    for row in record["evidence"]["rows"]:
        for value in row.values():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                exempt.add(round(abs(float(value)), 2))
    for match in tokenizer.finditer(record["question"]):
        exempt.add(_scan_number(match.group(0)))
    total = record["evidence"].get("metadata", {}).get("total_merchandise_net_revenue")
    if total is not None:
        exempt.add(round(abs(float(total)), 2))
    targets = {round(abs(value), 2) for value in _float_leaves(record.get("gold_answer", {}))} - exempt
    hits = []
    for text in texts:
        for match in tokenizer.finditer(text):
            if _scan_number(match.group(0)) in targets:
                hits.append(match.group(0))
    return hits


def check_state_contract(state, record, span, config=None, questions=None, contract=None, label_row=None):
    """Structural whitelist plus leak scans over the fields the battery constructs (plan T1.4).

    `config` is accepted for backward compatibility; the rules come from the v2 state contract.
    `state["question"]` is only compared with the gold question text, never scanned.
    """
    contract = contract or load_state_contract()
    questions = questions or {}
    problems = []
    if sorted(state) != sorted(contract["included_keys"]):
        problems.append(f"state keys {sorted(state)} differ from contract")
        return problems
    if state["question"] != record["question"]:
        problems.append("question differs from the gold record question")
    allowed = set(contract["allowed_evidence_columns"])
    for row in state["evidence_rows"]:
        extra = set(row) - allowed
        if extra:
            problems.append(f"evidence columns outside the whitelist: {sorted(extra)}")
        for column, value in row.items():
            if not isinstance(value, str):
                problems.append(f"evidence cell {column} is not a string")
    for field, templates in (("metric_definitions", contract["metric_definition_templates"]),
                             ("scope_notes", contract["scope_note_templates"])):
        lines = state[field]
        if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
            problems.append(f"{field} must be a flat list of strings")
            continue
        for line in lines:
            if not _template_ok(line, templates, record):
                problems.append(f"{field} line does not match a template: {line[:60]}")
    forbidden_keys = [key.lower() for key in contract["forbidden_keys"]]
    for key in list(_all_keys(state)) + list(_all_keys(questions)):
        lowered = str(key).lower()
        for forbidden in forbidden_keys:
            if forbidden in lowered:
                problems.append(f"forbidden key name present: {key}")
    scanned = list(state["metric_definitions"]) + list(state["scope_notes"])
    scanned += list(_string_leaves(state["evidence_rows"])) + list(_string_leaves(questions))
    normalized = [normalize_for_scan(text) for text in scanned]
    for fragment in forbidden_fragments(record, span, label_row):
        target = normalize_for_scan(fragment)
        if target and any(target in text for text in normalized):
            problems.append(f"forbidden fragment present: {fragment[:60]}")
    for label in contract["forbidden_label_strings"]:
        if any(label in text for text in normalized):
            problems.append(f"forbidden label string present: {label}")
    for hit in numeric_scan_hits(scanned, record, contract["numeric_scan"]):
        problems.append(f"gold number not shown to the generator: {hit}")
    if state["marked_answer"].count(MARK_OPEN) != 1 or state["marked_answer"].count(MARK_CLOSE) != 1:
        problems.append("marker must appear exactly once")
    return problems


def build_questions(config, state):
    """Frozen wording from the config; dynamic option lists depend only on the table shape."""
    questions = {}
    row_ids = [row["row_id"] for row in state["evidence_rows"]]
    numeric = [column for column in state["evidence_rows"][0] if column not in {"row_id", "country", "year_month", "stock_code", "product_name"}]
    for key, spec in config["questions"].items():
        question = {"type": spec["type"], "instructions": spec["instructions"]}
        dynamic = spec.get("dynamic_criteria")
        if dynamic == "row_ids_plus_none":
            question["criteria"] = {**{rid: f"Row {rid} of evidence_rows" for rid in row_ids}, "none": "Not tied to a single row"}
        elif dynamic == "numeric_columns_plus_not_a_number_plus_derived":
            question["criteria"] = {**{column: f"Copied from column {column}" for column in numeric},
                                    "derived": "A number computed from the table, such as a difference, sum or percentage",
                                    "not_a_number": "The marked text is not a number"}
        elif dynamic == "rank_positions_plus_unranked":
            question["criteria"] = {**{f"rank_{i}": f"Rank position {i}" for i in range(1, len(row_ids) + 1)},
                                    "unranked": "No rank position is assigned"}
        elif "criteria" in spec:
            question["criteria"] = spec["criteria"]
        questions[key] = question
    return questions


def build_states(config, gold, annotations, texts, sources):
    states, skipped = [], []
    for span in sorted(annotations, key=lambda row: row["annotation_id"]):
        qid = span["question_id"]
        if span["binary_label"] is None:
            skipped.append({"annotation_id": span["annotation_id"], "reason": "label excluded from binary metrics"})
            continue
        if qid not in texts:
            skipped.append({"annotation_id": span["annotation_id"], "reason": "generated text unavailable"})
            continue
        record = gold[qid]
        state = build_state(record, span, texts[qid])
        questions = build_questions(config, state)
        problems = check_state_contract(state, record, span, config, questions=questions)
        if problems:
            raise ValueError(f"{span['annotation_id']}: " + "; ".join(problems))
        states.append({
            "annotation_id": span["annotation_id"],
            "question_id": qid,
            "question_type": record["question_type"],
            "text_source": sources[qid],
            "state": state,
            "questions": questions,
        })
    return states, skipped


# ------------------------------------------------------------- API runner ---

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_POLICY_CACHE = {}


def api_policy(path=None):
    """Retry, stop and transport rules from the v2 config api block."""
    key = str(path or V2_CONFIG_PATH)
    if key not in _POLICY_CACHE:
        _POLICY_CACHE[key] = load_config(key)["api"]
    return _POLICY_CACHE[key]


def load_arms(path=ARMS_CONFIG_PATH):
    """Decision-model arms by arm_id."""
    return {arm["arm_id"]: arm for arm in load_config(path)["arms"]}


def check_arm_endpoint(arm):
    """Hosted arms need https on an allowed host; arms without a key must stay on loopback."""
    endpoint = arm.get("endpoint")
    if not endpoint:
        raise SystemExit(f"arm {arm['arm_id']}: endpoint is not set in the arms config")
    parsed = urllib.parse.urlparse(endpoint)
    host = parsed.hostname or ""
    if arm.get("auth_env"):
        if parsed.scheme != "https" or host not in arm.get("allowed_hosts", []):
            raise SystemExit(f"arm {arm['arm_id']}: a keyed arm must use https on an allowed host, got {parsed.scheme}://{host}")
    elif host not in LOOPBACK_HOSTS or host not in arm.get("allowed_hosts", []):
        raise SystemExit(f"arm {arm['arm_id']}: an arm without a key must use a loopback host, got {host}")
    return endpoint


def read_api_key(arm, environ=None):
    """Key from the arm's environment variable; None for arms without a key. Never printed."""
    env_name = arm.get("auth_env")
    if not env_name:
        return None
    environ = os.environ if environ is None else environ
    key = (environ.get(env_name) or "").strip()
    if not key:
        raise SystemExit(f"Set {env_name} in the environment (never in a file).")
    if any(char.isspace() for char in key):
        raise SystemExit(f"{env_name} contains whitespace; set it again without spaces or line breaks.")
    return key


def redact(text, api_key):
    text = str(text)
    return text.replace(api_key, "[REDACTED]") if api_key else text


def request_payload(state_record, model):
    """One request builder for every arm: the same state and question set, the arm's model id."""
    return {"state": state_record["state"], "model": model, "questions": state_record["questions"]}


def cache_key(payload, repeat):
    return hashlib.sha256((json.dumps(payload, sort_keys=True, ensure_ascii=False) + f"|repeat={repeat}").encode("utf-8")).hexdigest()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Redirects are failures: a 3xx response is raised as HTTPError instead of being followed."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def build_request(url, payload, api_key, user_agent):
    headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": user_agent}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return urllib.request.Request(url, data=data, method="POST", headers=headers)


def post_json(url, payload, api_key, user_agent="bizhallu-decision-battery/2", timeout=60):
    opener = urllib.request.build_opener(_NoRedirect)
    with opener.open(build_request(url, payload, api_key, user_agent), timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _retry_wait(policy, attempt, headers=None):
    backoff = policy["backoff_seconds"]
    wait = backoff[min(attempt, len(backoff) - 1)]
    retry_after = (headers or {}).get("Retry-After") if headers is not None else None
    if retry_after is not None:
        try:
            wait = max(wait, min(float(retry_after), float(policy["retry_after_cap_seconds"])))
        except (TypeError, ValueError):
            pass
    return wait


def call_with_retry(payload, endpoint, api_key, policy=None, sender=None, sleeper=time.sleep):
    """Send one request. Stop on 401/403, retry the configured statuses and transport errors."""
    policy = policy or api_policy()
    if sender is None:
        def sender(url, body, key):
            return post_json(url, body, key, user_agent=policy["user_agent"])
    attempts = policy["max_attempts"]
    for attempt in range(attempts):
        try:
            status, body = sender(endpoint, payload, api_key)
            return {"status": status, "body": body, "attempts": attempt + 1}
        except urllib.error.HTTPError as error:
            text = redact(error.read().decode("utf-8", "replace") if hasattr(error, "read") and error.fp else "", api_key)
            if error.code in policy["fatal_statuses"]:
                raise SystemExit(f"{error.code} from the API: the key or access was refused. Stopping; nothing more will be sent.")
            if error.code in policy["retry_statuses"] and attempt < attempts - 1:
                sleeper(_retry_wait(policy, attempt, error.headers))
                continue
            return {"status": error.code, "body": {"error": text[:2000]}, "attempts": attempt + 1}
        except (OSError, ValueError) as error:
            if attempt < attempts - 1:
                sleeper(_retry_wait(policy, attempt))
                continue
            return {"status": None, "body": {"error": redact(f"{type(error).__name__}: {error}", api_key)[:2000]},
                    "attempts": attempt + 1}
    return {"status": None, "body": {"error": "exhausted"}, "attempts": attempts}


def _is_probability(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0.0 <= value <= 1.0


def usable_response(row, questions):
    """A cached response counts only if it is a 200 whose answers cover every question with valid probabilities."""
    if row.get("status") != 200:
        return False
    response = row.get("response")
    if not isinstance(response, dict) or not isinstance(response.get("answers"), dict):
        return False
    answers = response["answers"]
    for key, spec in questions.items():
        answer = answers.get(key)
        if not isinstance(answer, dict):
            return False
        if spec["type"] == "noul":
            if not _is_probability(answer.get("noul")):
                return False
        else:
            probabilities = answer.get("probabilities")
            if not isinstance(probabilities, dict):
                return False
            options = spec.get("criteria") or {}
            if any(option not in probabilities or not _is_probability(probabilities[option]) for option in options):
                return False
    return True


def read_response_rows(path, log=_stderr):
    """Response rows; a truncated last line (interrupted run) is skipped with a message."""
    rows = []
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        lines = [line for line in handle if line.strip()]
    for index, line in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            if index == len(lines) - 1:
                log(f"{path}: skipped a truncated last line")
                continue
            raise
    return rows


def run_battery(states, arm, api_key, repeats, responses_path, limit=None, policy=None, sender=None,
                sleeper=time.sleep, log=print):
    """Send every (span, repeat) that has no usable cached response yet."""
    policy = policy or api_policy()
    endpoint = check_arm_endpoint(arm)
    responses_path = Path(responses_path)
    usable_keys, failed_rows_on_disk = set(), 0
    questions_by_id = {state["annotation_id"]: state["questions"] for state in states}
    if responses_path.exists():
        for row in read_response_rows(responses_path, log=log):
            if usable_response(row, questions_by_id.get(row.get("annotation_id"), {})):
                usable_keys.add(row["cache_key"])
            else:
                failed_rows_on_disk += 1
    cached_before = len(usable_keys)
    done = failed = consecutive = sent = 0
    succeeded_spans, attempted_spans = set(), set()
    with responses_path.open("a", encoding="utf-8", newline="\n") as handle:
        for state_record in states[:limit]:
            payload = request_payload(state_record, arm["model"])
            for repeat in range(repeats):
                key = cache_key(payload, repeat)
                if key in usable_keys:
                    succeeded_spans.add(state_record["annotation_id"])
                    continue
                attempted_spans.add(state_record["annotation_id"])
                started = time.time()
                outcome = call_with_retry(payload, endpoint, api_key, policy=policy, sender=sender, sleeper=sleeper)
                row = {"annotation_id": state_record["annotation_id"], "question_id": state_record["question_id"],
                       "repeat": repeat, "cache_key": key, "request_sha256": cache_key(payload, -1),
                       "status": outcome["status"], "attempts": outcome["attempts"],
                       "elapsed_seconds": round(time.time() - started, 3), "response": outcome["body"]}
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
                handle.flush()
                sent += 1
                if usable_response(row, state_record["questions"]):
                    usable_keys.add(key)
                    succeeded_spans.add(state_record["annotation_id"])
                    done += 1
                    consecutive = 0
                else:
                    failed += 1
                    consecutive += 1
                    log(f"{state_record['annotation_id']} repeat {repeat}: status {outcome['status']}")
                    if consecutive >= policy["consecutive_failure_limit"]:
                        raise SystemExit(f"{consecutive} consecutive failed calls; stopping. Rows so far are saved in {responses_path}.")
                if sent % 25 == 0:
                    log(f"progress: {sent} calls sent, {done} usable, {failed} failed")
    summary = {"completed": done, "failed": failed, "cached_success_before_run": cached_before,
               "failed_rows_on_disk": failed_rows_on_disk + failed,
               "spans_without_success": sorted(attempted_spans - succeeded_spans)}
    return summary


def check_state_structure(state, contract=None):
    """Structural part of the contract, usable for hand-written control states without a gold record."""
    contract = contract or load_state_contract()
    problems = []
    if sorted(state) != sorted(contract["included_keys"]):
        return [f"state keys {sorted(state)} differ from contract"]
    allowed = set(contract["allowed_evidence_columns"])
    for row in state["evidence_rows"]:
        if set(row) - allowed:
            problems.append(f"evidence columns outside the whitelist: {sorted(set(row) - allowed)}")
        if not all(isinstance(value, str) for value in row.values()):
            problems.append("evidence cells must be strings")
    for field in ("metric_definitions", "scope_notes"):
        if not isinstance(state[field], list) or not all(isinstance(line, str) for line in state[field]):
            problems.append(f"{field} must be a flat list of strings")
    if state["marked_answer"].count(MARK_OPEN) != 1 or state["marked_answer"].count(MARK_CLOSE) != 1:
        problems.append("marker must appear exactly once")
    return problems


def run_smoke(config, arm, api_key, out_path, policy=None, sender=None, sleeper=time.sleep, log=print):
    """Send each hand-written control state three times; report orientation, probability sums and spread."""
    endpoint = check_arm_endpoint(arm)
    controls = config["control_states"]
    report = {"arm_id": arm["arm_id"], "requested_model": arm["model"], "controls": {}, "problems": []}
    all_values = []
    for name in ("control_correct", "control_wrong"):
        state = controls[name]
        problems = check_state_structure(state)
        if problems:
            raise SystemExit(f"{name}: " + "; ".join(problems))
        questions = build_questions(config, state)
        payload = request_payload({"state": state, "questions": questions}, arm["model"])
        calls = []
        for _ in range(3):
            outcome = call_with_retry(payload, endpoint, api_key, policy=policy, sender=sender, sleeper=sleeper)
            if outcome["status"] != 200 or not usable_response({"status": 200, "response": outcome["body"]}, questions):
                raise SystemExit(f"{name}: unusable response (status {outcome['status']})")
            calls.append(outcome["body"])
        answers = [body["answers"] for body in calls]
        yes = [answer["slot_correct"]["noul"] for answer in answers]
        sums = {key: [round(sum(answer[key]["probabilities"].values()), 6) for answer in answers]
                for key in ("status", "value_faithful") if key in questions}
        flat = [_flatten_probabilities(answer) for answer in answers]
        spread = max((max(values) - min(values) for values in zip(*flat)), default=0.0)
        all_values.append(spread)
        report["controls"][name] = {"slot_correct_yes": yes, "probability_sums": sums,
                                    "max_abs_difference_across_3_calls": spread,
                                    "response_models": [body.get("model") for body in calls]}
        if name == "control_correct" and not all(value > 0.5 for value in yes):
            report["problems"].append("control_correct: slot_correct yes-probability is not above 0.5")
        if name == "control_wrong" and not all(value < 0.5 for value in yes):
            report["problems"].append("control_wrong: slot_correct yes-probability is not below 0.5")
        for key, values in sums.items():
            if any(not 0.99 <= value <= 1.01 for value in values):
                report["problems"].append(f"{name}: {key} probabilities do not sum to 1")
    report["deterministic"] = max(all_values) <= 0.000001
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)
    log(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def _flatten_probabilities(answers):
    values = []
    for key in sorted(answers):
        answer = answers[key]
        if "noul" in answer:
            values.append(float(answer["noul"]))
        for option in sorted(answer.get("probabilities", {})):
            values.append(float(answer["probabilities"][option]))
    return values


# ------------------------------------------------------------------ score ---

def derived_scores(response):
    answers = response.get("answers", {})
    scores = {}
    if "supported" in answers:
        scores["jev_risk"] = 1.0 - float(answers["supported"]["noul"])
    if "status" in answers:
        scores["jev_conflict"] = float(answers["status"]["probabilities"].get("m2", 0.0))
    if "present" in answers:
        scores["jev_absent"] = 1.0 - float(answers["present"]["noul"])
    if "conclusion" in answers:
        scores["jev_conclusion"] = float(answers["conclusion"]["noul"])
    for key in ("relation", "source_row", "source_column", "rank_claim", "direction_claim"):
        if key in answers:
            scores[f"{key}_choice"] = answers[key].get("choice")
    return scores


def aggregate_responses(response_rows):
    """Mean probability per span across repeats plus argmax flip rates."""
    per_span = defaultdict(list)
    for row in response_rows:
        if row.get("status") == 200:
            per_span[row["annotation_id"]].append(row["response"])
    aggregated = {}
    for annotation_id, responses in per_span.items():
        numeric = defaultdict(list)
        choices = defaultdict(list)
        models = Counter()
        for response in responses:
            models[response.get("model")] += 1
            for key, value in derived_scores(response).items():
                (choices if key.endswith("_choice") else numeric)[key].append(value)
        item = {key: sum(values) / len(values) for key, values in numeric.items()}
        item["repeats"] = len(responses)
        item["models"] = dict(models)
        item["choice_modes"] = {key: Counter(values).most_common(1)[0][0] for key, values in choices.items()}
        item["choice_flip_rate"] = {key: 1 - Counter(values).most_common(1)[0][1] / len(values) for key, values in choices.items()}
        aggregated[annotation_id] = item
    return aggregated


def score_rows(aggregated, annotations, signals, checker_results):
    checker = {item["annotation_id"]: item for item in checker_results}
    rows = []
    for span in annotations:
        aid = span["annotation_id"]
        if aid not in aggregated or span["binary_label"] is None:
            continue
        stored = signals.get(aid, {})
        row = {"annotation_id": aid, "question_id": span["question_id"], "split": span["split"] if "split" in span else None,
               "fact_type": span["fact_type"], "binary_label": span["binary_label"],
               "evidence_cluster": stored.get("evidence_cluster"), "is_month": span["fact_type"] == "month",
               "checker_verdict": checker.get(aid, {}).get("verdict"), "checker_mechanism": checker.get(aid, {}).get("mechanism"),
               "all_positive": 1.0}
        row.update({key: stored[key] for key in REFERENCE_ARMS if key in stored})
        row.update({key: value for key, value in aggregated[aid].items() if isinstance(value, float)})
        rows.append(row)
    return rows


def attach_splits(rows, gold):
    for row in rows:
        row["split"] = gold[row["question_id"]]["split"]
    return rows


def evaluate_arms(rows, arms):
    dev = [row for row in rows if row["split"] == "dev"]
    test = [row for row in rows if row["split"] == "test"]
    test_main = [row for row in test if not row["is_month"]]
    report = {"counts": {"dev": len(dev), "test": len(test), "test_non_month": len(test_main),
                         "test_positive": sum(r["binary_label"] for r in test)}, "arms": {}, "thresholds": {}}
    for arm in arms:
        usable = [row for row in rows if arm in row and row[arm] is not None]
        if len(usable) != len(rows):
            report["arms"][arm] = {"status": "missing for some spans", "available": len(usable)}
            continue
        try:
            threshold = 0.5 if arm == "all_positive" else metrics.dev_threshold([r for r in usable if r["split"] == "dev"], arm)
        except ValueError as error:
            report["arms"][arm] = {"status": f"threshold not selectable: {error}"}
            continue
        report["thresholds"][arm] = threshold
        report["arms"][arm] = {}
        for name, subset in (("dev", dev), ("test", test), ("test_non_month", test_main)):
            if subset:
                report["arms"][arm][name] = metrics.evaluate([r["binary_label"] for r in subset], [r[arm] for r in subset], threshold)
    return report


def paired_intervals(rows, thresholds, comparisons, replicates, seed):
    test = [row for row in rows if row["split"] == "test" and all(a in row and b in row for a, b in comparisons)]
    if not test:
        return {"status": "no test rows"}
    return metrics.paired_cluster_bootstrap(test, thresholds, comparisons, "question_id", replicates=replicates, seed=seed)


def mechanism_table(rows, score="jev_risk", threshold=None):
    table = {}
    for mechanism, group in groupby_key(rows, "checker_mechanism").items():
        positives = [r for r in group if r["binary_label"] == 1]
        flagged = [r for r in positives if threshold is not None and score in r and r[score] >= threshold]
        table[mechanism] = {"spans": len(group), "hallucinated": len(positives),
                            "flagged_hallucinated": len(flagged), "recall": rule_checker.wilson(len(flagged), len(positives)) if positives and threshold is not None else None}
    return table


def groupby_key(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[row.get(key)].append(row)
    return groups


def render_markdown(report):
    lines = ["# Jev evidence battery v1: retrospective comparison", "",
             f"Spans scored: dev {report['evaluation']['counts']['dev']}, test {report['evaluation']['counts']['test']} "
             f"(non-month {report['evaluation']['counts']['test_non_month']}).", "",
             "| arm | dev threshold | test AP | test AUROC | test F1 | non-month test AP |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for arm, values in report["evaluation"]["arms"].items():
        if "test" not in values:
            lines.append(f"| {arm} | n/a | {values.get('status', '')} | | | |")
            continue
        t, m = values["test"], values.get("test_non_month", {})
        fmt = lambda x: "n/a" if x is None else f"{x:.3f}"  # noqa: E731
        lines.append(f"| {arm} | {report['evaluation']['thresholds'][arm]:.4f} | {fmt(t['average_precision'])} | {fmt(t['auroc'])} | {fmt(t['f1'])} | {fmt(m.get('average_precision'))} |")
    lines += ["", "Paired test intervals (question clusters):", ""]
    for interval in report.get("paired_intervals", {}).get("intervals", []):
        if interval["metric"] in {"average_precision", "f1"}:
            lines.append(f"- {interval['signal']} minus {interval['reference']} {interval['metric']}: "
                         f"{interval['point_difference']:+.4f} [{interval['lower_95']:+.4f}, {interval['upper_95']:+.4f}]")
    lines += ["", "Mechanism strata (checker, label-blind) and jev_risk recall at the dev threshold:", "",
              "| mechanism | spans | hallucinated | flagged | recall |", "| --- | ---: | ---: | ---: | --- |"]
    for mechanism, values in report["mechanisms"].items():
        recall = values["recall"]
        text = "n/a" if recall is None else f"{recall['point']:.2f} [{recall['lower_95']:.2f}, {recall['upper_95']:.2f}]"
        lines.append(f"| {mechanism} | {values['spans']} | {values['hallucinated']} | {values['flagged_hallucinated']} | {text} |")
    lines += ["", "Model versions seen: " + json.dumps(report["model_versions"]),
              "", "Claim boundary: retrospective estimation on AI-assisted provisional labels; historical published values unchanged; "
              "the checker replicates the label rule and is an audit reference, not an independent detector."]
    return "\n".join(lines) + "\n"


def score_battery(config, gold, annotations, responses_path, checker_results, signals, replicates, seed):
    responses = read_jsonl(responses_path) if responses_path.exists() else []
    aggregated = aggregate_responses(responses)
    rows = attach_splits(score_rows(aggregated, annotations, signals, checker_results), gold)
    if not rows:
        raise SystemExit("No successful responses to score; run the battery first.")
    jev_arms = [key for key in ("jev_risk", "jev_conflict", "jev_absent") if all(key in row for row in rows)]
    arms = jev_arms + [arm for arm in REFERENCE_ARMS if all(arm in row for row in rows)]
    evaluation = evaluate_arms(rows, arms)
    comparisons = [(a, b) for a in jev_arms[:1] for b in ("one_minus_min_top2_margin", "dev_fact_type_prior", "all_positive") if b in evaluation["thresholds"]]
    intervals = paired_intervals(rows, evaluation["thresholds"], comparisons, replicates, seed) if comparisons and jev_arms and jev_arms[0] in evaluation["thresholds"] else {"status": "not computed"}
    models = Counter()
    for item in aggregated.values():
        for model, count in item["models"].items():
            models[model] += count
    flip = defaultdict(list)
    for item in aggregated.values():
        for key, value in item["choice_flip_rate"].items():
            flip[key].append(value)
    report = {
        "battery_id": config["battery_id"], "model_pinned": config["api"]["model"], "model_versions": dict(models),
        "unexpected_model_versions": [m for m in models if m != config["api"]["model"]],
        "evaluation": evaluation, "paired_intervals": intervals,
        "mechanisms": mechanism_table(rows, "jev_risk", evaluation["thresholds"].get("jev_risk")),
        "choice_flip_rate_mean": {key: sum(values) / len(values) for key, values in flip.items()},
        "repeats_per_span": Counter(item["repeats"] for item in aggregated.values()),
        "claim_boundary": config["claim_boundary"],
    }
    return report, rows


# --------------------------------------------------------------- validate ---

def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate(config_path=CONFIG_PATH, output_dir=OUTPUT_DIR, generations_path=None, require_local=False):
    """Public tier by default (nine demo answers); require_local checks the full local package."""
    config = load_config(config_path)
    failures = []
    for key in ("supported", "present", "status", "relation", "conclusion", "source_row", "source_column", "rank_claim", "direction_claim"):
        if key not in config["questions"]:
            failures.append(f"missing question {key}")
    for key, spec in config["questions"].items():
        text = json.dumps(spec).lower()
        if "gold" in text or "label" in text.replace("labelled", ""):
            failures.append(f"question {key} mentions gold or labels")
    if config["api"]["model"] == "jev-latest":
        failures.append("model must be pinned, not jev-latest")
    gold = load_gold()
    annotations = load_annotations()
    if require_local and not (generations_path and Path(generations_path).exists()):
        failures.append(f"local generation file not found: {generations_path}")
    texts, sources = load_generated_texts(generations_path)
    try:
        states, skipped = build_states(config, gold, annotations, texts, sources)
    except ValueError as error:
        failures.append(str(error))
        states, skipped = [], []
    if not states:
        failures.append("no states were built")
    if require_local:
        if set(sources.values()) != {"local_generations"}:
            failures.append(f"text sources are not all local: {dict(Counter(sources.values()))}")
        if len(states) != 205 or skipped:
            failures.append(f"expected 205 states and 0 skipped, got {len(states)} and {len(skipped)}")
    checker = rule_checker.run_checker(config, gold, annotations, texts)
    audit = rule_checker.checker_audit(checker, annotations) if checker else None
    result = {"config_sha256": file_sha256(config_path), "script_sha256": file_sha256(__file__),
              "tier": "local" if require_local else "public",
              "states_built": len(states), "states_skipped": len(skipped), "text_sources": dict(Counter(sources.values())),
              "checker_audit": audit, "num_failures": len(failures), "failures": failures,
              "scope": "offline; no API call; the sealed confirmation manifests are never read"}
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "validation.json").open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    return result


# ------------------------------------------------------------------- main ---

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["build", "check", "run", "smoke", "score", "validate"])
    parser.add_argument("--generations", default=str(DEFAULT_GENERATIONS), help="local qwen_full100_generations.jsonl")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--split", choices=["dev", "test", "all"], default="all")
    parser.add_argument("--replicates", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260904)
    parser.add_argument("--model", default=None, help="override the pinned model id (recorded in the report)")
    parser.add_argument("--require-local", action="store_true",
                        help="validate: require the local generation file and all 205 states")
    parser.add_argument("--arm", default=None, help="run, smoke: arm_id from the arms config")
    parser.add_argument("--public-demo", action="store_true",
                        help="run, score: allow the nine public demo answers instead of the local generation file")
    args = parser.parse_args(argv)
    if args.repeats is not None and (args.repeats < 1 or args.limit is None):
        parser.error("--repeats must be at least 1 and is only allowed together with --limit")

    config = load_config()
    if args.model:
        config["api"]["model"] = args.model
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    gold = load_gold()
    annotations = load_annotations()
    texts, sources = load_generated_texts(args.generations)
    uses_demo = not Path(args.generations).exists() or "public_demo_bundle" in sources.values()
    if uses_demo and args.command in {"run", "score"} and not args.public_demo:
        raise SystemExit(f"generation file not found or incomplete: {args.generations}; "
                         "pass --public-demo to use the nine public demo answers")
    if uses_demo and args.command in {"build", "check"}:
        _stderr(f"using public demo bundle: {dict(Counter(sources.values()))}")

    if args.command == "smoke":
        if not args.arm:
            parser.error("smoke needs --arm")
        v2 = load_config(V2_CONFIG_PATH)
        arm = load_arms()[args.arm]
        out_path = PROJECT_ROOT / "outputs" / "decision_battery_v2" / arm["arm_id"] / "smoke.json"
        report = run_smoke(v2, arm, read_api_key(arm), out_path)
        return 1 if report["problems"] else 0

    if args.command == "validate":
        result = validate(generations_path=args.generations if args.require_local else None,
                          output_dir=output_dir, require_local=args.require_local)
        print(json.dumps({k: v for k, v in result.items() if k != "checker_audit"}, indent=2))
        return 1 if result["num_failures"] else 0

    states, skipped = [], []
    if args.command in {"build", "run"}:
        states, skipped = build_states(config, gold, annotations, texts, sources)
        if args.split != "all":
            states = [s for s in states if gold[s["question_id"]]["split"] == args.split]
    states_path = output_dir / "states.jsonl"

    if args.command == "build":
        with states_path.open("w", encoding="utf-8") as handle:
            for state in states:
                handle.write(json.dumps(state, ensure_ascii=False) + "\n")
        print(json.dumps({"states": len(states), "skipped": skipped[:5], "skipped_count": len(skipped),
                          "text_sources": dict(Counter(sources.values())), "path": str(states_path)}, indent=2, ensure_ascii=False))
        return 0

    checker_results = rule_checker.run_checker(config, gold, annotations, texts)
    if args.command == "check":
        with (output_dir / "checker.jsonl").open("w", encoding="utf-8") as handle:
            for item in checker_results:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        audit = rule_checker.checker_audit(checker_results, annotations)
        with (output_dir / "checker_audit.json").open("w", encoding="utf-8") as handle:
            json.dump(audit, handle, indent=2, ensure_ascii=False)
        print(json.dumps(audit, indent=2, ensure_ascii=False))
        return 0

    responses_path = output_dir / "responses.jsonl"
    if args.command == "run":
        if not args.arm:
            parser.error("run needs --arm")
        arm = load_arms()[args.arm]
        api_key = read_api_key(arm)
        if args.repeats is not None:
            repeats = args.repeats
        else:
            role = "dev" if args.split == "dev" else "eval"
            repeats = (arm.get("repeats") or {}).get(role)
            if not repeats:
                raise SystemExit(f"arm {arm['arm_id']}: repeats.{role} is not set in the arms config")
        summary = run_battery(states, arm, api_key, repeats, responses_path, limit=args.limit)
        print(json.dumps(summary, indent=2))
        return 0

    signals = load_stored_signals()
    report, rows = score_battery(config, gold, annotations, responses_path, checker_results, signals, args.replicates, args.seed)
    with (output_dir / "report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False, default=str)
    with (output_dir / "span_scores.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = sorted({key for row in rows for key in row})
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (output_dir / "report.md").write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
