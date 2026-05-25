from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
ANNOTATION_DIR = PROJECT_ROOT / "data" / "annotations"

ANNOTATION_PATH = ANNOTATION_DIR / "span_annotations_full100_draft.jsonl"
BATCH_PATH = OUTPUT_DIR / "full100_heldout_high_annotation_batch.jsonl"
PREVIEW_PATH = OUTPUT_DIR / "full100_annotation_draft_preview.csv"
DRAFT_REPORT_PATH = OUTPUT_DIR / "full100_annotation_draft_report.json"
DRAFT_VALIDATION_PATH = OUTPUT_DIR / "full100_annotation_draft_validation.json"

REPORT_PATH = OUTPUT_DIR / "full100_annotation_consistency_audit_report.json"
BY_QUESTION_PATH = OUTPUT_DIR / "full100_annotation_consistency_audit_by_question.csv"
BY_SPLIT_PATH = OUTPUT_DIR / "full100_annotation_consistency_audit_by_split.csv"
POLICY_FLAGS_PATH = OUTPUT_DIR / "full100_annotation_consistency_audit_policy_flags.csv"

EXPECTED_QUESTION_COUNT = 35
EXPECTED_SPAN_COUNT = 205
EXPECTED_SPLIT_COUNTS = {"dev": 17, "test": 18}
EXPECTED_SOURCE_FILE = "outputs/qwen_full100_generations.jsonl"

POSITIVE_LABELS = {"hallucinated_key_fact", "unsupported_claim"}
ALLOWED_SOURCE_BATCHES = {"seed", "draft_round1", "draft_round2", "draft_round3", "draft_round4"}
BARE_RANK_RE = re.compile(r"^\*{0,2}\d+(?:st|nd|rd|th)?[.)]?\*{0,2}$", re.IGNORECASE)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        record = json.loads(line)
        record["_line_number"] = line_number
        records.append(record)
    return records


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def add_issue(
    issues: list[dict[str, Any]],
    severity: str,
    issue_type: str,
    detail: str,
    *,
    question_id: str = "",
    annotation_id: str = "",
) -> None:
    issues.append(
        {
            "severity": severity,
            "issue_type": issue_type,
            "question_id": question_id,
            "annotation_id": annotation_id,
            "detail": detail,
        }
    )


def json_cell(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True)


