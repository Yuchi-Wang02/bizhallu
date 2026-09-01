from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import contains_local_path, repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUALITY_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_quality_report.json"
HTML_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_quality.html"
VALIDATION_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_quality_validation.json"
STRICT_TABLE_PATH = (
    PROJECT_ROOT / "data" / "processed" / "confirmation_online_retail_ii" / "strict_window_lines.csv.gz"
)
LOCAL_VALIDATION_PATH = STRICT_TABLE_PATH.parent / "local_quality_validation.json"
PREFLIGHT_PATH = PROJECT_ROOT / "results" / "full100_preflight_report.json"

EXPECTED_TABLE_SIZE = 10_959_387
EXPECTED_TABLE_SHA256 = "ab875caaf527d5d528f4edad4fd372b15d4e1ae9c39f6cea20f8211178e256fc"
EXPECTED_COLUMNS = [
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
EXPECTED_COMPLETENESS = {
    "InvoiceNo": 0,
    "StockCode": 0,
    "Description": 2_821,
    "Quantity": 0,
    "InvoiceDate": 0,
    "UnitPrice": 0,
    "CustomerID": 100_207,
    "Country": 0,
}
EXPECTED_CARDINALITY = {
    "invoice_count": 27_728,
    "stock_code_count": 4_621,
    "description_count": 4_624,
    "customer_count": 4_336,
    "country_count": 40,
}
EXPECTED_MONTHS = {
    "2009-12": (45_228, 796_648.50),
    "2010-01": (31_555, 622_479.50),
    "2010-02": (29_388, 531_265.37),
    "2010-03": (41_511, 763_247.24),
    "2010-04": (34_057, 641_521.05),
    "2010-05": (35_323, 613_270.72),
    "2010-06": (39_983, 677_073.87),
    "2010-07": (33_383, 617_365.48),
    "2010-08": (33_306, 654_774.39),
    "2010-09": (42_091, 851_105.96),
    "2010-10": (59_098, 1_080_611.48),
    "2010-11": (78_015, 1_416_697.20),
}

REQUIRED_HTML_FRAGMENTS = [
    "BizHallu Confirmation Dataset Quality Profile",
    "The prior-period window is usable only after explicit controls.",
    "502,938",
    "19.92%",
    "1.30%",
    "GBP 9,266,060.76",
    "The dataset gate is still pending.",
    "InvoiceNo + StockCode",
    "Negative quantity is broader than the invoice-prefix signal.",
    "Every frozen month is present and reconciled.",
    "No current-source overlap comparison was performed in this step.",
    "No prompt, Qwen answer, annotation target, verifier output, or detector metric was created.",
    "overflow-x:auto;",
    "overflow-wrap:anywhere;",
]
FORBIDDEN_HTML_FRAGMENTS = [
    "production-ready",
    "dataset gate passed",
    "confirmation AUPRC",
    "confirmation F1",
    "new detector metric",
    "clamp(",
]


class StructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tag_counts: dict[str, int] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_failure(failures: list[dict[str, Any]], name: str, detail: Any) -> None:
    failures.append({"name": name, "detail": detail})


def close(left: float, right: float, tolerance: float = 0.02) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def validate_local_table() -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    if not STRICT_TABLE_PATH.exists():
        add_failure(failures, "local_table_missing", repo_path(STRICT_TABLE_PATH))
        result = {
            "status": "local_quality_validation_failed",
            "num_failures": len(failures),
            "failures": failures,
        }
        STRICT_TABLE_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_VALIDATION_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
        return result

    observed = {
        "path": repo_path(STRICT_TABLE_PATH),
        "size_bytes": STRICT_TABLE_PATH.stat().st_size,
        "sha256": sha256_file(STRICT_TABLE_PATH),
        "header": [],
        "row_count": 0,
        "date_min": None,
        "date_max": None,
        "source_sheet_counts": {},
        "missing_description_rows": 0,
        "missing_customer_id_rows": 0,
        "exact_duplicate_extra_rows": 0,
        "cancel_invoice_rows": 0,
        "negative_quantity_rows": 0,
        "nonpositive_unit_price_rows": 0,
        "valid_net_revenue_line_count": 0,
        "gross_positive_revenue": 0.0,
        "negative_revenue": 0.0,
        "net_revenue": 0.0,
    }
    with gzip.open(STRICT_TABLE_PATH, mode="rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        observed["header"] = reader.fieldnames or []
        for row in reader:
            observed["row_count"] += 1
            invoice_date = row["invoice_date"]
            observed["date_min"] = invoice_date if observed["date_min"] is None else min(observed["date_min"], invoice_date)
            observed["date_max"] = invoice_date if observed["date_max"] is None else max(observed["date_max"], invoice_date)
            source_sheet = row["source_sheet"]
            observed["source_sheet_counts"][source_sheet] = observed["source_sheet_counts"].get(source_sheet, 0) + 1
            observed["missing_description_rows"] += row["description"] == ""
            observed["missing_customer_id_rows"] += row["customer_id"] == ""
            observed["exact_duplicate_extra_rows"] += row["is_exact_duplicate"] == "True"
            observed["cancel_invoice_rows"] += row["is_cancel_invoice"] == "True"
            observed["negative_quantity_rows"] += row["is_negative_quantity"] == "True"
            observed["nonpositive_unit_price_rows"] += row["is_nonpositive_unit_price"] == "True"
            if row["is_valid_net_revenue_line"] == "True":
                revenue = float(row["line_revenue"])
                observed["valid_net_revenue_line_count"] += 1
                observed["net_revenue"] += revenue
                if revenue > 0:
                    observed["gross_positive_revenue"] += revenue
                elif revenue < 0:
                    observed["negative_revenue"] += revenue

    for key in ["gross_positive_revenue", "negative_revenue", "net_revenue"]:
        observed[key] = round(observed[key], 2)

    expected = {
        "size_bytes": EXPECTED_TABLE_SIZE,
        "sha256": EXPECTED_TABLE_SHA256,
        "header": EXPECTED_COLUMNS,
        "row_count": 502_938,
        "date_min": "2009-12-01 07:45:00",
        "date_max": "2010-11-30 19:35:00",
        "source_sheet_counts": {"Year 2009-2010": 502_938},
        "missing_description_rows": 2_821,
        "missing_customer_id_rows": 100_207,
        "exact_duplicate_extra_rows": 6_544,
        "cancel_invoice_rows": 9_877,
        "negative_quantity_rows": 11_933,
        "nonpositive_unit_price_rows": 3_512,
        "valid_net_revenue_line_count": 492_887,
        "gross_positive_revenue": 9_834_505.21,
        "negative_revenue": -568_444.45,
        "net_revenue": 9_266_060.76,
    }
    for key, expected_value in expected.items():
        if observed.get(key) != expected_value:
            add_failure(
                failures,
                "local_table_value",
                {"field": key, "expected": expected_value, "actual": observed.get(key)},
            )
    result = {
        "status": "local_quality_validation_passed" if not failures else "local_quality_validation_failed",
        "observed": observed,
        "num_failures": len(failures),
        "failures": failures,
    }
    LOCAL_VALIDATION_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the Confirmation Dataset strict-window quality profile.")
    parser.add_argument(
        "--require-local",
        action="store_true",
        help="Independently scan the ignored local strict-window table.",
    )
    args = parser.parse_args()
    failures: list[dict[str, Any]] = []

    for path in [QUALITY_PATH, HTML_PATH, PREFLIGHT_PATH]:
        if not path.exists():
            add_failure(failures, "required_artifact_missing", repo_path(path))

    report = load_json(QUALITY_PATH) if QUALITY_PATH.exists() else {}
    preflight = load_json(PREFLIGHT_PATH) if PREFLIGHT_PATH.exists() else {}
    html_text = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""

    if report and contains_local_path(json.dumps(report, ensure_ascii=True)):
        add_failure(failures, "local_absolute_path_in_quality_json", repo_path(QUALITY_PATH))
    if html_text and contains_local_path(html_text):
        add_failure(failures, "local_absolute_path_in_quality_html", repo_path(HTML_PATH))

    expected_boundary = {
        "schema_version": "1.0",
        "status": "quality_profile_complete_with_documented_controls",
        "study_name": "Confirmation Set v1",
        "candidate_id": "uci_online_retail_ii_prior_period",
        "quality_decision": "conditionally_suitable_for_aggregate_business_analysis_after_documented_controls",
        "quality_profile_complete": True,
        "historical_overlap_check_complete": False,
        "context_feasibility_check_complete": False,
        "context_manifest_created": False,
        "prompt_created": False,
        "model_run_performed": False,
        "new_metrics_reported": False,
        "execution_ready": False,
        "no_new_results": True,
        "public_report_contains_raw_identifier_values": False,
    }
    for key, expected in expected_boundary.items():
        if report.get(key) != expected:
            add_failure(failures, "quality_boundary", {"field": key, "expected": expected, "actual": report.get(key)})

    source = report.get("source", {})
    expected_source = {
        "workbook_sha256": "bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980",
        "window_start_inclusive": "2009-12-01T00:00:00",
        "window_end_exclusive": "2010-12-01T00:00:00",
        "strict_window_row_count": 502_938,
        "strict_window_date_min": "2009-12-01 07:45:00",
        "strict_window_date_max": "2010-11-30 19:35:00",
        "month_count": 12,
        "months": list(EXPECTED_MONTHS),
    }
    for key, expected in expected_source.items():
        if source.get(key) != expected:
            add_failure(failures, "source_value", {"field": key, "expected": expected, "actual": source.get(key)})

    local_table = report.get("local_strict_table", {})
    expected_table = {
        "path": "data/processed/confirmation_online_retail_ii/strict_window_lines.csv.gz",
        "format": "gzip-compressed CSV",
        "row_count": 502_938,
        "column_count": 23,
        "columns": EXPECTED_COLUMNS,
        "size_bytes": EXPECTED_TABLE_SIZE,
        "sha256": EXPECTED_TABLE_SHA256,
        "contains_source_invoice_and_customer_identifiers": True,
        "git_ignored_and_local_only": True,
    }
    if local_table != expected_table:
        add_failure(failures, "local_table_manifest", local_table)

    completeness = report.get("completeness", {}).get("by_column", {})
    for column, expected_count in EXPECTED_COMPLETENESS.items():
        values = completeness.get(column, {})
        if values.get("missing_or_blank_count") != expected_count:
            add_failure(
                failures,
                "completeness_count",
                {"column": column, "expected": expected_count, "actual": values.get("missing_or_blank_count")},
            )
        if values.get("missing_or_blank_rate") != round(expected_count / 502_938, 8):
            add_failure(failures, "completeness_rate", {"column": column, "values": values})

    if report.get("cardinality") != EXPECTED_CARDINALITY:
        add_failure(failures, "cardinality", report.get("cardinality"))

    duplicate_expected = {
        "raw_exact_row_profile": (6_544, 12_666, 6_122, 6),
        "normalized_exact_row_profile": (6_544, 12_666, 6_122, 6),
        "invoice_stock_candidate_key_profile": (12_740, 24_280, 11_540, 10),
    }
    duplicate_report = report.get("duplicates_and_grain", {})
    for key, expected in duplicate_expected.items():
        values = duplicate_report.get(key, {})
        observed = (
            values.get("duplicate_extra_rows"),
            values.get("duplicate_affected_rows"),
            values.get("duplicated_group_count"),
            values.get("max_rows_per_duplicated_group"),
        )
        if observed != expected:
            add_failure(failures, "duplicate_profile", {"profile": key, "expected": expected, "actual": observed})

    business = report.get("business_rules", {})
    expected_business = {
        "quantity_sign_counts": {"negative": 11_933, "zero": 0, "positive": 491_005},
        "unit_price_sign_counts": {"negative": 3, "zero": 3_509, "positive": 499_426},
        "line_revenue_sign_counts": {"negative": 9_879, "zero": 3_509, "positive": 489_550},
        "cancel_invoice_row_count": 9_877,
        "negative_quantity_row_count": 11_933,
        "cancellation_prefix_crosscheck": {
            "cancel_prefix_and_negative_quantity": 9_876,
            "cancel_prefix_and_nonnegative_quantity": 1,
            "no_cancel_prefix_and_negative_quantity": 2_057,
            "neither_cancel_prefix_nor_negative_quantity": 491_004,
        },
        "non_merchandise_row_count": 2_820,
        "cancellation_or_return_rows_after_exact_dedup": 11_910,
    }
    for key, expected in expected_business.items():
        if business.get(key) != expected:
            add_failure(failures, "business_rule_value", {"field": key, "expected": expected, "actual": business.get(key)})

    reconciliation = report.get("analysis_policy_reconciliation", {})
    expected_reconciliation = {
        "positive_sales_line_count": 483_034,
        "positive_sales_revenue": 9_834_131.64,
        "valid_net_revenue_line_count": 492_887,
        "gross_positive_revenue": 9_834_505.21,
        "negative_revenue": -568_444.45,
        "net_revenue": 9_266_060.76,
        "gross_plus_negative_minus_net": 0.0,
        "merchandise_net_revenue_line_count": 490_093,
        "merchandise_net_revenue": 9_157_800.84,
    }
    for key, expected in expected_reconciliation.items():
        if not close(reconciliation.get(key, float("nan")), expected):
            add_failure(
                failures,
                "reconciliation_value",
                {"field": key, "expected": expected, "actual": reconciliation.get(key)},
            )
    if not close(
        reconciliation.get("gross_positive_revenue", 0) + reconciliation.get("negative_revenue", 0),
        reconciliation.get("net_revenue", 0),
        tolerance=0.000001,
    ):
        add_failure(failures, "gross_negative_net_reconciliation", reconciliation)

    months = report.get("monthly_coverage", {}).get("months", [])
    observed_months = {item.get("year_month"): item for item in months}
    if set(observed_months) != set(EXPECTED_MONTHS):
        add_failure(failures, "monthly_keys", sorted(observed_months))
    for year_month, (expected_rows, expected_net) in EXPECTED_MONTHS.items():
        item = observed_months.get(year_month, {})
        if item.get("row_count") != expected_rows or not close(item.get("net_revenue", float("nan")), expected_net):
            add_failure(
                failures,
                "monthly_value",
                {"month": year_month, "expected": [expected_rows, expected_net], "actual": item},
            )
        if not close(
            item.get("gross_positive_revenue", 0) + item.get("negative_revenue", 0),
            item.get("net_revenue", 0),
            tolerance=0.02,
        ):
            add_failure(failures, "monthly_reconciliation", item)
    if sum(item.get("row_count", 0) for item in months) != 502_938:
        add_failure(failures, "monthly_row_reconciliation", months)
    for column, expected_count in EXPECTED_COMPLETENESS.items():
        monthly_missing = sum(item.get("missing_or_blank_by_column", {}).get(column, 0) for item in months)
        if monthly_missing != expected_count:
            add_failure(
                failures,
                "monthly_missingness_reconciliation",
                {"column": column, "expected": expected_count, "actual": monthly_missing},
            )

    checks = report.get("critical_checks", {})
    if len(checks) != 9 or not all(checks.values()) or report.get("failed_critical_checks") != []:
        add_failure(failures, "critical_checks", {"checks": checks, "failed": report.get("failed_critical_checks")})
    if len(report.get("quality_findings", [])) != 6:
        add_failure(failures, "quality_finding_count", len(report.get("quality_findings", [])))

    if preflight:
        locked = {
            "questions": preflight.get("full100_question_count"),
            "spans": preflight.get("full100_annotation_draft", {}).get("span_count"),
            "test_spans": preflight.get("full100_detector_scores", {}).get("split_counts", {}).get("test"),
            "auprc": preflight.get("full100_simple_split_metrics", {}).get("best_test_by_auprc", {}).get("auprc"),
            "f1": preflight.get("full100_simple_split_metrics", {}).get("best_test_by_f1", {}).get("f1"),
        }
        expected_locked = {"questions": 100, "spans": 205, "test_spans": 103, "auprc": 0.835073, "f1": 0.779412}
        if locked != expected_locked:
            add_failure(failures, "locked_exploratory_results", locked)

    if html_text:
        parser_state = StructureParser()
        parser_state.feed(html_text)
        for fragment in REQUIRED_HTML_FRAGMENTS:
            if fragment not in html_text:
                add_failure(failures, "required_html_fragment", fragment)
        for fragment in FORBIDDEN_HTML_FRAGMENTS:
            if fragment.lower() in html_text.lower():
                add_failure(failures, "forbidden_html_fragment", fragment)
        if parser_state.tag_counts.get("section", 0) != 9:
            add_failure(failures, "html_section_count", parser_state.tag_counts.get("section", 0))
        if parser_state.tag_counts.get("table", 0) != 5:
            add_failure(failures, "html_table_count", parser_state.tag_counts.get("table", 0))
        if parser_state.tag_counts.get("article", 0) != 6:
            add_failure(failures, "html_finding_count", parser_state.tag_counts.get("article", 0))

    public_validation = {
        "status": "confirmation_dataset_quality_validation_passed" if not failures else "confirmation_dataset_quality_validation_failed",
        "quality_report_path": repo_path(QUALITY_PATH),
        "quality_html_path": repo_path(HTML_PATH),
        "candidate_id": report.get("candidate_id"),
        "strict_window_row_count": source.get("strict_window_row_count"),
        "month_count": source.get("month_count"),
        "quality_decision": report.get("quality_decision"),
        "historical_overlap_check_complete": report.get("historical_overlap_check_complete"),
        "context_feasibility_check_complete": report.get("context_feasibility_check_complete"),
        "execution_ready": False,
        "no_new_results": True,
        "local_artifact_verification_command": "python src/validate_confirmation_dataset_quality.py --require-local",
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(public_validation, indent=2, ensure_ascii=True), encoding="utf-8")

    local_validation = validate_local_table() if args.require_local else None
    print(json.dumps({"public_validation": public_validation, "local_validation": local_validation}, indent=2, ensure_ascii=True))
    if failures or (local_validation and local_validation["num_failures"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
