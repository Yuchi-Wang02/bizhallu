from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from build_span_token_alignment import build_token_char_spans, overlapping_tokens


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
ANNOTATION_DIR = PROJECT_ROOT / "data" / "annotations"

ANNOTATION_PATH = ANNOTATION_DIR / "span_annotations_full100_draft.jsonl"
GENERATION_PATH = OUTPUT_DIR / "qwen_full100_generations.jsonl"
TRACE_PATH = OUTPUT_DIR / "qwen_full100_token_traces.jsonl"
BATCH_PATH = OUTPUT_DIR / "full100_heldout_high_annotation_batch.jsonl"
AUDIT_REPORT_PATH = OUTPUT_DIR / "full100_annotation_consistency_audit_report.json"

ALIGNMENT_JSONL_PATH = OUTPUT_DIR / "full100_draft_span_token_alignment.jsonl"
ALIGNMENT_CSV_PATH = OUTPUT_DIR / "full100_draft_span_token_alignment.csv"
ALIGNMENT_REPORT_PATH = OUTPUT_DIR / "full100_draft_span_token_alignment_report.json"
VALIDATION_PATH = OUTPUT_DIR / "full100_draft_span_token_alignment_validation.json"
BY_SPLIT_PATH = OUTPUT_DIR / "full100_draft_span_token_alignment_by_split.csv"
BY_QUESTION_PATH = OUTPUT_DIR / "full100_draft_span_token_alignment_by_question.csv"

EXPECTED_SPAN_COUNT = 205
EXPECTED_QUESTION_COUNT = 35
EXPECTED_SPLIT_COUNTS = {"dev": 17, "test": 18}
SIMPLE_SCORE_FIELDS = [
    "mean_token_logprob",
    "mean_token_nll",
    "mean_token_entropy",
    "max_token_entropy",
    "mean_top2_margin",
    "min_top2_margin",
]
ENERGY_SCORE_FIELDS = [
    "mean_selected_step_energy_gap",
    "max_selected_step_energy_gap",
    "mean_spilled_energy_delta",
    "mean_spilled_energy_abs_delta",
    "max_spilled_energy_abs_delta",
    "mean_token_energy",
    "mean_marginal_energy",
    "mean_spilled_probability_mass_after_top1",
    "mean_spilled_probability_mass_after_top2",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None, **context: Any) -> None:
    failure = {"reason": reason, **{key: value for key, value in context.items() if value not in (None, "")}}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def is_finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    return math.isfinite(float(value))


def json_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def write_dict_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized: dict[str, Any] = {}
            for field in fieldnames:
                value = row.get(field, "")
                normalized[field] = json_cell(value) if isinstance(value, (dict, list)) else value
            writer.writerow(normalized)


