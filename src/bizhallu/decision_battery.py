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
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import detector_metrics as metrics  # noqa: E402
from bizhallu import evidence, rule_checker  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
V1_CONFIG_PATH = PROJECT_ROOT / "configs" / "jev_battery_v1.json"
V2_CONFIG_PATH = PROJECT_ROOT / "configs" / "decision_battery_v2.json"
CONFIG_PATH = V2_CONFIG_PATH
ARMS_CONFIG_PATH = PROJECT_ROOT / "configs" / "decision_battery_arms_v1.json"
HELDOUT_SLICE_PATH = PROJECT_ROOT / "configs" / "heldout_slice_v1.json"
GOLD_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
ANNOTATIONS_PATH = PROJECT_ROOT / "data" / "annotations" / "span_annotations_full100_draft.jsonl"
DEMO_PATH = PROJECT_ROOT / "reports" / "bizhallu_demo_v2_data.json"
SCORES_PATH = PROJECT_ROOT / "results" / "full100_statistics_v2_scores.csv"
DEFAULT_GENERATIONS = PROJECT_ROOT / "outputs" / "qwen_full100_generations.jsonl"
DEFAULT_TRACES = PROJECT_ROOT / "outputs" / "qwen_full100_token_traces.jsonl"
OUTPUT_ROOT = PROJECT_ROOT / "outputs" / "decision_battery_v2"
OUTPUT_DIR = OUTPUT_ROOT
SPAN_SET_FILES = {
    "spans_full100_v1.jsonl": "full100_205",
    "spans_extractor_only_devtest_v1.jsonl": "extractor_only_devtest_v1",
    "spans_heldout_v1.jsonl": "heldout_v1",
    "span_annotations_full100_draft.jsonl": "full100_205",
}
NUMERIC_DISPLAY_COLUMNS = ["net_revenue_gbp", "gross_positive_revenue_gbp", "cancellation_return_revenue_gbp", "invoice_count"]
CONFIG_STATUSES = {"draft_wording_not_frozen_not_run", "final_wording_not_frozen", "frozen"}

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


def _dynamic_criteria(kind, template, state):
    """Option lists that depend only on the table shape, from the config's criteria_template."""
    if kind not in {"rank_positions", "row_ids", "numeric_columns"}:
        raise ValueError(f"unknown dynamic_criteria: {kind}")
    rows = state["evidence_rows"]
    criteria = {}
    for key, text in template.items():
        if key == "p{i}":
            for index in range(1, len(rows) + 1):
                criteria[f"p{index}"] = text.replace("{i}", str(index))
        elif key == "{row_id}":
            for row in rows:
                criteria[row["row_id"]] = text.replace("{row_id}", row["row_id"])
        elif key == "c{i}":
            columns = [column for column in rows[0] if column in NUMERIC_DISPLAY_COLUMNS]
            for index, column in enumerate(columns, start=1):
                criteria[f"c{index}"] = text.replace("{column_name}", column)
        elif "{" in key:
            raise ValueError(f"unknown criteria template key: {key}")
        else:
            criteria[key] = text
    return criteria


def build_questions(config, state):
    """Question wording from the config; dynamic option lists depend only on the table shape."""
    questions = {}
    for key, spec in config["questions"].items():
        question = {"type": spec["type"], "instructions": spec["instructions"]}
        if "dynamic_criteria" in spec:
            question["criteria"] = _dynamic_criteria(spec["dynamic_criteria"], spec["criteria_template"], state)
        elif "criteria" in spec:
            question["criteria"] = spec["criteria"]
        else:
            raise ValueError(f"question {key} has no criteria in the config")
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
            "role": record["split"],
            "text_source": sources[qid],
            "state": state,
            "questions": questions,
        })
    return states, skipped


# ------------------------------------------------------------ states files ---

MODULE_DIR = Path(__file__).resolve().parent
ENFORCED_MODULES = ["evidence.py", "rule_checker.py", "span_signals.py"]


