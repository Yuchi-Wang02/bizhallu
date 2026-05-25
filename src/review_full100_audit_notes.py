from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
ANNOTATION_DIR = PROJECT_ROOT / "data" / "annotations"

ANNOTATION_PATH = ANNOTATION_DIR / "span_annotations_full100_draft.jsonl"
BATCH_PATH = OUTPUT_DIR / "full100_heldout_high_annotation_batch.jsonl"
POLICY_FLAGS_PATH = OUTPUT_DIR / "full100_annotation_consistency_audit_policy_flags.csv"
ALIGNMENT_VALIDATION_PATH = OUTPUT_DIR / "full100_draft_span_token_alignment_validation.json"

REVIEW_CSV_PATH = OUTPUT_DIR / "full100_audit_note_review.csv"
REVIEW_REPORT_PATH = OUTPUT_DIR / "full100_audit_note_review_report.json"
REVIEW_VALIDATION_PATH = OUTPUT_DIR / "full100_audit_note_review_validation.json"


REVIEW_DECISIONS: list[dict[str, Any]] = [
    {
        "question_id": "q_0021",
        "issue_type": "unsupported_claim_review",
        "status": "resolved_keep_label",
        "reviewed_annotation_ids": ["ann_full100_draft_q_0021_005"],
        "decision": "Keep `1.3% increase` as unsupported_claim.",
        "rationale": "The answer makes a previous-month product-change claim, but the prompt evidence only provides April 2011 product rows and no previous-month product revenue.",
        "label_change_required": False,
        "remaining_metric_risk": "low",
    },
    {
        "question_id": "q_0049",
        "issue_type": "unsupported_vs_contradicted_review",
        "status": "resolved_label_changed",
        "reviewed_annotation_ids": ["ann_full100_draft_q_0049_006"],
        "decision": "Change `24.5% difference` from unsupported_claim to hallucinated_key_fact.",
        "rationale": "The prompt evidence gives both country net revenues, so the percentage can be checked. Standard percentage differences from GBP 26,937.26 and GBP 42,476.20 do not equal 24.5%, and the requested answer is the absolute GBP 15,538.94 difference.",
        "label_change_required": True,
        "remaining_metric_risk": "low",
    },
    {
        "question_id": "q_0058",
        "issue_type": "correct_only_question",
        "status": "resolved_keep_correct_only",
        "reviewed_annotation_ids": [
            "ann_full100_draft_q_0058_001",
            "ann_full100_draft_q_0058_002",
            "ann_full100_draft_q_0058_003",
            "ann_full100_draft_q_0058_004",
            "ann_full100_draft_q_0058_005",
            "ann_full100_draft_q_0058_006",
        ],
        "decision": "Keep the question as correct-only.",
        "rationale": "The generated answer gives the two month revenues, absolute change, and percentage within tolerance. It omits the explicit word `increase`, but missing gold facts are not generated spans and should not be labeled as hallucinations.",
        "label_change_required": False,
        "remaining_metric_risk": "low",
    },
    {
        "question_id": "q_0097",
        "issue_type": "correct_only_question",
        "status": "resolved_keep_correct_only",
        "reviewed_annotation_ids": [
            "ann_full100_draft_q_0097_001",
            "ann_full100_draft_q_0097_002",
            "ann_full100_draft_q_0097_003",
        ],
        "decision": "Keep the question as correct-only.",
        "rationale": "The generated answer states the correct month, reduction amount, and net revenue. It omits gross positive revenue and reduction rate, but omissions are not generated spans. The statement that the reduction is positive while cancellation revenue is negative is consistent with using an absolute reduction amount.",
        "label_change_required": False,
        "remaining_metric_risk": "low",
    },
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "question_id",
        "issue_type",
        "status",
        "reviewed_annotation_ids",
        "decision",
        "rationale",
        "label_change_required",
        "remaining_metric_risk",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    field: json.dumps(row[field], ensure_ascii=True) if isinstance(row.get(field), list) else row.get(field, "")
                    for field in fieldnames
                }
            )


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None, **context: Any) -> None:
    failure = {"reason": reason, **{key: value for key, value in context.items() if value not in (None, "")}}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def main() -> None:
    failures: list[dict[str, Any]] = []
    for name, path in {
        "annotation": ANNOTATION_PATH,
        "heldout_batch": BATCH_PATH,
        "policy_flags": POLICY_FLAGS_PATH,
        "alignment_validation": ALIGNMENT_VALIDATION_PATH,
    }.items():
        if not path.exists():
            add_failure(failures, "missing required file", {"name": name, "path": str(path)})

    if failures:
        validation = {"num_failures": len(failures), "failures": failures, "review_notes_resolved": False}
        REVIEW_VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    annotations = load_jsonl(ANNOTATION_PATH)
    batch_records = load_jsonl(BATCH_PATH)
    policy_flags = load_csv(POLICY_FLAGS_PATH)
    alignment_validation = load_json(ALIGNMENT_VALIDATION_PATH)

    annotations_by_id = {str(record["annotation_id"]): record for record in annotations}
    annotations_by_qid: dict[str, list[dict[str, Any]]] = {}
    for record in annotations:
        annotations_by_qid.setdefault(str(record["question_id"]), []).append(record)

    batch_by_qid = {str(record["question_id"]): record for record in batch_records}
    reviewed_qids = {decision["question_id"] for decision in REVIEW_DECISIONS}
    if reviewed_qids != {"q_0021", "q_0049", "q_0058", "q_0097"}:
        add_failure(failures, "unexpected reviewed question set", sorted(reviewed_qids))

    for decision in REVIEW_DECISIONS:
        qid = decision["question_id"]
        if qid not in batch_by_qid:
            add_failure(failures, "reviewed question is not in heldout batch", question_id=qid)
        for annotation_id in decision["reviewed_annotation_ids"]:
            if annotation_id not in annotations_by_id:
                add_failure(failures, "reviewed annotation id missing from draft", annotation_id=annotation_id, question_id=qid)

    q0021_record = annotations_by_id.get("ann_full100_draft_q_0021_005", {})
    if q0021_record.get("label") != "unsupported_claim":
        add_failure(failures, "q_0021 unsupported claim label changed unexpectedly", q0021_record, question_id="q_0021")

    q0049_record = annotations_by_id.get("ann_full100_draft_q_0049_006", {})
    if q0049_record.get("label") != "hallucinated_key_fact":
        add_failure(failures, "q_0049 percentage label was not changed to hallucinated_key_fact", q0049_record, question_id="q_0049")
    if q0049_record.get("gold_reference", {}).get("field") != "derived_percentage_difference":
        add_failure(failures, "q_0049 gold_reference does not document derived percentage review", q0049_record, question_id="q_0049")

    for qid in ("q_0058", "q_0097"):
        label_counts = Counter(str(record["label"]) for record in annotations_by_qid.get(qid, []))
        if any(label in label_counts for label in ("hallucinated_key_fact", "unsupported_claim")):
            add_failure(failures, "correct-only reviewed question still has positive labels", dict(label_counts), question_id=qid)

    warning_qids = sorted(
        {
            row["question_id"]
            for row in policy_flags
            if row.get("severity") == "warning" and row.get("question_id")
        }
    )
    if warning_qids != ["q_0021", "q_0058", "q_0097"]:
        add_failure(
            failures,
            "unexpected remaining consistency-audit warning qids",
            {"expected": ["q_0021", "q_0058", "q_0097"], "actual": warning_qids},
        )

    if alignment_validation.get("num_failures") != 0 or alignment_validation.get("ready_for_scoring_prep") is not True:
        add_failure(failures, "alignment validation is not ready after audit-note review", alignment_validation)
    expected_label_counts = {"correct_key_fact": 83, "hallucinated_key_fact": 121, "unsupported_claim": 1}
    if alignment_validation.get("label_counts") != expected_label_counts:
        add_failure(
            failures,
            "alignment label counts do not reflect audit-note review",
            {"expected": expected_label_counts, "actual": alignment_validation.get("label_counts")},
        )

    write_csv(REVIEW_CSV_PATH, REVIEW_DECISIONS)
    label_change_count = sum(1 for decision in REVIEW_DECISIONS if decision["label_change_required"])
    report = {
        "review_csv_path": str(REVIEW_CSV_PATH),
        "reviewed_question_count": len(REVIEW_DECISIONS),
        "reviewed_question_ids": sorted(reviewed_qids),
        "label_change_count": label_change_count,
        "label_changes": [
            decision for decision in REVIEW_DECISIONS if decision["label_change_required"]
        ],
        "remaining_warning_qids_after_review": warning_qids,
        "review_notes_resolved": len(failures) == 0,
        "human_confirmation_recommended_before_public_metrics": True,
        "metrics_reported": False,
        "num_failures": len(failures),
        "failures": failures,
    }
    validation = {
        "report_path": str(REVIEW_REPORT_PATH),
        "num_failures": len(failures),
        "failures": failures,
        "review_notes_resolved": len(failures) == 0,
        "metrics_reported": False,
    }
    REVIEW_REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    REVIEW_VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
