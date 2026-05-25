from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_CSV_PATH = PROJECT_ROOT / "outputs" / "full100_review.csv"
QUEUE_CSV_PATH = PROJECT_ROOT / "outputs" / "full100_annotation_queue.csv"
QUEUE_JSONL_PATH = PROJECT_ROOT / "outputs" / "full100_annotation_queue.jsonl"
BATCH_CSV_PATH = PROJECT_ROOT / "outputs" / "full100_heldout_high_annotation_batch.csv"
BATCH_JSONL_PATH = PROJECT_ROOT / "outputs" / "full100_heldout_high_annotation_batch.jsonl"
REPORT_PATH = PROJECT_ROOT / "outputs" / "full100_annotation_queue_report.json"

TARGET_ANNOTATION_PATH = "data/annotations/span_annotations_full100.jsonl"
SOURCE_GENERATION_FILE = "outputs/qwen_full100_generations.jsonl"
ANNOTATION_VERSION = "0.1-full100"


PHASE_ORDER = {
    "phase_1_heldout_high": 1,
    "phase_2_heldout_remaining": 2,
    "phase_3_train_high": 3,
    "phase_4_train_remaining": 4,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")


def queue_phase(row: dict[str, str]) -> str:
    is_heldout = row["split"] in {"dev", "test"}
    is_high = row["annotation_priority"] == "high"
    if is_heldout and is_high:
        return "phase_1_heldout_high"
    if is_heldout:
        return "phase_2_heldout_remaining"
    if is_high:
        return "phase_3_train_high"
    return "phase_4_train_remaining"


def annotation_template(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "annotation_id": f"ann_{row['question_id']}_001",
        "question_id": row["question_id"],
        "prompt_id": row["prompt_id"],
        "source_generation_file": SOURCE_GENERATION_FILE,
        "annotation_version": ANNOTATION_VERSION,
        "span_text": "",
        "span_start_char": None,
        "span_end_char": None,
        "fact_type": "",
        "label": "",
        "gold_reference": {},
        "reason": "",
        "confidence": "",
        "notes": "",
    }


def queue_row(review_row: dict[str, str], rank: int) -> dict[str, Any]:
    phase = queue_phase(review_row)
    is_initial_batch = phase == "phase_1_heldout_high"
    row = {
        "queue_rank": rank,
        "queue_phase": phase,
        "is_initial_batch": str(is_initial_batch).lower(),
        "target_annotation_file": TARGET_ANNOTATION_PATH,
        "source_generation_file": SOURCE_GENERATION_FILE,
        "annotation_version": ANNOTATION_VERSION,
        "question_id": review_row["question_id"],
        "prompt_id": review_row["prompt_id"],
        "split": review_row["split"],
        "question_type": review_row["question_type"],
        "difficulty": review_row["difficulty"],
        "annotation_priority": review_row["annotation_priority"],
        "auto_status": review_row["auto_status"],
        "suggested_annotation_focus": review_row["suggested_annotation_focus"],
        "question": review_row["question"],
        "gold_short_answer": review_row["gold_short_answer"],
        "generated_text": review_row["generated_text"],
        "matched_key_fact_count": review_row["matched_key_fact_count"],
        "total_key_fact_count": review_row["total_key_fact_count"],
        "matched_gold_fact_fields": review_row["matched_gold_fact_fields"],
        "missing_or_mismatched_gold_fact_fields": review_row["missing_or_mismatched_gold_fact_fields"],
        "preliminary_error_types": review_row["preliminary_error_types"],
        "evidence_table_markdown": review_row["evidence_table_markdown"],
        "prompt_evidence_rows_json": review_row["prompt_evidence_rows_json"],
        "gold_answer_json": review_row["gold_answer_json"],
        "gold_facts_json": review_row["gold_facts_json"],
        "annotation_record_template_json": "",
        "manual_annotation_started": "",
        "manual_annotation_notes": "",
    }
    row["annotation_record_template_json"] = json.dumps(annotation_template(row), ensure_ascii=False, sort_keys=True)
    return row


def queue_json_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "queue_rank": int(row["queue_rank"]),
        "queue_phase": row["queue_phase"],
        "is_initial_batch": row["is_initial_batch"] == "true",
        "target_annotation_file": row["target_annotation_file"],
        "source_generation_file": row["source_generation_file"],
        "annotation_version": row["annotation_version"],
        "question_id": row["question_id"],
        "prompt_id": row["prompt_id"],
        "split": row["split"],
        "question_type": row["question_type"],
        "difficulty": row["difficulty"],
        "annotation_priority": row["annotation_priority"],
        "auto_status": row["auto_status"],
        "suggested_annotation_focus": row["suggested_annotation_focus"],
        "question": row["question"],
        "gold_short_answer": row["gold_short_answer"],
        "generated_text": row["generated_text"],
        "gold_answer": json.loads(row["gold_answer_json"]),
        "gold_facts": json.loads(row["gold_facts_json"]),
        "prompt_evidence_rows": json.loads(row["prompt_evidence_rows_json"]),
        "evidence_table_markdown": row["evidence_table_markdown"],
        "auto_review": {
            "matched_key_fact_count": int(row["matched_key_fact_count"]),
            "total_key_fact_count": int(row["total_key_fact_count"]),
            "matched_gold_fact_fields": json.loads(row["matched_gold_fact_fields"]),
            "missing_or_mismatched_gold_fact_fields": json.loads(row["missing_or_mismatched_gold_fact_fields"]),
            "preliminary_error_types": json.loads(row["preliminary_error_types"]),
        },
        "annotation_record_template": json.loads(row["annotation_record_template_json"]),
    }


