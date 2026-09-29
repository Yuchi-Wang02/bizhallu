"""Decision battery v2 for BizHallu (standard library only).

Poses each pre-identified business-fact span as typed questions to a
non-generative decision model (TypeSafe Jev) over the same evidence table the
generator saw, and compares the returned probabilities with a deterministic,
label-blind evidence checker and with the stored token-time uncertainty signals.

Subcommands (all offline unless stated):

  export-spans  Write the six D10 span fields of the 205 annotations to
                data/annotations/spans_full100_v1.jsonl (labels stay in their own files).
  build     Build one state per span (labelled or not) from committed artifacts plus
            the local generation file; write states_<span_set_id>.jsonl and its manifest.
  check     Run the label-blind checker and the span-kind rules over every span; with
            --labels and --label-mapping also audit the checker against those labels.
  run       Send states to a decision-model arm (network for the hosted arm; the key
            is read from the environment variable named by the arm) with repeats and a cache.
  smoke     Send the two control states of the config to one arm and check the replies.
  score     Join cached responses with labels, uncertainty signals (recomputed from the
            token traces when present) and priors; write report.json and report.md.
  validate  Offline check of the config, span file, state contract and span kinds.

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
from bizhallu import cluster_bootstrap as cb  # noqa: E402
from bizhallu import evidence, rule_checker, scoring, span_signals  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
V1_CONFIG_PATH = PROJECT_ROOT / "configs" / "jev_battery_v1.json"
V2_CONFIG_PATH = PROJECT_ROOT / "configs" / "decision_battery_v2.json"
CONFIG_PATH = V2_CONFIG_PATH
ARMS_CONFIG_PATH = PROJECT_ROOT / "configs" / "decision_battery_arms_v1.json"
HELDOUT_SLICE_PATH = PROJECT_ROOT / "configs" / "heldout_slice_v1.json"
GOLD_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
ANNOTATIONS_PATH = PROJECT_ROOT / "data" / "annotations" / "span_annotations_full100_draft.jsonl"
SPANS_PATH = PROJECT_ROOT / "data" / "annotations" / "spans_full100_v1.jsonl"
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
SPAN_FIELDS = ["annotation_id", "question_id", "source_generation_file", "span_start_char", "span_end_char", "span_text"]
EXTRACTOR_SPAN_FIELDS = ["span_source", "span_kind", "restated_from_question"]
TRACE_SIGNALS = ["one_minus_min_top2_margin", "mean_token_entropy"]
PRIOR_ARMS = {"dev_span_kind_prior": "span_kind", "dev_question_type_prior": "question_type"}
LEGACY_PRIOR_ARM = "dev_fact_type_prior"
REFERENCE_ARMS = TRACE_SIGNALS + list(PRIOR_ARMS) + [LEGACY_PRIOR_ARM, "all_positive"]


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


def load_spans(path=SPANS_PATH):
    """Span rows with the six D10 fields (plus the extractor fields when present); labels are never read here."""
    spans, seen = [], set()
    for row in read_jsonl(path):
        missing = [field for field in SPAN_FIELDS if field not in row]
        if missing:
            raise SystemExit(f"{Path(path).name}: span {row.get('annotation_id')} lacks {missing}")
        if row["annotation_id"] in seen:
            raise SystemExit(f"{Path(path).name}: duplicate annotation_id {row['annotation_id']}")
        seen.add(row["annotation_id"])
        spans.append({field: row[field] for field in SPAN_FIELDS + EXTRACTOR_SPAN_FIELDS if field in row})
    return spans


def export_spans(annotations_path=ANNOTATIONS_PATH, out_path=SPANS_PATH):
    """Write the span file: the six D10 fields of every annotation, sorted by annotation_id."""
    rows = sorted(read_jsonl(annotations_path), key=lambda row: row["annotation_id"])
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps({field: row[field] for field in SPAN_FIELDS}, ensure_ascii=False) + "\n")
    return len(rows)


def label_mapping_names(config):
    return sorted(name for name, spec in config["label_mapping"].items() if isinstance(spec, dict))


def load_labels(paths, mapping_name, config):
    """Binary labels under one label_mapping of the config, by annotation_id.

    Values listed as excluded, and rows without the mapped field, get binary_label None; any other
    unlisted value stops the run. Label files are separate from span files and may be repeated.
    """
    if mapping_name not in label_mapping_names(config):
        raise SystemExit(f"unknown label mapping {mapping_name!r}; expected one of {label_mapping_names(config)}")
    mapping = config["label_mapping"][mapping_name]
    labels = {}
    for path in paths:
        for row in read_jsonl(path):
            annotation_id = row["annotation_id"]
            if annotation_id in labels:
                raise SystemExit(f"annotation_id {annotation_id} has labels in more than one row")
            value = row.get(mapping["field"])
            if value in mapping["positive"]:
                binary = 1
            elif value in mapping["negative"]:
                binary = 0
            elif value is None or value in mapping["excluded"]:
                binary = None
            else:
                raise SystemExit(f"{Path(path).name}: {annotation_id} has {mapping['field']}={value!r}, "
                                 f"which label mapping {mapping_name} does not list")
            labels[annotation_id] = {"binary_label": binary, "value": value, "fact_type": row.get("fact_type"),
                                     "row": row}
    return labels


def binary_labels(labels):
    return {annotation_id: item["binary_label"] for annotation_id, item in labels.items()}


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
    """Uncertainty signals saved by the retrospective statistics run; fallback when traces are absent."""
    signals = {}
    if not Path(path).exists():
        return signals
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("arm") != arm:
                continue
            signals[row["annotation_id"]] = {key: float(row[key]) for key in TRACE_SIGNALS if key in row}
    return signals


def trace_signals(spans, texts, traces_path=DEFAULT_TRACES, heldout_ids=None, log=_stderr):
    """Uncertainty signals recomputed from saved token traces (read through the guarded loader)."""
    traces = {record["question_id"]: record["token_traces"]
              for record in load_traces(traces_path, heldout_ids, log)}
    signals = {}
    for span in spans:
        qid = span["question_id"]
        if qid not in traces or qid not in texts:
            continue
        scores = span_signals.span_token_signals(traces[qid], texts[qid], span["span_start_char"],
                                                 span["span_end_char"], qid)
        signals[span["annotation_id"]] = {key: scores[key] for key in TRACE_SIGNALS}
    return signals


def load_signals(spans, texts, sources, traces_path=DEFAULT_TRACES):
    """Recomputed signals when the trace file and local answers exist, else the stored CSV values."""
    if traces_path and Path(traces_path).exists() and "local_generations" in sources.values():
        return trace_signals(spans, texts, traces_path), "recomputed_from_traces"
    return load_stored_signals(), "stored_csv_saved_trace_precision"


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


def role_for(question_id, gold, heldout_ids):
    return "heldout" if question_id in heldout_ids else gold[question_id]["split"]


def build_states(config, gold, spans, texts, sources, label_rows=None, heldout_ids=None):
    """One state per span, labelled or not; label rows are used only for the leak scan.

    The role is heldout for a question in the held-out slice and the gold split otherwise.
    """
    label_rows = label_rows or {}
    heldout_ids = load_heldout_ids() if heldout_ids is None else heldout_ids
    states, skipped = [], []
    for span in sorted(spans, key=lambda row: row["annotation_id"]):
        qid = span["question_id"]
        if qid not in texts:
            skipped.append({"annotation_id": span["annotation_id"], "reason": "generated text unavailable"})
            continue
        record = gold[qid]
        state = build_state(record, span, texts[qid])
        questions = build_questions(config, state)
        problems = check_state_contract(state, record, span, config, questions=questions,
                                        label_row=label_rows.get(span["annotation_id"]))
        if problems:
            raise ValueError(f"{span['annotation_id']}: " + "; ".join(problems))
        states.append({
            "annotation_id": span["annotation_id"],
            "question_id": qid,
            "question_type": record["question_type"],
            "role": role_for(qid, gold, heldout_ids),
            "text_source": sources[qid],
            "state": state,
            "questions": questions,
        })
    return states, skipped


def span_attributes(config, gold, spans):
    """Label-independent attributes per span: span kind, restatement, question type and evidence cluster."""
    rules = config["span_kind"]
    clusters = {}
    attributes = {}
    for span in spans:
        record = gold[span["question_id"]]
        if record["question_id"] not in clusters:
            clusters[record["question_id"]] = span_signals.evidence_cluster(record)
        attributes[span["annotation_id"]] = {
            "span_kind": span_signals.span_kind(span["span_text"], record, rules),
            "restated_from_question": span_signals.restated_from_question(span["span_text"], record["question"]),
            "question_type": record["question_type"],
            "evidence_cluster": clusters[record["question_id"]],
        }
    return attributes


def span_kind_rows(attributes):
    return [{"annotation_id": annotation_id, "span_kind": item["span_kind"],
             "restated_from_question": item["restated_from_question"]}
            for annotation_id, item in sorted(attributes.items())]


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


# ----------------------------------------------------------- freeze guard ---

FREEZE_PATH = PROJECT_ROOT / "configs" / "decision_battery_v2_freeze.json"
_AMENDMENT_NAME = re.compile(r"^decision_battery_v2_freeze_amendment_(\d+)\.json$")
EVALUATION_ROLES = ("dev", "test", "heldout")
EVAL_READY_STATUSES = {"final_wording_not_frozen", "frozen"}
FREEZE_ENFORCED_FIELDS = [
    "battery_config_sha256", "arms_config_sha256",
    "evidence_sha256", "rule_checker_sha256", "span_extractor_sha256", "span_signals_sha256",
    "codebook_sha256", "annotation_schema_sha256", "labels_205_sha256", "heldout_ids_sha256",
    "preregistration_sha256", "gold_sha256", "generations_sha256", "token_traces_sha256",
    "spans_full100_sha256", "spans_extractor_only_devtest_sha256", "span_source_devtest_sha256",
    "states_manifest_full100_205_sha256", "test_request_set_sha256", "amendments",
]
# Written as null while the extractor-only spans are not approved (Q9); then not checked.
FREEZE_NULLABLE_FIELDS = {"spans_extractor_only_devtest_sha256", "span_source_devtest_sha256"}
# --split heldout does not check these two (appendix C).
FREEZE_TEST_ONLY_FIELDS = {"states_manifest_full100_205_sha256", "test_request_set_sha256"}
REQUEST_SET_SPAN_SETS = ("full100_205", "extractor_only_devtest_v1")


def default_freeze_inputs():
    """Default file behind each file-hash field; the freeze record's `inputs` and the run's own paths override."""
    return {
        "battery_config_sha256": V2_CONFIG_PATH,
        "arms_config_sha256": ARMS_CONFIG_PATH,
        "evidence_sha256": MODULE_DIR / "evidence.py",
        "rule_checker_sha256": MODULE_DIR / "rule_checker.py",
        "span_extractor_sha256": MODULE_DIR / "span_extractor.py",
        "span_signals_sha256": MODULE_DIR / "span_signals.py",
        "heldout_ids_sha256": HELDOUT_SLICE_PATH,
        "gold_sha256": GOLD_PATH,
        "generations_sha256": DEFAULT_GENERATIONS,
        "token_traces_sha256": DEFAULT_TRACES,
        "spans_full100_sha256": SPANS_PATH,
        "spans_extractor_only_devtest_sha256": SPANS_PATH.parent / "spans_extractor_only_devtest_v1.jsonl",
        "span_source_devtest_sha256": SPANS_PATH.parent / "span_source_devtest_v1.jsonl",
    }


def freeze_input_paths(record_inputs=None, overrides=None, states_root=None):
    paths = default_freeze_inputs()
    paths["states_manifest_full100_205_sha256"] = states_paths("full100_205", states_root)[1]
    for field, relative in (record_inputs or {}).items():
        paths[field] = PROJECT_ROOT / relative
    paths.update({field: Path(path) for field, path in (overrides or {}).items() if path is not None})
    return paths


def request_set_sha256(arms, states_root=None):
    """SHA-256 over sorted `<arm_id>|<request_sha256>` lines for every test-role state of both span sets and every arm."""
    lines = []
    for span_set_id in REQUEST_SET_SPAN_SETS:
        states_path, _ = states_paths(span_set_id, states_root)
        if not states_path.exists():
            continue
        test_states = [state for state in read_jsonl(states_path) if state.get("role") == "test"]
        for arm in arms.values():
            lines += [f"{arm['arm_id']}|{digest}" for digest in expected_request_hashes(test_states, arm).values()]
    return hashlib.sha256("\n".join(sorted(lines)).encode("utf-8")).hexdigest()


def load_freeze(freeze_path=FREEZE_PATH):
    """The freeze record with every amendment applied in number order, or None when no record exists.

    Amendment N lives next to the record as decision_battery_v2_freeze_amendment_N.json with
    {"fields": {field: {"old_sha256": ..., "new_sha256": ...}}}. Numbers run 1, 2, ... without gaps;
    each old hash must equal the value in force before it.
    """
    freeze_path = Path(freeze_path)
    if not freeze_path.exists():
        return None
    effective = load_config(freeze_path)
    applied = list(effective.get("amendments") or [])
    found = sorted((int(match.group(1)), path) for path in freeze_path.parent.iterdir()
                   if (match := _AMENDMENT_NAME.match(path.name)))
    for expected, (number, path) in enumerate(found, start=1):
        if number != expected:
            raise SystemExit(f"freeze amendments must be numbered 1, 2, ... without gaps; found {path.name}")
        for field, change in load_config(path).get("fields", {}).items():
            if field not in FREEZE_ENFORCED_FIELDS or field == "amendments":
                raise SystemExit(f"{path.name}: {field} cannot be amended")
            if change.get("old_sha256") != effective.get(field):
                raise SystemExit(f"{path.name}: old hash of {field} does not equal the version in force")
            effective[field] = change["new_sha256"]
        applied.append({"file": path.name, "sha256": file_sha256(path)})
    effective["amendments"] = applied
    effective["_freeze_dir"] = str(freeze_path.parent)
    return effective


def current_freeze_values(overrides=None, arms_path=ARMS_CONFIG_PATH, states_root=None, record_inputs=None,
                          include_request_set=True):
    """Current hash of every enforced field that has a file behind it, plus the test request set."""
    paths = freeze_input_paths(record_inputs, overrides, states_root)
    values = {field: _sha_or_none(path) for field, path in paths.items() if field in FREEZE_ENFORCED_FIELDS}
    if include_request_set:
        values["test_request_set_sha256"] = request_set_sha256(load_arms(arms_path), states_root)
    return values


def freeze_mismatches(record, role, overrides=None, arms_path=ARMS_CONFIG_PATH, states_root=None):
    """Enforced fields whose recorded hash differs from the current inputs, for sending or scoring `role`."""
    current = current_freeze_values(overrides, arms_path, states_root, record.get("inputs"),
                                    include_request_set=role == "test")
    problems = []
    for field in FREEZE_ENFORCED_FIELDS:
        if role != "test" and field in FREEZE_TEST_ONLY_FIELDS:
            continue
        expected = record.get(field)
        if field in FREEZE_NULLABLE_FIELDS and expected is None:
            continue
        if field == "amendments":
            directory = Path(record["_freeze_dir"])
            if any(not (directory / item["file"]).exists() or file_sha256(directory / item["file"]) != item["sha256"]
                   for item in expected or []):
                problems.append(field)
        elif expected is None:
            problems.append(f"{field} (not recorded)")
        elif current.get(field) != expected:
            problems.append(field)
    return problems


def require_freeze(role, what, freeze_path=FREEZE_PATH, overrides=None, arms_path=ARMS_CONFIG_PATH, states_root=None):
    """Stop unless a freeze record exists and matches the current inputs for `role`; return the record."""
    record = load_freeze(freeze_path)
    if record is None:
        raise SystemExit(f"{what} needs the freeze record {Path(freeze_path).name}, which does not exist")
    problems = freeze_mismatches(record, role, overrides, arms_path, states_root)
    if problems:
        raise SystemExit(f"{what}: the freeze record does not match the current inputs: {', '.join(problems)}")
    return record


def readable_heldout_ids(heldout_ids, freeze_record):
    """Held-out ids that the loaders drop: all of them until a valid freeze record exists, none after."""
    return frozenset() if freeze_record is not None else frozenset(heldout_ids)


def check_response_roles(rows):
    """Scoring accepts only response rows whose role is dev, test or heldout."""
    for row in rows:
        if row.get("role") not in EVALUATION_ROLES:
            raise SystemExit(f"response row for {row.get('annotation_id')} has role {row.get('role')!r}; "
                             f"only {list(EVALUATION_ROLES)} can be scored")


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
                sleeper=time.sleep, log=print, provenance=None, cleared_roles=("dev",)):
    """Send every (span, repeat) that has no usable cached response yet.

    Only states whose role is in `cleared_roles` are sent; test and heldout are cleared only by
    require_freeze in main, so nothing but dev leaves this function before freeze point A.
    """
    blocked = sorted({state.get("role") for state in states[:limit]} - set(cleared_roles), key=str)
    if blocked:
        raise SystemExit(f"refusing to send states with role {blocked}; cleared roles are {sorted(cleared_roles)}")
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
    """Mean of every derived score per span across repeats, its range, and argmax flip rates."""
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
            try:
                scores = derived_scores(response, config)
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError(f"{annotation_id}: response cannot be scored: {error!r}") from error
            for key, value in scores.items():
                (choices if key.endswith("_choice") else numeric)[key].append(value)
        item = {key: sum(values) / len(values) for key, values in numeric.items()}
        item["ranges"] = {key: max(values) - min(values) for key, values in numeric.items()}
        item["repeats"] = len(responses)
        item["models"] = dict(models)
        item["choice_modes"] = {key: Counter(values).most_common(1)[0][0] for key, values in choices.items()}
        item["choice_flip_rate"] = {key: 1 - Counter(values).most_common(1)[0][1] / len(values) for key, values in choices.items()}
        aggregated[annotation_id] = item
    return aggregated


LABEL_ROW_FIELDS = ["slot_label", "value_label", "mechanism", "matched_row_id", "rater_a_slot_label", "rater_b_slot_label"]


def base_rows(spans, labels, gold, attributes, signals, checker_results, heldout_ids=None, lookup_results=None,
              value_labels=None, include_unlabelled=False):
    """One row per span with a binary label (or every span with include_unlabelled) and the offline arms.

    Spans may carry `span_set_id`; spans without it belong to full100_205. Decision-model scores are merged later.
    """
    heldout_ids = load_heldout_ids() if heldout_ids is None else heldout_ids
    checker = {item["annotation_id"]: item for item in checker_results}
    lookup = {item["annotation_id"]: item for item in lookup_results or []}
    value_labels = value_labels or {}
    rows = []
    for span in spans:
        aid = span["annotation_id"]
        label = labels.get(aid, {})
        if label.get("binary_label") is None and not include_unlabelled:
            continue
        attribute = attributes[aid]
        label_row = label.get("row") or {}
        verdict = checker.get(aid, {}).get("verdict")
        row = {"annotation_id": aid, "span_set_id": span.get("span_set_id", "full100_205"),
               "question_id": span["question_id"], "role": role_for(span["question_id"], gold, heldout_ids),
               "question_type": attribute["question_type"], "span_kind": attribute["span_kind"],
               "restated_from_question": attribute["restated_from_question"],
               "evidence_cluster": attribute["evidence_cluster"],
               "derivation_need": scoring.derivation_need(attribute["span_kind"], attribute["question_type"]),
               "fact_type": label.get("fact_type"), "binary_label": label.get("binary_label"),
               "label_value": label.get("value"), "value_binary": value_labels.get(aid),
               "checker_verdict": verdict, "checker_mechanism": checker.get(aid, {}).get("mechanism"),
               "all_positive": 1.0}
        row.update({field: label_row.get(field) for field in LABEL_ROW_FIELDS})
        row["rule_checker_flag"], row["rule_checker_abstain"] = scoring.binary_flags(verdict, "rule_checker")
        row["evidence_lookup_flag"], row["evidence_lookup_abstain"] = scoring.binary_flags(
            lookup.get(aid, {}).get("verdict"), "evidence_lookup")
        row.update(signals.get(aid, {}))
        rows.append(row)
    return rows


def fit_prior(fit_rows, key):
    """Positive rate per category of the fit set; unseen categories use the fit set's overall rate."""
    if not fit_rows:
        raise ValueError("empty prior fit set")
    groups = defaultdict(list)
    for row in fit_rows:
        groups[row[key]].append(row["binary_label"])
    return {"key": key, "rates": {name: sum(values) / len(values) for name, values in sorted(groups.items())},
            "counts": {name: len(values) for name, values in sorted(groups.items())},
            "fallback": sum(row["binary_label"] for row in fit_rows) / len(fit_rows)}


