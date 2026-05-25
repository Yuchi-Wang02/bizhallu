from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

NON_MERCHANDISE_STOCK_CODES = {
    "AMAZONFEE",
    "B",
    "BANK CHARGES",
    "C2",
    "CRUK",
    "D",
    "DOT",
    "M",
    "POST",
    "S",
}


def _clean_description(value: object) -> object:
    if pd.isna(value):
        return np.nan
    return re.sub(r"\s+", " ", str(value).strip())


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = df.rename(
        columns={
            "InvoiceNo": "invoice_no",
            "StockCode": "stock_code",
            "Description": "description",
            "Quantity": "quantity",
            "InvoiceDate": "invoice_date",
            "UnitPrice": "unit_price",
            "CustomerID": "customer_id",
            "Country": "country",
        }
    ).copy()

    renamed["invoice_no"] = renamed["invoice_no"].astype(str).str.strip()
    renamed["stock_code"] = renamed["stock_code"].astype(str).str.strip()
    renamed["description"] = renamed["description"].map(_clean_description)
    renamed["country"] = renamed["country"].astype(str).str.strip()
    renamed["invoice_date"] = pd.to_datetime(renamed["invoice_date"])
    renamed["invoice_date_only"] = renamed["invoice_date"].dt.date.astype(str)
    renamed["year_month"] = renamed["invoice_date"].dt.to_period("M").astype(str)
    renamed["revenue"] = renamed["quantity"] * renamed["unit_price"]

    renamed["customer_id"] = renamed["customer_id"].astype("Int64")
    renamed["is_cancel_invoice"] = renamed["invoice_no"].str.upper().str.startswith("C")
    renamed["is_negative_quantity"] = renamed["quantity"] < 0
    renamed["is_nonpositive_unit_price"] = renamed["unit_price"] <= 0
    renamed["is_missing_description"] = renamed["description"].isna() | (
        renamed["description"].astype("string").str.len() == 0
    )
    renamed["is_exact_duplicate"] = renamed.duplicated(keep="first")
    renamed["has_no_digit_stock_code"] = ~renamed["stock_code"].str.contains(r"\d", regex=True)
    renamed["is_non_merchandise"] = (
        renamed["stock_code"].str.upper().isin(NON_MERCHANDISE_STOCK_CODES)
        | renamed["has_no_digit_stock_code"]
    )
    return renamed


def _raw_profile(raw: pd.DataFrame, normalized: pd.DataFrame) -> dict:
    return {
        "source_file": str(RAW_PATH),
        "raw_shape": list(raw.shape),
        "columns": list(raw.columns),
        "date_min": str(raw["InvoiceDate"].min()),
        "date_max": str(raw["InvoiceDate"].max()),
        "missing_values": {col: int(value) for col, value in raw.isna().sum().items()},
        "duplicate_rows": int(raw.duplicated().sum()),
        "invoice_count": int(raw["InvoiceNo"].nunique(dropna=True)),
        "stock_code_count": int(raw["StockCode"].nunique(dropna=True)),
        "description_count": int(raw["Description"].nunique(dropna=True)),
        "country_count": int(raw["Country"].nunique(dropna=True)),
        "customer_count": int(raw["CustomerID"].nunique(dropna=True)),
        "cancel_invoice_rows": int(normalized["is_cancel_invoice"].sum()),
        "negative_quantity_rows": int(normalized["is_negative_quantity"].sum()),
        "zero_quantity_rows": int((normalized["quantity"] == 0).sum()),
        "negative_unit_price_rows": int((normalized["unit_price"] < 0).sum()),
        "zero_unit_price_rows": int((normalized["unit_price"] == 0).sum()),
        "non_merchandise_rows": int(normalized["is_non_merchandise"].sum()),
    }


def _add_exclusion_reason(df: pd.DataFrame) -> pd.DataFrame:
    reasons = []
    for row in df.itertuples(index=False):
        row_reasons = []
        if row.is_exact_duplicate:
            row_reasons.append("exact_duplicate")
        if row.is_cancel_invoice:
            row_reasons.append("cancel_invoice")
        if row.is_negative_quantity:
            row_reasons.append("negative_quantity")
        if row.is_nonpositive_unit_price:
            row_reasons.append("nonpositive_unit_price")
        if row.is_missing_description:
            row_reasons.append("missing_description")
        reasons.append(";".join(row_reasons))
    out = df.copy()
    out["exclusion_reason"] = reasons
    return out


def _summarize_monthly(sales: pd.DataFrame) -> pd.DataFrame:
    return (
        sales.groupby("year_month", as_index=False)
        .agg(
            line_count=("invoice_no", "size"),
            invoice_count=("invoice_no", "nunique"),
            customer_count=("customer_id", "nunique"),
            total_quantity=("quantity", "sum"),
            total_revenue=("revenue", "sum"),
            avg_line_revenue=("revenue", "mean"),
        )
        .sort_values("year_month")
    )


