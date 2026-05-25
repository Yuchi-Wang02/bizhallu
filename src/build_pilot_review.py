from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "pilot20_questions.json"
QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
GENERATIONS_PATH = PROJECT_ROOT / "outputs" / "qwen_pilot20_generations.jsonl"
REVIEW_PATH = PROJECT_ROOT / "outputs" / "pilot20_review.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "pilot20_review_report.json"

MONTH_LABELS = {
    "2010-12": "December 2010",
    "2011-01": "January 2011",
    "2011-02": "February 2011",
    "2011-03": "March 2011",
    "2011-04": "April 2011",
    "2011-05": "May 2011",
    "2011-06": "June 2011",
    "2011-07": "July 2011",
    "2011-08": "August 2011",
    "2011-09": "September 2011",
    "2011-10": "October 2011",
    "2011-11": "November 2011",
    "2011-12": "December 2011",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold()).strip()


def extract_numbers(text: str) -> list[float]:
    values: list[float] = []
    for match in re.finditer(r"[-+]?\d[\d,]*(?:\.\d+)?", text):
        raw = match.group(0).replace(",", "")
        try:
            values.append(float(raw))
        except ValueError:
            continue
    return values


def numeric_match(gold_value: float, generated_numbers: list[float], tolerance: Any) -> bool:
    if isinstance(tolerance, dict) and "percentage_points" in tolerance:
        limit = float(tolerance["percentage_points"])
    elif isinstance(tolerance, dict):
        absolute = float(tolerance.get("absolute", 1.0))
        relative = abs(float(gold_value)) * float(tolerance.get("relative_percent", 0.5)) / 100
        limit = max(absolute, relative)
    else:
        limit = 1.0

    gold_abs = abs(float(gold_value))
    return any(abs(abs(number) - gold_abs) <= limit for number in generated_numbers)


def text_match(fact: dict[str, Any], generated_norm: str, generated_text: str, gold_answer: dict[str, Any]) -> bool:
    value = str(fact["value"])
    fact_type = fact["fact_type"]
    if fact_type == "month":
        candidates = {value}
        if value in MONTH_LABELS:
            candidates.add(MONTH_LABELS[value])
        if value == "2011-12" and "through December 9" in generated_text:
            candidates.add("December 2011 through December 9")
        return any(normalize_text(candidate) in generated_norm for candidate in candidates)
    return normalize_text(value) in generated_norm


def ranking_match(fact: dict[str, Any], generated_norm: str) -> bool:
    positions: list[int] = []
    for item in fact.get("value", []):
        stock_code = normalize_text(str(item["stock_code"]))
        description = normalize_text(str(item["description"]))
        stock_pos = generated_norm.find(stock_code)
        desc_pos = generated_norm.find(description)
        candidates = [pos for pos in [stock_pos, desc_pos] if pos >= 0]
        if not candidates:
            return False
        positions.append(min(candidates))
    return positions == sorted(positions)


def fact_matches(fact: dict[str, Any], generated_text: str, generated_numbers: list[float], gold_answer: dict[str, Any]) -> bool:
    generated_norm = normalize_text(generated_text)
    fact_type = fact["fact_type"]
    if fact_type in {"currency_amount", "percentage"}:
        return numeric_match(float(fact["value"]), generated_numbers, fact.get("tolerance"))
    if fact_type == "ranking":
        return ranking_match(fact, generated_norm)
    if fact_type in {"country", "product_stock_code", "product_name", "month", "comparison_direction"}:
        return text_match(fact, generated_norm, generated_text, gold_answer)
    return False


def error_type_for_fact(fact: dict[str, Any]) -> str:
    fact_type = fact["fact_type"]
    if fact_type in {"country", "product_stock_code", "product_name"}:
        return "entity_or_product_mismatch"
    if fact_type in {"currency_amount", "percentage"}:
        return "numeric_mismatch"
    if fact_type == "ranking":
        return "ranking_mismatch"
    if fact_type == "comparison_direction":
        return "direction_mismatch"
    if fact_type == "month":
        return "time_period_mismatch"
    return "other_fact_mismatch"


