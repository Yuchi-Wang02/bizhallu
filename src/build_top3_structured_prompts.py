from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from build_prompts import (
    QUESTIONS_PATH,
    markdown_table,
    metric_definitions,
    ordered_rows,
    scope_notes,
    system_prompt,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"

VARIANT_ID = "top3_structured_v0.1"
PROMPTS_JSONL = OUTPUT_DIR / "qwen_top3_structured_prompts.jsonl"
PROMPTS_SAMPLE_CSV = OUTPUT_DIR / "qwen_top3_structured_prompts_sample.csv"
PROMPTS_REPORT = OUTPUT_DIR / "qwen_top3_structured_prompts_report.json"


def load_questions() -> list[dict[str, Any]]:
    return [json.loads(line) for line in QUESTIONS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def format_currency(value: Any) -> str:
    return f"GBP {float(value):,.2f}"


def structured_user_prompt(record: dict[str, Any], evidence_table: str) -> str:
    definitions = "\n".join(f"- {item}" for item in metric_definitions(record))
    notes = scope_notes(record)
    notes_block = "\n".join(f"- {item}" for item in notes) if notes else "- No additional scope notes."

    return (
        "Business question:\n"
        f"{record['question']}\n\n"
        "Metric definitions:\n"
        f"{definitions}\n\n"
        "Scope notes:\n"
        f"{notes_block}\n\n"
        "Evidence table:\n"
        f"{evidence_table}\n\n"
        "Structured response requirements:\n"
        "- First determine the top 3 rows by net_revenue_gbp in descending order.\n"
        "- Return exactly one markdown table and no extra prose.\n"
        "- The table must use exactly these columns: rank, stock_code, product_name, net_revenue_gbp.\n"
        "- Each output row must copy stock_code, product_name, and net_revenue_gbp from one evidence row.\n"
        "- Do not use gross_positive_revenue_gbp or cancellation_return_revenue_gbp as the ranked metric.\n"
        "- Do not include any product outside the evidence table.\n\n"
        "Required output table:\n"
        "| rank | stock_code | product_name | net_revenue_gbp |\n"
        "| --- | --- | --- | --- |\n"
        "| 1 | ... | ... | GBP ... |\n"
        "| 2 | ... | ... | GBP ... |\n"
        "| 3 | ... | ... | GBP ... |\n"
    )


def build_prompt_record(record: dict[str, Any]) -> dict[str, Any]:
    rows, row_order_policy = ordered_rows(record)
    table = markdown_table(rows)
    sys_prompt = system_prompt()
    usr_prompt = structured_user_prompt(record, table)
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": usr_prompt},
    ]
    top_products = record["gold_answer"]["top_products"]
    expected_output_rows = [
        {
            "rank": item["rank"],
            "stock_code": item["stock_code"],
            "product_name": item["description"],
            "net_revenue_gbp": format_currency(item["merchandise_net_revenue"]),
        }
        for item in top_products
    ]

    return {
        "prompt_id": f"p_{record['question_id'][2:]}_top3_structured",
        "question_id": record["question_id"],
        "question_type": record["question_type"],
        "difficulty": record["difficulty"],
        "split": record["split"],
        "variant_id": VARIANT_ID,
        "base_template_version": "bizhallu_prompt_v0.1",
        "row_order_policy": row_order_policy,
        "variant_purpose": "Test whether structured output reduces rank-product-amount binding errors for top3 product questions.",
        "messages": messages,
        "full_prompt": f"System:\n{sys_prompt}\n\nUser:\n{usr_prompt}",
        "evidence_table_markdown": table,
        "prompt_evidence_rows": rows,
        "structured_response_contract": {
            "format": "markdown_table",
            "columns": ["rank", "stock_code", "product_name", "net_revenue_gbp"],
            "row_count": 3,
            "rank_metric": "net_revenue_gbp",
            "sort_order": "descending",
        },
        "expected_output_rows_for_validation_only": expected_output_rows,
        "gold_answer": record["gold_answer"],
        "gold_facts": record["gold_facts"],
        "gold_short_answer": record["gold_short_answer"],
        "source_question_record": {
            "question": record["question"],
            "evidence_source": record["evidence"]["source_file"],
            "evidence_filters": record["evidence"]["filters"],
            "evidence_metadata": record["evidence"].get("metadata", {}),
        },
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")


def write_sample(path: Path, records: list[dict[str, Any]]) -> None:
    fieldnames = [
        "prompt_id",
        "question_id",
        "split",
        "difficulty",
        "row_order_policy",
        "question",
        "expected_top3",
        "prompt_preview",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "prompt_id": record["prompt_id"],
                    "question_id": record["question_id"],
                    "split": record["split"],
                    "difficulty": record["difficulty"],
                    "row_order_policy": record["row_order_policy"],
                    "question": record["source_question_record"]["question"],
                    "expected_top3": json.dumps(record["expected_output_rows_for_validation_only"], ensure_ascii=False),
                    "prompt_preview": " ".join(record["full_prompt"][:700].split()),
                }
            )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    questions = [record for record in load_questions() if record["question_type"] == "top3_products_month"]
    prompts = [build_prompt_record(record) for record in questions]
    write_jsonl(PROMPTS_JSONL, prompts)
    write_sample(PROMPTS_SAMPLE_CSV, prompts)

    report = {
        "variant_id": VARIANT_ID,
        "prompt_count": len(prompts),
        "question_ids": [record["question_id"] for record in prompts],
        "split_counts": dict(sorted({split: sum(1 for record in prompts if record["split"] == split) for split in {record["split"] for record in prompts}}.items())),
        "difficulty_counts": dict(
            sorted({difficulty: sum(1 for record in prompts if record["difficulty"] == difficulty) for difficulty in {record["difficulty"] for record in prompts}}.items())
        ),
        "row_order_policy_counts": dict(
            sorted({policy: sum(1 for record in prompts if record["row_order_policy"] == policy) for policy in {record["row_order_policy"] for record in prompts}}.items())
        ),
        "design_note": (
            "This variant changes the answer contract to a fixed 3-row table but keeps the original deterministic "
            "hash row order, so the prompt tests rank binding without sorting the evidence table for the model."
        ),
        "outputs": {
            "jsonl": str(PROMPTS_JSONL),
            "sample_csv": str(PROMPTS_SAMPLE_CSV),
        },
    }
    PROMPTS_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