def attach_priors(rows, legacy=False):
    """dev_span_kind_prior and dev_question_type_prior, fitted on the labelled non-month dev spans of full100_205
    (the for_test fit set, analysis_policy.prior_fallback for unseen categories).

    With legacy=True (ai_provisional labels only) dev_fact_type_prior is added, fitted on all dev spans of
    full100_205 as in the published statistics so the historical 0.768 can be reproduced.
    """
    fits = {}
    dev = [row for row in rows if row["span_set_id"] == "full100_205" and row["role"] == "dev"
           and row["binary_label"] is not None]
    fit_rows = [row for row in dev if row["span_kind"] != "month"]
    arms = dict(PRIOR_ARMS)
    if legacy:
        arms[LEGACY_PRIOR_ARM] = "fact_type"
    for arm, key in arms.items():
        fit_set = dev if arm == LEGACY_PRIOR_ARM else fit_rows
        try:
            prior = fit_prior(fit_set, key)
        except ValueError:
            continue
        fits[arm] = {**prior, "fit_set": "all dev spans" if arm == LEGACY_PRIOR_ARM else "non-month dev spans",
                     "fit_size": len(fit_set)}
        for row in rows:
            row[arm] = prior["rates"].get(row[key], prior["fallback"])
    return fits


# ----------------------------------------------------------------- report ---

