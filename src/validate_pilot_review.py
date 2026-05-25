from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "pilot20_questions.json"
QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
GENERATIONS_PATH = PROJECT_ROOT / "outputs" / "qwen_pilot20_generations.jsonl"
REVIEW_PATH = PROJECT_ROOT / "outputs" / "pilot20_review.csv"
VALIDATION_PATH = PROJECT_ROOT / "outputs" / "pilot20_review_validation.json"

ALLOWED_AUTO_STATUSES = {"likely_correct", "partially_correct", "likely_wrong", "needs_manual_review"}
REQUIRED_COLUMNS = {
    "question_id",
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
    "generated_token_count",
    "input_token_count",
    "model_id",
    "manual_review_status",
    "manual_review_notes",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def add_failure(failures: list[dict[str, Any]], question_id: str, reason: str) -> None:
    failures.append({"question_id": question_id, "reason": reason})


def main() -> None:
    failures: list[dict[str, Any]] = []
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    expected_ids = config["question_ids"]
    questions_by_id = {record["question_id"]: record for record in load_jsonl(QUESTIONS_PATH)}
    generations_by_id = {record["question_id"]: record for record in load_jsonl(GENERATIONS_PATH)}

    if not REVIEW_PATH.exists():
        add_failure(failures, "GLOBAL", f"missing review file: {REVIEW_PATH}")
        rows: list[dict[str, str]] = []
    else:
        with REVIEW_PATH.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                add_failure(failures, "GLOBAL", "review CSV has no header")
                rows = []
            else:
                missing_columns = sorted(REQUIRED_COLUMNS - set(reader.fieldnames))
                if missing_columns:
                    add_failure(failures, "GLOBAL", f"missing columns: {missing_columns}")
                rows = list(reader)

    row_ids = [row.get("question_id", "") for row in rows]
    if row_ids != expected_ids:
        add_failure(failures, "GLOBAL", f"question_id order mismatch: {row_ids}")
    if len(row_ids) != len(set(row_ids)):
        add_failure(failures, "GLOBAL", "duplicate question_id values in review")

    for row in rows:
        qid = row.get("question_id", "UNKNOWN")
        question = questions_by_id.get(qid)
        generation = generations_by_id.get(qid)
        if question is None:
            add_failure(failures, qid, "review question_id missing from gold questions")
            continue
        if generation is None:
            add_failure(failures, qid, "review question_id missing from generations")
            continue

        for field in ["split", "question_type", "difficulty", "question", "gold_short_answer"]:
            if row.get(field) != str(question.get(field, "")):
                add_failure(failures, qid, f"{field} mismatch with gold question")

        if row.get("generated_text") != generation.get("generated_text"):
            add_failure(failures, qid, "generated_text mismatch with generation file")
        if not row.get("generated_text", "").strip():
            add_failure(failures, qid, "generated_text is empty")
        if row.get("auto_status") not in ALLOWED_AUTO_STATUSES:
            add_failure(failures, qid, f"invalid auto_status: {row.get('auto_status')}")

        try:
            matched = int(row.get("matched_key_fact_count", ""))
            total = int(row.get("total_key_fact_count", ""))
        except ValueError:
            add_failure(failures, qid, "fact counts are not integers")
            continue
        expected_total = len(question.get("gold_facts", []))
        if question.get("question_type") == "country_comparison_month":
            expected_total += 1
        if total != expected_total:
            add_failure(failures, qid, "total_key_fact_count mismatch with gold_facts")
        if matched < 0 or matched > total:
            add_failure(failures, qid, "matched_key_fact_count outside valid range")

        for json_field in [
            "matched_gold_fact_fields",
            "missing_or_mismatched_gold_fact_fields",
            "preliminary_error_types",
        ]:
            try:
                parsed = json.loads(row.get(json_field, ""))
            except json.JSONDecodeError:
                add_failure(failures, qid, f"{json_field} is not valid JSON")
                continue
            if not isinstance(parsed, list):
                add_failure(failures, qid, f"{json_field} should be a JSON list")

        if "through December 9" in question["question"] and "through December 9" not in row["gold_short_answer"]:
            add_failure(failures, qid, "partial December gold_short_answer missing December 9")

    report = {
        "review_path": str(REVIEW_PATH),
        "record_count": len(rows),
        "num_failures": len(failures),
        "failures": failures,
        "question_ids": row_ids,
        "auto_status_counts": {
            status: sum(1 for row in rows if row.get("auto_status") == status)
            for status in sorted({row.get("auto_status") for row in rows})
        },
    }
    VALIDATION_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