def _summarize_monthly_coverage(lines: pd.DataFrame) -> pd.DataFrame:
    coverage = (
        lines.groupby("year_month", as_index=False)
        .agg(
            first_invoice_datetime=("invoice_date", "min"),
            last_invoice_datetime=("invoice_date", "max"),
            transaction_days=("invoice_date_only", "nunique"),
            line_count=("invoice_no", "size"),
            invoice_count=("invoice_no", "nunique"),
        )
        .sort_values("year_month")
    )
    coverage["recommended_for_monthly_trend_questions"] = coverage["year_month"].between(
        "2011-01", "2011-11"
    )
    coverage["notes"] = np.where(
        coverage["year_month"] == "2011-12",
        "partial month; source data ends on 2011-12-09",
        "",
    )
    return coverage


def _summarize_monthly_net(lines: pd.DataFrame) -> pd.DataFrame:
    return (
        lines.groupby("year_month", as_index=False)
        .agg(
            line_count=("invoice_no", "size"),
            invoice_count=("invoice_no", "nunique"),
            customer_count=("customer_id", "nunique"),
            total_quantity=("quantity", "sum"),
            net_revenue=("revenue", "sum"),
            gross_positive_revenue=("revenue", lambda values: values[values > 0].sum()),
            cancellation_revenue=("revenue", lambda values: values[values < 0].sum()),
        )
        .sort_values("year_month")
    )


def _summarize_country_month(sales: pd.DataFrame) -> pd.DataFrame:
    return (
        sales.groupby(["year_month", "country"], as_index=False)
        .agg(
            line_count=("invoice_no", "size"),
            invoice_count=("invoice_no", "nunique"),
            customer_count=("customer_id", "nunique"),
            total_quantity=("quantity", "sum"),
            total_revenue=("revenue", "sum"),
        )
        .sort_values(["year_month", "total_revenue"], ascending=[True, False])
    )


def _summarize_country_month_net(lines: pd.DataFrame) -> pd.DataFrame:
    return (
        lines.groupby(["year_month", "country"], as_index=False)
        .agg(
            line_count=("invoice_no", "size"),
            invoice_count=("invoice_no", "nunique"),
            customer_count=("customer_id", "nunique"),
            total_quantity=("quantity", "sum"),
            net_revenue=("revenue", "sum"),
            gross_positive_revenue=("revenue", lambda values: values[values > 0].sum()),
            cancellation_revenue=("revenue", lambda values: values[values < 0].sum()),
        )
        .sort_values(["year_month", "net_revenue"], ascending=[True, False])
    )


def _summarize_product_month(merchandise: pd.DataFrame) -> pd.DataFrame:
    return (
        merchandise.groupby(["year_month", "stock_code", "description"], as_index=False)
        .agg(
            line_count=("invoice_no", "size"),
            invoice_count=("invoice_no", "nunique"),
            total_quantity=("quantity", "sum"),
            total_revenue=("revenue", "sum"),
        )
        .sort_values(["year_month", "total_revenue"], ascending=[True, False])
    )


def _summarize_product_month_net(merchandise: pd.DataFrame) -> pd.DataFrame:
    return (
        merchandise.groupby(["year_month", "stock_code", "description"], as_index=False)
        .agg(
            line_count=("invoice_no", "size"),
            invoice_count=("invoice_no", "nunique"),
            total_quantity=("quantity", "sum"),
            net_revenue=("revenue", "sum"),
            gross_positive_revenue=("revenue", lambda values: values[values > 0].sum()),
            cancellation_revenue=("revenue", lambda values: values[values < 0].sum()),
        )
        .sort_values(["year_month", "net_revenue"], ascending=[True, False])
    )


def _summarize_product(merchandise: pd.DataFrame) -> pd.DataFrame:
    return (
        merchandise.groupby(["stock_code", "description"], as_index=False)
        .agg(
            line_count=("invoice_no", "size"),
            invoice_count=("invoice_no", "nunique"),
            total_quantity=("quantity", "sum"),
            total_revenue=("revenue", "sum"),
            first_sale_date=("invoice_date_only", "min"),
            last_sale_date=("invoice_date_only", "max"),
        )
        .sort_values("total_revenue", ascending=False)
    )


def _summarize_product_net(merchandise: pd.DataFrame) -> pd.DataFrame:
    return (
        merchandise.groupby(["stock_code", "description"], as_index=False)
        .agg(
            line_count=("invoice_no", "size"),
            invoice_count=("invoice_no", "nunique"),
            total_quantity=("quantity", "sum"),
            net_revenue=("revenue", "sum"),
            gross_positive_revenue=("revenue", lambda values: values[values > 0].sum()),
            cancellation_revenue=("revenue", lambda values: values[values < 0].sum()),
            first_transaction_date=("invoice_date_only", "min"),
            last_transaction_date=("invoice_date_only", "max"),
        )
        .sort_values("net_revenue", ascending=False)
    )