ROLE_STATUS = {
    "dev": "in-sample: dev fits thresholds and priors and informs calibration and wording",
    "test": "in-sample with respect to instrument design",
    "heldout": "label-held-out retrospective extension",
}
MODULE_FILES = ["evidence.py", "rule_checker.py", "span_extractor.py", "span_signals.py", "scoring.py",
                "cluster_bootstrap.py", "decision_battery.py"]


def main_set(rows, role):
    source = "heldout_v1" if role == "heldout" else "full100_205"
    return [row for row in rows if row["role"] == role and row["span_set_id"] == source and row["span_kind"] != "month"]


def continuous_columns(config, dm_arm_ids, legacy):
    columns = []
    for arm in config["analysis_policy"]["fixed_arms"]:
        if arm == "all_positive":
            continue
        columns += [scoring.dm_column(arm, arm_id) for arm_id in dm_arm_ids] if arm.startswith("dm_") else [arm]
    return columns + ([LEGACY_PRIOR_ARM] if legacy else [])


def arm_exclusions(config, rows, dm_arm_ids):
    exclusions = {}
    for name, spec in config["derived_scores"].items():
        extra = set(spec.get("extra_excluded", []))
        if extra:
            ids = {row["annotation_id"] for row in rows if row.get("slot_label") in extra}
            for arm_id in dm_arm_ids:
                exclusions[scoring.dm_column(name, arm_id)] = ids
    return exclusions


