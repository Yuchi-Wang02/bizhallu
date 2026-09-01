from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any

from public_paths import contains_local_path, repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "confirmation_online_retail_ii"
ZIP_PATH = RAW_DIR / "online_retail_ii.zip"
XLSX_PATH = RAW_DIR / "online_retail_II.xlsx"
LOCAL_VALIDATION_PATH = RAW_DIR / "local_acquisition_validation.json"

ACQUISITION_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_acquisition_report.json"
STRUCTURE_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_structure_report.json"
AUDIT_PATH = PROJECT_ROOT / "configs" / "confirmation_dataset_source_audit_v1.json"
PROTOCOL_PATH = PROJECT_ROOT / "configs" / "confirmation_set_v1_protocol.json"
FEASIBILITY_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility_report.json"
VALIDATION_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_acquisition_validation.json"

EXPECTED_ZIP_SIZE = 45_622_418
EXPECTED_ZIP_SHA256 = "572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb"
EXPECTED_XLSX_SIZE = 45_622_278
EXPECTED_XLSX_SHA256 = "bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980"
EXPECTED_CRC32 = "e51262e5"
EXPECTED_HEADERS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
]
EXPECTED_CANONICAL_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]
EXPECTED_ALIAS_CHANGES = {
    "Invoice": "InvoiceNo",
    "Price": "UnitPrice",
    "Customer ID": "CustomerID",
}


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