def malformed_number_detected(text: str) -> bool:
    # Flags comma groupings such as 145,6145.80.
    return bool(re.search(r"\b\d{1,3},\d{4,}(?:\.\d+)?\b", text))


def country_comparison_direction_match(question: dict[str, Any], generated_text: str) -> bool:
    gold_answer = question["gold_answer"]
    higher = normalize_text(str(gold_answer.get("higher_country", "")))
    lower = normalize_text(str(gold_answer.get("lower_country", "")))
    generated_norm = normalize_text(generated_text)

    correct_patterns = [
        f"{higher} generated more",
        f"{higher} had more",
        f"{higher} generated higher",
        f"{higher} more net revenue",
    ]
    wrong_patterns = [
        f"{lower} generated more",
        f"{lower} had more",
        f"{lower} generated higher",
        f"{lower} more net revenue",
    ]
    if any(pattern in generated_norm for pattern in wrong_patterns):
        return False
    if any(pattern in generated_norm for pattern in correct_patterns):
        return True
    return False


def build_review_row(question: dict[str, Any], generation: dict[str, Any]) -> dict[str, Any]:
    generated_text = generation["generated_text"]
    generated_numbers = extract_numbers(generated_text)

    matched_fields: list[str] = []
    missing_fields: list[str] = []
    error_types: set[str] = set()

    for fact in question["gold_facts"]:
        if fact_matches(fact, generated_text, generated_numbers, question["gold_answer"]):
            matched_fields.append(fact["display_name"])
        else:
            missing_fields.append(fact["display_name"])
            error_types.add(error_type_for_fact(fact))

    if question["question_type"] == "country_comparison_month":
        if country_comparison_direction_match(question, generated_text):
            matched_fields.append("comparison direction")
        else:
            missing_fields.append("comparison direction")
            error_types.add("direction_mismatch")

    if malformed_number_detected(generated_text):
        error_types.add("malformed_number_format")

    total = len(matched_fields) + len(missing_fields)
    matched = len(matched_fields)
    if matched == total and "malformed_number_format" not in error_types:
        auto_status = "likely_correct"
    elif matched == 0:
        auto_status = "likely_wrong"
    else:
        auto_status = "partially_correct"

    return {
        "question_id": question["question_id"],
        "split": question["split"],
        "question_type": question["question_type"],
        "difficulty": question["difficulty"],
        "question": question["question"],
        "gold_short_answer": question["gold_short_answer"],
        "generated_text": generated_text,
        "auto_status": auto_status,
        "matched_key_fact_count": matched,
        "total_key_fact_count": total,
        "matched_gold_fact_fields": json.dumps(matched_fields, ensure_ascii=False),
        "missing_or_mismatched_gold_fact_fields": json.dumps(missing_fields, ensure_ascii=False),
        "preliminary_error_types": json.dumps(sorted(error_types), ensure_ascii=False),
        "generated_token_count": generation["generated_token_count"],
        "input_token_count": generation["input_token_count"],
        "model_id": generation["model_id"],
        "manual_review_status": "",
        "manual_review_notes": "",
    }


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    question_ids = config["question_ids"]

    questions_by_id = {record["question_id"]: record for record in load_jsonl(QUESTIONS_PATH)}
    generations_by_id = {record["question_id"]: record for record in load_jsonl(GENERATIONS_PATH)}

    rows = [build_review_row(questions_by_id[qid], generations_by_id[qid]) for qid in question_ids]

    fieldnames = [
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
    ]
    with REVIEW_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "review_path": str(REVIEW_PATH),
        "record_count": len(rows),
        "auto_status_counts": dict(Counter(row["auto_status"] for row in rows)),
        "question_type_counts": dict(Counter(row["question_type"] for row in rows)),
        "preliminary_error_type_counts": dict(
            Counter(
                error_type
                for row in rows
                for error_type in json.loads(row["preliminary_error_types"])
            )
        ),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