def binary_under(mapping, value, excluded_as=None):
    if value in mapping["positive"]:
        return 1
    if value in mapping["negative"]:
        return 0
    return excluded_as if value in mapping["excluded"] else None


LABEL_SET_MAPPINGS = {
    "adjudicated": ("human_v1_slot", None),
    "rater_a before discussion": ("human_v1_slot_rater_a", None),
    "rater_b before discussion": ("human_v1_slot_rater_b", None),
    "excluded spans all counted positive": ("human_v1_slot", 1),
    "excluded spans all counted negative": ("human_v1_slot", 0),
}


def label_set_sensitivity(config, all_rows, dm_arm_ids, replicates, seed):
    """The primary contrast on each role's main set under the five label sets of the config."""
    policy = config["analysis_policy"]
    result = {}
    for name in policy["label_sets_for_sensitivity"]:
        mapping_name, excluded_as = LABEL_SET_MAPPINGS[name]
        mapping = config["label_mapping"][mapping_name]
        relabelled = []
        for row in all_rows:
            value = row.get(mapping["field"])
            binary = binary_under(mapping, value, excluded_as) if value is not None else None
            if binary is not None:
                relabelled.append({**row, "binary_label": binary})
        result[name] = {}
        for role in ("test", "heldout"):
            spec = policy["primary"]["heldout" if role == "heldout" else "test_in_sample"]
            primary = scoring.dm_column(spec["score"], spec["arm"])
            subset = main_set(relabelled, role)
            if spec["arm"] not in dm_arm_ids or not subset or any(row.get(primary) is None for row in subset):
                result[name][role] = {"status": "primary arm scores or labels not available"}
                continue
            boot = cb.ranking_intervals(subset, [primary, scoring.REFERENCE_ARM], spec["cluster_unit"],
                                        [(primary, scoring.REFERENCE_ARM)], replicates, seed)
            result[name][role] = {metric: boot["estimates"][f"{primary} minus {scoring.REFERENCE_ARM}|{metric}"]
                                  for metric in ("average_precision", "auroc")}
    return result


def build_report(config, all_rows, arms, dm_aggregates, label_mapping, label_files, labels, signals_source,
                 exposed_ids, replicates, seed, frozen=None, span_sources=None, coverage=None,
                 rater_declarations=None, partial=False, shortfalls=()):
    """Every table of plan T1.9 and appendix D for the selected arms; returns (report, labelled rows)."""
    policy = config["analysis_policy"]
    rows = [row for row in all_rows if row["binary_label"] is not None]
    dm_arm_ids = sorted(dm_aggregates)
    legacy = label_mapping == "ai_provisional"
    human = bool(label_mapping) and label_mapping.startswith("human_")
    columns = continuous_columns(config, dm_arm_ids, legacy)
    thresholds = scoring.fit_thresholds(rows, columns, config, label_mapping, span_sources, frozen)
    exclusions = arm_exclusions(config, rows, dm_arm_ids)
    report = {"battery_id": config["battery_id"], "arms_scored": dm_arm_ids or "reference",
              "label_mapping": label_mapping, "label_files": label_files, "signals_source": signals_source,
              "human_labels": human, "partial": bool(partial), "repeat_shortfalls": list(shortfalls),
              "thresholds": {**thresholds, **{key: {arm: {**info, "threshold": scoring.json_threshold(info["threshold"])}
                                                    for arm, info in thresholds[key].items()}
                                              for key in ("for_test", "for_heldout")}},
              "roles": {}, "derivation_need": {}, "mechanism_tables": {}}
    for role in EVALUATION_ROLES:
        role_rows = [row for row in rows if row["role"] == role]
        if not role_rows:
            continue
        spec = policy["primary"]["heldout" if role == "heldout" else "test_in_sample"]
        primary = scoring.dm_column(spec["score"], spec["arm"])
        table = scoring.threshold_for(thresholds, role)

        def section(subset, spec=spec, primary=primary, table=table):
            return scoring.metric_section(subset, columns, table, spec["cluster_unit"], primary,
                                          spec["sensitivity_cluster_unit"], replicates, seed, exclusions)
        main = main_set(rows, role)
        sets = {"main set": section(main), "all spans": section(role_rows)}
        if role == "heldout":
            sets["main set, answers not viewed during review"] = section(
                [row for row in main if row["question_id"] not in exposed_ids])
            sets["main set without restated spans"] = section([row for row in main if not row["restated_from_question"]])
        report["roles"][role] = {"sample_status": ROLE_STATUS[role], "primary_score": primary, "sets": sets}
        # derivation_need.negatives_below_10: strata with fewer than 10 negatives report counts only
        report["derivation_need"][role] = scoring.derivation_table(role_rows, columns, 10)
        mechanism_columns = list(policy["mechanism_table"]["columns"])
        report["mechanism_tables"][role if role != "dev" else "dev (in-sample)"] = scoring.mechanism_table(
            main, mechanism_columns, table, config, human)
    value_rows = [{**row, "binary_label": row["value_binary"]} for row in all_rows if row.get("value_binary") is not None]
    if human and value_rows:
        value_columns = [scoring.dm_column("dm_unfaithful", arm_id) for arm_id in dm_arm_ids]
        report["value_axis"] = {role: scoring.metric_section(main_set(value_rows, role), value_columns,
                                                             scoring.threshold_for(thresholds, role), "evidence_cluster",
                                                             None, None, replicates, seed)
                                for role in EVALUATION_ROLES if main_set(value_rows, role)}
    report["label_set_sensitivity"] = (label_set_sensitivity(config, all_rows, dm_arm_ids, replicates, seed)
                                       if label_mapping == "human_v1_slot"
                                       else {"status": f"not applicable with label mapping {label_mapping}"})
    eval_main = main_set(rows, "test") + main_set(rows, "heldout")
    if human:
        primary_arm = policy["primary"]["heldout"]["arm"]
        primary_column = scoring.dm_column("dm_risk", primary_arm)
        report["estimands"] = {
            "E1": {role: scoring.estimand_e1([row for row in rows if row["role"] == role], replicates, seed)
                   for role in EVALUATION_ROLES if any(row["role"] == role for row in rows)},
            "E2": scoring.estimand_e2(eval_main, scoring.UNCERTAINTY_ARMS, replicates, seed),
            "E3": scoring.estimand_e3(eval_main, scoring.UNCERTAINTY_ARMS, thresholds, replicates, seed),
            "E4": {role: scoring.estimand_e4(main_set(rows, role), primary_column, replicates, seed)
                   for role in ("test", "heldout")},
        }
        report["funnel"] = {role: scoring.funnel(main_set(rows, role), primary_arm, thresholds,
                                                 policy["funnel"]["minimum_cell"])
                            for role in ("test", "heldout") if main_set(rows, role)}
    else:
        report["estimands"] = {"status": "not computed: E1 to E4 need human slot_label, value_label and mechanism"}
        report["funnel"] = {"status": "not computed: needs human labels"}
    report["coverage"] = coverage or {}
    report["excluded_label_values"] = dict(Counter(item["value"] for item in labels.values()
                                                   if item["binary_label"] is None))
    report["dm_arms"] = {}
    for arm_id, aggregated in dm_aggregates.items():
        models = Counter()
        for item in aggregated.values():
            models.update(item["models"])
        report["dm_arms"][arm_id] = {"requested_model": arms[arm_id].get("model"), "model_versions": dict(models),
                                     "unexpected_model_versions": sorted(str(m) for m in models if m != arms[arm_id].get("model")),
                                     "repeats_per_span": dict(Counter(item["repeats"] for item in aggregated.values())),
                                     "repeat_spread": scoring.repeat_spread(aggregated, arms[arm_id])}
    report["module_sha256"] = {name: _sha_or_none(MODULE_DIR / name) for name in MODULE_FILES}
    report["module_sha256"]["detector_metrics.py"] = _sha_or_none(MODULE_DIR.parent / "detector_metrics.py")
    report["rater_declarations"] = rater_declarations or "not available"
    report["claim_boundary"] = config["claim_boundary"]
    report["interval_count"] = scoring.interval_count(report)
    return report, rows