def collect_question_rows(
    annotations_by_qid: dict[str, list[dict[str, Any]]],
    batch_by_qid: dict[str, dict[str, Any]],
    source_batch_by_qid: dict[str, set[str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for qid in sorted(annotations_by_qid):
        records = annotations_by_qid[qid]
        batch = batch_by_qid.get(qid, {})
        labels = Counter(str(record.get("label")) for record in records)
        fact_types = Counter(str(record.get("fact_type")) for record in records)
        positive_count = sum(labels[label] for label in POSITIVE_LABELS)
        rows.append(
            {
                "question_id": qid,
                "split": batch.get("split", ""),
                "question_type": batch.get("question_type", ""),
                "source_batches": sorted(source_batch_by_qid.get(qid, set())),
                "span_count": len(records),
                "correct_key_fact_count": labels.get("correct_key_fact", 0),
                "hallucinated_key_fact_count": labels.get("hallucinated_key_fact", 0),
                "unsupported_claim_count": labels.get("unsupported_claim", 0),
                "positive_count": positive_count,
                "positive_rate": round(positive_count / len(records), 4) if records else 0.0,
                "label_counts": dict(sorted(labels.items())),
                "fact_type_counts": dict(sorted(fact_types.items())),
            }
        )
    return rows


def collect_split_rows(question_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in question_rows:
        by_split[str(row["split"])].append(row)

    rows: list[dict[str, Any]] = []
    for split in sorted(by_split):
        split_question_rows = by_split[split]
        label_counts: Counter[str] = Counter()
        fact_type_counts: Counter[str] = Counter()
        span_count = 0
        for row in split_question_rows:
            span_count += int(row["span_count"])
            label_counts.update(row["label_counts"])
            fact_type_counts.update(row["fact_type_counts"])
        positive_count = sum(label_counts[label] for label in POSITIVE_LABELS)
        rows.append(
            {
                "split": split,
                "question_count": len(split_question_rows),
                "span_count": span_count,
                "correct_key_fact_count": label_counts.get("correct_key_fact", 0),
                "hallucinated_key_fact_count": label_counts.get("hallucinated_key_fact", 0),
                "unsupported_claim_count": label_counts.get("unsupported_claim", 0),
                "positive_count": positive_count,
                "positive_rate": round(positive_count / span_count, 4) if span_count else 0.0,
                "label_counts": dict(sorted(label_counts.items())),
                "fact_type_counts": dict(sorted(fact_type_counts.items())),
            }
        )
    return rows


def write_dict_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            normalized = {}
            for field in fieldnames:
                value = row.get(field, "")
                if isinstance(value, (dict, list, set)):
                    normalized[field] = json_cell(sorted(value) if isinstance(value, set) else value)
                else:
                    normalized[field] = value
            writer.writerow(normalized)


def build_expected_source_batch_by_qid(draft_report: dict[str, Any], batch_qids: set[str]) -> dict[str, str]:
    expected: dict[str, str] = {}
    for qid in batch_qids:
        expected[qid] = "seed"
    for round_name in ("round1", "round2", "round3", "round4"):
        for qid in draft_report.get(f"{round_name}_question_ids", []):
            expected[str(qid)] = f"draft_{round_name}"
    return expected


def main() -> None:
    issues: list[dict[str, Any]] = []
    for path_name, path in {
        "annotation": ANNOTATION_PATH,
        "heldout high-priority batch": BATCH_PATH,
        "draft preview": PREVIEW_PATH,
        "draft report": DRAFT_REPORT_PATH,
        "draft validation": DRAFT_VALIDATION_PATH,
    }.items():
        if not path.exists():
            add_issue(issues, "failure", "missing_file", f"Missing {path_name} file: {path}")

    if any(issue["severity"] == "failure" for issue in issues):
        report = {"ready_for_alignment": False, "num_failures": len(issues), "issues": issues}
        REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    annotations = load_jsonl(ANNOTATION_PATH)
    batch_records = load_jsonl(BATCH_PATH)
    preview_rows = load_csv(PREVIEW_PATH)
    draft_report = load_json(DRAFT_REPORT_PATH)
    draft_validation = load_json(DRAFT_VALIDATION_PATH)

    batch_by_qid = {str(record["question_id"]): record for record in batch_records}
    batch_qids = set(batch_by_qid)
    annotation_qids = {str(record.get("question_id")) for record in annotations}
    annotations_by_qid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in annotations:
        annotations_by_qid[str(record.get("question_id"))].append(record)

    if len(annotations) != EXPECTED_SPAN_COUNT:
        add_issue(
            issues,
            "failure",
            "unexpected_span_count",
            f"Expected {EXPECTED_SPAN_COUNT} spans, found {len(annotations)}.",
        )
    if len(annotation_qids) != EXPECTED_QUESTION_COUNT:
        add_issue(
            issues,
            "failure",
            "unexpected_question_count",
            f"Expected {EXPECTED_QUESTION_COUNT} questions, found {len(annotation_qids)}.",
        )
    if annotation_qids != batch_qids:
        missing = sorted(batch_qids - annotation_qids)
        extra = sorted(annotation_qids - batch_qids)
        add_issue(
            issues,
            "failure",
            "annotated_question_set_mismatch",
            f"Annotated questions must exactly match held-out high-priority batch. Missing={missing}; extra={extra}.",
        )

    split_counts = Counter(str(batch_by_qid[qid].get("split")) for qid in annotation_qids if qid in batch_by_qid)
    if dict(sorted(split_counts.items())) != EXPECTED_SPLIT_COUNTS:
        add_issue(
            issues,
            "failure",
            "unexpected_split_counts",
            f"Expected split counts {EXPECTED_SPLIT_COUNTS}, found {dict(sorted(split_counts.items()))}.",
        )
    if any(split not in {"dev", "test"} for split in split_counts):
        add_issue(issues, "failure", "train_or_unknown_split_in_draft", f"Found split counts {dict(split_counts)}.")

    for qid, batch in sorted(batch_by_qid.items()):
        if batch.get("annotation_priority") != "high":
            add_issue(issues, "failure", "non_high_priority_batch_row", "Initial batch row is not high priority.", question_id=qid)
        if batch.get("is_initial_batch") is not True:
            add_issue(issues, "failure", "non_initial_batch_row", "Held-out high batch row is not marked initial.", question_id=qid)
        if batch.get("queue_phase") != "phase_1_heldout_high":
            add_issue(
                issues,
                "failure",
                "unexpected_queue_phase",
                f"Expected phase_1_heldout_high, found {batch.get('queue_phase')}.",
                question_id=qid,
            )

    validation_failures = draft_validation.get("num_failures")
    if validation_failures != 0:
        add_issue(
            issues,
            "failure",
            "draft_schema_offset_validation_failed",
            f"Draft span validation reports {validation_failures} failures.",
        )
    if draft_validation.get("span_count") != len(annotations):
        add_issue(
            issues,
            "failure",
            "validation_span_count_mismatch",
            f"Validation span count {draft_validation.get('span_count')} does not match JSONL count {len(annotations)}.",
        )
    if draft_validation.get("annotated_question_count") != len(annotation_qids):
        add_issue(
            issues,
            "failure",
            "validation_question_count_mismatch",
            "Validation question count does not match annotation JSONL question count.",
        )

    preview_by_annotation_id = {str(row.get("annotation_id")): row for row in preview_rows}
    annotation_ids = {str(record.get("annotation_id")) for record in annotations}
    preview_annotation_ids = set(preview_by_annotation_id)
    if len(preview_rows) != len(annotations) or preview_annotation_ids != annotation_ids:
        add_issue(
            issues,
            "failure",
            "preview_annotation_set_mismatch",
            f"Preview rows={len(preview_rows)}, annotation rows={len(annotations)}; id sets must match.",
        )

    source_batch_by_qid: dict[str, set[str]] = defaultdict(set)
    expected_source_batch_by_qid = build_expected_source_batch_by_qid(draft_report, batch_qids)
    for row in preview_rows:
        qid = str(row.get("question_id", ""))
        source_batch = str(row.get("source_batch", ""))
        source_batch_by_qid[qid].add(source_batch)
        if source_batch not in ALLOWED_SOURCE_BATCHES:
            add_issue(
                issues,
                "failure",
                "unexpected_source_batch",
                f"Unexpected source_batch={source_batch}.",
                question_id=qid,
                annotation_id=str(row.get("annotation_id", "")),
            )
        expected_source_batch = expected_source_batch_by_qid.get(qid)
        if expected_source_batch and source_batch != expected_source_batch:
            add_issue(
                issues,
                "failure",
                "source_batch_question_mismatch",
                f"Expected source_batch={expected_source_batch}, found {source_batch}.",
                question_id=qid,
                annotation_id=str(row.get("annotation_id", "")),
            )
        batch = batch_by_qid.get(qid)
        if batch:
            if row.get("split") != batch.get("split"):
                add_issue(
                    issues,
                    "failure",
                    "preview_split_mismatch",
                    f"Preview split={row.get('split')} but batch split={batch.get('split')}.",
                    question_id=qid,
                    annotation_id=str(row.get("annotation_id", "")),
                )
            if row.get("question_type") != batch.get("question_type"):
                add_issue(
                    issues,
                    "failure",
                    "preview_question_type_mismatch",
                    f"Preview question_type={row.get('question_type')} but batch question_type={batch.get('question_type')}.",
                    question_id=qid,
                    annotation_id=str(row.get("annotation_id", "")),
                )

    for record in annotations:
        qid = str(record.get("question_id"))
        annotation_id = str(record.get("annotation_id"))
        if record.get("source_generation_file") != EXPECTED_SOURCE_FILE:
            add_issue(
                issues,
                "failure",
                "unexpected_source_generation_file",
                f"Expected {EXPECTED_SOURCE_FILE}, found {record.get('source_generation_file')}.",
                question_id=qid,
                annotation_id=annotation_id,
            )
        gold_reference = record.get("gold_reference")
        if not isinstance(gold_reference, dict):
            continue
        ref_fact_type = gold_reference.get("fact_type")
        fact_type = record.get("fact_type")
        if ref_fact_type and ref_fact_type != fact_type:
            allowed_malformed_ref = fact_type == "malformed_number" and ref_fact_type == "currency_amount"
            if not allowed_malformed_ref:
                add_issue(
                    issues,
                    "warning",
                    "gold_reference_fact_type_mismatch",
                    f"Span fact_type={fact_type} but gold_reference.fact_type={ref_fact_type}.",
                    question_id=qid,
                    annotation_id=annotation_id,
                )
        if fact_type == "ranking" and BARE_RANK_RE.fullmatch(str(record.get("span_text", "")).strip()):
            if "list_rank_marker" in str(record.get("notes", "")):
                add_issue(
                    issues,
                    "info",
                    "bare_rank_marker_allowed",
                    "Bare rank marker is allowed because notes include list_rank_marker.",
                    question_id=qid,
                    annotation_id=annotation_id,
                )

    question_rows = collect_question_rows(annotations_by_qid, batch_by_qid, source_batch_by_qid)
    split_rows = collect_split_rows(question_rows)

    for row in question_rows:
        qid = str(row["question_id"])
        question_type = str(row["question_type"])
        fact_types = set(row["fact_type_counts"])
        if row["positive_count"] == 0:
            add_issue(
                issues,
                "warning",
                "correct_only_question",
                "Question has no positive spans; verify this is an omission-only or genuinely correct generated answer.",
                question_id=qid,
            )
        if row["correct_key_fact_count"] == 0:
            add_issue(
                issues,
                "warning",
                "no_correct_key_fact",
                "Question has no correct_key_fact spans; verify this is intended for this answer.",
                question_id=qid,
            )
        if row["unsupported_claim_count"] > 0:
            add_issue(
                issues,
                "warning",
                "unsupported_claim_review",
                "Question contains unsupported_claim spans; verify unsupported vs contradicted decision before final scoring.",
                question_id=qid,
            )
        if question_type == "top3_products_month" and "ranking" not in fact_types:
            add_issue(
                issues,
                "warning",
                "top3_without_ranking_span",
                "Top3 answer has no ranking spans; verify whether the generated text omitted rank-binding claims.",
                question_id=qid,
            )
        if question_type == "product_revenue_share_month" and "percentage" not in fact_types:
            add_issue(
                issues,
                "warning",
                "share_question_without_percentage",
                "Product-share answer has no percentage span; verify whether the generated answer omitted share percentage.",
                question_id=qid,
            )

    split_positive_counts = {row["split"]: row["positive_count"] for row in split_rows}
    for split in ("dev", "test"):
        if split_positive_counts.get(split, 0) == 0:
            add_issue(
                issues,
                "failure",
                "split_has_no_positive_spans",
                f"{split} split has no hallucinated or unsupported spans.",
            )

    label_counts = Counter(str(record.get("label")) for record in annotations)
    fact_type_counts = Counter(str(record.get("fact_type")) for record in annotations)
    question_type_counts = Counter(str(batch_by_qid[qid].get("question_type")) for qid in annotation_qids if qid in batch_by_qid)
    source_batch_counts = Counter(str(row.get("source_batch", "")) for row in preview_rows)

    distribution_by_split_label: dict[str, dict[str, int]] = {}
    distribution_by_split_fact_type: dict[str, dict[str, int]] = {}
    for split in ("dev", "test"):
        qids = {qid for qid, batch in batch_by_qid.items() if batch.get("split") == split}
        split_records = [record for record in annotations if record.get("question_id") in qids]
        distribution_by_split_label[split] = dict(sorted(Counter(str(record.get("label")) for record in split_records).items()))
        distribution_by_split_fact_type[split] = dict(
            sorted(Counter(str(record.get("fact_type")) for record in split_records).items())
        )

    policy_flags = sorted(issues, key=lambda item: (item["severity"], item["question_id"], item["annotation_id"], item["issue_type"]))
    failures = [issue for issue in issues if issue["severity"] == "failure"]
    warnings = [issue for issue in issues if issue["severity"] == "warning"]
    infos = [issue for issue in issues if issue["severity"] == "info"]
    ready_for_alignment = len(failures) == 0

    write_dict_csv(
        BY_QUESTION_PATH,
        question_rows,
        [
            "question_id",
            "split",
            "question_type",
            "source_batches",
            "span_count",
            "correct_key_fact_count",
            "hallucinated_key_fact_count",
            "unsupported_claim_count",
            "positive_count",
            "positive_rate",
            "label_counts",
            "fact_type_counts",
        ],
    )
    write_dict_csv(
        BY_SPLIT_PATH,
        split_rows,
        [
            "split",
            "question_count",
            "span_count",
            "correct_key_fact_count",
            "hallucinated_key_fact_count",
            "unsupported_claim_count",
            "positive_count",
            "positive_rate",
            "label_counts",
            "fact_type_counts",
        ],
    )
    write_dict_csv(
        POLICY_FLAGS_PATH,
        policy_flags,
        ["severity", "issue_type", "question_id", "annotation_id", "detail"],
    )

    report = {
        "annotation_path": str(ANNOTATION_PATH),
        "batch_path": str(BATCH_PATH),
        "preview_path": str(PREVIEW_PATH),
        "status": "pass_with_review_notes" if ready_for_alignment and warnings else "pass" if ready_for_alignment else "fail",
        "ready_for_alignment": ready_for_alignment,
        "requires_human_review_before_final_metrics": True,
        "span_count": len(annotations),
        "annotated_question_count": len(annotation_qids),
        "split_counts": dict(sorted(split_counts.items())),
        "label_counts": dict(sorted(label_counts.items())),
        "fact_type_counts": dict(sorted(fact_type_counts.items())),
        "question_type_counts": dict(sorted(question_type_counts.items())),
        "source_batch_counts": dict(sorted(source_batch_counts.items())),
        "distribution_by_split_label": distribution_by_split_label,
        "distribution_by_split_fact_type": distribution_by_split_fact_type,
        "num_failures": len(failures),
        "num_warnings": len(warnings),
        "num_infos": len(infos),
        "failures": failures,
        "warnings": warnings,
        "infos": infos,
        "by_question_csv": str(BY_QUESTION_PATH),
        "by_split_csv": str(BY_SPLIT_PATH),
        "policy_flags_csv": str(POLICY_FLAGS_PATH),
        "next_allowed_step": "build full100 span-token alignment" if ready_for_alignment else "fix audit failures first",
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
