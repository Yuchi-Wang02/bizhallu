from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from build_pilot_review import build_review_row, load_jsonl
except ModuleNotFoundError as exc:
    if exc.name != "build_pilot_review":
        raise
    from src.build_pilot_review import build_review_row, load_jsonl


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "full100_questions.json"
QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
PROMPTS_PATH = PROJECT_ROOT / "outputs" / "qwen_input_prompts.jsonl"
GENERATIONS_PATH = PROJECT_ROOT / "outputs" / "qwen_full100_generations.jsonl"
REVIEW_CSV_PATH = PROJECT_ROOT / "outputs" / "full100_review.csv"
REVIEW_JSONL_PATH = PROJECT_ROOT / "outputs" / "full100_review.jsonl"
REVIEW_SAMPLE_PATH = PROJECT_ROOT / "outputs" / "full100_review_sample.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "full100_review_report.json"


def dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def annotation_priority(review_row: dict[str, Any]) -> str:
    split = review_row["split"]
    status = review_row["auto_status"]
    errors = set(json.loads(review_row["preliminary_error_types"]))
    token_count = int(review_row["generated_token_count"])
    if split in {"dev", "test"} and status != "likely_correct":
        return "high"
    if "malformed_number_format" in errors or token_count >= 160:
        return "high"
    if split in {"dev", "test"}:
        return "medium"
    if status != "likely_correct":
        return "medium"
    return "low"


def suggested_annotation_focus(review_row: dict[str, Any]) -> str:
    missing = json.loads(review_row["missing_or_mismatched_gold_fact_fields"])
    errors = json.loads(review_row["preliminary_error_types"])
    if not missing and not errors:
        return "confirm correct key facts and unsupported extra claims"
    parts = []
    if missing:
        parts.append("check fields: " + ", ".join(missing[:6]))
    if errors:
        parts.append("error types: " + ", ".join(errors[:6]))
    if int(review_row["generated_token_count"]) >= 160:
        parts.append("answer hit max_new_tokens; inspect truncation")
    return " | ".join(parts)


def compact_csv_row(
    base_row: dict[str, Any],
    question: dict[str, Any],
    prompt: dict[str, Any],
    generation: dict[str, Any],
) -> dict[str, Any]:
    priority = annotation_priority(base_row)
    focus = suggested_annotation_focus(base_row)
    return {
        **base_row,
        "prompt_id": prompt["prompt_id"],
        "seed": generation["seed"],
        "row_order_policy": prompt["row_order_policy"],
        "evidence_source": question["evidence"]["source_file"],
        "evidence_filters_json": dump_json(question["evidence"]["filters"]),
        "evidence_metadata_json": dump_json(question["evidence"].get("metadata", {})),
        "evidence_table_markdown": prompt["evidence_table_markdown"],
        "prompt_evidence_rows_json": dump_json(prompt["prompt_evidence_rows"]),
        "gold_answer_json": dump_json(question["gold_answer"]),
        "gold_facts_json": dump_json(question["gold_facts"]),
        "annotation_priority": priority,
        "suggested_annotation_focus": focus,
        "annotation_batch": "heldout_annotation" if base_row["split"] in {"dev", "test"} else "train_annotation",
    }


def jsonl_row(
    csv_row: dict[str, Any],
    question: dict[str, Any],
    prompt: dict[str, Any],
    generation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "question_id": csv_row["question_id"],
        "prompt_id": csv_row["prompt_id"],
        "split": csv_row["split"],
        "question_type": csv_row["question_type"],
        "difficulty": csv_row["difficulty"],
        "question": csv_row["question"],
        "gold_short_answer": csv_row["gold_short_answer"],
        "gold_answer": question["gold_answer"],
        "gold_facts": question["gold_facts"],
        "evidence": question["evidence"],
        "prompt_evidence_rows": prompt["prompt_evidence_rows"],
        "evidence_table_markdown": prompt["evidence_table_markdown"],
        "generation": {
            "model_id": generation["model_id"],
            "seed": generation["seed"],
            "generated_text": generation["generated_text"],
            "generated_token_count": generation["generated_token_count"],
            "input_token_count": generation["input_token_count"],
        },
        "auto_review": {
            "auto_status": csv_row["auto_status"],
            "matched_key_fact_count": int(csv_row["matched_key_fact_count"]),
            "total_key_fact_count": int(csv_row["total_key_fact_count"]),
            "matched_gold_fact_fields": json.loads(csv_row["matched_gold_fact_fields"]),
            "missing_or_mismatched_gold_fact_fields": json.loads(csv_row["missing_or_mismatched_gold_fact_fields"]),
            "preliminary_error_types": json.loads(csv_row["preliminary_error_types"]),
            "annotation_priority": csv_row["annotation_priority"],
            "suggested_annotation_focus": csv_row["suggested_annotation_focus"],
            "annotation_batch": csv_row["annotation_batch"],
        },
        "manual_review": {
            "manual_review_status": "",
            "manual_review_notes": "",
        },
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    question_ids = config["question_ids"]
    questions_by_id = {record["question_id"]: record for record in load_jsonl(QUESTIONS_PATH)}
    prompts_by_id = {record["question_id"]: record for record in load_jsonl(PROMPTS_PATH)}
    generations_by_id = {record["question_id"]: record for record in load_jsonl(GENERATIONS_PATH)}

    csv_rows: list[dict[str, Any]] = []
    jsonl_rows: list[dict[str, Any]] = []
    for question_id in question_ids:
        question = questions_by_id[question_id]
        prompt = prompts_by_id[question_id]
        generation = generations_by_id[question_id]
        base_row = build_review_row(question, generation)
        row = compact_csv_row(base_row, question, prompt, generation)
        csv_rows.append(row)
        jsonl_rows.append(jsonl_row(row, question, prompt, generation))

    fieldnames = [
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
    ]
    with REVIEW_CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    with REVIEW_SAMPLE_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows[:20])

    write_jsonl(REVIEW_JSONL_PATH, jsonl_rows)

    report = {
        "review_csv_path": str(REVIEW_CSV_PATH),
        "review_jsonl_path": str(REVIEW_JSONL_PATH),
        "review_sample_path": str(REVIEW_SAMPLE_PATH),
        "record_count": len(csv_rows),
        "split_counts": dict(sorted(Counter(row["split"] for row in csv_rows).items())),
        "question_type_counts": dict(sorted(Counter(row["question_type"] for row in csv_rows).items())),
        "auto_status_counts": dict(sorted(Counter(row["auto_status"] for row in csv_rows).items())),
        "annotation_priority_counts": dict(sorted(Counter(row["annotation_priority"] for row in csv_rows).items())),
        "preliminary_error_type_counts": dict(
            sorted(
                Counter(
                    error_type
                    for row in csv_rows
                    for error_type in json.loads(row["preliminary_error_types"])
                ).items()
            )
        ),
        "heldout_review_rows": sum(1 for row in csv_rows if row["split"] in {"dev", "test"}),
        "note": (
            "Auto-status is a triage aid only. Manual span annotation remains the source of truth "
            "for detector evaluation."
        ),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
