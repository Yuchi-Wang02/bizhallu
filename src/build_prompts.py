from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
PROMPTS_JSONL = OUTPUT_DIR / "qwen_input_prompts.jsonl"
PROMPTS_SAMPLE_CSV = OUTPUT_DIR / "qwen_input_prompts_sample.csv"
PROMPTS_REPORT = OUTPUT_DIR / "qwen_input_prompts_report.json"


DISPLAY_COLUMNS = {
    "country": "country",
    "year_month": "year_month",
    "stock_code": "stock_code",
    "description": "product_name",
    "net_revenue": "net_revenue_gbp",
    "gross_positive_revenue": "gross_positive_revenue_gbp",
    "cancellation_revenue": "cancellation_return_revenue_gbp",
    "invoice_count": "invoice_count",
}


def load_questions() -> list[dict[str, Any]]:
    with QUESTIONS_PATH.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ordered_rows(record: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    rows = list(record["evidence"]["rows"])
    question_type = record["question_type"]

    if question_type in {"top_product_month", "top3_products_month", "product_revenue_share_month"}:
        question_id = record["question_id"]
        ordered = sorted(
            rows,
            key=lambda row: stable_hash(f"{question_id}|{row.get('stock_code')}|{row.get('description')}"),
        )
        return ordered, "deterministic_hash_by_question_and_product"

    if question_type in {"top_country_month", "country_comparison_month"}:
        ordered = sorted(rows, key=lambda row: str(row.get("country", "")).lower())
        return ordered, "alphabetical_by_country"

    if question_type == "monthly_revenue_change":
        ordered = sorted(rows, key=lambda row: str(row.get("year_month", "")))
        return ordered, "chronological_by_year_month"

    if question_type == "return_impact_month":
        return rows, "single_month_row"

    return rows, "source_order"


def format_value(value: Any, column: str) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if column in {"net_revenue", "gross_positive_revenue", "cancellation_revenue"}:
            return f"{value:.2f}"
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def markdown_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""

    columns: list[str] = []
    for row in rows:
        for column in row:
            if column not in columns:
                columns.append(column)

    display_columns = [DISPLAY_COLUMNS.get(column, column) for column in columns]
    lines = [
        "| " + " | ".join(display_columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for row in rows:
        values = [format_value(row.get(column), column) for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def metric_definitions(record: dict[str, Any]) -> list[str]:
    definitions = [
        "net_revenue = gross_positive_revenue + cancellation_return_revenue.",
        "cancellation_return_revenue is negative when cancellations or returns reduce revenue.",
        "All currency amounts are in GBP.",
    ]
    if "product" in record["question_type"]:
        definitions.append(
            "merchandise net revenue excludes non-product charges such as postage, discounts, bank charges, and manual adjustments."
        )
    if record["question_type"] == "product_revenue_share_month":
        total = record["evidence"].get("metadata", {}).get("total_merchandise_net_revenue")
        if total is not None:
            definitions.append(
                f"Total merchandise net revenue for the month is GBP {float(total):,.2f}; use this as the denominator for share calculations."
            )
    return definitions


def scope_notes(record: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    filters = record["evidence"]["filters"]
    if filters.get("exclude_countries"):
        excluded = ", ".join(filters["exclude_countries"])
        notes.append(f"Exclude these countries when selecting the answer: {excluded}.")
    if filters.get("year_month") == "2011-12" or record["gold_answer"].get("year_month") == "2011-12":
        notes.append("December 2011 evidence is partial and covers data through December 9 only.")
    if record["question_type"] == "return_impact_month":
        notes.append("Report the reduction as a positive amount even though cancellation_return_revenue is negative.")
    if record["question_type"] == "monthly_revenue_change":
        notes.append("For percentage change, divide the absolute change by the previous month's net revenue.")
    return notes


def system_prompt() -> str:
    return (
        "You are a cautious business analyst. Use only the evidence provided in the user message. "
        "Do not use outside knowledge. Do not invent causes, marketing explanations, inventory recommendations, "
        "or strategic advice unless directly supported by the evidence. If a conclusion is not supported, do not state it. "
        "Answer concisely and include the key calculation or comparison when useful."
    )


def user_prompt(record: dict[str, Any], evidence_table: str) -> str:
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
        "Response requirements:\n"
        "- Answer in 2 to 4 sentences.\n"
        "- Use GBP for currency amounts.\n"
        "- Include the relevant country, product, month, ranking, or percentage requested.\n"
        "- Do not add unsupported causes or recommendations.\n"
    )


def build_prompt_record(record: dict[str, Any]) -> dict[str, Any]:
    rows, row_order_policy = ordered_rows(record)
    table = markdown_table(rows)
    sys_prompt = system_prompt()
    usr_prompt = user_prompt(record, table)
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": usr_prompt},
    ]
    full_prompt = f"System:\n{sys_prompt}\n\nUser:\n{usr_prompt}"

    return {
        "prompt_id": f"p_{record['question_id'][2:]}",
        "question_id": record["question_id"],
        "question_type": record["question_type"],
        "difficulty": record["difficulty"],
        "split": record["split"],
        "template_version": "bizhallu_prompt_v0.1",
        "row_order_policy": row_order_policy,
        "messages": messages,
        "full_prompt": full_prompt,
        "evidence_table_markdown": table,
        "prompt_evidence_rows": rows,
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


def flatten_for_sample(records: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "prompt_id": record["prompt_id"],
                "question_id": record["question_id"],
                "split": record["split"],
                "question_type": record["question_type"],
                "difficulty": record["difficulty"],
                "row_order_policy": record["row_order_policy"],
                "question": record["source_question_record"]["question"],
                "prompt_preview": record["full_prompt"][:600].replace("\n", " "),
            }
            for record in records
        ]
    )


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    questions = load_questions()
    prompts = [build_prompt_record(record) for record in questions]
    write_jsonl(PROMPTS_JSONL, prompts)
    flatten_for_sample(prompts).to_csv(PROMPTS_SAMPLE_CSV, index=False)

    sample = flatten_for_sample(prompts)
    report = {
        "prompt_count": len(prompts),
        "template_version": "bizhallu_prompt_v0.1",
        "question_type_counts": sample["question_type"].value_counts().sort_index().to_dict(),
        "difficulty_counts": sample["difficulty"].value_counts().sort_index().to_dict(),
        "split_counts": sample["split"].value_counts().sort_index().to_dict(),
        "row_order_policy_counts": sample["row_order_policy"].value_counts().sort_index().to_dict(),
        "outputs": {
            "jsonl": str(PROMPTS_JSONL),
            "sample_csv": str(PROMPTS_SAMPLE_CSV),
        },
    }
    PROMPTS_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
