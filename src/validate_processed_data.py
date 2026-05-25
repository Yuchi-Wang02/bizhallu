from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def _load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name, low_memory=False)


def _check(results: list[dict], name: str, condition: bool, detail: str) -> None:
    results.append({"check": name, "pass": bool(condition), "detail": detail})


def main() -> None:
    raw = pd.read_excel(RAW_PATH, engine="openpyxl")
    report = json.loads((PROCESSED_DIR / "data_quality_report.json").read_text())

    normalized = _load_csv("retail_lines_normalized.csv")
    sales = _load_csv("retail_sales_lines.csv")
    net = _load_csv("retail_net_revenue_lines.csv")
    merchandise_net = _load_csv("retail_merchandise_net_revenue_lines.csv")
    monthly_net = _load_csv("monthly_net_revenue_summary.csv")
    country_net = _load_csv("country_net_revenue_summary.csv")
    country_month_net = _load_csv("country_month_net_revenue_summary.csv")
    product_net = _load_csv("product_net_revenue_summary.csv")
    product_month_net = _load_csv("product_month_net_revenue_summary.csv")

    results: list[dict] = []

    _check(
        results,
        "raw row count matches normalized",
        len(raw) == len(normalized),
        f"{len(raw)} vs {len(normalized)}",
    )
    _check(results, "raw column count expected", raw.shape[1] == 8, str(raw.shape))
    _check(
        results,
        "report raw shape matches actual",
        report["raw_shape"] == list(raw.shape),
        f"report={report['raw_shape']} actual={list(raw.shape)}",
    )
    _check(
        results,
        "positive sales + excluded = raw",
        report["positive_sales_rows"] + report["excluded_rows"] == len(raw),
        f"{report['positive_sales_rows']} + {report['excluded_rows']} vs {len(raw)}",
    )
    _check(
        results,
        "sales has only positive quantity",
        (sales["quantity"] > 0).all(),
        f"min quantity={sales['quantity'].min()}",
    )
    _check(
        results,
        "sales has only positive unit price",
        (sales["unit_price"] > 0).all(),
        f"min unit_price={sales['unit_price'].min()}",
    )
    _check(
        results,
        "sales has no cancel invoices",
        (~sales["invoice_no"].astype(str).str.upper().str.startswith("C")).all(),
        "cancel rows="
        + str(sales["invoice_no"].astype(str).str.upper().str.startswith("C").sum()),
    )
    _check(
        results,
        "sales has no missing description",
        sales["description"].notna().all(),
        f"missing={sales['description'].isna().sum()}",
    )
    _check(
        results,
        "net has only positive unit price",
        (net["unit_price"] > 0).all(),
        f"min unit_price={net['unit_price'].min()}",
    )
    _check(
        results,
        "net has no missing description",
        net["description"].notna().all(),
        f"missing={net['description'].isna().sum()}",
    )
    _check(
        results,
        "net includes negative quantity rows",
        (net["quantity"] < 0).sum() > 0,
        "negative rows=" + str((net["quantity"] < 0).sum()),
    )
    _check(
        results,
        "merchandise net excludes no-digit stock codes",
        merchandise_net["stock_code"].astype(str).str.contains(r"\d", regex=True).all(),
        "no-digit rows="
        + str((~merchandise_net["stock_code"].astype(str).str.contains(r"\d", regex=True)).sum()),
    )
    _check(
        results,
        "revenue formula normalized",
        np.allclose(normalized["revenue"], normalized["quantity"] * normalized["unit_price"]),
        "max diff="
        + str((normalized["revenue"] - normalized["quantity"] * normalized["unit_price"]).abs().max()),
    )
    _check(
        results,
        "monthly net sum equals net line revenue",
        abs(monthly_net["net_revenue"].sum() - net["revenue"].sum()) < 1e-5,
        f"monthly={monthly_net['net_revenue'].sum()} line={net['revenue'].sum()}",
    )
    _check(
        results,
        "country net sum equals net line revenue",
        abs(country_net["net_revenue"].sum() - net["revenue"].sum()) < 1e-5,
        f"country={country_net['net_revenue'].sum()} line={net['revenue'].sum()}",
    )
    _check(
        results,
        "country-month net sum equals net line revenue",
        abs(country_month_net["net_revenue"].sum() - net["revenue"].sum()) < 1e-5,
        f"country_month={country_month_net['net_revenue'].sum()} line={net['revenue'].sum()}",
    )
    _check(
        results,
        "product net sum equals merchandise net line revenue",
        abs(product_net["net_revenue"].sum() - merchandise_net["revenue"].sum()) < 1e-5,
        f"product={product_net['net_revenue'].sum()} merch_line={merchandise_net['revenue'].sum()}",
    )
    _check(
        results,
        "product-month net sum equals merchandise net line revenue",
        abs(product_month_net["net_revenue"].sum() - merchandise_net["revenue"].sum()) < 1e-5,
        f"product_month={product_month_net['net_revenue'].sum()} merch_line={merchandise_net['revenue'].sum()}",
    )
    _check(
        results,
        "monthly gross plus cancellation equals net",
        np.allclose(
            monthly_net["gross_positive_revenue"] + monthly_net["cancellation_revenue"],
            monthly_net["net_revenue"],
        ),
        "max diff="
        + str(
            (
                monthly_net["gross_positive_revenue"]
                + monthly_net["cancellation_revenue"]
                - monthly_net["net_revenue"]
            )
            .abs()
            .max()
        ),
    )
    _check(
        results,
        "country gross plus cancellation equals net",
        np.allclose(
            country_net["gross_positive_revenue"] + country_net["cancellation_revenue"],
            country_net["net_revenue"],
        ),
        "max diff="
        + str(
            (
                country_net["gross_positive_revenue"]
                + country_net["cancellation_revenue"]
                - country_net["net_revenue"]
            )
            .abs()
            .max()
        ),
    )
    _check(
        results,
        "product gross plus cancellation equals net",
        np.allclose(
            product_net["gross_positive_revenue"] + product_net["cancellation_revenue"],
            product_net["net_revenue"],
        ),
        "max diff="
        + str(
            (
                product_net["gross_positive_revenue"]
                + product_net["cancellation_revenue"]
                - product_net["net_revenue"]
            )
            .abs()
            .max()
        ),
    )

    failures = [result for result in results if not result["pass"]]
    output = {
        "num_checks": len(results),
        "num_failures": len(failures),
        "failures": failures,
        "checks": results,
    }
    print(json.dumps(output, indent=2))

    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