def summarize_rows_by_split(
    alignment_records: list[dict[str, Any]],
    batch_by_qid: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in alignment_records:
        split = str(batch_by_qid[str(record["question_id"])]["split"])
        grouped[split].append(record)

    rows: list[dict[str, Any]] = []
    for split in sorted(grouped):
        records = grouped[split]
        label_counts = Counter(str(record["label"]) for record in records)
        fact_type_counts = Counter(str(record["fact_type"]) for record in records)
        question_ids = sorted({str(record["question_id"]) for record in records})
        rows.append(
            {
                "split": split,
                "question_count": len(question_ids),
                "span_count": len(records),
                "question_ids": question_ids,
                "label_counts": dict(sorted(label_counts.items())),
                "fact_type_counts": dict(sorted(fact_type_counts.items())),
                "min_token_count": min(int(record["token_count"]) for record in records),
                "max_token_count": max(int(record["token_count"]) for record in records),
                "max_left_boundary_slop": max(int(record["left_boundary_slop"]) for record in records),
                "max_right_boundary_slop": max(int(record["right_boundary_slop"]) for record in records),
            }
        )
    return rows


def summarize_rows_by_question(
    alignment_records: list[dict[str, Any]],
    batch_by_qid: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in alignment_records:
        grouped[str(record["question_id"])].append(record)

    rows: list[dict[str, Any]] = []
    for qid in sorted(grouped):
        records = grouped[qid]
        batch = batch_by_qid[qid]
        label_counts = Counter(str(record["label"]) for record in records)
        fact_type_counts = Counter(str(record["fact_type"]) for record in records)
        rows.append(
            {
                "question_id": qid,
                "split": batch["split"],
                "question_type": batch["question_type"],
                "span_count": len(records),
                "label_counts": dict(sorted(label_counts.items())),
                "fact_type_counts": dict(sorted(fact_type_counts.items())),
                "min_token_count": min(int(record["token_count"]) for record in records),
                "max_token_count": max(int(record["token_count"]) for record in records),
                "max_left_boundary_slop": max(int(record["left_boundary_slop"]) for record in records),
                "max_right_boundary_slop": max(int(record["right_boundary_slop"]) for record in records),
            }
        )
    return rows


def main() -> None:
    failures: list[dict[str, Any]] = []
    required_paths = {
        "annotation": ANNOTATION_PATH,
        "generation": GENERATION_PATH,
        "trace": TRACE_PATH,
        "heldout_batch": BATCH_PATH,
        "consistency_audit_report": AUDIT_REPORT_PATH,
        "alignment_jsonl": ALIGNMENT_JSONL_PATH,
        "alignment_csv": ALIGNMENT_CSV_PATH,
        "alignment_report": ALIGNMENT_REPORT_PATH,
    }
    for name, path in required_paths.items():
        if not path.exists():
            add_failure(failures, "missing required file", {"name": name, "path": str(path)})

    if failures:
        validation = {"num_failures": len(failures), "failures": failures, "ready_for_scoring_prep": False}
        VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    annotations = load_jsonl(ANNOTATION_PATH)
    generations = load_jsonl(GENERATION_PATH)
    trace_records = load_jsonl(TRACE_PATH)
    batch_records = load_jsonl(BATCH_PATH)
    alignment_records = load_jsonl(ALIGNMENT_JSONL_PATH)
    alignment_csv_rows = load_csv(ALIGNMENT_CSV_PATH)
    alignment_report = load_json(ALIGNMENT_REPORT_PATH)
    audit_report = load_json(AUDIT_REPORT_PATH)

    annotations_by_id = {str(record["annotation_id"]): record for record in annotations}
    alignment_by_id = {str(record["annotation_id"]): record for record in alignment_records}
    generations_by_qid = {str(record["question_id"]): record for record in generations}
    traces_by_qid = {str(record["question_id"]): record for record in trace_records}
    batch_by_qid = {str(record["question_id"]): record for record in batch_records}

    annotation_ids = set(annotations_by_id)
    alignment_ids = set(alignment_by_id)
    if annotation_ids != alignment_ids:
        add_failure(
            failures,
            "alignment annotation_id set mismatch",
            {"missing": sorted(annotation_ids - alignment_ids), "extra": sorted(alignment_ids - annotation_ids)},
        )

    if len(alignment_records) != EXPECTED_SPAN_COUNT:
        add_failure(failures, "unexpected alignment record count", {"expected": EXPECTED_SPAN_COUNT, "actual": len(alignment_records)})
    if len(alignment_csv_rows) != len(alignment_records):
        add_failure(
            failures,
            "alignment csv/jsonl row count mismatch",
            {"csv_rows": len(alignment_csv_rows), "jsonl_rows": len(alignment_records)},
        )

    question_ids = sorted({str(record["question_id"]) for record in alignment_records})
    if len(question_ids) != EXPECTED_QUESTION_COUNT:
        add_failure(failures, "unexpected aligned question count", {"expected": EXPECTED_QUESTION_COUNT, "actual": len(question_ids)})
    if set(question_ids) != set(batch_by_qid):
        add_failure(
            failures,
            "aligned question set does not match heldout high-priority batch",
            {"missing": sorted(set(batch_by_qid) - set(question_ids)), "extra": sorted(set(question_ids) - set(batch_by_qid))},
        )

    split_counts = Counter(str(batch_by_qid[qid]["split"]) for qid in question_ids if qid in batch_by_qid)
    if dict(sorted(split_counts.items())) != EXPECTED_SPLIT_COUNTS:
        add_failure(failures, "unexpected aligned question split counts", {"expected": EXPECTED_SPLIT_COUNTS, "actual": dict(sorted(split_counts.items()))})
    if audit_report.get("ready_for_alignment") is not True or audit_report.get("num_failures") != 0:
        add_failure(failures, "consistency audit is not ready for alignment", audit_report)

    if alignment_report.get("num_failures") != 0:
        add_failure(failures, "alignment report has failures", alignment_report.get("failures"))
    if alignment_report.get("aligned_span_count") != len(alignment_records):
        add_failure(
            failures,
            "alignment report count mismatch",
            {"report_count": alignment_report.get("aligned_span_count"), "actual": len(alignment_records)},
        )
    if alignment_report.get("ready_for_simple_logit_baselines") is not True:
        add_failure(failures, "alignment report is not simple-baseline ready")
    if alignment_report.get("ready_for_energy_baselines") is not True:
        add_failure(failures, "alignment report is not energy-baseline ready")

    token_spans_by_qid: dict[str, list[dict[str, Any]]] = {}
    annotated_replacement_pair_questions: set[str] = set()
    for qid in question_ids:
        generation = generations_by_qid.get(qid)
        trace_record = traces_by_qid.get(qid)
        if generation is None or trace_record is None:
            add_failure(failures, "missing generation or trace for aligned question", question_id=qid)
            continue
        token_spans, token_failures = build_token_char_spans(qid, str(generation["generated_text"]), trace_record["token_traces"])
        token_spans_by_qid[qid] = token_spans
        for failure in token_failures:
            add_failure(failures, "token reconstruction failure", failure, question_id=qid)
        if qid in set(alignment_report.get("replacement_pair_questions", [])):
            annotated_replacement_pair_questions.add(qid)

    for annotation_id, record in sorted(alignment_by_id.items()):
        annotation = annotations_by_id.get(annotation_id)
        if annotation is None:
            continue
        qid = str(record.get("question_id"))
        generation = generations_by_qid.get(qid)
        token_spans = token_spans_by_qid.get(qid, [])
        if generation is None or not token_spans:
            continue

        comparable_fields = ["question_id", "prompt_id", "fact_type", "label", "span_text", "span_start_char", "span_end_char"]
        for field in comparable_fields:
            if record.get(field) != annotation.get(field):
                add_failure(
                    failures,
                    "alignment record does not match annotation",
                    {"field": field, "annotation": annotation.get(field), "alignment": record.get(field)},
                    annotation_id=annotation_id,
                    question_id=qid,
                )

        span_start = int(record["span_start_char"])
        span_end = int(record["span_end_char"])
        generated_text = str(generation["generated_text"])
        if generated_text[span_start:span_end] != record["span_text"]:
            add_failure(
                failures,
                "alignment span offsets do not match generated text",
                {"expected": record["span_text"], "actual": generated_text[span_start:span_end]},
                annotation_id=annotation_id,
                question_id=qid,
            )

        expected_tokens = overlapping_tokens(token_spans, span_start, span_end)
        expected_positions = [int(token["position"]) for token in expected_tokens]
        if expected_positions != record.get("token_positions"):
            add_failure(
                failures,
                "alignment token positions mismatch recomputed overlap",
                {"expected": expected_positions, "actual": record.get("token_positions")},
                annotation_id=annotation_id,
                question_id=qid,
            )
        if int(record.get("token_count", -1)) != len(expected_positions) or int(record.get("token_count", -1)) <= 0:
            add_failure(
                failures,
                "invalid token_count",
                {"token_count": record.get("token_count"), "expected": len(expected_positions)},
                annotation_id=annotation_id,
                question_id=qid,
            )
        if expected_positions:
            if int(record["token_start_position"]) != min(expected_positions) or int(record["token_end_position"]) != max(expected_positions) + 1:
                add_failure(
                    failures,
                    "token start/end positions inconsistent",
                    {"positions": expected_positions, "start": record["token_start_position"], "end": record["token_end_position"]},
                    annotation_id=annotation_id,
                    question_id=qid,
                )
            if expected_positions != list(range(min(expected_positions), max(expected_positions) + 1)):
                add_failure(
                    failures,
                    "token positions are not contiguous",
                    expected_positions,
                    annotation_id=annotation_id,
                    question_id=qid,
                )

        token_char_start = int(record["token_char_start"])
        token_char_end = int(record["token_char_end"])
        token_window = generated_text[token_char_start:token_char_end]
        if token_window != record.get("token_text_window"):
            add_failure(
                failures,
                "token_text_window does not match generated text",
                {"expected": token_window, "actual": record.get("token_text_window")},
                annotation_id=annotation_id,
                question_id=qid,
            )
        if record["span_text"] not in token_window:
            add_failure(
                failures,
                "token window does not contain span text",
                {"span_text": record["span_text"], "token_window": token_window},
                annotation_id=annotation_id,
                question_id=qid,
            )
        if int(record["left_boundary_slop"]) < 0 or int(record["right_boundary_slop"]) < 0:
            add_failure(
                failures,
                "negative boundary slop",
                {"left": record["left_boundary_slop"], "right": record["right_boundary_slop"]},
                annotation_id=annotation_id,
                question_id=qid,
            )
        if int(record["left_boundary_slop"]) > 1 or int(record["right_boundary_slop"]) > 1:
            add_failure(
                failures,
                "boundary slop larger than expected for full100 draft",
                {"left": record["left_boundary_slop"], "right": record["right_boundary_slop"]},
                annotation_id=annotation_id,
                question_id=qid,
            )

        for field in SIMPLE_SCORE_FIELDS + ENERGY_SCORE_FIELDS:
            if not is_finite_number(record.get(field)):
                add_failure(
                    failures,
                    "missing or non-finite score field",
                    {"field": field, "value": record.get(field)},
                    annotation_id=annotation_id,
                    question_id=qid,
                )

    by_split_rows = summarize_rows_by_split(alignment_records, batch_by_qid)
    by_question_rows = summarize_rows_by_question(alignment_records, batch_by_qid)
    write_dict_csv(
        BY_SPLIT_PATH,
        by_split_rows,
        [
            "split",
            "question_count",
            "span_count",
            "question_ids",
            "label_counts",
            "fact_type_counts",
            "min_token_count",
            "max_token_count",
            "max_left_boundary_slop",
            "max_right_boundary_slop",
        ],
    )
    write_dict_csv(
        BY_QUESTION_PATH,
        by_question_rows,
        [
            "question_id",
            "split",
            "question_type",
            "span_count",
            "label_counts",
            "fact_type_counts",
            "min_token_count",
            "max_token_count",
            "max_left_boundary_slop",
            "max_right_boundary_slop",
        ],
    )

    distribution_by_split_label = {
        row["split"]: row["label_counts"] for row in by_split_rows
    }
    if distribution_by_split_label != audit_report.get("distribution_by_split_label"):
        add_failure(
            failures,
            "split label distribution does not match consistency audit",
            {"alignment": distribution_by_split_label, "audit": audit_report.get("distribution_by_split_label")},
        )

    distribution_by_split_fact_type = {
        row["split"]: row["fact_type_counts"] for row in by_split_rows
    }
    if distribution_by_split_fact_type != audit_report.get("distribution_by_split_fact_type"):
        add_failure(
            failures,
            "split fact_type distribution does not match consistency audit",
            {"alignment": distribution_by_split_fact_type, "audit": audit_report.get("distribution_by_split_fact_type")},
        )

    label_counts = Counter(str(record["label"]) for record in alignment_records)
    fact_type_counts = Counter(str(record["fact_type"]) for record in alignment_records)
    token_counts = [int(record["token_count"]) for record in alignment_records]
    ready_for_scoring_prep = len(failures) == 0
    validation = {
        "alignment_jsonl_path": str(ALIGNMENT_JSONL_PATH),
        "alignment_csv_path": str(ALIGNMENT_CSV_PATH),
        "alignment_report_path": str(ALIGNMENT_REPORT_PATH),
        "by_split_path": str(BY_SPLIT_PATH),
        "by_question_path": str(BY_QUESTION_PATH),
        "span_count": len(alignment_records),
        "question_count": len(question_ids),
        "split_counts": dict(sorted(split_counts.items())),
        "label_counts": dict(sorted(label_counts.items())),
        "fact_type_counts": dict(sorted(fact_type_counts.items())),
        "token_count_summary": {
            "min": min(token_counts) if token_counts else None,
            "max": max(token_counts) if token_counts else None,
            "mean": round(sum(token_counts) / len(token_counts), 4) if token_counts else None,
        },
        "boundary_slop_summary": alignment_report.get("boundary_slop_summary"),
        "replacement_pair_questions_in_full_generation": alignment_report.get("replacement_pair_questions", []),
        "replacement_pair_questions_in_annotated_draft": sorted(annotated_replacement_pair_questions),
        "ready_for_scoring_prep": ready_for_scoring_prep,
        "allowed_next_step": "build full100 draft detector score files, after reviewing audit notes" if ready_for_scoring_prep else "fix alignment validation failures",
        "metrics_reported": False,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
