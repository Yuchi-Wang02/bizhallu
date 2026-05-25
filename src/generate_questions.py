from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

OUTPUT_JSONL = PROCESSED_DIR / "business_questions_gold.jsonl"
OUTPUT_SAMPLE_CSV = PROCESSED_DIR / "business_questions_gold_sample.csv"
OUTPUT_REPORT = PROCESSED_DIR / "business_questions_gold_report.json"

QUESTION_TYPE_QUOTAS = {
    "top_country_month": 16,
    "top_product_month": 13,
    "country_comparison_month": 20,
    "monthly_revenue_change": 10,
    "top3_products_month": 13,
    "product_revenue_share_month": 16,
    "return_impact_month": 12,
}


def money(value: float) -> float:
    return round(float(value), 2)


def pct(value: float) -> float:
    return round(float(value), 2)


def month_label(year_month: str) -> str:
    return pd.Period(year_month, freq="M").strftime("%B %Y")


def to_records(df: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in df[columns].to_dict(orient="records"):
        clean_row: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, float):
                clean_row[key] = money(value)
            elif pd.isna(value):
                clean_row[key] = None
            else:
                clean_row[key] = value
        out.append(clean_row)
    return out


def base_record(
    question_type: str,
    difficulty: str,
    question: str,
    evidence_source: str,
    evidence_rows: list[dict[str, Any]],
    filters: dict[str, Any],
    gold_answer: dict[str, Any],
    gold_facts: list[dict[str, Any]],
    gold_short_answer: str,
    evidence_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "question_id": "",
        "question_type": question_type,
        "difficulty": difficulty,
        "split": "",
        "question": question,
        "gold_short_answer": gold_short_answer,
        "gold_answer": gold_answer,
        "gold_facts": gold_facts,
        "evidence": {
            "source_file": evidence_source,
            "filters": filters,
            "rows": evidence_rows,
            "metadata": evidence_metadata or {},
        },
        "generation_guidance": {
            "answer_style": "concise business analysis",
            "must_use_only_provided_evidence": True,
            "default_metric": "net_revenue",
        },
    }


def currency_fact(field: str, value: float, display_name: str | None = None) -> dict[str, Any]:
    rounded = money(value)
    return {
        "field": field,
        "fact_type": "currency_amount",
        "value": rounded,
        "display_value": f"GBP {rounded:,.2f}",
        "tolerance": {"absolute": 1.0, "relative_percent": 0.5},
        "display_name": display_name or field,
    }


def percent_fact(field: str, value: float, display_name: str | None = None) -> dict[str, Any]:
    rounded = pct(value)
    return {
        "field": field,
        "fact_type": "percentage",
        "value": rounded,
        "display_value": f"{rounded:.2f}%",
        "tolerance": {"percentage_points": 0.5},
        "display_name": display_name or field,
    }


def text_fact(field: str, fact_type: str, value: str, display_name: str | None = None) -> dict[str, Any]:
    return {
        "field": field,
        "fact_type": fact_type,
        "value": value,
        "display_value": value,
        "tolerance": "exact_normalized_match",
        "display_name": display_name or field,
    }


def rank_fact(field: str, ranking: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "field": field,
        "fact_type": "ranking",
        "value": ranking,
        "display_value": " > ".join(
            f"{item['rank']}. {item.get('stock_code', item.get('country'))}" for item in ranking
        ),
        "tolerance": "ordered_exact_match",
        "display_name": field,
    }


def load_tables() -> dict[str, pd.DataFrame]:
    return {
        "monthly_net": pd.read_csv(PROCESSED_DIR / "monthly_net_revenue_summary.csv"),
        "monthly_coverage": pd.read_csv(PROCESSED_DIR / "monthly_coverage_summary.csv"),
        "country_month_net": pd.read_csv(PROCESSED_DIR / "country_month_net_revenue_summary.csv"),
        "product_month_net": pd.read_csv(PROCESSED_DIR / "product_month_net_revenue_summary.csv"),
    }