def file_sha256(path):
    """SHA-256 of the file with line endings normalised to LF, so Windows and Git checkouts agree."""
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _sha_or_none(path):
    return file_sha256(path) if path and Path(path).exists() else None


def span_set_id_for(path):
    name = Path(path).name
    if name not in SPAN_SET_FILES:
        raise SystemExit(f"unknown span file name: {name}; expected one of {sorted(SPAN_SET_FILES)}")
    return SPAN_SET_FILES[name]


def states_paths(span_set_id, root=None):
    root = Path(root or OUTPUT_ROOT)
    return root / f"states_{span_set_id}.jsonl", root / f"states_{span_set_id}_manifest.json"


def manifest_inputs(config_path, arms_path, spans_path, generations_path):
    """Enforced input hashes (they decide what is sent) and informational module hashes."""
    enforced = {
        "config": _sha_or_none(config_path),
        "arms_config": _sha_or_none(arms_path),
        "gold": _sha_or_none(GOLD_PATH),
        "spans": _sha_or_none(spans_path),
        "generations": _sha_or_none(generations_path),
    }
    for module in ENFORCED_MODULES:
        enforced[f"module:{module}"] = _sha_or_none(MODULE_DIR / module)
    informational = {f"module:{path.name}": file_sha256(path)
                     for path in sorted(MODULE_DIR.glob("*.py")) if path.name not in ENFORCED_MODULES}
    return enforced, informational


