from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "full100_questions.json"
QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
PROMPTS_PATH = PROJECT_ROOT / "outputs" / "qwen_input_prompts.jsonl"
GENERATIONS_PATH = PROJECT_ROOT / "outputs" / "qwen_full100_generations.jsonl"
FULL100_VALIDATION_PATH = PROJECT_ROOT / "outputs" / "qwen_full100_validation.json"
REVIEW_CSV_PATH = PROJECT_ROOT / "outputs" / "full100_review.csv"
REVIEW_JSONL_PATH = PROJECT_ROOT / "outputs" / "full100_review.jsonl"
REVIEW_SAMPLE_PATH = PROJECT_ROOT / "outputs" / "full100_review_sample.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "full100_review_report.json"
VALIDATION_PATH = PROJECT_ROOT / "outputs" / "full100_review_validation.json"

ALLOWED_AUTO_STATUSES = {"likely_correct", "partially_correct", "likely_wrong", "needs_manual_review"}
ALLOWED_PRIORITIES = {"high", "medium", "low"}
EXPECTED_SPLIT_COUNTS = {"train": 64, "dev": 18, "test": 18}
REQUIRED_COLUMNS = {
    "question_id",
    "prompt_id",
    "split",
    "question_type",
    "difficulty",
    "question",
    "gold_short_answer",
    "generated_text",
    "auto_status",
    "matched_key_fact_count",
    "total_key_fact_count",
    "matched_gold_fact_fields",
    "missing_or_mismatched_gold_fact_fields",
    "preliminary_error_types",
    "annotation_priority",
    "suggested_annotation_focus",
    "annotation_batch",
    "generated_token_count",
    "input_token_count",
    "model_id",
    "seed",
    "row_order_policy",
    "evidence_source",
    "evidence_filters_json",
    "evidence_metadata_json",
    "evidence_table_markdown",
    "prompt_evidence_rows_json",
    "gold_answer_json",
    "gold_facts_json",
    "manual_review_status",
    "manual_review_notes",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def add_failure(failures: list[dict[str, Any]], question_id: str, reason: str, detail: Any = None) -> None:
    failure: dict[str, Any] = {"question_id": question_id, "reason": reason}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def parse_json_field(row: dict[str, str], field: str, failures: list[dict[str, Any]]) -> Any:
    try:
        return json.loads(row.get(field, ""))
    except json.JSONDecodeError as exc:
        add_failure(failures, row.get("question_id", "UNKNOWN"), f"{field} is not valid JSON", str(exc))
        return None


def main() -> None:
    failures: list[dict[str, Any]] = []
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    expected_ids = config["question_ids"]
    questions_by_id = {record["question_id"]: record for record in load_jsonl(QUESTIONS_PATH)}
    prompts_by_id = {record["question_id"]: record for record in load_jsonl(PROMPTS_PATH)}
    generations_by_id = {record["question_id"]: record for record in load_jsonl(GENERATIONS_PATH)}
    full100_validation = json.loads(FULL100_VALIDATION_PATH.read_text(encoding="utf-8"))

    for path in [REVIEW_CSV_PATH, REVIEW_JSONL_PATH, REVIEW_SAMPLE_PATH, REPORT_PATH]:
        if not path.exists():
            add_failure(failures, "GLOBAL", "missing full100 review artifact", str(path))

    fieldnames: list[str] = []
    rows: list[dict[str, str]] = []
    if REVIEW_CSV_PATH.exists():
        fieldnames, rows = read_csv(REVIEW_CSV_PATH)
        missing_columns = sorted(REQUIRED_COLUMNS - set(fieldnames))
        if missing_columns:
            add_failure(failures, "GLOBAL", "missing review CSV columns", missing_columns)

    jsonl_rows = load_jsonl(REVIEW_JSONL_PATH) if REVIEW_JSONL_PATH.exists() else []
    sample_rows = read_csv(REVIEW_SAMPLE_PATH)[1] if REVIEW_SAMPLE_PATH.exists() else []
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8")) if REPORT_PATH.exists() else {}

    row_ids = [row.get("question_id", "") for row in rows]
    if row_ids != expected_ids:
        add_failure(failures, "GLOBAL", "question_id order mismatch", {"first_ids": row_ids[:5], "last_ids": row_ids[-5:]})
    if len(row_ids) != len(set(row_ids)):
        add_failure(failures, "GLOBAL", "duplicate question_id values")
    if len(rows) != 100:
        add_failure(failures, "GLOBAL", "review row count is not 100", len(rows))
    if len(jsonl_rows) != len(rows):
        add_failure(failures, "GLOBAL", "JSONL row count does not match CSV", {"csv": len(rows), "jsonl": len(jsonl_rows)})
    if len(sample_rows) != min(20, len(rows)):
        add_failure(failures, "GLOBAL", "sample row count mismatch", len(sample_rows))

    split_counts = dict(Counter(row.get("split", "") for row in rows))
    if split_counts != EXPECTED_SPLIT_COUNTS:
        add_failure(failures, "GLOBAL", "split counts mismatch", split_counts)
    if full100_validation.get("num_failures") != 0 or full100_validation.get("record_count") != 100:
        add_failure(failures, "GLOBAL", "full100 generation validation is not clean", full100_validation)
    if report.get("record_count") != len(rows):
        add_failure(failures, "GLOBAL", "review report record_count mismatch", report.get("record_count"))

    for row in rows:
        qid = row.get("question_id", "UNKNOWN")
        question = questions_by_id.get(qid)
        prompt = prompts_by_id.get(qid)
        generation = generations_by_id.get(qid)
        if question is None or prompt is None or generation is None:
            add_failure(failures, qid, "question, prompt, or generation missing")
            continue

        expected_prompt_id = f"p_{qid[2:]}"
        if row.get("prompt_id") != expected_prompt_id:
            add_failure(failures, qid, "prompt_id mismatch", row.get("prompt_id"))
        for field in ["split", "question_type", "difficulty", "question", "gold_short_answer"]:
            if row.get(field) != str(question.get(field, "")):
                add_failure(failures, qid, f"{field} mismatch with gold question")
        if row.get("generated_text") != generation.get("generated_text"):
            add_failure(failures, qid, "generated_text mismatch with generation file")
        if not row.get("generated_text", "").strip():
            add_failure(failures, qid, "generated_text is empty")
        if row.get("auto_status") not in ALLOWED_AUTO_STATUSES:
            add_failure(failures, qid, "invalid auto_status", row.get("auto_status"))
        if row.get("annotation_priority") not in ALLOWED_PRIORITIES:
            add_failure(failures, qid, "invalid annotation_priority", row.get("annotation_priority"))
        expected_batch = "heldout_annotation" if row.get("split") in {"dev", "test"} else "train_annotation"
        if row.get("annotation_batch") != expected_batch:
            add_failure(failures, qid, "annotation_batch mismatch", row.get("annotation_batch"))

        try:
            matched = int(row.get("matched_key_fact_count", ""))
            total = int(row.get("total_key_fact_count", ""))
        except ValueError:
            add_failure(failures, qid, "fact counts are not integers")
            matched = -1
            total = -1
        expected_total = len(question.get("gold_facts", []))
        if question.get("question_type") == "country_comparison_month":
            expected_total += 1
        if total != expected_total:
            add_failure(failures, qid, "total_key_fact_count mismatch", {"actual": total, "expected": expected_total})
        if matched < 0 or matched > total:
            add_failure(failures, qid, "matched_key_fact_count outside valid range")

        matched_fields = parse_json_field(row, "matched_gold_fact_fields", failures)
        missing_fields = parse_json_field(row, "missing_or_mismatched_gold_fact_fields", failures)
        error_types = parse_json_field(row, "preliminary_error_types", failures)
        prompt_evidence_rows = parse_json_field(row, "prompt_evidence_rows_json", failures)
        gold_answer = parse_json_field(row, "gold_answer_json", failures)
        gold_facts = parse_json_field(row, "gold_facts_json", failures)
        evidence_filters = parse_json_field(row, "evidence_filters_json", failures)
        evidence_metadata = parse_json_field(row, "evidence_metadata_json", failures)

        for parsed, field in [
            (matched_fields, "matched_gold_fact_fields"),
            (missing_fields, "missing_or_mismatched_gold_fact_fields"),
            (error_types, "preliminary_error_types"),
            (prompt_evidence_rows, "prompt_evidence_rows_json"),
            (gold_facts, "gold_facts_json"),
        ]:
            if parsed is not None and not isinstance(parsed, list):
                add_failure(failures, qid, f"{field} should be a JSON list")
        if gold_answer != question["gold_answer"]:
            add_failure(failures, qid, "gold_answer_json mismatch")
        if gold_facts != question["gold_facts"]:
            add_failure(failures, qid, "gold_facts_json mismatch")
        if prompt_evidence_rows != prompt["prompt_evidence_rows"]:
            add_failure(failures, qid, "prompt_evidence_rows_json mismatch")
        if row.get("evidence_table_markdown") != prompt["evidence_table_markdown"]:
            add_failure(failures, qid, "evidence_table_markdown mismatch")
        if row.get("row_order_policy") != prompt["row_order_policy"]:
            add_failure(failures, qid, "row_order_policy mismatch")
        if row.get("evidence_source") != question["evidence"]["source_file"]:
            add_failure(failures, qid, "evidence_source mismatch")
        if evidence_filters != question["evidence"]["filters"]:
            add_failure(failures, qid, "evidence_filters_json mismatch")
        if evidence_metadata != question["evidence"].get("metadata", {}):
            add_failure(failures, qid, "evidence_metadata_json mismatch")

    jsonl_by_id = {record.get("question_id"): record for record in jsonl_rows}
    for row in rows:
        qid = row.get("question_id", "UNKNOWN")
        record = jsonl_by_id.get(qid)
        if record is None:
            add_failure(failures, qid, "missing JSONL review row")
            continue
        if record.get("generation", {}).get("generated_text") != row.get("generated_text"):
            add_failure(failures, qid, "JSONL generated_text mismatch")
        if record.get("auto_review", {}).get("annotation_priority") != row.get("annotation_priority"):
            add_failure(failures, qid, "JSONL annotation_priority mismatch")

    validation = {
        "review_csv_path": str(REVIEW_CSV_PATH),
        "review_jsonl_path": str(REVIEW_JSONL_PATH),
        "review_sample_path": str(REVIEW_SAMPLE_PATH),
        "record_count": len(rows),
        "jsonl_record_count": len(jsonl_rows),
        "sample_record_count": len(sample_rows),
        "split_counts": split_counts,
        "auto_status_counts": dict(sorted(Counter(row.get("auto_status", "") for row in rows).items())),
        "annotation_priority_counts": dict(sorted(Counter(row.get("annotation_priority", "") for row in rows).items())),
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