def recommended_months(tables: dict[str, pd.DataFrame]) -> list[str]:
    coverage = tables["monthly_coverage"]
    mask = coverage["recommended_for_monthly_trend_questions"].astype(bool)
    return coverage.loc[mask, "year_month"].astype(str).tolist()


def generate_top_country_month(tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    cm = tables["country_month_net"]
    months = recommended_months(tables)
    records: list[dict[str, Any]] = []

    specs: list[tuple[str, bool]] = [(month, True) for month in months]
    specs.extend([(month, False) for month in ["2011-01", "2011-03", "2011-06", "2011-09", "2011-11"]])

    for year_month, exclude_uk in specs:
        sub = cm.loc[cm["year_month"].eq(year_month)].sort_values("net_revenue", ascending=False)
        if exclude_uk:
            gold_pool = sub.loc[~sub["country"].eq("United Kingdom")]
            evidence = pd.concat([sub.head(1), gold_pool.head(7)], ignore_index=True)
            question = (
                f"Which country had the highest net revenue in {month_label(year_month)}, "
                "excluding the United Kingdom?"
            )
            filters = {"year_month": year_month, "exclude_countries": ["United Kingdom"]}
            difficulty = "medium"
            scope = "excluding United Kingdom"
        else:
            gold_pool = sub
            evidence = sub.head(8)
            question = f"Which country had the highest net revenue in {month_label(year_month)}?"
            filters = {"year_month": year_month, "exclude_countries": []}
            difficulty = "easy"
            scope = "all countries"

        top = gold_pool.iloc[0]
        rows = to_records(
            evidence,
            [
                "country",
                "net_revenue",
                "gross_positive_revenue",
                "cancellation_revenue",
                "invoice_count",
            ],
        )
        country = str(top["country"])
        revenue = money(top["net_revenue"])
        records.append(
            base_record(
                "top_country_month",
                difficulty,
                question,
                "country_month_net_revenue_summary.csv",
                rows,
                filters,
                {
                    "year_month": year_month,
                    "month_label": month_label(year_month),
                    "scope": scope,
                    "country": country,
                    "net_revenue": revenue,
                    "currency": "GBP",
                },
                [
                    text_fact("year_month", "month", year_month, "month"),
                    text_fact("country", "country", country),
                    currency_fact("net_revenue", revenue),
                ],
                f"{country} had the highest net revenue in {month_label(year_month)} ({scope}) at GBP {revenue:,.2f}.",
            )
        )
    return records


def generate_top_product_month(tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    pm = tables["product_month_net"]
    months = ["2010-12"] + recommended_months(tables) + ["2011-12"]
    records: list[dict[str, Any]] = []
    for year_month in months:
        sub = pm.loc[pm["year_month"].eq(year_month)].sort_values("net_revenue", ascending=False)
        top = sub.iloc[0]
        label = month_label(year_month)
        partial_note = " through December 9" if year_month == "2011-12" else ""
        answer_label = f"{label}{partial_note}"
        question = (
            f"Which product had the highest merchandise net revenue in {label}{partial_note}? "
            "Provide the stock code, product name, and net revenue."
        )
        rows = to_records(
            sub.head(8),
            ["stock_code", "description", "net_revenue", "gross_positive_revenue", "cancellation_revenue"],
        )
        stock_code = str(top["stock_code"])
        description = str(top["description"])
        revenue = money(top["net_revenue"])
        records.append(
            base_record(
                "top_product_month",
                "medium",
                question,
                "product_month_net_revenue_summary.csv",
                rows,
                {"year_month": year_month, "metric": "merchandise_net_revenue"},
                {
                    "year_month": year_month,
                    "month_label": label,
                    "stock_code": stock_code,
                    "description": description,
                    "merchandise_net_revenue": revenue,
                    "currency": "GBP",
                },
                [
                    text_fact("year_month", "month", year_month, "month"),
                    text_fact("stock_code", "product_stock_code", stock_code, "stock code"),
                    text_fact("description", "product_name", description, "product name"),
                    currency_fact("merchandise_net_revenue", revenue),
                ],
                f"{stock_code} ({description}) had the highest merchandise net revenue in {answer_label} at GBP {revenue:,.2f}.",
            )
        )
    return records


def generate_country_comparison_month(tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    cm = tables["country_month_net"]
    months = recommended_months(tables)
    pairs = [
        ("Germany", "France"),
        ("Netherlands", "EIRE"),
        ("Spain", "Switzerland"),
        ("Australia", "France"),
        ("Germany", "EIRE"),
        ("Belgium", "Norway"),
    ]
    records: list[dict[str, Any]] = []

    candidates_by_month: dict[str, list[tuple[str, str]]] = {}
    for year_month in months:
        sub = cm.loc[cm["year_month"].eq(year_month)]
        candidates_by_month[year_month] = []
        for country_a, country_b in pairs:
            if country_a not in set(sub["country"]) or country_b not in set(sub["country"]):
                continue
            row_a = sub.loc[sub["country"].eq(country_a)].iloc[0]
            row_b = sub.loc[sub["country"].eq(country_b)].iloc[0]
            revenue_a = money(row_a["net_revenue"])
            revenue_b = money(row_b["net_revenue"])
            if abs(revenue_a) < 1000 and abs(revenue_b) < 1000:
                continue
            candidates_by_month[year_month].append((country_a, country_b))

    selected: list[tuple[str, str, str]] = []
    round_index = 0
    while len(selected) < QUESTION_TYPE_QUOTAS["country_comparison_month"]:
        added_this_round = False
        for year_month in months:
            candidates = candidates_by_month[year_month]
            if round_index < len(candidates):
                country_a, country_b = candidates[round_index]
                selected.append((year_month, country_a, country_b))
                added_this_round = True
                if len(selected) >= QUESTION_TYPE_QUOTAS["country_comparison_month"]:
                    break
        if not added_this_round:
            break
        round_index += 1

    if len(selected) != QUESTION_TYPE_QUOTAS["country_comparison_month"]:
        raise ValueError(
            f"Expected {QUESTION_TYPE_QUOTAS['country_comparison_month']} country comparison questions, "
            f"selected {len(selected)}"
        )

    for year_month, country_a, country_b in selected:
        sub = cm.loc[cm["year_month"].eq(year_month)]
        row_a = sub.loc[sub["country"].eq(country_a)].iloc[0]
        row_b = sub.loc[sub["country"].eq(country_b)].iloc[0]
        revenue_a = money(row_a["net_revenue"])
        revenue_b = money(row_b["net_revenue"])
        if revenue_a >= revenue_b:
            higher, lower = country_a, country_b
            higher_revenue, lower_revenue = revenue_a, revenue_b
        else:
            higher, lower = country_b, country_a
            higher_revenue, lower_revenue = revenue_b, revenue_a
        delta = money(higher_revenue - lower_revenue)
        evidence = pd.concat(
            [
                sub.loc[sub["country"].isin([country_a, country_b])],
                sub.sort_values("net_revenue", ascending=False).head(3),
            ],
            ignore_index=True,
        ).drop_duplicates(subset=["country"])
        rows = to_records(
            evidence,
            [
                "country",
                "net_revenue",
                "gross_positive_revenue",
                "cancellation_revenue",
                "invoice_count",
            ],
        )
        question = (
            f"In {month_label(year_month)}, did {country_a} or {country_b} generate more "
            "net revenue, and by how much?"
        )
        records.append(
            base_record(
                "country_comparison_month",
                "medium",
                question,
                "country_month_net_revenue_summary.csv",
                rows,
                {"year_month": year_month, "countries": [country_a, country_b]},
                {
                    "year_month": year_month,
                    "month_label": month_label(year_month),
                    "country_a": country_a,
                    "country_b": country_b,
                    "country_a_net_revenue": revenue_a,
                    "country_b_net_revenue": revenue_b,
                    "higher_country": higher,
                    "lower_country": lower,
                    "revenue_delta": delta,
                    "currency": "GBP",
                },
                [
                    text_fact("year_month", "month", year_month, "month"),
                    text_fact("higher_country", "country", higher, "higher country"),
                    text_fact("lower_country", "country", lower, "lower country"),
                    currency_fact("country_a_net_revenue", revenue_a, f"{country_a} net revenue"),
                    currency_fact("country_b_net_revenue", revenue_b, f"{country_b} net revenue"),
                    currency_fact("revenue_delta", delta, "difference"),
                ],
                f"{higher} generated more net revenue than {lower} by GBP {delta:,.2f} in {month_label(year_month)}.",
            )
        )
    return records


def generate_monthly_revenue_change(tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    monthly = tables["monthly_net"]
    months = recommended_months(tables)
    records: list[dict[str, Any]] = []
    for previous_month, current_month in zip(months[:-1], months[1:]):
        prev = monthly.loc[monthly["year_month"].eq(previous_month)].iloc[0]
        cur = monthly.loc[monthly["year_month"].eq(current_month)].iloc[0]
        prev_revenue = money(prev["net_revenue"])
        cur_revenue = money(cur["net_revenue"])
        absolute_change = money(cur_revenue - prev_revenue)
        percent_change = pct((cur_revenue - prev_revenue) / abs(prev_revenue) * 100)
        direction = "increase" if absolute_change >= 0 else "decrease"
        evidence = monthly.loc[monthly["year_month"].isin([previous_month, current_month])].sort_values(
            "year_month"
        )
        rows = to_records(
            evidence,
            ["year_month", "net_revenue", "gross_positive_revenue", "cancellation_revenue", "invoice_count"],
        )
        question = (
            f"How did net revenue change from {month_label(previous_month)} to {month_label(current_month)}? "
            "Provide the absolute change and percentage change."
        )
        records.append(
            base_record(
                "monthly_revenue_change",
                "hard",
                question,
                "monthly_net_revenue_summary.csv",
                rows,
                {"previous_month": previous_month, "current_month": current_month},
                {
                    "previous_month": previous_month,
                    "current_month": current_month,
                    "previous_month_label": month_label(previous_month),
                    "current_month_label": month_label(current_month),
                    "previous_net_revenue": prev_revenue,
                    "current_net_revenue": cur_revenue,
                    "absolute_change": absolute_change,
                    "percent_change": percent_change,
                    "direction": direction,
                    "currency": "GBP",
                },
                [
                    text_fact("previous_month", "month", previous_month, "previous month"),
                    text_fact("current_month", "month", current_month, "current month"),
                    currency_fact("previous_net_revenue", prev_revenue),
                    currency_fact("current_net_revenue", cur_revenue),
                    currency_fact("absolute_change", absolute_change),
                    percent_fact("percent_change", percent_change),
                    text_fact("direction", "comparison_direction", direction),
                ],
                (
                    f"Net revenue {direction}d by GBP {abs(absolute_change):,.2f} "
                    f"({percent_change:.2f}%) from {month_label(previous_month)} to {month_label(current_month)}."
                ),
            )
        )
    return records


def generate_top3_products_month(tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    pm = tables["product_month_net"]
    months = ["2010-12"] + recommended_months(tables) + ["2011-12"]
    records: list[dict[str, Any]] = []
    for year_month in months:
        sub = pm.loc[pm["year_month"].eq(year_month)].sort_values("net_revenue", ascending=False)
        top3 = sub.head(3).copy()
        ranking: list[dict[str, Any]] = []
        for rank, (_, row) in enumerate(top3.iterrows(), start=1):
            ranking.append(
                {
                    "rank": rank,
                    "stock_code": str(row["stock_code"]),
                    "description": str(row["description"]),
                    "merchandise_net_revenue": money(row["net_revenue"]),
                }
            )
        label = month_label(year_month)
        partial_note = " through December 9" if year_month == "2011-12" else ""
        answer_label = f"{label}{partial_note}"
        question = (
            f"What were the top 3 products by merchandise net revenue in {label}{partial_note}? "
            "Give the rank, stock code, product name, and net revenue."
        )
        rows = to_records(
            sub.head(8),
            ["stock_code", "description", "net_revenue", "gross_positive_revenue", "cancellation_revenue"],
        )
        records.append(
            base_record(
                "top3_products_month",
                "medium",
                question,
                "product_month_net_revenue_summary.csv",
                rows,
                {"year_month": year_month, "metric": "merchandise_net_revenue", "top_k": 3},
                {
                    "year_month": year_month,
                    "month_label": label,
                    "top_products": ranking,
                    "currency": "GBP",
                },
                [
                    text_fact("year_month", "month", year_month, "month"),
                    rank_fact("top_products", ranking),
                ],
                f"Top 3 products in {answer_label}: "
                + "; ".join(
                    f"{item['rank']}. {item['stock_code']} ({item['description']}), GBP {item['merchandise_net_revenue']:,.2f}"
                    for item in ranking
                )
                + ".",
            )
        )
    return records


def generate_product_revenue_share_month(tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    pm = tables["product_month_net"]
    months = recommended_months(tables)
    specs: list[tuple[str, int]] = [(month, 1) for month in months]
    specs.extend([(month, 3) for month in ["2011-01", "2011-03", "2011-06", "2011-09", "2011-11"]])
    records: list[dict[str, Any]] = []
    for year_month, top_n in specs:
        sub = pm.loc[pm["year_month"].eq(year_month)].sort_values("net_revenue", ascending=False)
        denominator = money(sub["net_revenue"].sum())
        top_rows = sub.head(top_n)
        numerator = money(top_rows["net_revenue"].sum())
        share = pct(numerator / denominator * 100)
        ranking: list[dict[str, Any]] = []
        for rank, (_, row) in enumerate(top_rows.iterrows(), start=1):
            ranking.append(
                {
                    "rank": rank,
                    "stock_code": str(row["stock_code"]),
                    "description": str(row["description"]),
                    "merchandise_net_revenue": money(row["net_revenue"]),
                }
            )
        if top_n == 1:
            row = top_rows.iloc[0]
            focus = f"the top product ({row['stock_code']} - {row['description']})"
            question = (
                f"What percentage of merchandise net revenue in {month_label(year_month)} "
                "came from the top product?"
            )
        else:
            focus = f"the top {top_n} products"
            question = (
                f"What percentage of merchandise net revenue in {month_label(year_month)} "
                f"came from the top {top_n} products combined?"
            )
        rows = to_records(
            sub.head(8),
            ["stock_code", "description", "net_revenue", "gross_positive_revenue", "cancellation_revenue"],
        )
        records.append(
            base_record(
                "product_revenue_share_month",
                "hard",
                question,
                "product_month_net_revenue_summary.csv",
                rows,
                {"year_month": year_month, "metric": "merchandise_net_revenue", "top_n": top_n},
                {
                    "year_month": year_month,
                    "month_label": month_label(year_month),
                    "top_n": top_n,
                    "top_products": ranking,
                    "numerator_merchandise_net_revenue": numerator,
                    "total_merchandise_net_revenue": denominator,
                    "share_percent": share,
                    "currency": "GBP",
                },
                [
                    text_fact("year_month", "month", year_month, "month"),
                    rank_fact("top_products", ranking),
                    currency_fact("numerator_merchandise_net_revenue", numerator, "share numerator"),
                    currency_fact("total_merchandise_net_revenue", denominator, "share denominator"),
                    percent_fact("share_percent", share),
                ],
                (
                    f"In {month_label(year_month)}, {focus} contributed GBP {numerator:,.2f} "
                    f"out of GBP {denominator:,.2f}, or {share:.2f}% of merchandise net revenue."
                ),
                {
                    "total_merchandise_net_revenue": denominator,
                    "share_numerator_label": focus,
                },
            )
        )
    return records


def generate_return_impact_month(tables: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    monthly = tables["monthly_net"]
    months = ["2010-12"] + recommended_months(tables)
    records: list[dict[str, Any]] = []
    for year_month in months:
        row = monthly.loc[monthly["year_month"].eq(year_month)].iloc[0]
        gross = money(row["gross_positive_revenue"])
        cancellation = money(row["cancellation_revenue"])
        reduction = money(abs(cancellation))
        net_revenue = money(row["net_revenue"])
        reduction_rate = pct(reduction / gross * 100)
        rows = to_records(
            pd.DataFrame([row]),
            ["year_month", "net_revenue", "gross_positive_revenue", "cancellation_revenue", "invoice_count"],
        )
        question = (
            f"In {month_label(year_month)}, how much did cancellations and returns reduce gross positive revenue, "
            "and what was the final net revenue?"
        )
        records.append(
            base_record(
                "return_impact_month",
                "hard",
                question,
                "monthly_net_revenue_summary.csv",
                rows,
                {"year_month": year_month},
                {
                    "year_month": year_month,
                    "month_label": month_label(year_month),
                    "gross_positive_revenue": gross,
                    "cancellation_revenue": cancellation,
                    "reduction_amount": reduction,
                    "reduction_rate_percent": reduction_rate,
                    "net_revenue": net_revenue,
                    "currency": "GBP",
                },
                [
                    text_fact("year_month", "month", year_month, "month"),
                    currency_fact("gross_positive_revenue", gross),
                    currency_fact("cancellation_revenue", cancellation),
                    currency_fact("reduction_amount", reduction),
                    percent_fact("reduction_rate_percent", reduction_rate),
                    currency_fact("net_revenue", net_revenue),
                ],
                (
                    f"Cancellations and returns reduced gross positive revenue by GBP {reduction:,.2f} "
                    f"({reduction_rate:.2f}% of gross), leaving net revenue of GBP {net_revenue:,.2f}."
                ),
            )
        )
    return records


def assign_ids_and_splits(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counters: dict[str, int] = {}
    for idx, record in enumerate(records, start=1):
        question_type = record["question_type"]
        counters[question_type] = counters.get(question_type, 0) + 1
        position = counters[question_type]
        if position % 5 in (1, 2, 3):
            split = "train"
        elif position % 5 == 4:
            split = "dev"
        else:
            split = "test"
        record["question_id"] = f"q_{idx:04d}"
        record["split"] = split
    return records


def flatten_for_sample(records: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for record in records:
        rows.append(
            {
                "question_id": record["question_id"],
                "split": record["split"],
                "question_type": record["question_type"],
                "difficulty": record["difficulty"],
                "question": record["question"],
                "gold_short_answer": record["gold_short_answer"],
                "evidence_source": record["evidence"]["source_file"],
            }
        )
    return pd.DataFrame(rows)


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")


def main() -> None:
    tables = load_tables()
    generators = [
        generate_top_country_month,
        generate_top_product_month,
        generate_country_comparison_month,
        generate_monthly_revenue_change,
        generate_top3_products_month,
        generate_product_revenue_share_month,
        generate_return_impact_month,
    ]

    records: list[dict[str, Any]] = []
    for generator in generators:
        generated = generator(tables)
        records.extend(generated)

    records = assign_ids_and_splits(records)

    counts = pd.Series([record["question_type"] for record in records]).value_counts().sort_index().to_dict()
    expected_total = sum(QUESTION_TYPE_QUOTAS.values())
    if len(records) != expected_total:
        raise ValueError(f"Expected {expected_total} records, generated {len(records)}")
    for question_type, expected_count in QUESTION_TYPE_QUOTAS.items():
        actual_count = int(counts.get(question_type, 0))
        if actual_count != expected_count:
            raise ValueError(
                f"Question type {question_type} expected {expected_count}, generated {actual_count}"
            )

    write_jsonl(OUTPUT_JSONL, records)
    sample = flatten_for_sample(records)
    sample.to_csv(OUTPUT_SAMPLE_CSV, index=False)

    split_counts = (
        sample.groupby(["question_type", "split"], as_index=False).size().to_dict(orient="records")
    )
    report = {
        "record_count": len(records),
        "question_type_counts": counts,
        "difficulty_counts": sample["difficulty"].value_counts().sort_index().to_dict(),
        "split_counts": split_counts,
        "outputs": {
            "jsonl": str(OUTPUT_JSONL),
            "sample_csv": str(OUTPUT_SAMPLE_CSV),
        },
    }
    OUTPUT_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
