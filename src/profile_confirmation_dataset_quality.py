from __future__ import annotations

import hashlib
import json
import math
import re
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "confirmation_online_retail_ii" / "online_retail_II.xlsx"
ACQUISITION_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_acquisition_report.json"
STRUCTURE_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_structure_report.json"
LOCAL_DIR = PROJECT_ROOT / "data" / "processed" / "confirmation_online_retail_ii"
STRICT_TABLE_PATH = LOCAL_DIR / "strict_window_lines.csv.gz"
REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_quality_report.json"

WINDOW_START = pd.Timestamp("2009-12-01 00:00:00")
WINDOW_END = pd.Timestamp("2010-12-01 00:00:00")
EXPECTED_STRICT_ROWS = 502_938
EXPECTED_MONTHS = [f"2009-{month:02d}" for month in [12]] + [f"2010-{month:02d}" for month in range(1, 12)]

ACTUAL_HEADERS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
]
RAW_TO_CANONICAL = {
    "Invoice": "InvoiceNo",
    "StockCode": "StockCode",
    "Description": "Description",
    "Quantity": "Quantity",
    "InvoiceDate": "InvoiceDate",
    "Price": "UnitPrice",
    "Customer ID": "CustomerID",
    "Country": "Country",
}
CANONICAL_TO_NORMALIZED = {
    "InvoiceNo": "invoice_no",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_date",
    "UnitPrice": "unit_price",
    "CustomerID": "customer_id",
    "Country": "country",
}
CANONICAL_COLUMNS = list(CANONICAL_TO_NORMALIZED)
NORMALIZED_COLUMNS = list(CANONICAL_TO_NORMALIZED.values())
STRING_COLUMNS = ["InvoiceNo", "StockCode", "Description", "Country"]

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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rounded(value: Any, digits: int = 6) -> float:
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"Expected a finite number, received {value!r}.")
    return round(numeric, digits)


def rate(count: int, total: int) -> float:
    return round(count / total, 8) if total else 0.0


def clean_text(series: pd.Series, collapse_whitespace: bool = False) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    if collapse_whitespace:
        cleaned = cleaned.str.replace(r"\s+", " ", regex=True)
    return cleaned.mask(cleaned.eq(""), pd.NA)


def missing_profile(frame: pd.DataFrame, column: str) -> tuple[dict[str, Any], pd.Series]:
    null_mask = frame[column].isna()
    if column in STRING_COLUMNS:
        blank_mask = (~null_mask) & frame[column].astype("string").str.strip().eq("")
    else:
        blank_mask = pd.Series(False, index=frame.index)
    missing_mask = null_mask | blank_mask
    result = {
        "null_count": int(null_mask.sum()),
        "blank_count": int(blank_mask.sum()),
        "missing_or_blank_count": int(missing_mask.sum()),
        "missing_or_blank_rate": rate(int(missing_mask.sum()), len(frame)),
    }
    return result, missing_mask


