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
VALIDATION_PATH = PROJECT_ROOT / "outputs" / "full100_annotation_queue_validation.json"

EXPECTED_PHASE_COUNTS = {
    "phase_1_heldout_high": 35,
    "phase_2_heldout_remaining": 1,
    "phase_3_train_high": 4,
    "phase_4_train_remaining": 60,
}
EXPECTED_INITIAL_BATCH_SPLIT_COUNTS = {"dev": 17, "test": 18}
EXPECTED_TARGET_ANNOTATION_FILE = "data/annotations/span_annotations_full100.jsonl"
EXPECTED_SOURCE_GENERATION_FILE = "outputs/qwen_full100_generations.jsonl"
EXPECTED_ANNOTATION_VERSION = "0.1-full100"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None) -> None:
    failure: dict[str, Any] = {"reason": reason}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path in [REVIEW_CSV_PATH, QUEUE_CSV_PATH, QUEUE_JSONL_PATH, BATCH_CSV_PATH, BATCH_JSONL_PATH, REPORT_PATH]:
        if not path.exists():
            add_failure(failures, "missing annotation queue artifact", str(path))

    review_rows = read_csv(REVIEW_CSV_PATH) if REVIEW_CSV_PATH.exists() else []
    queue_rows = read_csv(QUEUE_CSV_PATH) if QUEUE_CSV_PATH.exists() else []
    batch_rows = read_csv(BATCH_CSV_PATH) if BATCH_CSV_PATH.exists() else []
    queue_jsonl = load_jsonl(QUEUE_JSONL_PATH) if QUEUE_JSONL_PATH.exists() else []
    batch_jsonl = load_jsonl(BATCH_JSONL_PATH) if BATCH_JSONL_PATH.exists() else []
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8")) if REPORT_PATH.exists() else {}

    if len(queue_rows) != 100:
        add_failure(failures, "queue row count mismatch", len(queue_rows))
    if len(queue_jsonl) != len(queue_rows):
        add_failure(failures, "queue JSONL row count mismatch", {"csv": len(queue_rows), "jsonl": len(queue_jsonl)})
    if len(batch_rows) != EXPECTED_PHASE_COUNTS["phase_1_heldout_high"]:
        add_failure(failures, "initial batch row count mismatch", len(batch_rows))
    if len(batch_jsonl) != len(batch_rows):
        add_failure(failures, "batch JSONL row count mismatch", {"csv": len(batch_rows), "jsonl": len(batch_jsonl)})

    review_by_id = {row["question_id"]: row for row in review_rows}
    ranks = [int(row["queue_rank"]) for row in queue_rows if row.get("queue_rank")]
    if ranks != list(range(1, len(queue_rows) + 1)):
        add_failure(failures, "queue ranks are not contiguous", ranks[:10])
    phase_counts = dict(Counter(row.get("queue_phase", "") for row in queue_rows))
    if phase_counts != EXPECTED_PHASE_COUNTS:
        add_failure(failures, "phase counts mismatch", phase_counts)
    initial_batch_split_counts = dict(Counter(row.get("split", "") for row in batch_rows))
    if initial_batch_split_counts != EXPECTED_INITIAL_BATCH_SPLIT_COUNTS:
        add_failure(failures, "initial batch split counts mismatch", initial_batch_split_counts)

    phase_order = [row.get("queue_phase", "") for row in queue_rows]
    expected_sorted = sorted(phase_order, key=lambda phase: list(EXPECTED_PHASE_COUNTS).index(phase))
    if phase_order != expected_sorted:
        add_failure(failures, "queue phases are not grouped in expected order")

    for row in queue_rows:
        qid = row.get("question_id", "")
        review = review_by_id.get(qid)
        if review is None:
            add_failure(failures, "queue question missing from full100 review", qid)
            continue
        for field in ["split", "question_type", "difficulty", "annotation_priority", "auto_status", "generated_text"]:
            if row.get(field) != review.get(field):
                add_failure(failures, f"{field} mismatch with review", qid)
        if row.get("target_annotation_file") != EXPECTED_TARGET_ANNOTATION_FILE:
            add_failure(failures, "target annotation file mismatch", {"question_id": qid, "value": row.get("target_annotation_file")})
        if row.get("source_generation_file") != EXPECTED_SOURCE_GENERATION_FILE:
            add_failure(failures, "source generation file mismatch", {"question_id": qid, "value": row.get("source_generation_file")})
        if row.get("annotation_version") != EXPECTED_ANNOTATION_VERSION:
            add_failure(failures, "annotation version mismatch", {"question_id": qid, "value": row.get("annotation_version")})
        try:
            template = json.loads(row.get("annotation_record_template_json", ""))
        except json.JSONDecodeError as exc:
            add_failure(failures, "invalid annotation_record_template_json", {"question_id": qid, "error": str(exc)})
            continue
        required_template_fields = {
            "annotation_id",
            "question_id",
            "prompt_id",
            "source_generation_file",
            "annotation_version",
            "span_text",
            "span_start_char",
            "span_end_char",
            "fact_type",
            "label",
            "gold_reference",
            "reason",
            "confidence",
            "notes",
        }
        missing = sorted(required_template_fields - set(template))
        if missing:
            add_failure(failures, "annotation template missing fields", {"question_id": qid, "missing": missing})
        if template.get("question_id") != qid or template.get("prompt_id") != row.get("prompt_id"):
            add_failure(failures, "annotation template id mismatch", qid)

    for row in batch_rows:
        if row.get("queue_phase") != "phase_1_heldout_high":
            add_failure(failures, "batch contains non phase_1 row", row.get("question_id"))
        if row.get("split") not in {"dev", "test"} or row.get("annotation_priority") != "high":
            add_failure(failures, "batch contains non-heldout-high row", row.get("question_id"))
        if row.get("is_initial_batch") != "true":
            add_failure(failures, "batch row is_initial_batch flag mismatch", row.get("question_id"))

    if report.get("record_count") != len(queue_rows):
        add_failure(failures, "report record_count mismatch", report.get("record_count"))
    if report.get("initial_batch_count") != len(batch_rows):
        add_failure(failures, "report initial_batch_count mismatch", report.get("initial_batch_count"))
    if report.get("phase_counts") != EXPECTED_PHASE_COUNTS:
        add_failure(failures, "report phase_counts mismatch", report.get("phase_counts"))

    validation = {
        "queue_csv_path": str(QUEUE_CSV_PATH),
        "queue_jsonl_path": str(QUEUE_JSONL_PATH),
        "initial_batch_csv_path": str(BATCH_CSV_PATH),
        "initial_batch_jsonl_path": str(BATCH_JSONL_PATH),
        "record_count": len(queue_rows),
        "initial_batch_count": len(batch_rows),
        "phase_counts": phase_counts,
        "initial_batch_split_counts": initial_batch_split_counts,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
