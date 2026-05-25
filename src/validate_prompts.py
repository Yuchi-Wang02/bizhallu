from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
PROMPTS_PATH = PROJECT_ROOT / "outputs" / "qwen_input_prompts.jsonl"
VALIDATION_REPORT = PROJECT_ROOT / "outputs" / "qwen_input_prompts_validation.json"


EXPECTED_PROMPT_COUNT = 100


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def add_failure(failures: list[dict[str, Any]], prompt_id: str, reason: str) -> None:
    failures.append({"prompt_id": prompt_id, "reason": reason})


def main() -> None:
    questions = load_jsonl(QUESTIONS_PATH)
    prompts = load_jsonl(PROMPTS_PATH)
    questions_by_id = {record["question_id"]: record for record in questions}
    failures: list[dict[str, Any]] = []

    if len(prompts) != EXPECTED_PROMPT_COUNT:
        failures.append(
            {
                "prompt_id": "GLOBAL",
                "reason": f"expected {EXPECTED_PROMPT_COUNT} prompts, found {len(prompts)}",
            }
        )

    prompt_ids = [record.get("prompt_id") for record in prompts]
    if len(prompt_ids) != len(set(prompt_ids)):
        failures.append({"prompt_id": "GLOBAL", "reason": "duplicate prompt_id values"})

    question_ids = [record.get("question_id") for record in prompts]
    if set(question_ids) != set(questions_by_id):
        missing = sorted(set(questions_by_id) - set(question_ids))
        extra = sorted(set(question_ids) - set(questions_by_id))
        failures.append(
            {
                "prompt_id": "GLOBAL",
                "reason": f"question_id mismatch: missing={missing}, extra={extra}",
            }
        )

    required_fields = {
        "prompt_id",
        "question_id",
        "question_type",
        "difficulty",
        "split",
        "template_version",
        "row_order_policy",
        "messages",
        "full_prompt",
        "evidence_table_markdown",
        "prompt_evidence_rows",
        "gold_answer",
        "gold_facts",
        "gold_short_answer",
        "source_question_record",
    }

    for record in prompts:
        prompt_id = record.get("prompt_id", "UNKNOWN")
        missing = sorted(required_fields - set(record))
        if missing:
            add_failure(failures, prompt_id, f"missing required fields: {missing}")
            continue

        question = questions_by_id.get(record["question_id"])
        if question is None:
            add_failure(failures, prompt_id, "unknown question_id")
            continue

        if record["question_type"] != question["question_type"]:
            add_failure(failures, prompt_id, "question_type mismatch with question record")
        if record["difficulty"] != question["difficulty"]:
            add_failure(failures, prompt_id, "difficulty mismatch with question record")
        if record["split"] != question["split"]:
            add_failure(failures, prompt_id, "split mismatch with question record")
        if record["gold_short_answer"] != question["gold_short_answer"]:
            add_failure(failures, prompt_id, "gold_short_answer mismatch with question record")

        full_prompt = record["full_prompt"]
        if question["question"] not in full_prompt:
            add_failure(failures, prompt_id, "question text missing from prompt")
        if question["gold_short_answer"] in full_prompt:
            add_failure(failures, prompt_id, "exact gold short answer appears in prompt")
        if "gold_answer" in full_prompt.lower() or "gold short answer" in full_prompt.lower():
            add_failure(failures, prompt_id, "prompt mentions gold answer")
        if "Evidence table:" not in full_prompt:
            add_failure(failures, prompt_id, "missing evidence table block")
        if not record["prompt_evidence_rows"]:
            add_failure(failures, prompt_id, "empty prompt evidence rows")
        if not record["evidence_table_markdown"].startswith("| "):
            add_failure(failures, prompt_id, "evidence table is not markdown table")

        messages = record["messages"]
        if len(messages) != 2:
            add_failure(failures, prompt_id, "messages should contain system and user messages")
        else:
            if messages[0].get("role") != "system" or messages[1].get("role") != "user":
                add_failure(failures, prompt_id, "messages roles should be system then user")

        if record["question_type"] == "product_revenue_share_month":
            metadata = record["source_question_record"].get("evidence_metadata", {})
            if "total_merchandise_net_revenue" not in metadata:
                add_failure(failures, prompt_id, "share prompt missing denominator metadata")
            if "Total merchandise net revenue for the month is GBP" not in full_prompt:
                add_failure(failures, prompt_id, "share denominator missing from prompt text")

        if record["gold_answer"].get("year_month") == "2011-12" and "December 9" not in full_prompt:
            add_failure(failures, prompt_id, "partial December prompt missing December 9 note")
        if "through December 9" in question["question"] and "through December 9" not in record["gold_short_answer"]:
            add_failure(failures, prompt_id, "partial December prompt missing December 9 in gold_short_answer")

        if record["question_type"] in {
            "top_product_month",
            "top3_products_month",
            "product_revenue_share_month",
        } and record["row_order_policy"] != "deterministic_hash_by_question_and_product":
            add_failure(failures, prompt_id, "product ranking prompt uses wrong row order policy")

        if record["question_type"] in {"top_country_month", "country_comparison_month"}:
            if record["row_order_policy"] != "alphabetical_by_country":
                add_failure(failures, prompt_id, "country prompt uses wrong row order policy")
            countries = [row.get("country") for row in record["prompt_evidence_rows"]]
            if countries != sorted(countries, key=lambda value: str(value).lower()):
                add_failure(failures, prompt_id, "country prompt rows are not alphabetic")

        if record["question_type"] == "monthly_revenue_change":
            months = [row.get("year_month") for row in record["prompt_evidence_rows"]]
            if months != sorted(months):
                add_failure(failures, prompt_id, "monthly change rows are not chronological")

    sample = pd.DataFrame(
        {
            "question_type": [record["question_type"] for record in prompts],
            "difficulty": [record["difficulty"] for record in prompts],
            "split": [record["split"] for record in prompts],
            "row_order_policy": [record["row_order_policy"] for record in prompts],
        }
    )
    report = {
        "prompt_count": len(prompts),
        "num_failures": len(failures),
        "failures": failures,
        "question_type_counts": sample["question_type"].value_counts().sort_index().to_dict(),
        "difficulty_counts": sample["difficulty"].value_counts().sort_index().to_dict(),
        "split_counts": sample["split"].value_counts().sort_index().to_dict(),
        "row_order_policy_counts": sample["row_order_policy"].value_counts().sort_index().to_dict(),
    }
    VALIDATION_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