def numeric_summary(series: pd.Series) -> dict[str, Any]:
    values = pd.to_numeric(series, errors="coerce").dropna().astype(float)
    quantiles = values.quantile([0.001, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 0.999])
    q1 = float(quantiles.loc[0.25])
    q3 = float(quantiles.loc[0.75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return {
        "non_null_count": int(len(values)),
        "min": rounded(values.min()),
        "p00_1": rounded(quantiles.loc[0.001]),
        "p01": rounded(quantiles.loc[0.01]),
        "p05": rounded(quantiles.loc[0.05]),
        "p25": rounded(q1),
        "p50": rounded(quantiles.loc[0.5]),
        "p75": rounded(q3),
        "p95": rounded(quantiles.loc[0.95]),
        "p99": rounded(quantiles.loc[0.99]),
        "p99_9": rounded(quantiles.loc[0.999]),
        "max": rounded(values.max()),
        "mean": rounded(values.mean()),
        "iqr_lower_fence": rounded(lower),
        "iqr_upper_fence": rounded(upper),
        "outside_iqr_fence_count": int(((values < lower) | (values > upper)).sum()),
        "outside_iqr_fence_rate": rate(int(((values < lower) | (values > upper)).sum()), len(values)),
        "interpretation": "IQR and tail counts are review indicators, not automatic exclusion rules.",
    }


def duplicate_profile(frame: pd.DataFrame, columns: list[str]) -> tuple[dict[str, Any], pd.Series]:
    extra_mask = frame.duplicated(subset=columns, keep="first")
    affected_mask = frame.duplicated(subset=columns, keep=False)
    grouped = frame.loc[affected_mask, columns].value_counts(dropna=False)
    return (
        {
            "columns": columns,
            "duplicate_extra_rows": int(extra_mask.sum()),
            "duplicate_extra_row_rate": rate(int(extra_mask.sum()), len(frame)),
            "duplicate_affected_rows": int(affected_mask.sum()),
            "duplicate_affected_row_rate": rate(int(affected_mask.sum()), len(frame)),
            "duplicated_group_count": int(len(grouped)),
            "max_rows_per_duplicated_group": int(grouped.max()) if len(grouped) else 1,
        },
        extra_mask,
    )


def read_strict_window(structure: dict[str, Any]) -> pd.DataFrame:
    selected_frames: list[pd.DataFrame] = []
    for sheet_name in structure["sheet_names"]:
        frame = pd.read_excel(RAW_PATH, sheet_name=sheet_name, engine="openpyxl")
        if list(frame.columns) != ACTUAL_HEADERS:
            raise RuntimeError(f"Unexpected headers in {sheet_name!r}: {list(frame.columns)!r}")
        parsed_dates = pd.to_datetime(frame["InvoiceDate"], errors="coerce")
        if int(parsed_dates.isna().sum()) != 0:
            raise RuntimeError(f"Worksheet {sheet_name!r} contains invalid InvoiceDate values.")
        selected = frame.loc[(parsed_dates >= WINDOW_START) & (parsed_dates < WINDOW_END)].copy()
        selected["InvoiceDate"] = parsed_dates.loc[selected.index]
        selected.insert(0, "source_row_number", selected.index.to_numpy() + 2)
        selected.insert(0, "source_sheet", sheet_name)
        selected_frames.append(selected)

    strict = pd.concat(selected_frames, ignore_index=True)
    if len(strict) != EXPECTED_STRICT_ROWS:
        raise RuntimeError(f"Strict-window row count is {len(strict):,}, expected {EXPECTED_STRICT_ROWS:,}.")
    observed_min = strict["InvoiceDate"].min()
    observed_max = strict["InvoiceDate"].max()
    if observed_min != pd.Timestamp(structure["date_scan"]["strict_window_date_min"]):
        raise RuntimeError(f"Strict-window minimum date drifted to {observed_min}.")
    if observed_max != pd.Timestamp(structure["date_scan"]["strict_window_date_max"]):
        raise RuntimeError(f"Strict-window maximum date drifted to {observed_max}.")
    return strict


def normalize_frame(strict_raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    canonical = strict_raw.rename(columns=RAW_TO_CANONICAL).copy()
    normalized = canonical.rename(columns=CANONICAL_TO_NORMALIZED).copy()

    normalized["invoice_no"] = clean_text(normalized["invoice_no"])
    normalized["stock_code"] = clean_text(normalized["stock_code"])
    normalized["description"] = clean_text(normalized["description"], collapse_whitespace=True)
    normalized["country"] = clean_text(normalized["country"])
    normalized["invoice_date"] = pd.to_datetime(normalized["invoice_date"], errors="coerce")

    quantity_numeric = pd.to_numeric(normalized["quantity"], errors="coerce")
    unit_price_numeric = pd.to_numeric(normalized["unit_price"], errors="coerce")
    customer_numeric = pd.to_numeric(normalized["customer_id"], errors="coerce")
    quantity_fractional = quantity_numeric.notna() & ~np.isclose(quantity_numeric % 1, 0)
    customer_fractional = customer_numeric.notna() & ~np.isclose(customer_numeric % 1, 0)
    finite_quantity = quantity_numeric.notna() & np.isfinite(quantity_numeric)
    finite_price = unit_price_numeric.notna() & np.isfinite(unit_price_numeric)

    type_conformance = {
        "invalid_invoice_date_rows": int(normalized["invoice_date"].isna().sum()),
        "quantity_numeric_parse_failures": int((normalized["quantity"].notna() & quantity_numeric.isna()).sum()),
        "quantity_nonfinite_rows": int((quantity_numeric.notna() & ~finite_quantity).sum()),
        "quantity_fractional_rows": int(quantity_fractional.sum()),
        "unit_price_numeric_parse_failures": int((normalized["unit_price"].notna() & unit_price_numeric.isna()).sum()),
        "unit_price_nonfinite_rows": int((unit_price_numeric.notna() & ~finite_price).sum()),
        "customer_id_numeric_parse_failures": int((normalized["customer_id"].notna() & customer_numeric.isna()).sum()),
        "customer_id_fractional_rows": int(customer_fractional.sum()),
    }
    if any(type_conformance.values()):
        raise RuntimeError(f"Canonical type conformance failed: {type_conformance}")

    normalized["quantity"] = quantity_numeric.astype("Int64")
    normalized["unit_price"] = unit_price_numeric.astype(float)
    normalized["customer_id"] = customer_numeric.astype("Int64")
    normalized["year_month"] = normalized["invoice_date"].dt.to_period("M").astype(str)
    normalized["line_revenue"] = normalized["quantity"].astype(float) * normalized["unit_price"]
    return normalized, type_conformance


def build_monthly_profile(
    frame: pd.DataFrame,
    missing_masks: dict[str, pd.Series],
) -> list[dict[str, Any]]:
    monthly: list[dict[str, Any]] = []
    for year_month in EXPECTED_MONTHS:
        month_mask = frame["year_month"].eq(year_month)
        month = frame.loc[month_mask]
        valid_net = month.loc[month["is_valid_net_revenue_line"]]
        gross = float(valid_net.loc[valid_net["line_revenue"] > 0, "line_revenue"].sum())
        negative = float(valid_net.loc[valid_net["line_revenue"] < 0, "line_revenue"].sum())
        net = float(valid_net["line_revenue"].sum())
        monthly.append(
            {
                "year_month": year_month,
                "row_count": int(len(month)),
                "first_invoice_datetime": str(month["invoice_date"].min()),
                "last_invoice_datetime": str(month["invoice_date"].max()),
                "transaction_day_count": int(month["invoice_date"].dt.date.nunique()),
                "invoice_count": int(month["invoice_no"].nunique(dropna=True)),
                "customer_count": int(month["customer_id"].nunique(dropna=True)),
                "stock_code_count": int(month["stock_code"].nunique(dropna=True)),
                "country_count": int(month["country"].nunique(dropna=True)),
                "cancel_invoice_row_count": int(month["is_cancel_invoice"].sum()),
                "negative_quantity_row_count": int(month["is_negative_quantity"].sum()),
                "exact_duplicate_extra_row_count": int(month["is_exact_duplicate"].sum()),
                "nonpositive_unit_price_row_count": int(month["is_nonpositive_unit_price"].sum()),
                "missing_description_row_count": int(month["is_missing_description"].sum()),
                "non_merchandise_row_count": int(month["is_non_merchandise"].sum()),
                "valid_net_revenue_line_count": int(len(valid_net)),
                "gross_positive_revenue": rounded(gross, 2),
                "negative_revenue": rounded(negative, 2),
                "net_revenue": rounded(net, 2),
                "reconciliation_difference": rounded(gross + negative - net, 6),
                "missing_or_blank_by_column": {
                    column: int((missing_mask & month_mask).sum())
                    for column, missing_mask in missing_masks.items()
                },
            }
        )
    return monthly


def main() -> None:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Missing local workbook: {RAW_PATH}")
    if not ACQUISITION_PATH.exists() or not STRUCTURE_PATH.exists():
        raise FileNotFoundError("Acquisition and structure reports must exist before quality profiling.")

    acquisition = load_json(ACQUISITION_PATH)
    structure = load_json(STRUCTURE_PATH)
    if sha256_file(RAW_PATH) != acquisition["raw_artifacts"]["xlsx"]["sha256"]:
        raise RuntimeError("Local workbook SHA-256 does not match the acquisition report.")

    started = time.perf_counter()
    strict_raw = read_strict_window(structure)
    strict_canonical = strict_raw.rename(columns=RAW_TO_CANONICAL).copy()
    normalized, type_conformance = normalize_frame(strict_raw)

    completeness: dict[str, dict[str, Any]] = {}
    missing_masks: dict[str, pd.Series] = {}
    for column in CANONICAL_COLUMNS:
        completeness[column], missing_masks[column] = missing_profile(strict_canonical, column)

    raw_exact_profile, _ = duplicate_profile(strict_canonical, CANONICAL_COLUMNS)
    normalized_exact_profile, exact_duplicate_extra_mask = duplicate_profile(normalized, NORMALIZED_COLUMNS)
    invoice_stock_profile, _ = duplicate_profile(normalized, ["invoice_no", "stock_code"])

    normalized["is_exact_duplicate"] = exact_duplicate_extra_mask
    normalized["is_cancel_invoice"] = normalized["invoice_no"].fillna("").str.upper().str.startswith("C")
    normalized["is_negative_quantity"] = normalized["quantity"] < 0
    normalized["is_zero_quantity"] = normalized["quantity"] == 0
    normalized["is_nonpositive_unit_price"] = normalized["unit_price"] <= 0
    normalized["is_missing_description"] = normalized["description"].isna()
    normalized["has_no_digit_stock_code"] = ~normalized["stock_code"].fillna("").str.contains(r"\d", regex=True)
    normalized["is_non_merchandise"] = (
        normalized["stock_code"].fillna("").str.upper().isin(NON_MERCHANDISE_STOCK_CODES)
        | normalized["has_no_digit_stock_code"]
    )

    normalized["is_positive_sales_line"] = (
        ~normalized["is_exact_duplicate"]
        & ~normalized["is_cancel_invoice"]
        & (normalized["quantity"] > 0)
        & (normalized["unit_price"] > 0)
        & ~normalized["is_missing_description"]
    )
    normalized["is_valid_net_revenue_line"] = (
        ~normalized["is_exact_duplicate"]
        & (normalized["unit_price"] > 0)
        & ~normalized["is_missing_description"]
    )
    normalized["is_merchandise_net_revenue_line"] = (
        normalized["is_valid_net_revenue_line"] & ~normalized["is_non_merchandise"]
    )
    normalized["is_cancellation_or_return_line"] = (
        (normalized["is_cancel_invoice"] | normalized["is_negative_quantity"])
        & ~normalized["is_exact_duplicate"]
    )

    valid_net = normalized.loc[normalized["is_valid_net_revenue_line"]]
    merchandise_net = normalized.loc[normalized["is_merchandise_net_revenue_line"]]
    positive_sales = normalized.loc[normalized["is_positive_sales_line"]]
    gross_positive = float(valid_net.loc[valid_net["line_revenue"] > 0, "line_revenue"].sum())
    negative_revenue = float(valid_net.loc[valid_net["line_revenue"] < 0, "line_revenue"].sum())
    net_revenue = float(valid_net["line_revenue"].sum())

    prefix = normalized["is_cancel_invoice"]
    negative_quantity = normalized["is_negative_quantity"]
    cancellation_crosscheck = {
        "cancel_prefix_and_negative_quantity": int((prefix & negative_quantity).sum()),
        "cancel_prefix_and_nonnegative_quantity": int((prefix & ~negative_quantity).sum()),
        "no_cancel_prefix_and_negative_quantity": int((~prefix & negative_quantity).sum()),
        "neither_cancel_prefix_nor_negative_quantity": int((~prefix & ~negative_quantity).sum()),
    }

    monthly = build_monthly_profile(normalized, missing_masks)
    observed_months = [item["year_month"] for item in monthly if item["row_count"] > 0]

    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    local_columns = [
        "source_sheet",
        "source_row_number",
        "invoice_no",
        "stock_code",
        "description",
        "quantity",
        "invoice_date",
        "unit_price",
        "customer_id",
        "country",
        "year_month",
        "line_revenue",
        "is_exact_duplicate",
        "is_cancel_invoice",
        "is_negative_quantity",
        "is_zero_quantity",
        "is_nonpositive_unit_price",
        "is_missing_description",
        "is_non_merchandise",
        "is_positive_sales_line",
        "is_valid_net_revenue_line",
        "is_merchandise_net_revenue_line",
        "is_cancellation_or_return_line",
    ]
    normalized[local_columns].to_csv(
        STRICT_TABLE_PATH,
        index=False,
        compression={"method": "gzip", "compresslevel": 9, "mtime": 0},
        date_format="%Y-%m-%d %H:%M:%S",
        float_format="%.6f",
        lineterminator="\n",
    )

    critical_checks = {
        "strict_row_count_matches_structure_report": len(normalized) == EXPECTED_STRICT_ROWS,
        "strict_dates_inside_frozen_window": bool(
            normalized["invoice_date"].ge(WINDOW_START).all()
            and normalized["invoice_date"].lt(WINDOW_END).all()
        ),
        "all_expected_months_present": observed_months == EXPECTED_MONTHS,
        "core_transaction_fields_complete": all(
            completeness[column]["missing_or_blank_count"] == 0
            for column in ["InvoiceNo", "StockCode", "Quantity", "InvoiceDate", "UnitPrice", "Country"]
        ),
        "canonical_types_conform": not any(type_conformance.values()),
        "monthly_rows_reconcile_to_strict_rows": sum(item["row_count"] for item in monthly) == len(normalized),
        "monthly_net_revenue_reconciles": abs(
            sum(item["net_revenue"] for item in monthly) - round(net_revenue, 2)
        ) <= 0.02,
        "gross_plus_negative_equals_net": abs(gross_positive + negative_revenue - net_revenue) < 1e-6,
        "local_table_created_and_nonempty": STRICT_TABLE_PATH.exists() and STRICT_TABLE_PATH.stat().st_size > 0,
    }
    failed_checks = [name for name, passed in critical_checks.items() if not passed]

    findings = [
        {
            "finding_id": "optional_customer_id_missingness",
            "severity": "medium",
            "confidence": "high",
            "evidence": completeness["CustomerID"],
            "analytical_risk": "Customer-level questions and customer-count comparisons may be biased if missing IDs are treated as observed customers.",
            "control": "Keep CustomerID optional for aggregate month, country, product, and cancellation analyses; prohibit customer-level confirmation questions until a separate coverage rule is frozen.",
        },
        {
            "finding_id": "missing_product_descriptions",
            "severity": "medium",
            "confidence": "high",
            "evidence": completeness["Description"],
            "analytical_risk": "Rows without descriptions cannot support auditable product-name claims.",
            "control": "Exclude missing-description rows from product and valid-net evidence while retaining their counts in the quality report.",
        },
        {
            "finding_id": "exact_duplicate_source_rows",
            "severity": "medium",
            "confidence": "high",
            "evidence": normalized_exact_profile,
            "analytical_risk": "Uncontrolled duplicates would overstate quantities, gross revenue, cancellation impact, and ranking values.",
            "control": "Use first-occurrence exact-row deduplication on the eight normalized canonical fields before revenue aggregation.",
        },
        {
            "finding_id": "cancellation_encoding_is_not_prefix_complete",
            "severity": "medium",
            "confidence": "high",
            "evidence": cancellation_crosscheck,
            "analytical_risk": "Using only InvoiceNo prefix C would miss negative-quantity adjustments or returns.",
            "control": "Retain negative quantities in net revenue and define cancellation/return review rows as cancel-prefix OR negative-quantity after exact deduplication.",
        },
        {
            "finding_id": "nonpositive_prices_require_control",
            "severity": "medium",
            "confidence": "high",
            "evidence": {
                "negative_unit_price_rows": int((normalized["unit_price"] < 0).sum()),
                "zero_unit_price_rows": int((normalized["unit_price"] == 0).sum()),
            },
            "analytical_risk": "Nonpositive prices do not represent ordinary merchandise revenue and can distort value-based questions.",
            "control": "Require UnitPrice > 0 for positive-sales and valid-net evidence; retain excluded-row counts for auditability.",
        },
        {
            "finding_id": "long_tailed_numeric_values",
            "severity": "low",
            "confidence": "high",
            "evidence": "Quantity, UnitPrice, and line revenue tail profiles are reported with robust IQR indicators.",
            "analytical_risk": "Large legitimate wholesale orders and manual adjustments can dominate rankings; automatic outlier deletion would create outcome-dependent filtering.",
            "control": "Do not remove tail values automatically. Review only evidence contexts selected by frozen, outcome-blind rules.",
        },
    ]

    report = {
        "schema_version": "1.0",
        "status": "quality_profile_complete_with_documented_controls" if not failed_checks else "quality_profile_failed",
        "study_name": "Confirmation Set v1",
        "candidate_id": "uci_online_retail_ii_prior_period",
        "profile_scope": "strict-window completeness, normalized duplicates and grain, business-rule validity, cancellation consistency, numeric tails, and monthly coverage",
        "explicitly_not_in_scope": [
            "historical overlap against the current Online Retail lineage",
            "36-context feasibility or split assignment",
            "question, prompt, model, annotation, verifier, or detector generation",
        ],
        "source": {
            "workbook_path": repo_path(RAW_PATH),
            "workbook_sha256": acquisition["raw_artifacts"]["xlsx"]["sha256"],
            "acquisition_report_path": repo_path(ACQUISITION_PATH),
            "structure_report_path": repo_path(STRUCTURE_PATH),
            "window_start_inclusive": WINDOW_START.isoformat(),
            "window_end_exclusive": WINDOW_END.isoformat(),
            "strict_window_row_count": int(len(normalized)),
            "strict_window_date_min": str(normalized["invoice_date"].min()),
            "strict_window_date_max": str(normalized["invoice_date"].max()),
            "month_count": len(observed_months),
            "months": observed_months,
        },
        "local_strict_table": {
            "path": repo_path(STRICT_TABLE_PATH),
            "format": "gzip-compressed CSV",
            "row_count": int(len(normalized)),
            "column_count": len(local_columns),
            "columns": local_columns,
            "size_bytes": STRICT_TABLE_PATH.stat().st_size,
            "sha256": sha256_file(STRICT_TABLE_PATH),
            "contains_source_invoice_and_customer_identifiers": True,
            "git_ignored_and_local_only": True,
        },
        "schema": {
            "raw_headers": ACTUAL_HEADERS,
            "raw_to_canonical": RAW_TO_CANONICAL,
            "canonical_to_normalized": CANONICAL_TO_NORMALIZED,
            "type_conformance": type_conformance,
            "normalized_dtypes": {column: str(normalized[column].dtype) for column in NORMALIZED_COLUMNS},
            "intended_analytical_grain": "one normalized source invoice-line row before exact-row deduplication",
            "stable_source_primary_key_available": False,
            "local_lineage_key": ["source_sheet", "source_row_number"],
        },
        "completeness": {
            "row_count": int(len(normalized)),
            "by_column": completeness,
            "customer_id_is_optional_for_aggregate_questions": True,
            "description_required_for_product_and_valid_net_evidence": True,
        },
        "cardinality": {
            "invoice_count": int(normalized["invoice_no"].nunique(dropna=True)),
            "stock_code_count": int(normalized["stock_code"].nunique(dropna=True)),
            "description_count": int(normalized["description"].nunique(dropna=True)),
            "customer_count": int(normalized["customer_id"].nunique(dropna=True)),
            "country_count": int(normalized["country"].nunique(dropna=True)),
        },
        "duplicates_and_grain": {
            "raw_exact_row_profile": raw_exact_profile,
            "normalized_exact_row_profile": normalized_exact_profile,
            "invoice_stock_candidate_key_profile": invoice_stock_profile,
            "grain_decision": "InvoiceNo plus StockCode is not unique. Preserve source-row grain locally and remove only repeated normalized exact rows before aggregation.",
        },
        "business_rules": {
            "quantity_sign_counts": {
                "negative": int((normalized["quantity"] < 0).sum()),
                "zero": int((normalized["quantity"] == 0).sum()),
                "positive": int((normalized["quantity"] > 0).sum()),
            },
            "unit_price_sign_counts": {
                "negative": int((normalized["unit_price"] < 0).sum()),
                "zero": int((normalized["unit_price"] == 0).sum()),
                "positive": int((normalized["unit_price"] > 0).sum()),
            },
            "line_revenue_sign_counts": {
                "negative": int((normalized["line_revenue"] < 0).sum()),
                "zero": int((normalized["line_revenue"] == 0).sum()),
                "positive": int((normalized["line_revenue"] > 0).sum()),
            },
            "cancel_invoice_row_count": int(prefix.sum()),
            "negative_quantity_row_count": int(negative_quantity.sum()),
            "cancellation_prefix_crosscheck": cancellation_crosscheck,
            "non_merchandise_row_count": int(normalized["is_non_merchandise"].sum()),
            "cancellation_or_return_rows_after_exact_dedup": int(normalized["is_cancellation_or_return_line"].sum()),
            "numeric_profiles": {
                "quantity": numeric_summary(normalized["quantity"]),
                "absolute_quantity": numeric_summary(normalized["quantity"].abs()),
                "unit_price": numeric_summary(normalized["unit_price"]),
                "line_revenue": numeric_summary(normalized["line_revenue"]),
            },
        },
        "analysis_policy_reconciliation": {
            "positive_sales_line_count": int(len(positive_sales)),
            "positive_sales_revenue": rounded(positive_sales["line_revenue"].sum(), 2),
            "valid_net_revenue_line_count": int(len(valid_net)),
            "gross_positive_revenue": rounded(gross_positive, 2),
            "negative_revenue": rounded(negative_revenue, 2),
            "net_revenue": rounded(net_revenue, 2),
            "gross_plus_negative_minus_net": rounded(gross_positive + negative_revenue - net_revenue, 6),
            "merchandise_net_revenue_line_count": int(len(merchandise_net)),
            "merchandise_net_revenue": rounded(merchandise_net["line_revenue"].sum(), 2),
            "policy": {
                "exact_duplicate": "keep first normalized exact row across the eight canonical business fields",
                "positive_sales": "deduplicated, no cancel prefix, Quantity > 0, UnitPrice > 0, Description present",
                "valid_net_revenue": "deduplicated, UnitPrice > 0, Description present; negative quantities and cancel invoices retained",
                "merchandise_net_revenue": "valid net revenue plus the existing no-digit and special stock-code exclusion",
            },
        },
        "monthly_coverage": {
            "expected_months": EXPECTED_MONTHS,
            "observed_months": observed_months,
            "month_count": len(observed_months),
            "all_expected_months_present": observed_months == EXPECTED_MONTHS,
            "rows_reconciled": sum(item["row_count"] for item in monthly),
            "months": monthly,
        },
        "quality_findings": findings,
        "critical_checks": critical_checks,
        "failed_critical_checks": failed_checks,
        "quality_decision": (
            "conditionally_suitable_for_aggregate_business_analysis_after_documented_controls"
            if not failed_checks
            else "not_suitable_until_critical_failures_are_resolved"
        ),
        "quality_profile_complete": not failed_checks,
        "historical_overlap_check_complete": False,
        "context_feasibility_check_complete": False,
        "context_manifest_created": False,
        "prompt_created": False,
        "model_run_performed": False,
        "new_metrics_reported": False,
        "execution_ready": False,
        "no_new_results": True,
        "public_report_contains_raw_identifier_values": False,
        "next_authorized_action": "Run only the normalized record-overlap proof against the current Online Retail lineage; do not generate contexts or prompts yet.",
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "strict_window_row_count": len(normalized),
                "month_count": len(observed_months),
                "missing_customer_id": completeness["CustomerID"]["missing_or_blank_count"],
                "missing_description": completeness["Description"]["missing_or_blank_count"],
                "normalized_duplicate_extra_rows": normalized_exact_profile["duplicate_extra_rows"],
                "cancel_invoice_rows": int(prefix.sum()),
                "negative_quantity_rows": int(negative_quantity.sum()),
                "net_revenue": report["analysis_policy_reconciliation"]["net_revenue"],
                "failed_critical_checks": failed_checks,
                "local_table_sha256": report["local_strict_table"]["sha256"],
                "elapsed_seconds": round(time.perf_counter() - started, 3),
                "report_path": repo_path(REPORT_PATH),
            },
            indent=2,
            ensure_ascii=True,
        )
    )
    if failed_checks:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