def power_notes(rows, primary_arm_id, replicates, seed):
    """Dev-only planning numbers (plan T1.9 item 20); written only with dev human labels."""
    dev = main_set(rows, "dev")
    if not dev:
        return None
    labels = [row["binary_label"] for row in dev]
    margin = [row[scoring.REFERENCE_ARM] for row in dev]
    notes = {"dev_main_set_spans": len(dev), "dev_main_set_positive_rate": sum(labels) / len(labels),
             "perfect_detector_gap_to_margin": {
                 "average_precision": 1.0 - metrics.average_precision(labels, margin),
                 "auroc": 1.0 - metrics.auroc(labels, margin)}}
    primary = scoring.dm_column("dm_risk", primary_arm_id)
    if all(row.get(primary) is not None for row in dev):
        boot = cb.ranking_intervals(dev, [primary, scoring.REFERENCE_ARM], "question_id",
                                    [(primary, scoring.REFERENCE_ARM)], replicates, seed)
        widths = {}
        for metric in ("average_precision", "auroc"):
            estimate = boot["estimates"][f"{primary} minus {scoring.REFERENCE_ARM}|{metric}"]
            widths[metric] = (None if estimate["lower_95"] is None
                              else estimate["upper_95"] - estimate["lower_95"])
        notes["dev_paired_difference_interval_width"] = widths
    else:
        notes["dev_paired_difference_interval_width"] = "primary arm dev scores not available"
    return notes


# ----------------------------------------------------------------- freeze ---

def span_set_files(config):
    """Span file of every span set of the config, by span_set_id (existing or not)."""
    return {span_set_id: PROJECT_ROOT / spec["file"]
            for span_set_id, spec in config["analysis_policy"]["span_sets"].items()}


def load_span_sources(path=None):
    """annotation_id -> span_source from span_source_devtest_v1.jsonl, or None when the file does not exist."""
    path = Path(path or SPANS_PATH.parent / "span_source_devtest_v1.jsonl")
    if not path.exists():
        return None
    return {row["annotation_id"]: row["span_source"] for row in read_jsonl(path)}


def response_arm_rows(arm, states, root=None):
    """(kept rows, excluded count, all rows) of one arm's response file against the given states."""
    path = Path(root or OUTPUT_ROOT) / arm["arm_id"] / "responses.jsonl"
    rows = read_response_rows(path) if path.exists() else []
    kept, excluded = select_scored_rows(rows, expected_request_hashes(states, arm))
    return kept, excluded, rows


def assemble_rows(config, gold, spans, labels, texts, sources, traces_path, dm_aggregates, heldout_ids,
                  value_labels=None, include_unlabelled=True, legacy=False):
    """Rows of every span with offline arms, priors and the decision-model columns of every given arm."""
    attributes = span_attributes(config, gold, spans)
    signals, signals_source = load_signals(spans, texts, sources, traces_path)
    checker_results = rule_checker.run_checker(config, gold, spans, texts)
    rows = base_rows(spans, labels, gold, attributes, signals, checker_results, heldout_ids,
                     value_labels=value_labels, include_unlabelled=include_unlabelled)
    labelled = [row for row in rows if row["binary_label"] is not None]
    priors = attach_priors(labelled, legacy=legacy)
    for row in rows:
        if row["binary_label"] is None:
            for arm, fit in priors.items():
                row[arm] = fit["rates"].get(row[fit["key"]], fit["fallback"])
    score_names = list(config["derived_scores"])
    for arm_id, aggregated in dm_aggregates.items():
        scoring.attach_dm_scores(rows, arm_id, aggregated, score_names)
    return rows, priors, signals_source


def _repo_relative(path):
    path = Path(path).resolve()
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def _git_head():
    import subprocess
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def config_text_with_status(text, status):
    """The config text with its top-level status value replaced, layout unchanged."""
    new, count = re.subn(r'^(  "status": )"[^"]*"', lambda match: f'{match.group(1)}"{status}"', text, count=1,
                         flags=re.MULTILINE)
    if count != 1:
        raise SystemExit("the config has no top-level status line")
    return new


