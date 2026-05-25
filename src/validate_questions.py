from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
QUESTIONS_PATH = PROCESSED_DIR / "business_questions_gold.jsonl"
VALIDATION_REPORT = PROCESSED_DIR / "business_questions_gold_validation.json"

EXPECTED_COUNTS = {
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


def load_questions() -> list[dict[str, Any]]:
    with QUESTIONS_PATH.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_tables() -> dict[str, pd.DataFrame]:
    return {
        "monthly_net_revenue_summary.csv": pd.read_csv(
            PROCESSED_DIR / "monthly_net_revenue_summary.csv"
        ),
        "monthly_coverage_summary.csv": pd.read_csv(PROCESSED_DIR / "monthly_coverage_summary.csv"),
        "country_month_net_revenue_summary.csv": pd.read_csv(
            PROCESSED_DIR / "country_month_net_revenue_summary.csv"
        ),
        "product_month_net_revenue_summary.csv": pd.read_csv(
            PROCESSED_DIR / "product_month_net_revenue_summary.csv"
        ),
    }


def add_failure(failures: list[dict[str, Any]], question_id: str, reason: str) -> None:
    failures.append({"question_id": question_id, "reason": reason})


def assert_close(
    failures: list[dict[str, Any]],
    question_id: str,
    field: str,
    actual: float,
    expected: float,
    tolerance: float = 0.01,
) -> None:
    if abs(float(actual) - float(expected)) > tolerance:
        add_failure(
            failures,
            question_id,
            f"{field} mismatch: actual={actual}, expected={expected}",
        )


def validate_top_country(record: dict[str, Any], tables: dict[str, pd.DataFrame], failures: list[dict[str, Any]]) -> None:
    qid = record["question_id"]
    filters = record["evidence"]["filters"]
    answer = record["gold_answer"]
    cm = tables["country_month_net_revenue_summary.csv"]
    sub = cm.loc[cm["year_month"].eq(filters["year_month"])].copy()
    for country in filters.get("exclude_countries", []):
        sub = sub.loc[~sub["country"].eq(country)]
    top = sub.sort_values("net_revenue", ascending=False).iloc[0]
    if answer["country"] != top["country"]:
        add_failure(failures, qid, f"country mismatch: {answer['country']} vs {top['country']}")
    assert_close(failures, qid, "net_revenue", answer["net_revenue"], money(top["net_revenue"]))


def validate_top_product(record: dict[str, Any], tables: dict[str, pd.DataFrame], failures: list[dict[str, Any]]) -> None:
    qid = record["question_id"]
    year_month = record["evidence"]["filters"]["year_month"]
    answer = record["gold_answer"]
    pm = tables["product_month_net_revenue_summary.csv"]
    top = pm.loc[pm["year_month"].eq(year_month)].sort_values("net_revenue", ascending=False).iloc[0]
    if str(answer["stock_code"]) != str(top["stock_code"]):
        add_failure(failures, qid, f"stock_code mismatch: {answer['stock_code']} vs {top['stock_code']}")
    if str(answer["description"]) != str(top["description"]):
        add_failure(failures, qid, "description mismatch")
    assert_close(
        failures,
        qid,
        "merchandise_net_revenue",
        answer["merchandise_net_revenue"],
        money(top["net_revenue"]),
    )


def validate_country_comparison(
    record: dict[str, Any], tables: dict[str, pd.DataFrame], failures: list[dict[str, Any]]
) -> None:
    qid = record["question_id"]
    filters = record["evidence"]["filters"]
    answer = record["gold_answer"]
    cm = tables["country_month_net_revenue_summary.csv"]
    sub = cm.loc[cm["year_month"].eq(filters["year_month"])]
    rows = {row["country"]: row for _, row in sub.iterrows()}
    country_a, country_b = filters["countries"]
    rev_a = money(rows[country_a]["net_revenue"])
    rev_b = money(rows[country_b]["net_revenue"])
    if rev_a >= rev_b:
        higher, lower, delta = country_a, country_b, money(rev_a - rev_b)
    else:
        higher, lower, delta = country_b, country_a, money(rev_b - rev_a)
    if answer["higher_country"] != higher:
        add_failure(failures, qid, f"higher_country mismatch: {answer['higher_country']} vs {higher}")
    if answer["lower_country"] != lower:
        add_failure(failures, qid, f"lower_country mismatch: {answer['lower_country']} vs {lower}")
    assert_close(failures, qid, "country_a_net_revenue", answer["country_a_net_revenue"], rev_a)
    assert_close(failures, qid, "country_b_net_revenue", answer["country_b_net_revenue"], rev_b)
    assert_close(failures, qid, "revenue_delta", answer["revenue_delta"], delta)


def validate_monthly_change(
    record: dict[str, Any], tables: dict[str, pd.DataFrame], failures: list[dict[str, Any]]
) -> None:
    qid = record["question_id"]
    filters = record["evidence"]["filters"]
    answer = record["gold_answer"]
    monthly = tables["monthly_net_revenue_summary.csv"]
    prev = monthly.loc[monthly["year_month"].eq(filters["previous_month"])].iloc[0]
    cur = monthly.loc[monthly["year_month"].eq(filters["current_month"])].iloc[0]
    prev_rev = money(prev["net_revenue"])
    cur_rev = money(cur["net_revenue"])
    change = money(cur_rev - prev_rev)
    percent = pct((cur_rev - prev_rev) / abs(prev_rev) * 100)
    direction = "increase" if change >= 0 else "decrease"
    assert_close(failures, qid, "previous_net_revenue", answer["previous_net_revenue"], prev_rev)
    assert_close(failures, qid, "current_net_revenue", answer["current_net_revenue"], cur_rev)
    assert_close(failures, qid, "absolute_change", answer["absolute_change"], change)
    assert_close(failures, qid, "percent_change", answer["percent_change"], percent)
    if answer["direction"] != direction:
        add_failure(failures, qid, f"direction mismatch: {answer['direction']} vs {direction}")


def validate_top3(record: dict[str, Any], tables: dict[str, pd.DataFrame], failures: list[dict[str, Any]]) -> None:
    qid = record["question_id"]
    year_month = record["evidence"]["filters"]["year_month"]
    answer = record["gold_answer"]
    pm = tables["product_month_net_revenue_summary.csv"]
    top3 = pm.loc[pm["year_month"].eq(year_month)].sort_values("net_revenue", ascending=False).head(3)
    expected = [
        {
            "rank": rank,
            "stock_code": str(row["stock_code"]),
            "description": str(row["description"]),
            "merchandise_net_revenue": money(row["net_revenue"]),
        }
        for rank, (_, row) in enumerate(top3.iterrows(), start=1)
    ]
    if answer["top_products"] != expected:
        add_failure(failures, qid, "top_products ranking mismatch")


def validate_share(record: dict[str, Any], tables: dict[str, pd.DataFrame], failures: list[dict[str, Any]]) -> None:
    qid = record["question_id"]
    filters = record["evidence"]["filters"]
    answer = record["gold_answer"]
    pm = tables["product_month_net_revenue_summary.csv"]
    sub = pm.loc[pm["year_month"].eq(filters["year_month"])].sort_values("net_revenue", ascending=False)
    top_n = int(filters["top_n"])
    denominator = money(sub["net_revenue"].sum())
    top_rows = sub.head(top_n)
    numerator = money(top_rows["net_revenue"].sum())
    share = pct(numerator / denominator * 100)
    expected_top_products = [
        {
            "rank": rank,
            "stock_code": str(row["stock_code"]),
            "description": str(row["description"]),
            "merchandise_net_revenue": money(row["net_revenue"]),
        }
        for rank, (_, row) in enumerate(top_rows.iterrows(), start=1)
    ]
    if answer.get("top_products") != expected_top_products:
        add_failure(failures, qid, "share top_products mismatch")
    metadata = record["evidence"].get("metadata", {})
    if "total_merchandise_net_revenue" not in metadata:
        add_failure(failures, qid, "missing total_merchandise_net_revenue in evidence metadata")
    else:
        assert_close(
            failures,
            qid,
            "evidence.metadata.total_merchandise_net_revenue",
            metadata["total_merchandise_net_revenue"],
            denominator,
        )
    assert_close(
        failures,
        qid,
        "numerator_merchandise_net_revenue",
        answer["numerator_merchandise_net_revenue"],
        numerator,
    )
    assert_close(
        failures,
        qid,
        "total_merchandise_net_revenue",
        answer["total_merchandise_net_revenue"],
        denominator,
    )
    assert_close(failures, qid, "share_percent", answer["share_percent"], share)


def validate_return_impact(
    record: dict[str, Any], tables: dict[str, pd.DataFrame], failures: list[dict[str, Any]]
) -> None:
    qid = record["question_id"]
    year_month = record["evidence"]["filters"]["year_month"]
    answer = record["gold_answer"]
    monthly = tables["monthly_net_revenue_summary.csv"]
    row = monthly.loc[monthly["year_month"].eq(year_month)].iloc[0]
    gross = money(row["gross_positive_revenue"])
    cancellation = money(row["cancellation_revenue"])
    reduction = money(abs(cancellation))
    net = money(row["net_revenue"])
    rate = pct(reduction / gross * 100)
    assert_close(failures, qid, "gross_positive_revenue", answer["gross_positive_revenue"], gross)
    assert_close(failures, qid, "cancellation_revenue", answer["cancellation_revenue"], cancellation)
    assert_close(failures, qid, "reduction_amount", answer["reduction_amount"], reduction)
    assert_close(failures, qid, "reduction_rate_percent", answer["reduction_rate_percent"], rate)
    assert_close(failures, qid, "net_revenue", answer["net_revenue"], net)


VALIDATORS = {
    "top_country_month": validate_top_country,
    "top_product_month": validate_top_product,
    "country_comparison_month": validate_country_comparison,
    "monthly_revenue_change": validate_monthly_change,
    "top3_products_month": validate_top3,
    "product_revenue_share_month": validate_share,
    "return_impact_month": validate_return_impact,
}


def main() -> None:
    questions = load_questions()
    tables = load_tables()
    failures: list[dict[str, Any]] = []

    ids = [record.get("question_id") for record in questions]
    if len(ids) != len(set(ids)):
        failures.append({"question_id": "GLOBAL", "reason": "duplicate question_id values"})
    if len(questions) != sum(EXPECTED_COUNTS.values()):
        failures.append(
            {
                "question_id": "GLOBAL",
                "reason": f"expected {sum(EXPECTED_COUNTS.values())} questions, found {len(questions)}",
            }
        )

    counts = pd.Series([record["question_type"] for record in questions]).value_counts().sort_index().to_dict()
    for question_type, expected in EXPECTED_COUNTS.items():
        actual = int(counts.get(question_type, 0))
        if actual != expected:
            failures.append(
                {
                    "question_id": "GLOBAL",
                    "reason": f"{question_type} expected {expected}, found {actual}",
                }
            )

    coverage = tables["monthly_coverage_summary.csv"]
    recommended_months = set(
        coverage.loc[
            coverage["recommended_for_monthly_trend_questions"].astype(bool),
            "year_month",
        ].astype(str)
    )

    required_fields = {
        "question_id",
        "question_type",
        "difficulty",
        "split",
        "question",
        "gold_short_answer",
        "gold_answer",
        "gold_facts",
        "evidence",
    }

    for record in questions:
        qid = record.get("question_id", "UNKNOWN")
        missing = sorted(required_fields - set(record))
        if missing:
            add_failure(failures, qid, f"missing required fields: {missing}")
            continue
        if record["difficulty"] not in {"easy", "medium", "hard"}:
            add_failure(failures, qid, f"invalid difficulty: {record['difficulty']}")
        if record["split"] not in {"train", "dev", "test"}:
            add_failure(failures, qid, f"invalid split: {record['split']}")
        source_file = record["evidence"].get("source_file")
        if source_file not in tables:
            add_failure(failures, qid, f"unknown evidence source: {source_file}")
        if not record["evidence"].get("rows"):
            add_failure(failures, qid, "empty evidence rows")
        if "through December 9" in record["question"] and "through December 9" not in record["gold_short_answer"]:
            add_failure(failures, qid, "partial December question missing December 9 in gold_short_answer")

        question_type = record["question_type"]
        if question_type in {"monthly_revenue_change"}:
            filters = record["evidence"]["filters"]
            if filters["previous_month"] not in recommended_months or filters["current_month"] not in recommended_months:
                add_failure(failures, qid, "monthly trend question uses non-recommended month")

        validator = VALIDATORS.get(question_type)
        if validator is None:
            add_failure(failures, qid, f"no validator for question_type={question_type}")
            continue
        validator(record, tables, failures)

    sample = pd.DataFrame(
        {
            "question_type": [record["question_type"] for record in questions],
            "difficulty": [record["difficulty"] for record in questions],
            "split": [record["split"] for record in questions],
        }
    )
    report = {
        "question_count": len(questions),
        "num_failures": len(failures),
        "failures": failures,
        "question_type_counts": counts,
        "difficulty_counts": sample["difficulty"].value_counts().sort_index().to_dict(),
        "split_counts": sample["split"].value_counts().sort_index().to_dict(),
    }
    VALIDATION_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