def main() -> None:
    review_rows = read_csv(REVIEW_CSV_PATH)
    sorted_review_rows = sorted(
        review_rows,
        key=lambda row: (
            PHASE_ORDER[queue_phase(row)],
            int(row["question_id"].split("_")[1]),
        ),
    )
    queue_rows = [queue_row(row, rank=index + 1) for index, row in enumerate(sorted_review_rows)]
    batch_rows = [row for row in queue_rows if row["is_initial_batch"] == "true"]

    fieldnames = [
        "queue_rank",
        "queue_phase",
        "is_initial_batch",
        "target_annotation_file",
        "source_generation_file",
        "annotation_version",
        "question_id",
        "prompt_id",
        "split",
        "question_type",
        "difficulty",
        "annotation_priority",
        "auto_status",
        "suggested_annotation_focus",
        "question",
        "gold_short_answer",
        "generated_text",
        "matched_key_fact_count",
        "total_key_fact_count",
        "matched_gold_fact_fields",
        "missing_or_mismatched_gold_fact_fields",
        "preliminary_error_types",
        "evidence_table_markdown",
        "prompt_evidence_rows_json",
        "gold_answer_json",
        "gold_facts_json",
        "annotation_record_template_json",
        "manual_annotation_started",
        "manual_annotation_notes",
    ]
    write_csv(QUEUE_CSV_PATH, queue_rows, fieldnames)
    write_csv(BATCH_CSV_PATH, batch_rows, fieldnames)
    write_jsonl(QUEUE_JSONL_PATH, [queue_json_record(row) for row in queue_rows])
    write_jsonl(BATCH_JSONL_PATH, [queue_json_record(row) for row in batch_rows])

    report = {
        "queue_csv_path": str(QUEUE_CSV_PATH),
        "queue_jsonl_path": str(QUEUE_JSONL_PATH),
        "initial_batch_csv_path": str(BATCH_CSV_PATH),
        "initial_batch_jsonl_path": str(BATCH_JSONL_PATH),
        "target_annotation_file": TARGET_ANNOTATION_PATH,
        "record_count": len(queue_rows),
        "initial_batch_count": len(batch_rows),
        "phase_counts": dict(sorted(Counter(row["queue_phase"] for row in queue_rows).items())),
        "initial_batch_split_counts": dict(sorted(Counter(row["split"] for row in batch_rows).items())),
        "initial_batch_question_type_counts": dict(sorted(Counter(row["question_type"] for row in batch_rows).items())),
        "policy": (
            "Queue order is heldout high-priority rows first, then remaining heldout rows, "
            "then high-priority train rows, then remaining train rows. Queue order is for "
            "annotation logistics only; detector thresholds must still be selected on dev "
            "and reported on held-out test."
        ),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