def _summarize_country(sales: pd.DataFrame) -> pd.DataFrame:
    return (
        sales.groupby("country", as_index=False)
        .agg(
            line_count=("invoice_no", "size"),
            invoice_count=("invoice_no", "nunique"),
            customer_count=("customer_id", "nunique"),
            total_quantity=("quantity", "sum"),
            total_revenue=("revenue", "sum"),
        )
        .sort_values("total_revenue", ascending=False)
    )


def _summarize_country_net(lines: pd.DataFrame) -> pd.DataFrame:
    return (
        lines.groupby("country", as_index=False)
        .agg(
            line_count=("invoice_no", "size"),
            invoice_count=("invoice_no", "nunique"),
            customer_count=("customer_id", "nunique"),
            total_quantity=("quantity", "sum"),
            net_revenue=("revenue", "sum"),
            gross_positive_revenue=("revenue", lambda values: values[values > 0].sum()),
            cancellation_revenue=("revenue", lambda values: values[values < 0].sum()),
        )
        .sort_values("net_revenue", ascending=False)
    )


def main() -> None:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Missing raw dataset: {RAW_PATH}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    raw = pd.read_excel(RAW_PATH, engine="openpyxl")
    normalized = _normalize_columns(raw)

    positive_sales_mask = (
        ~normalized["is_exact_duplicate"]
        & ~normalized["is_cancel_invoice"]
        & ~normalized["is_negative_quantity"]
        & ~normalized["is_nonpositive_unit_price"]
        & ~normalized["is_missing_description"]
    )
    valid_revenue_mask = (
        ~normalized["is_exact_duplicate"]
        & ~normalized["is_nonpositive_unit_price"]
        & ~normalized["is_missing_description"]
    )
    cancellation_mask = normalized["is_cancel_invoice"] | normalized["is_negative_quantity"]

    sales = normalized.loc[positive_sales_mask].copy()
    merchandise_sales = sales.loc[~sales["is_non_merchandise"]].copy()
    net_lines = normalized.loc[valid_revenue_mask].copy()
    merchandise_net_lines = net_lines.loc[~net_lines["is_non_merchandise"]].copy()
    cancellations = normalized.loc[cancellation_mask & ~normalized["is_exact_duplicate"]].copy()
    excluded = _add_exclusion_reason(normalized.loc[~positive_sales_mask].copy())

    profile = _raw_profile(raw, normalized)
    profile.update(
        {
            "positive_sales_rows": int(len(sales)),
            "merchandise_sales_rows": int(len(merchandise_sales)),
            "valid_net_revenue_rows": int(len(net_lines)),
            "merchandise_net_revenue_rows": int(len(merchandise_net_lines)),
            "cancellation_or_return_rows": int(len(cancellations)),
            "excluded_rows": int(len(excluded)),
            "positive_sales_revenue": round(float(sales["revenue"].sum()), 2),
            "merchandise_sales_revenue": round(float(merchandise_sales["revenue"].sum()), 2),
            "net_revenue": round(float(net_lines["revenue"].sum()), 2),
            "merchandise_net_revenue": round(float(merchandise_net_lines["revenue"].sum()), 2),
        }
    )

    outputs = {
        "retail_lines_normalized.csv": normalized,
        "retail_sales_lines.csv": sales,
        "retail_merchandise_sales_lines.csv": merchandise_sales,
        "retail_net_revenue_lines.csv": net_lines,
        "retail_merchandise_net_revenue_lines.csv": merchandise_net_lines,
        "retail_cancellation_lines.csv": cancellations,
        "retail_excluded_lines.csv": excluded,
        "monthly_coverage_summary.csv": _summarize_monthly_coverage(net_lines),
        "monthly_sales_summary.csv": _summarize_monthly(sales),
        "monthly_net_revenue_summary.csv": _summarize_monthly_net(net_lines),
        "country_month_sales_summary.csv": _summarize_country_month(sales),
        "country_month_net_revenue_summary.csv": _summarize_country_month_net(net_lines),
        "product_month_sales_summary.csv": _summarize_product_month(merchandise_sales),
        "product_month_net_revenue_summary.csv": _summarize_product_month_net(
            merchandise_net_lines
        ),
        "product_sales_summary.csv": _summarize_product(merchandise_sales),
        "product_net_revenue_summary.csv": _summarize_product_net(merchandise_net_lines),
        "country_sales_summary.csv": _summarize_country(sales),
        "country_net_revenue_summary.csv": _summarize_country_net(net_lines),
    }

    for filename, frame in outputs.items():
        frame.to_csv(PROCESSED_DIR / filename, index=False)

    (PROCESSED_DIR / "data_quality_report.json").write_text(
        json.dumps(profile, indent=2), encoding="utf-8"
    )

    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