def validate_local_artifacts(failures: list[dict[str, Any]]) -> dict[str, Any]:
    local_failures: list[dict[str, Any]] = []
    for path in [ZIP_PATH, XLSX_PATH]:
        if not path.exists():
            add_failure(local_failures, "local_raw_artifact_missing", repo_path(path))

    observed: dict[str, Any] = {
        "zip_path": repo_path(ZIP_PATH),
        "xlsx_path": repo_path(XLSX_PATH),
        "zip_size_bytes": None,
        "xlsx_size_bytes": None,
        "zip_sha256": None,
        "xlsx_sha256": None,
        "zip_crc_passed": False,
        "xlsx_container_valid": False,
    }
    if ZIP_PATH.exists():
        observed["zip_size_bytes"] = ZIP_PATH.stat().st_size
        observed["zip_sha256"] = sha256_file(ZIP_PATH)
        if observed["zip_size_bytes"] != EXPECTED_ZIP_SIZE:
            add_failure(local_failures, "local_zip_size", observed["zip_size_bytes"])
        if observed["zip_sha256"] != EXPECTED_ZIP_SHA256:
            add_failure(local_failures, "local_zip_sha256", observed["zip_sha256"])
        if zipfile.is_zipfile(ZIP_PATH):
            with zipfile.ZipFile(ZIP_PATH) as archive:
                observed["zip_crc_passed"] = archive.testzip() is None
        if not observed["zip_crc_passed"]:
            add_failure(local_failures, "local_zip_crc", observed["zip_crc_passed"])
    if XLSX_PATH.exists():
        observed["xlsx_size_bytes"] = XLSX_PATH.stat().st_size
        observed["xlsx_sha256"] = sha256_file(XLSX_PATH)
        observed["xlsx_container_valid"] = zipfile.is_zipfile(XLSX_PATH)
        if observed["xlsx_size_bytes"] != EXPECTED_XLSX_SIZE:
            add_failure(local_failures, "local_xlsx_size", observed["xlsx_size_bytes"])
        if observed["xlsx_sha256"] != EXPECTED_XLSX_SHA256:
            add_failure(local_failures, "local_xlsx_sha256", observed["xlsx_sha256"])
        if not observed["xlsx_container_valid"]:
            add_failure(local_failures, "local_xlsx_container", False)

    result = {
        "status": "local_acquisition_validation_passed" if not local_failures else "local_acquisition_validation_failed",
        "observed": observed,
        "num_failures": len(local_failures),
        "failures": local_failures,
    }
    LOCAL_VALIDATION_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    failures.extend(local_failures)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Confirmation Set v1 acquisition artifacts.")
    parser.add_argument(
        "--require-local",
        action="store_true",
        help="Recompute hashes from ignored local raw files and write an ignored local validation record.",
    )
    args = parser.parse_args()

    failures: list[dict[str, Any]] = []
    required_public_paths = [ACQUISITION_PATH, STRUCTURE_PATH, AUDIT_PATH, PROTOCOL_PATH, FEASIBILITY_PATH]
    for path in required_public_paths:
        if not path.exists():
            add_failure(failures, "required_public_artifact_missing", repo_path(path))

    acquisition = load_json(ACQUISITION_PATH) if ACQUISITION_PATH.exists() else {}
    structure = load_json(STRUCTURE_PATH) if STRUCTURE_PATH.exists() else {}
    audit = load_json(AUDIT_PATH) if AUDIT_PATH.exists() else {}
    protocol = load_json(PROTOCOL_PATH) if PROTOCOL_PATH.exists() else {}
    feasibility = load_json(FEASIBILITY_PATH) if FEASIBILITY_PATH.exists() else {}

    for path, payload in [
        (ACQUISITION_PATH, acquisition),
        (STRUCTURE_PATH, structure),
        (AUDIT_PATH, audit),
        (PROTOCOL_PATH, protocol),
        (FEASIBILITY_PATH, feasibility),
    ]:
        if payload and contains_local_path(json.dumps(payload, ensure_ascii=True)):
            add_failure(failures, "local_absolute_path_in_public_artifact", repo_path(path))

    expected_acquisition = {
        "status": "official_acquisition_and_hash_verified",
        "study_name": "Confirmation Set v1",
        "candidate_id": "uci_online_retail_ii_prior_period",
        "source_page_url": "https://archive.ics.uci.edu/dataset/502/online+retail",
        "official_download_url": "https://archive.ics.uci.edu/static/public/502/online%2Bretail%2Bii.zip",
        "doi": "10.24432/C5CG6D",
        "license": "CC BY 4.0",
        "acquisition_mode": "downloaded_from_official_source",
        "local_only_raw_data": True,
        "context_manifest_created": False,
        "prompt_created": False,
        "model_run_performed": False,
        "new_metrics_reported": False,
        "execution_ready": False,
        "no_new_results": True,
    }
    for key, expected in expected_acquisition.items():
        if acquisition.get(key) != expected:
            add_failure(
                failures,
                "acquisition_value_mismatch",
                {"field": key, "expected": expected, "actual": acquisition.get(key)},
            )

    try:
        parsed_retrieved_at = acquisition.get("retrieved_at_utc", "")
        if not parsed_retrieved_at or "+00:00" not in parsed_retrieved_at:
            raise ValueError(parsed_retrieved_at)
    except (TypeError, ValueError):
        add_failure(failures, "retrieval_timestamp", acquisition.get("retrieved_at_utc"))

    resolved_url = acquisition.get("http_response", {}).get("resolved_url", "")
    if urllib.parse.urlparse(resolved_url).hostname != "archive.ics.uci.edu":
        add_failure(failures, "resolved_download_host", resolved_url)
    if acquisition.get("http_response", {}).get("http_status") != 200:
        add_failure(failures, "download_http_status", acquisition.get("http_response"))

    expected_raw = {
        "zip": {
            "path": "data/raw/confirmation_online_retail_ii/online_retail_ii.zip",
            "size_bytes": EXPECTED_ZIP_SIZE,
            "sha256": EXPECTED_ZIP_SHA256,
        },
        "xlsx": {
            "path": "data/raw/confirmation_online_retail_ii/online_retail_II.xlsx",
            "size_bytes": EXPECTED_XLSX_SIZE,
            "sha256": EXPECTED_XLSX_SHA256,
        },
    }
    if acquisition.get("raw_artifacts") != expected_raw:
        add_failure(failures, "raw_artifact_manifest", acquisition.get("raw_artifacts"))
    expected_member = {
        "name": "online_retail_II.xlsx",
        "uncompressed_size_bytes": EXPECTED_XLSX_SIZE,
        "compressed_size_bytes": EXPECTED_XLSX_SIZE,
        "crc32_hex": EXPECTED_CRC32,
    }
    if acquisition.get("archive_member") != expected_member:
        add_failure(failures, "archive_member", acquisition.get("archive_member"))
    if not all(acquisition.get("checks", {}).values()):
        add_failure(failures, "acquisition_checks", acquisition.get("checks"))

    expected_structure = {
        "status": "workbook_structure_and_strict_window_verified",
        "study_name": "Confirmation Set v1",
        "candidate_id": "uci_online_retail_ii_prior_period",
        "workbook_sha256": EXPECTED_XLSX_SHA256,
        "documented_instance_count": 1_067_371,
        "workbook_sheet_count": 2,
        "sheet_names": ["Year 2009-2010", "Year 2010-2011"],
        "workbook_total_data_rows": 1_067_371,
        "documented_instance_delta": 0,
        "workbook_total_fully_blank_rows": 0,
        "canonical_columns": EXPECTED_CANONICAL_COLUMNS,
        "actual_workbook_headers": EXPECTED_HEADERS,
        "metadata_header_drift_detected": True,
        "parse_warning_count": 0,
        "full_missingness_profile_complete": False,
        "duplicate_and_grain_profile_complete": False,
        "business_rule_profile_complete": False,
        "historical_overlap_check_complete": False,
        "context_feasibility_check_complete": False,
        "context_manifest_created": False,
        "prompt_created": False,
        "model_run_performed": False,
        "new_metrics_reported": False,
        "execution_ready": False,
        "no_new_results": True,
    }
    for key, expected in expected_structure.items():
        if structure.get(key) != expected:
            add_failure(
                failures,
                "structure_value_mismatch",
                {"field": key, "expected": expected, "actual": structure.get(key)},
            )
    if structure.get("metadata_header_drift", {}).get("actual_to_canonical_changes") != EXPECTED_ALIAS_CHANGES:
        add_failure(failures, "header_alias_changes", structure.get("metadata_header_drift"))

    expected_date_scan = {
        "valid_invoice_date_rows": 1_067_371,
        "blank_invoice_date_rows": 0,
        "invalid_invoice_date_rows": 0,
        "overall_date_min": "2009-12-01 07:45:00",
        "overall_date_max": "2011-12-09 12:50:00",
        "rows_before_window": 0,
        "strict_window_row_count": 502_938,
        "strict_window_date_min": "2009-12-01 07:45:00",
        "strict_window_date_max": "2010-11-30 19:35:00",
        "rows_at_or_after_window": 564_433,
    }
    if structure.get("date_scan") != expected_date_scan:
        add_failure(failures, "date_scan", structure.get("date_scan"))
    if sum(
        expected_date_scan[key]
        for key in ["rows_before_window", "strict_window_row_count", "rows_at_or_after_window"]
    ) != expected_date_scan["valid_invoice_date_rows"]:
        add_failure(failures, "date_partition_reconciliation", expected_date_scan)

    expected_sheet_counts = {
        "Year 2009-2010": {
            "data_rows": 525_461,
            "strict_window_row_count": 502_938,
            "rows_before_window": 0,
            "rows_at_or_after_window": 22_523,
            "date_min": "2009-12-01 07:45:00",
            "date_max": "2010-12-09 20:01:00",
        },
        "Year 2010-2011": {
            "data_rows": 541_910,
            "strict_window_row_count": 0,
            "rows_before_window": 0,
            "rows_at_or_after_window": 541_910,
            "date_min": "2010-12-01 08:26:00",
            "date_max": "2011-12-09 12:50:00",
        },
    }
    observed_sheet_counts: dict[str, dict[str, Any]] = {}
    for item in structure.get("sheet_profiles", []):
        observed_sheet_counts[item.get("sheet_name", "")] = {
            key: item.get(key) for key in next(iter(expected_sheet_counts.values()))
        }
        if item.get("actual_headers") != EXPECTED_HEADERS or item.get("canonical_headers") != EXPECTED_CANONICAL_COLUMNS:
            add_failure(failures, "sheet_headers", {"sheet": item.get("sheet_name"), "headers": item.get("actual_headers")})
    if observed_sheet_counts != expected_sheet_counts:
        add_failure(failures, "sheet_counts", observed_sheet_counts)

    if audit.get("status") != "dataset_source_selected_and_audited_precision_review_pending":
        add_failure(failures, "audit_status", audit.get("status"))
    expected_audit_flags = {
        "download_performed": True,
        "acquisition_verified": True,
        "structure_profile_complete": True,
        "quality_profile_complete": True,
        "historical_overlap_check_complete": True,
        "context_feasibility_check_complete": True,
        "local_profile_complete": True,
        "execution_ready": False,
        "no_new_results": True,
    }
    for key, expected in expected_audit_flags.items():
        if audit.get(key) != expected:
            add_failure(failures, "audit_flag", {"field": key, "expected": expected, "actual": audit.get(key)})

    check_statuses = {
        item.get("check_id"): item.get("status") for item in audit.get("required_local_profile_checks", [])
    }
    expected_completed_checks = {
        "official_acquisition_and_hash": "completed",
        "workbook_structure": "completed",
        "strict_prior_period_filter": "completed",
    }
    for check_id, expected in expected_completed_checks.items():
        if check_statuses.get(check_id) != expected:
            add_failure(
                failures,
                "audit_check_status",
                {"check_id": check_id, "expected": expected, "actual": check_statuses.get(check_id)},
            )

    strategy = protocol.get("dataset_strategy", {})
    if strategy.get("selected_candidate_gate_status") != "complete":
        add_failure(failures, "protocol_gate_status", strategy.get("selected_candidate_gate_status"))
    gates = protocol.get("execution_gates", [])
    dataset_gate = next(
        (item for item in gates if item.get("gate") == "dataset_source_selected_and_audited"),
        {},
    )
    if dataset_gate.get("status") != "complete":
        add_failure(failures, "dataset_gate_not_complete", dataset_gate)
    expected_capacity = {
        "status": "outcome_blind_context_feasibility_complete",
        "observed_complete_period_count": 50,
        "required_total_context_count": 36,
        "maximum_slot_matching_count": 36,
        "context_manifest_created": False,
        "execution_ready": False,
        "no_new_results": True,
    }
    observed_capacity = {
        "status": feasibility.get("status"),
        "observed_complete_period_count": feasibility.get("source_capacity", {}).get("observed_complete_period_count"),
        "required_total_context_count": feasibility.get("capacity_proof", {}).get("required_total_context_count"),
        "maximum_slot_matching_count": feasibility.get("capacity_proof", {}).get("maximum_slot_matching_count"),
        "context_manifest_created": feasibility.get("context_manifest_created"),
        "execution_ready": feasibility.get("execution_ready"),
        "no_new_results": feasibility.get("no_new_results"),
    }
    if observed_capacity != expected_capacity:
        add_failure(failures, "dataset_gate_capacity_evidence", observed_capacity)
    if protocol.get("execution_ready") is not False or protocol.get("no_new_results") is not True:
        add_failure(failures, "protocol_execution_boundary", {"execution_ready": protocol.get("execution_ready"), "no_new_results": protocol.get("no_new_results")})

    public_validation = {
        "status": (
            "confirmation_dataset_acquisition_validation_passed"
            if not failures
            else "confirmation_dataset_acquisition_validation_failed"
        ),
        "acquisition_report_path": repo_path(ACQUISITION_PATH),
        "structure_report_path": repo_path(STRUCTURE_PATH),
        "candidate_id": acquisition.get("candidate_id"),
        "zip_sha256": acquisition.get("raw_artifacts", {}).get("zip", {}).get("sha256"),
        "xlsx_sha256": acquisition.get("raw_artifacts", {}).get("xlsx", {}).get("sha256"),
        "workbook_total_data_rows": structure.get("workbook_total_data_rows"),
        "strict_window_row_count": structure.get("date_scan", {}).get("strict_window_row_count"),
        "metadata_header_drift_detected": structure.get("metadata_header_drift_detected"),
        "dataset_gate_status": dataset_gate.get("status"),
        "execution_ready": False,
        "no_new_results": True,
        "local_artifact_verification_command": "python src/validate_confirmation_dataset_acquisition.py --require-local",
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(public_validation, indent=2, ensure_ascii=True), encoding="utf-8")

    local_result = None
    if args.require_local:
        local_failures: list[dict[str, Any]] = []
        local_result = validate_local_artifacts(local_failures)
        if local_failures:
            public_validation["status"] = "confirmation_dataset_acquisition_validation_failed"
            public_validation["num_failures"] += len(local_failures)
            public_validation["failures"].extend(local_failures)

    print(
        json.dumps(
            {"public_validation": public_validation, "local_validation": local_result},
            indent=2,
            ensure_ascii=True,
        )
    )
    if public_validation["num_failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