def _canonical_sha256(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def write_states(states, span_set_id, config_path, arms_path, spans_path, generations_path, root=None):
    """Write every state of one span set, each with its role, plus the manifest that run checks."""
    states_path, manifest_path = states_paths(span_set_id, root)
    states_path.parent.mkdir(parents=True, exist_ok=True)
    with states_path.open("w", encoding="utf-8", newline="\n") as handle:
        for state in states:
            handle.write(json.dumps(state, ensure_ascii=False) + "\n")
    enforced, informational = manifest_inputs(config_path, arms_path, spans_path, generations_path)
    enforced["states"] = file_sha256(states_path)
    manifest = {"span_set_id": span_set_id, "state_count": len(states),
                "roles": dict(Counter(state["role"] for state in states)),
                "enforced": enforced, "enforced_sha256": _canonical_sha256(enforced),
                "informational": informational}
    with manifest_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
    return states_path, manifest_path


def load_states(span_set_id, config_path, arms_path, spans_path, generations_path, root=None):
    """States as reviewed at build time; stop if any enforced input changed since then."""
    states_path, manifest_path = states_paths(span_set_id, root)
    if not states_path.exists() or not manifest_path.exists():
        raise SystemExit(f"{states_path.name} or its manifest is missing; run build first")
    with manifest_path.open("r", encoding="utf-8-sig") as handle:
        manifest = json.load(handle)
    enforced, _ = manifest_inputs(config_path, arms_path, spans_path, generations_path)
    enforced["states"] = file_sha256(states_path)
    changed = sorted(key for key in set(enforced) | set(manifest["enforced"])
                     if enforced.get(key) != manifest["enforced"].get(key))
    if changed:
        raise SystemExit(f"states manifest does not match the current inputs: {changed}; run build again")
    return read_jsonl(states_path), manifest


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


def cache_key(payload, repeat, arm_id="", endpoint=""):
    """One cache entry per request, repeat, arm and endpoint, so a new endpoint never reuses old rows."""
    return hashlib.sha256((json.dumps(payload, sort_keys=True, ensure_ascii=False)
                           + f"|repeat={repeat}|arm={arm_id}|endpoint={endpoint}").encode("utf-8")).hexdigest()


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
                sleeper=time.sleep, log=print, provenance=None):
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
                key = cache_key(payload, repeat, arm["arm_id"], endpoint)
                if key in usable_keys:
                    succeeded_spans.add(state_record["annotation_id"])
                    continue
                attempted_spans.add(state_record["annotation_id"])
                started = time.time()
                outcome = call_with_retry(payload, endpoint, api_key, policy=policy, sender=sender, sleeper=sleeper)
                row = {"annotation_id": state_record["annotation_id"], "question_id": state_record["question_id"],
                       "role": state_record.get("role"), "repeat": repeat, "cache_key": key,
                       "request_sha256": request_hash(payload, arm["arm_id"], endpoint),
                       "battery_id": (provenance or {}).get("battery_id"),
                       "config_sha256": (provenance or {}).get("config_sha256"),
                       "arm_id": arm["arm_id"], "endpoint": endpoint, "requested_model": arm["model"],
                       "called_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
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

_FORMULA = re.compile(r"^probabilities\.(\w+)(?:\s*\+\s*probabilities\.(\w+))?$")


def evaluate_formula(formula, answer):
    """The three formula forms allowed by derived_scores_policy; anything else is an error."""
    formula = formula.strip()
    if formula == "1 - noul":
        return 1.0 - float(answer["noul"])
    match = _FORMULA.match(formula)
    if not match:
        raise ValueError(f"unsupported derived-score formula: {formula}")
    total = float(answer["probabilities"][match.group(1)])
    if match.group(2):
        total += float(answer["probabilities"][match.group(2)])
    return total


def derived_scores(response, config):
    """Scores named in the config plus the argmax choice of every descriptive question and of status."""
    answers = response["answers"]
    scores = {}
    for name, spec in config["derived_scores"].items():
        scores[name] = evaluate_formula(spec["formula"], answers[spec["question"]])
    for key, spec in config["questions"].items():
        if (spec.get("role") == "descriptive" or key == "status") and key in answers:
            scores[f"{key}_choice"] = answers[key].get("choice")
    return scores


def request_hash(payload, arm_id, endpoint):
    return hashlib.sha256((json.dumps(payload, sort_keys=True, ensure_ascii=False)
                           + f"|arm={arm_id}|endpoint={endpoint}").encode("utf-8")).hexdigest()


def expected_request_hashes(states, arm):
    endpoint = arm.get("endpoint") or ""
    return {state["annotation_id"]: request_hash(request_payload(state, arm["model"]), arm["arm_id"], endpoint)
            for state in states}


def select_scored_rows(response_rows, expected):
    """Keep only 200 rows produced by the current config, arm and endpoint; count the rest."""
    kept, excluded = [], 0
    for row in response_rows:
        if row.get("status") != 200:
            continue
        if expected.get(row.get("annotation_id")) == row.get("request_sha256"):
            kept.append(row)
        else:
            excluded += 1
    return kept, excluded


def repeat_shortfalls(aggregated, states, arm):
    """Spans whose number of scored repeats differs from the arm's setting for their role."""
    roles = {state["annotation_id"]: state.get("role") for state in states}
    problems = []
    for annotation_id, item in aggregated.items():
        role_key = "dev" if roles.get(annotation_id) == "dev" else "eval"
        required = (arm.get("repeats") or {}).get(role_key)
        if required is not None and item["repeats"] != required:
            problems.append(annotation_id)
    return sorted(problems)


def aggregate_responses(response_rows, config):
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
            for key, value in derived_scores(response, config).items():
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
        row = {"annotation_id": aid, "question_id": span["question_id"], "split": span.get("split"),
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


def mechanism_table(rows, score="dm_risk", threshold=None):
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


def _fmt(value):
    return "n/a" if value is None else f"{value:.3f}"


def render_markdown(report):
    lines = []
    if report.get("partial"):
        lines += ["PARTIAL: some spans have fewer scored repeats than the arm setting; see repeat_shortfalls.", ""]
    lines += [f"# Decision battery: {report['battery_id']}, arm {report.get('arm_id')}", "",
              f"Spans scored: dev {report['evaluation']['counts']['dev']}, test {report['evaluation']['counts']['test']} "
              f"(non-month {report['evaluation']['counts']['test_non_month']}). "
              f"Response rows from another config, arm or endpoint excluded: {report.get('excluded_rows', 0)}.", "",
              "| arm | dev threshold | test AP | test AUROC | test F1 | non-month test AP |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for arm, values in report["evaluation"]["arms"].items():
        if "test" not in values:
            lines.append(f"| {arm} | n/a | {values.get('status', '')} | | | |")
            continue
        t, m = values["test"], values.get("test_non_month", {})
        lines.append(f"| {arm} | {report['evaluation']['thresholds'][arm]:.4f} | {_fmt(t['average_precision'])} | "
                     f"{_fmt(t['auroc'])} | {_fmt(t['f1'])} | {_fmt(m.get('average_precision'))} |")
    lines += ["", "Paired test intervals (question clusters):", ""]
    for interval in report.get("paired_intervals", {}).get("intervals", []):
        if interval["metric"] in {"average_precision", "f1"}:
            lines.append(f"- {interval['signal']} minus {interval['reference']} {interval['metric']}: "
                         f"{interval['point_difference']:+.4f} [{interval['lower_95']:+.4f}, {interval['upper_95']:+.4f}]")
    lines += ["", "Mechanism strata (checker, exploratory) and dm_risk recall at the dev threshold:", "",
              "| mechanism | spans | hallucinated | flagged | recall |", "| --- | ---: | ---: | ---: | --- |"]
    for mechanism, values in report["mechanisms"].items():
        recall = values["recall"]
        text = "n/a" if recall is None else f"{recall['point']:.2f} [{recall['lower_95']:.2f}, {recall['upper_95']:.2f}]"
        lines.append(f"| {mechanism} | {values['spans']} | {values['hallucinated']} | {values['flagged_hallucinated']} | {text} |")
    lines += ["", f"Requested model: {report['model_pinned']}. Model versions seen: {json.dumps(report['model_versions'])}."]
    if report["unexpected_model_versions"]:
        lines.append(f"Responses from a model other than the requested one: {report['unexpected_model_versions']}.")
    lines += ["", "Claim boundary: retrospective estimation on AI-assisted provisional labels; historical published values unchanged; "
              "the checker replicates the label rule and is an audit reference, not an independent detector."]
    return "\n".join(lines) + "\n"


def score_battery(config, gold, annotations, response_rows, checker_results, signals, replicates, seed,
                  arm=None, excluded_rows=0, partial=False, repeat_shortfall_ids=()):
    aggregated = aggregate_responses(response_rows, config)
    rows = attach_splits(score_rows(aggregated, annotations, signals, checker_results), gold)
    if not rows:
        raise SystemExit("No successful responses to score; run the battery first.")
    dm_arms = [name for name, spec in config["derived_scores"].items() if spec.get("label_axis") == "slot"]
    arms = dm_arms + [name for name in REFERENCE_ARMS if all(name in row for row in rows)]
    evaluation = evaluate_arms(rows, arms)
    primary = "dm_risk"
    comparisons = [(primary, other) for other in ("one_minus_min_top2_margin", "dev_fact_type_prior", "all_positive")
                   if other in evaluation["thresholds"]]
    intervals = (paired_intervals(rows, evaluation["thresholds"], comparisons, replicates, seed)
                 if comparisons and primary in evaluation["thresholds"] else {"status": f"not computed: {primary} unavailable"})
    models = Counter()
    for item in aggregated.values():
        for model, count in item["models"].items():
            models[model] += count
    flip = defaultdict(list)
    for item in aggregated.values():
        for key, value in item["choice_flip_rate"].items():
            flip[key].append(value)
    requested = (arm or {}).get("model")
    report = {
        "battery_id": config["battery_id"], "arm_id": (arm or {}).get("arm_id"),
        "model_pinned": requested, "model_versions": dict(models),
        "unexpected_model_versions": sorted(m for m in models if m != requested),
        "excluded_rows": excluded_rows, "partial": bool(partial), "repeat_shortfalls": list(repeat_shortfall_ids),
        "evaluation": evaluation, "paired_intervals": intervals,
        "mechanisms": mechanism_table(rows, primary, evaluation["thresholds"].get(primary)),
        "choice_flip_rate_mean": {key: sum(values) / len(values) for key, values in flip.items()},
        "repeats_per_span": Counter(item["repeats"] for item in aggregated.values()),
        "claim_boundary": config["claim_boundary"],
    }
    return report, rows


# --------------------------------------------------------------- validate ---

def config_problems(config, arms):
    """Structural checks of the wording config and the arms config; reads every key from the config."""
    problems = []
    if config.get("status") not in CONFIG_STATUSES:
        problems.append(f"config status {config.get('status')!r} is not one of {sorted(CONFIG_STATUSES)}")
    questions = config["questions"]
    for key, spec in questions.items():
        if "dynamic_criteria" not in spec and "criteria" not in spec:
            problems.append(f"question {key} has no criteria")
        text = json.dumps(spec).lower()
        if "gold" in text or "label" in text.replace("labelled", ""):
            problems.append(f"question {key} mentions gold or labels")
    allowed = config["derived_scores_policy"]["allowed_formula_forms"]
    for name, spec in config["derived_scores"].items():
        question = questions.get(spec.get("question"))
        if question is None:
            problems.append(f"derived score {name} names a missing question")
            continue
        formula = spec["formula"].strip()
        if formula == "1 - noul":
            if question["type"] != "noul":
                problems.append(f"derived score {name} uses noul on a {question['type']} question")
            continue
        match = _FORMULA.match(formula)
        if not match or not allowed:
            problems.append(f"derived score {name} has an unsupported formula: {formula}")
            continue
        options = question.get("criteria") or {}
        for option in [match.group(1), match.group(2)]:
            if option and option not in options:
                problems.append(f"derived score {name} names option {option} that {spec['question']} does not have")
    for arm in arms.values():
        if arm.get("model") in {"jev-latest", "jev-preview"}:
            problems.append(f"arm {arm['arm_id']} uses an alias model id; pin a version")
    return problems


def validate(config_path=CONFIG_PATH, output_dir=OUTPUT_DIR, generations_path=None, require_local=False,
             arms_path=ARMS_CONFIG_PATH):
    """Public tier by default (nine demo answers); require_local checks the full local package."""
    config = load_config(config_path)
    failures = config_problems(config, load_arms(arms_path))
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
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "validation.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
    return result


# ------------------------------------------------------------------- main ---

def _write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["build", "check", "run", "smoke", "score", "validate"])
    parser.add_argument("--config", default=str(CONFIG_PATH), help="wording and analysis config")
    parser.add_argument("--generations", default=str(DEFAULT_GENERATIONS), help="local qwen_full100_generations.jsonl")
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--split", choices=["dev", "test", "all"], default=None)
    parser.add_argument("--replicates", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20260904)
    parser.add_argument("--require-local", action="store_true",
                        help="validate: require the local generation file and all 205 states")
    parser.add_argument("--arm", default=None, help="run, smoke, score: arm_id from the arms config")
    parser.add_argument("--allow-partial", action="store_true",
                        help="score: report even if some spans have fewer repeats than the arm setting")
    parser.add_argument("--public-demo", action="store_true",
                        help="run, score: allow the nine public demo answers instead of the local generation file")
    args = parser.parse_args(argv)
    if args.repeats is not None and (args.repeats < 1 or args.limit is None):
        parser.error("--repeats must be at least 1 and is only allowed together with --limit")
    if args.command == "build" and args.split is not None:
        parser.error("build writes every state of the span set; it does not take --split")
    split = args.split or "all"

    config_path = Path(args.config)
    config = load_config(config_path)
    gold = load_gold()
    annotations = load_annotations()
    texts, sources = load_generated_texts(args.generations)
    uses_demo = not Path(args.generations).exists() or "public_demo_bundle" in sources.values()
    if uses_demo and args.command in {"run", "score"} and not args.public_demo:
        raise SystemExit(f"generation file not found or incomplete: {args.generations}; "
                         "pass --public-demo to use the nine public demo answers")
    if uses_demo and args.command in {"build", "check"}:
        _stderr(f"using public demo bundle: {dict(Counter(sources.values()))}")
    span_set_id = span_set_id_for(ANNOTATIONS_PATH)
    manifest_args = (config_path, ARMS_CONFIG_PATH, ANNOTATIONS_PATH, args.generations)

    if args.command == "smoke":
        if not args.arm:
            parser.error("smoke needs --arm")
        arm = load_arms()[args.arm]
        report = run_smoke(config, arm, read_api_key(arm), OUTPUT_ROOT / arm["arm_id"] / "smoke.json")
        return 1 if report["problems"] else 0

    if args.command == "validate":
        result = validate(config_path=config_path, generations_path=args.generations if args.require_local else None,
                          output_dir=OUTPUT_ROOT, require_local=args.require_local)
        print(json.dumps({k: v for k, v in result.items() if k != "checker_audit"}, indent=2))
        return 1 if result["num_failures"] else 0

    if args.command == "build":
        states, skipped = build_states(config, gold, annotations, texts, sources)
        states_path, manifest_path = write_states(states, span_set_id, *manifest_args)
        print(json.dumps({"states": len(states), "skipped": skipped[:5], "skipped_count": len(skipped),
                          "text_sources": dict(Counter(sources.values())), "path": str(states_path),
                          "manifest": str(manifest_path)}, indent=2, ensure_ascii=False))
        return 0

    checker_results = rule_checker.run_checker(config, gold, annotations, texts)
    if args.command == "check":
        _write_jsonl(OUTPUT_ROOT / f"checker_{span_set_id}.jsonl", checker_results)
        audit = rule_checker.checker_audit(checker_results, annotations)
        with (OUTPUT_ROOT / "checker_audit.json").open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(audit, handle, indent=2, ensure_ascii=False)
        print(json.dumps(audit, indent=2, ensure_ascii=False))
        return 0

    if not args.arm:
        parser.error(f"{args.command} needs --arm")
    arm = load_arms()[args.arm]
    arm_dir = OUTPUT_ROOT / arm["arm_id"]
    responses_path = arm_dir / "responses.jsonl"
    states, _ = load_states(span_set_id, *manifest_args)

    if args.command == "run":
        if split != "all":
            states = [state for state in states if state["role"] == split]
        api_key = read_api_key(arm)
        if args.repeats is not None:
            repeats = args.repeats
        else:
            role = "dev" if split == "dev" else "eval"
            repeats = (arm.get("repeats") or {}).get(role)
            if not repeats:
                raise SystemExit(f"arm {arm['arm_id']}: repeats.{role} is not set in the arms config")
        arm_dir.mkdir(parents=True, exist_ok=True)
        provenance = {"battery_id": config["battery_id"], "config_sha256": file_sha256(config_path)}
        summary = run_battery(states, arm, api_key, repeats, responses_path, limit=args.limit, provenance=provenance)
        print(json.dumps(summary, indent=2))
        return 0

    rows = read_response_rows(responses_path) if responses_path.exists() else []
    kept, excluded = select_scored_rows(rows, expected_request_hashes(states, arm))
    shortfalls = repeat_shortfalls(aggregate_responses(kept, config), states, arm)
    if shortfalls and not args.allow_partial:
        raise SystemExit(f"{len(shortfalls)} spans have a repeat count that differs from the arm setting, "
                         f"for example {shortfalls[:3]}; rerun or pass --allow-partial")
    signals = load_stored_signals()
    report, score_table = score_battery(config, gold, annotations, kept, checker_results, signals, args.replicates, args.seed,
                                        arm=arm, excluded_rows=excluded, partial=bool(shortfalls),
                                        repeat_shortfall_ids=shortfalls)
    arm_dir.mkdir(parents=True, exist_ok=True)
    with (arm_dir / "report.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False, default=str)
    with (arm_dir / "span_scores.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = sorted({key for row in score_table for key in row})
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(score_table)
    with (arm_dir / "report.md").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_markdown(report))
    print(render_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
