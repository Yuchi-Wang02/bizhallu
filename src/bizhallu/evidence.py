"""Evidence as the generator saw it: row order, column names, cell text, definitions, scope notes.

Standard library only. Mirrors src/build_prompts.py, which needs pandas and stays unchanged.
"""
from __future__ import annotations

import hashlib

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
NUMERIC_COLUMNS = ["net_revenue", "gross_positive_revenue", "cancellation_revenue", "invoice_count"]
CURRENCY_COLUMNS = {"net_revenue", "gross_positive_revenue", "cancellation_revenue"}

PRODUCT_TYPES = {"top_product_month", "top3_products_month", "product_revenue_share_month"}
COUNTRY_TYPES = {"top_country_month", "country_comparison_month"}


def stable_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def ordered_rows(record):
    """Same row order the generator saw; mirrors src/build_prompts.ordered_rows."""
    rows = list(record["evidence"]["rows"])
    question_type = record["question_type"]
    if question_type in PRODUCT_TYPES:
        question_id = record["question_id"]
        return sorted(rows, key=lambda row: stable_hash(f"{question_id}|{row.get('stock_code')}|{row.get('description')}"))
    if question_type in COUNTRY_TYPES:
        return sorted(rows, key=lambda row: str(row.get("country", "")).lower())
    if question_type == "monthly_revenue_change":
        return sorted(rows, key=lambda row: str(row.get("year_month", "")))
    if question_type == "return_impact_month":
        return rows
    raise ValueError(f"unknown question type for row ordering: {question_type}")


def format_value(value, column):
    """Cell text exactly as src/build_prompts.format_value renders it in the generator prompt."""
    if value is None:
        return ""
    if isinstance(value, float):
        if column in CURRENCY_COLUMNS:
            return f"{value:.2f}"
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value)


def metric_definitions(record):
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


def scope_notes(record):
    """Scope notes as in the generator prompt; reads only evidence.filters, never the gold answer."""
    notes = []
    filters = record["evidence"]["filters"]
    if filters.get("exclude_countries"):
        notes.append("Exclude these countries when selecting the answer: " + ", ".join(filters["exclude_countries"]) + ".")
    if filters.get("year_month") == "2011-12":
        notes.append("December 2011 evidence is partial and covers data through December 9 only.")
    if record["question_type"] == "return_impact_month":
        notes.append("Report the reduction as a positive amount even though cancellation_return_revenue is negative.")
    if record["question_type"] == "monthly_revenue_change":
        notes.append("For percentage change, divide the absolute change by the previous month's net revenue.")
    return notes or ["No additional scope notes."]


def evidence_rows_for_state(record):
    """Rows in generator order, display column names, every cell a string identical to the prompt cell."""
    rows = []
    for index, row in enumerate(ordered_rows(record), start=1):
        item = {"row_id": f"r{index}"}
        for column, value in row.items():
            item[DISPLAY_COLUMNS.get(column, column)] = format_value(value, column)
        rows.append(item)
    return rows