def run_freeze(date, config_path, arms_path, label_path, label_mapping, codebook, schema, heldout_slice,
               preregistration, power_notes_path, generations_path=DEFAULT_GENERATIONS, traces_path=DEFAULT_TRACES,
               freeze_path=None, states_root=None, overrides=None, validator=None, git_commit=None, log=print):
    """Freeze point A (plan T1.9 item 18): refuse on any failed precondition, then write the record once."""
    freeze_path = Path(freeze_path or FREEZE_PATH)
    states_root = Path(states_root or OUTPUT_ROOT)
    if freeze_path.exists():
        raise SystemExit(f"{freeze_path.name} already exists; changes after the freeze go into an amendment")
    config = load_config(config_path)
    file_overrides = {"battery_config_sha256": config_path, "arms_config_sha256": arms_path,
                      "codebook_sha256": codebook, "annotation_schema_sha256": schema, "labels_205_sha256": label_path,
                      "heldout_ids_sha256": heldout_slice, "preregistration_sha256": preregistration,
                      "generations_sha256": generations_path, "token_traces_sha256": traces_path, **(overrides or {})}
    paths = freeze_input_paths(None, file_overrides, states_root)
    missing = [field for field, path in paths.items()
               if field not in FREEZE_NULLABLE_FIELDS | {"states_manifest_full100_205_sha256"}
               and not Path(path).exists()]
    if not Path(power_notes_path).exists():
        missing.append("power_notes")
    if missing:
        raise SystemExit(f"freeze refused: input files missing for {missing}")
    validation = validator() if validator else validate(config_path=config_path, output_dir=states_root,
                                                        generations_path=generations_path, require_local=True,
                                                        arms_path=arms_path)
    if validation["num_failures"]:
        raise SystemExit(f"freeze refused: validate --require-local failed: {validation['failures'][:3]}")
    arms = load_arms(arms_path)
    labels = load_labels([label_path], label_mapping, config)
    set_files = span_set_files(config)
    set_files["full100_205"] = Path(paths["spans_full100_sha256"])
    states_by_set = {}
    for span_set_id in REQUEST_SET_SPAN_SETS:
        if not set_files[span_set_id].exists():
            continue
        states_by_set[span_set_id], _ = load_states(span_set_id, config_path, arms_path, set_files[span_set_id],
                                                    generations_path, root=states_root)
    if "full100_205" not in states_by_set:
        raise SystemExit("freeze refused: the full100_205 states are missing; run build first")
    all_states = [state for states in states_by_set.values() for state in states]
    dm_aggregates = {}
    for arm_id, arm in arms.items():
        kept, _, rows = response_arm_rows(arm, all_states, states_root)
        late = sorted({row.get("role") for row in rows} & {"test", "heldout"})
        if late:
            raise SystemExit(f"freeze refused: arm {arm_id} already has response rows with role {late}")
        aggregated = aggregate_responses(kept, config)
        required = (arm.get("repeats") or {}).get("dev")
        expected = [state["annotation_id"] for state in all_states if state["role"] == "dev"
                    and labels.get(state["annotation_id"], {}).get("binary_label") is not None]
        incomplete = [aid for aid in expected if aid not in aggregated or aggregated[aid]["repeats"] != required]
        if incomplete:
            raise SystemExit(f"freeze refused: arm {arm_id} dev coverage is incomplete for {len(incomplete)} spans, "
                             f"for example {incomplete[:3]}")
        dm_aggregates[arm_id] = aggregated
    # every precondition holds: write the frozen status, then rewrite the states manifests
    config_file = Path(config_path)
    with config_file.open("r", encoding="utf-8") as handle:
        text = handle.read()
    with config_file.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(config_text_with_status(text, "frozen"))
    config = load_config(config_path)
    for span_set_id, states in states_by_set.items():
        before = file_sha256(states_paths(span_set_id, states_root)[0])
        write_states(states, span_set_id, config_path, arms_path, set_files[span_set_id], generations_path,
                     root=states_root)
        if file_sha256(states_paths(span_set_id, states_root)[0]) != before:
            raise SystemExit(f"states of {span_set_id} changed while rewriting the manifest")
    values = current_freeze_values(file_overrides, arms_path, states_root)
    gold = load_gold()
    heldout_ids = load_heldout_ids(heldout_slice)
    spans = [{**span, "span_set_id": span_set_id} for span_set_id in states_by_set
             for span in load_spans(set_files[span_set_id])]
    texts, sources = load_generated_texts(generations_path, heldout_ids=heldout_ids, log=lambda message: None)
    rows, _, _ = assemble_rows(config, gold, spans, labels, texts, sources, traces_path, dm_aggregates, heldout_ids)
    labelled = [row for row in rows if row["binary_label"] is not None]
    columns = continuous_columns(config, sorted(dm_aggregates), legacy=False)
    thresholds = scoring.fit_thresholds(labelled, columns, config, label_mapping, load_span_sources())
    record = {"freeze_id": f"decision_battery_v2_freeze_{date}", "date": date,
              "git_commit": git_commit if git_commit is not None else _git_head()}
    for field in FREEZE_ENFORCED_FIELDS:
        record[field] = [] if field == "amendments" else values.get(field)
    record["inputs"] = {field: _repo_relative(path) for field, path in freeze_input_paths(None, file_overrides, states_root).items()
                        if field in FREEZE_ENFORCED_FIELDS and Path(path).exists()}
    record["informational_sha256"] = {f"module:{path.name}": file_sha256(path) for path in sorted(MODULE_DIR.glob("*.py"))}
    record["informational_sha256"]["module:detector_metrics.py"] = _sha_or_none(MODULE_DIR.parent / "detector_metrics.py")
    record["label_mapping"] = label_mapping
    record["dev_thresholds"] = {"rule": thresholds["rule"], "notes": thresholds["notes"],
                                **{key: {arm: {"threshold": scoring.json_threshold(info["threshold"]),
                                               "degenerate": info["degenerate"], "reason": info.get("reason")}
                                         for arm, info in thresholds[key].items()}
                                   for key in ("for_test", "for_heldout")}}
    record["main_set_rule"] = config["analysis_policy"]["main_set_rule"]
    record["primary"] = config["analysis_policy"]["primary"]
    record["local_arm_environment"] = {arm_id: arm.get("notes") for arm_id, arm in arms.items() if arm.get("kind") == "local"}
    record["power_notes"] = load_config(power_notes_path)
    freeze_path.parent.mkdir(parents=True, exist_ok=True)
    with freeze_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(record, handle, indent=2, ensure_ascii=False)
    log(f"freeze record written: {freeze_path.name}")
    return record


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
             arms_path=ARMS_CONFIG_PATH, spans_path=SPANS_PATH, labels_path=ANNOTATIONS_PATH):
    """Public tier by default (nine demo answers); require_local checks the full local package."""
    config = load_config(config_path)
    failures = config_problems(config, load_arms(arms_path))
    gold = load_gold()
    spans = load_spans(spans_path)
    label_rows = load_annotations(labels_path)
    exported = [{field: row[field] for field in SPAN_FIELDS} for row in sorted(label_rows, key=lambda r: r["annotation_id"])]
    if [{field: span[field] for field in SPAN_FIELDS} for span in spans] != exported:
        failures.append(f"{Path(spans_path).name} differs from the six span fields of {Path(labels_path).name}")
    labels = load_labels([labels_path], "ai_provisional", config)
    if require_local and not (generations_path and Path(generations_path).exists()):
        failures.append(f"local generation file not found: {generations_path}")
    texts, sources = load_generated_texts(generations_path)
    try:
        states, skipped = build_states(config, gold, spans, texts, sources,
                                       label_rows={aid: item["row"] for aid, item in labels.items()})
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
    attributes = span_attributes(config, gold, spans)
    kinds = Counter(item["span_kind"] for item in attributes.values())
    test_main = sum(1 for span in spans if gold[span["question_id"]]["split"] == "test"
                    and attributes[span["annotation_id"]]["span_kind"] != "month")
    if kinds["month"] != 37 or test_main != 85:
        failures.append(f"span_kind check: month {kinds['month']} (expected 37), test non-month {test_main} (expected 85)")
    checker = rule_checker.run_checker(config, gold, spans, texts)
    audit = rule_checker.checker_audit(checker, binary_labels(labels)) if checker else None
    result = {"config_sha256": file_sha256(config_path), "script_sha256": file_sha256(__file__),
              "tier": "local" if require_local else "public",
              "states_built": len(states), "states_skipped": len(skipped), "text_sources": dict(Counter(sources.values())),
              "span_kinds": dict(sorted(kinds.items())), "test_non_month_spans": test_main,
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


def _dump_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, default=str)


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fields = sorted({key for row in rows for key in row})
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def score_command(args, config, config_path, freeze_overrides, log=print):
    """score --arms reference | <arm_id> | all over every span set whose file exists (plan T1.9 items 2 to 20)."""
    gold = load_gold()
    heldout_ids = load_heldout_ids()
    set_files = {span_set_id: path for span_set_id, path in span_set_files(config).items() if path.exists()}
    freeze_record = None
    if any("heldout" in config["analysis_policy"]["span_sets"][span_set_id]["roles"] for span_set_id in set_files):
        freeze_record = require_freeze("heldout", "score of the heldout span set", FREEZE_PATH, freeze_overrides)
    spans = [{**span, "span_set_id": span_set_id} for span_set_id, path in set_files.items() for span in load_spans(path)]
    if freeze_record is None and any(span["question_id"] in heldout_ids for span in spans):
        freeze_record = require_freeze("heldout", "score of held-out spans", FREEZE_PATH, freeze_overrides)
    labels = load_labels(args.labels, args.label_mapping, config) if args.labels else {}
    value_labels = None
    if args.label_mapping and args.label_mapping.startswith("human_v1_slot"):
        value_labels = binary_labels(load_labels(args.labels, "human_v1_value", config))
    texts, sources = load_generated_texts(args.generations, heldout_ids=readable_heldout_ids(heldout_ids, freeze_record))
    if "public_demo_bundle" in sources.values() and not args.public_demo:
        raise SystemExit("some answers come from the public demo bundle; pass --public-demo to use them")
    arms = load_arms(ARMS_CONFIG_PATH)
    if args.arms in ("reference", "all"):
        selected = [] if args.arms == "reference" else sorted(arms)
    elif args.arms in arms:
        selected = [args.arms]
    else:
        raise SystemExit(f"unknown --arms value {args.arms!r}; use reference, all or one of {sorted(arms)}")
    if not labels and not (len(selected) == 1 and args.arms != "all"):
        raise SystemExit("score without --labels writes diagnostics for one arm only; pass --arms <arm_id>")
    states_by_set = {}
    for span_set_id, path in set_files.items():
        if states_paths(span_set_id)[0].exists():
            states_by_set[span_set_id], _ = load_states(span_set_id, config_path, ARMS_CONFIG_PATH, path, args.generations)
        elif selected:
            raise SystemExit(f"states of {span_set_id} are missing; run build --spans {path.name} first")
    all_states = [state for states in states_by_set.values() for state in states]
    dm_aggregates, kept_by_arm, shortfalls = {}, {}, []
    for arm_id in selected:
        kept, _, rows = response_arm_rows(arms[arm_id], all_states)
        for role in sorted({row.get("role") for row in rows} & {"test", "heldout"}):
            require_freeze(role, f"score of {role} responses of {arm_id}", FREEZE_PATH, freeze_overrides)
        check_response_roles(kept)
        aggregated = aggregate_responses(kept, config)
        shortfalls += [f"{arm_id}:{aid}" for aid in repeat_shortfalls(aggregated, all_states, arms[arm_id])]
        dm_aggregates[arm_id], kept_by_arm[arm_id] = aggregated, kept
    if shortfalls and not args.allow_partial:
        raise SystemExit(f"{len(shortfalls)} spans have a repeat count that differs from the arm setting, "
                         f"for example {shortfalls[:3]}; rerun or pass --allow-partial")
    if not labels:
        arm_id = selected[0]
        attributes = span_attributes(config, gold, spans)
        for span_set_id, states in states_by_set.items():
            ids = {state["annotation_id"] for state in states}
            tagged = [{**state, "span_kind": attributes[state["annotation_id"]]["span_kind"]} for state in states]
            result = scoring.diagnostics([row for row in kept_by_arm[arm_id] if row["annotation_id"] in ids], tagged, config)
            path = OUTPUT_ROOT / arm_id / f"diagnostics_{span_set_id}.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(scoring.render_diagnostics(result, arm_id, span_set_id))
            log(f"diagnostics written: {path.name}")
        return 0
    rows, priors, signals_source = assemble_rows(config, gold, spans, labels, texts, sources, args.traces, dm_aggregates,
                                                 heldout_ids, value_labels, legacy=args.label_mapping == "ai_provisional")
    coverage = {}
    for arm_id, aggregated in dm_aggregates.items():
        expected = [state["annotation_id"] for state in all_states
                    if labels.get(state["annotation_id"], {}).get("binary_label") is not None]
        missing = sorted(aid for aid in expected if aid not in aggregated)
        coverage[arm_id] = {"expected": len(expected), "scored": len(expected) - len(missing), "missing": missing}
    exposed = set(load_config(HELDOUT_SLICE_PATH)["exposed_in_review_question_ids"])
    label_files = [{"file": _repo_relative(path), "sha256": file_sha256(path)} for path in args.labels]
    report, labelled = build_report(config, rows, arms, dm_aggregates, args.label_mapping, label_files, labels,
                                    signals_source, exposed, args.replicates, args.seed, frozen=load_freeze(FREEZE_PATH),
                                    span_sources=load_span_sources(), coverage=coverage, partial=bool(shortfalls),
                                    shortfalls=shortfalls)
    report["priors"] = {name: {key: value for key, value in fit.items() if key != "key"} for name, fit in priors.items()}
    markdown = scoring.render_report(report)
    if args.arms == "reference":
        stem = OUTPUT_ROOT / "report_reference"
    elif args.arms == "all":
        stem = OUTPUT_ROOT / "report_all_arms"
        figure = {role: {name: {arm: {metric: values[metric] for metric in ("average_precision", "auroc")}
                                for arm, values in section["arms"].items()}
                         for name, section in entry["sets"].items() if name == "main set"}
                  for role, entry in report["roles"].items()}
        _dump_json(OUTPUT_ROOT / "report_all_arms_figure.json", figure)
    else:
        stem = OUTPUT_ROOT / args.arms / "report"
    _dump_json(stem.with_suffix(".json"), report)
    _write_csv(stem.parent / f"{stem.name}_span_scores.csv", labelled)
    with stem.with_suffix(".md").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(markdown)
    if args.label_mapping.startswith("human_"):
        notes = power_notes(labelled, config["analysis_policy"]["primary"]["heldout"]["arm"], args.replicates, args.seed)
        if notes is not None:
            _dump_json(PROJECT_ROOT / "outputs" / "research_plan" / "results" / "power_notes.json", notes)
    log(markdown)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["export-spans", "build", "check", "run", "smoke", "score", "validate", "freeze"])
    parser.add_argument("--config", default=str(CONFIG_PATH), help="wording and analysis config")
    parser.add_argument("--generations", default=str(DEFAULT_GENERATIONS), help="local qwen_full100_generations.jsonl")
    parser.add_argument("--traces", default=str(DEFAULT_TRACES), help="score: local qwen_full100_token_traces.jsonl")
    parser.add_argument("--spans", default=str(SPANS_PATH), help="span file (six D10 fields); its name fixes the span set")
    parser.add_argument("--labels", action="append", default=[],
                        help="check, score, freeze: label file, separate from the span file; may be repeated")
    parser.add_argument("--label-mapping", default=None, help="check, score, freeze: a key of the config's label_mapping")
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--split", choices=list(EVALUATION_ROLES), default=None,
                        help="run (required): the role to send; test and heldout need the freeze record")
    parser.add_argument("--replicates", type=int, default=None, help="score: bootstrap replicates (default from config)")
    parser.add_argument("--seed", type=int, default=None, help="score: bootstrap seed (default from config)")
    parser.add_argument("--require-local", action="store_true",
                        help="validate: require the local generation file and all 205 states")
    parser.add_argument("--arm", default=None, help="run, smoke: arm_id from the arms config")
    parser.add_argument("--arms", default=None, help="score (required): reference, all or one arm_id")
    parser.add_argument("--allow-partial", action="store_true",
                        help="score: report even if some spans have fewer repeats than the arm setting")
    parser.add_argument("--public-demo", action="store_true",
                        help="run, score: allow the nine public demo answers instead of the local generation file")
    parser.add_argument("--date", default=None, help="freeze: date of the freeze record, YYYY-MM-DD")
    parser.add_argument("--arms-config", default=None, help="freeze: arms config (default configs/decision_battery_arms_v1.json)")
    parser.add_argument("--codebook", default=None, help="freeze: codebook file")
    parser.add_argument("--schema", default=None, help="freeze: annotation schema file")
    parser.add_argument("--heldout-slice", default=None, help="freeze: held-out slice (default configs/heldout_slice_v1.json)")
    parser.add_argument("--preregistration", default=None, help="freeze: sealed preregistration file")
    parser.add_argument("--power-notes", default=None, help="freeze: outputs/research_plan/results/power_notes.json")
    args = parser.parse_args(argv)
    if args.repeats is not None and (args.repeats < 1 or args.limit is None):
        parser.error("--repeats must be at least 1 and is only allowed together with --limit")
    if args.command == "run" and args.split is None:
        parser.error("run needs --split dev, test or heldout")
    if args.command != "run" and args.split is not None:
        parser.error("--split is only used by run")
    if args.command == "freeze" and not args.label_mapping:
        args.label_mapping = "human_v1_slot"
    if bool(args.labels) != bool(args.label_mapping):
        parser.error("--labels and --label-mapping go together")
    if args.command == "score" and not args.arms:
        parser.error("score needs --arms reference, all or an arm_id")
    if args.command != "score" and args.arms:
        parser.error("--arms is only used by score; run and smoke take --arm")

    if args.command == "export-spans":
        count = export_spans(ANNOTATIONS_PATH, args.spans)
        print(json.dumps({"spans": count, "path": str(args.spans), "fields": SPAN_FIELDS}, indent=2))
        return 0

    config_path = Path(args.config)
    config = load_config(config_path)
    bootstrap = config["analysis_policy"]["bootstrap"]
    args.replicates = args.replicates or bootstrap["replicates"]
    args.seed = bootstrap["seed"] if args.seed is None else args.seed
    freeze_overrides = {"battery_config_sha256": config_path, "arms_config_sha256": ARMS_CONFIG_PATH,
                        "generations_sha256": args.generations, "token_traces_sha256": args.traces}

    if args.command == "freeze":
        missing = [flag for flag, value in (("--date", args.date), ("--labels", args.labels), ("--codebook", args.codebook),
                                            ("--schema", args.schema), ("--preregistration", args.preregistration),
                                            ("--power-notes", args.power_notes)) if not value]
        if missing or len(args.labels) != 1:
            parser.error(f"freeze needs {missing or ['exactly one --labels file']}")
        run_freeze(args.date, config_path, Path(args.arms_config or ARMS_CONFIG_PATH), Path(args.labels[0]),
                   args.label_mapping, Path(args.codebook), Path(args.schema), Path(args.heldout_slice or HELDOUT_SLICE_PATH),
                   Path(args.preregistration), Path(args.power_notes), Path(args.generations), Path(args.traces))
        return 0

    if args.command == "run" and args.split != "dev":
        if config.get("status") not in EVAL_READY_STATUSES:
            raise SystemExit(f"config status is {config.get('status')!r}; run accepts only --split dev "
                             f"until the status is one of {sorted(EVAL_READY_STATUSES)}")
        require_freeze(args.split, f"run --split {args.split}", FREEZE_PATH, freeze_overrides)

    if args.command == "validate":
        result = validate(config_path=config_path, generations_path=args.generations if args.require_local else None,
                          output_dir=OUTPUT_ROOT, require_local=args.require_local, spans_path=args.spans)
        print(json.dumps({k: v for k, v in result.items() if k != "checker_audit"}, indent=2))
        return 1 if result["num_failures"] else 0

    if args.command == "smoke":
        if not args.arm:
            parser.error("smoke needs --arm")
        arm = load_arms(ARMS_CONFIG_PATH)[args.arm]
        report = run_smoke(config, arm, read_api_key(arm), OUTPUT_ROOT / arm["arm_id"] / "smoke.json")
        return 1 if report["problems"] else 0

    uses_demo = not Path(args.generations).exists()
    if uses_demo and args.command in {"run", "score"} and not args.public_demo:
        raise SystemExit(f"generation file not found: {args.generations}; "
                         "pass --public-demo to use the nine public demo answers")
    if args.command == "score":
        return score_command(args, config, config_path, freeze_overrides)

    gold = load_gold()
    span_set_id = span_set_id_for(args.spans)
    heldout_ids = load_heldout_ids()
    freeze_record = None
    if "heldout" in config["analysis_policy"]["span_sets"][span_set_id]["roles"]:
        freeze_record = require_freeze("heldout", f"{args.command} on {span_set_id}", FREEZE_PATH, freeze_overrides)
    spans = load_spans(args.spans)
    if freeze_record is None and any(span["question_id"] in heldout_ids for span in spans):
        freeze_record = require_freeze("heldout", f"{args.command} on held-out spans", FREEZE_PATH, freeze_overrides)
    labels = load_labels(args.labels, args.label_mapping, config) if args.labels else {}
    texts, sources = load_generated_texts(args.generations, heldout_ids=readable_heldout_ids(heldout_ids, freeze_record))
    if "public_demo_bundle" in sources.values() and args.command == "run" and not args.public_demo:
        raise SystemExit("some answers come from the public demo bundle; pass --public-demo to use them")
    if uses_demo and args.command in {"build", "check"}:
        _stderr(f"using public demo bundle: {dict(Counter(sources.values()))}")
    manifest_args = (config_path, ARMS_CONFIG_PATH, args.spans, args.generations)

    if args.command == "build":
        scan_rows = {row["annotation_id"]: row for row in load_annotations()} if ANNOTATIONS_PATH.exists() else {}
        scan_rows.update({aid: item["row"] for aid, item in labels.items()})
        states, skipped = build_states(config, gold, spans, texts, sources, label_rows=scan_rows, heldout_ids=heldout_ids)
        states_path, manifest_path = write_states(states, span_set_id, *manifest_args)
        print(json.dumps({"states": len(states), "skipped": skipped[:5], "skipped_count": len(skipped),
                          "text_sources": dict(Counter(sources.values())), "path": str(states_path),
                          "manifest": str(manifest_path)}, indent=2, ensure_ascii=False))
        return 0

    if args.command == "check":
        checker_results = rule_checker.run_checker(config, gold, spans, texts)
        attributes = span_attributes(config, gold, spans)
        _write_jsonl(OUTPUT_ROOT / f"checker_{span_set_id}.jsonl", checker_results)
        _write_jsonl(OUTPUT_ROOT / f"span_kind_{span_set_id}.jsonl", span_kind_rows(attributes))
        summary = {"checker_spans": len(checker_results),
                   "span_kinds": dict(sorted(Counter(item["span_kind"] for item in attributes.values()).items()))}
        if labels:
            audit = rule_checker.checker_audit(checker_results, binary_labels(labels))
            audit["label_mapping"] = args.label_mapping
            _dump_json(OUTPUT_ROOT / f"checker_audit_{span_set_id}_{args.label_mapping}.json", audit)
            summary["audit"] = audit
        else:
            summary["audit"] = "not run: no --labels given"
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    if not args.arm:
        parser.error("run needs --arm")
    arm = load_arms(ARMS_CONFIG_PATH)[args.arm]
    arm_dir = OUTPUT_ROOT / arm["arm_id"]
    states, _ = load_states(span_set_id, *manifest_args)
    states = [state for state in states if state["role"] == args.split]
    api_key = read_api_key(arm)
    if args.repeats is not None:
        repeats = args.repeats
    else:
        role = "dev" if args.split == "dev" else "eval"
        repeats = (arm.get("repeats") or {}).get(role)
        if not repeats:
            raise SystemExit(f"arm {arm['arm_id']}: repeats.{role} is not set in the arms config")
    arm_dir.mkdir(parents=True, exist_ok=True)
    provenance = {"battery_id": config["battery_id"], "config_sha256": file_sha256(config_path)}
    summary = run_battery(states, arm, api_key, repeats, arm_dir / "responses.jsonl", limit=args.limit,
                          provenance=provenance, cleared_roles=(args.split,))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
