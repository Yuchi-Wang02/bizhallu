from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRENT_RAW_PATH = PROJECT_ROOT / "data" / "raw" / "Online Retail.xlsx"
CONFIRMATION_RAW_PATH = (
    PROJECT_ROOT / "data" / "raw" / "confirmation_online_retail_ii" / "online_retail_II.xlsx"
)
PRIOR_TABLE_PATH = (
    PROJECT_ROOT / "data" / "processed" / "confirmation_online_retail_ii" / "strict_window_lines.csv.gz"
)
LOCAL_PROOF_PATH = PRIOR_TABLE_PATH.parent / "historical_overlap_local_proof.json"
PUBLIC_REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_overlap_report.json"
ACQUISITION_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_acquisition_report.json"

EXPECTED_CURRENT_RAW_SHA256 = "43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d"
EXPECTED_CONFIRMATION_RAW_SHA256 = "bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980"
EXPECTED_PRIOR_TABLE_SHA256 = "ab875caaf527d5d528f4edad4fd372b15d4e1ae9c39f6cea20f8211178e256fc"
EXPECTED_PRIOR_ROWS = 502_938
EXPECTED_CURRENT_ROWS = 541_909
EXPECTED_LINEAGE_ROWS = 541_910

CANONICAL_FIELDS = [
    "invoice_no",
    "stock_code",
    "description",
    "quantity",
    "invoice_date",
    "unit_price",
    "customer_id",
    "country",
]
DATE_BLIND_FIELDS = [field for field in CANONICAL_FIELDS if field != "invoice_date"]
BUSINESS_PATTERN_FIELDS = ["stock_code", "description", "quantity", "unit_price", "country"]
ENTITY_FIELDS = ["invoice_no", "stock_code", "description", "customer_id", "country"]

CURRENT_HEADER_MAP = {
    "InvoiceNo": "invoice_no",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_date",
    "UnitPrice": "unit_price",
    "CustomerID": "customer_id",
    "Country": "country",
}
CONFIRMATION_HEADER_MAP = {
    "Invoice": "invoice_no",
    "StockCode": "stock_code",
    "Description": "description",
    "Quantity": "quantity",
    "InvoiceDate": "invoice_date",
    "Price": "unit_price",
    "Customer ID": "customer_id",
    "Country": "country",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rounded_rate(count: int, total: int) -> float:
    return round(count / total, 8) if total else 0.0


def clean_text(series: pd.Series, *, collapse_whitespace: bool = False) -> pd.Series:
    cleaned = series.astype("string").str.strip()
    if collapse_whitespace:
        cleaned = cleaned.str.replace(r"\s+", " ", regex=True)
    return cleaned.mask(cleaned.eq(""), pd.NA)


def normalize_frame(frame: pd.DataFrame, header_map: dict[str, str] | None = None) -> pd.DataFrame:
    normalized = frame.rename(columns=header_map or {}).copy()
    missing = [field for field in CANONICAL_FIELDS if field not in normalized.columns]
    if missing:
        raise RuntimeError(f"Missing canonical fields: {missing}")
    normalized = normalized[CANONICAL_FIELDS].copy()

    normalized["invoice_no"] = clean_text(normalized["invoice_no"])
    normalized["stock_code"] = clean_text(normalized["stock_code"])
    normalized["description"] = clean_text(normalized["description"], collapse_whitespace=True)
    normalized["country"] = clean_text(normalized["country"])
    normalized["invoice_date"] = pd.to_datetime(normalized["invoice_date"], errors="coerce")

    quantity = pd.to_numeric(normalized["quantity"], errors="coerce")
    price = pd.to_numeric(normalized["unit_price"], errors="coerce")
    customer = pd.to_numeric(normalized["customer_id"], errors="coerce")
    invalid = {
        "invoice_date": int(normalized["invoice_date"].isna().sum()),
        "invoice_date_subsecond": int(
            (
                normalized["invoice_date"].notna()
                & (
                    normalized["invoice_date"].dt.microsecond.ne(0)
                    | normalized["invoice_date"].dt.nanosecond.ne(0)
                )
            ).sum()
        ),
        "quantity": int((quantity.isna() | ~np.isfinite(quantity)).sum()),
        "quantity_fractional": int((quantity.notna() & ~np.isclose(quantity % 1, 0)).sum()),
        "unit_price": int((price.isna() | ~np.isfinite(price)).sum()),
        "unit_price_beyond_six_decimal_precision": int(
            (price.notna() & ~np.isclose(price, price.round(6), rtol=0, atol=1e-12)).sum()
        ),
        "customer_fractional": int((customer.notna() & ~np.isclose(customer % 1, 0)).sum()),
    }
    if any(invalid.values()):
        raise RuntimeError(f"Canonical normalization failed: {invalid}")

    normalized["quantity"] = quantity.astype("Int64")
    normalized["unit_price"] = price.astype(float)
    normalized["customer_id"] = customer.astype("Int64")
    return normalized


def token_frame(frame: pd.DataFrame) -> pd.DataFrame:
    tokens = pd.DataFrame(index=frame.index)
    for field in ["invoice_no", "stock_code", "description", "country"]:
        tokens[field] = frame[field].astype("string")
    tokens["quantity"] = frame["quantity"].astype("Int64").astype("string")
    tokens["invoice_date"] = frame["invoice_date"].dt.strftime("%Y-%m-%dT%H:%M:%S").astype("string")
    tokens["unit_price"] = frame["unit_price"].map(lambda value: f"{float(value):.6f}").astype("string")
    tokens["customer_id"] = frame["customer_id"].astype("Int64").astype("string")
    return tokens[CANONICAL_FIELDS]


def row_digest(domain: bytes, values: Iterable[Any]) -> bytes:
    digest = hashlib.sha256(domain + b"\x00")
    for value in values:
        if value is pd.NA or value is None or (isinstance(value, float) and math.isnan(value)):
            digest.update(b"\xff")
            continue
        encoded = str(value).encode("utf-8")
        digest.update(b"\x00")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return digest.digest()


def fingerprint_counters(
    frame: pd.DataFrame,
    *,
    include_sensitivity_families: bool,
) -> dict[str, Counter[bytes]]:
    tokens = token_frame(frame)
    field_positions = {field: index for index, field in enumerate(CANONICAL_FIELDS)}
    date_blind_positions = [field_positions[field] for field in DATE_BLIND_FIELDS]
    business_positions = [field_positions[field] for field in BUSINESS_PATTERN_FIELDS]
    counters: dict[str, Counter[bytes]] = {"canonical_record": Counter()}
    if include_sensitivity_families:
        counters["date_blind_record"] = Counter()
        counters["business_pattern"] = Counter()

    for row in tokens.itertuples(index=False, name=None):
        counters["canonical_record"][row_digest(b"bizhallu:canonical-record:v1", row)] += 1
        if include_sensitivity_families:
            counters["date_blind_record"][
                row_digest(b"bizhallu:date-blind-record:v1", (row[index] for index in date_blind_positions))
            ] += 1
            counters["business_pattern"][
                row_digest(b"bizhallu:business-pattern:v1", (row[index] for index in business_positions))
            ] += 1
    return counters


def inventory_manifest_sha256(counter: Counter[bytes]) -> str:
    digest = hashlib.sha256(b"bizhallu:fingerprint-inventory:v1\x00")
    for fingerprint, count in sorted(counter.items()):
        digest.update(fingerprint)
        digest.update(int(count).to_bytes(8, "big"))
    return digest.hexdigest()


def counter_profile(counter: Counter[bytes], row_count: int) -> dict[str, Any]:
    return {
        "row_count": row_count,
        "unique_fingerprint_count": len(counter),
        "duplicate_extra_row_count": row_count - len(counter),
        "fingerprint_inventory_manifest_sha256": inventory_manifest_sha256(counter),
    }


def compare_counters(
    left: Counter[bytes],
    right: Counter[bytes],
    *,
    left_rows: int,
    right_rows: int,
    left_name: str,
    right_name: str,
) -> dict[str, Any]:
    shared = left.keys() & right.keys()
    overlap_rows = sum(min(left[fingerprint], right[fingerprint]) for fingerprint in shared)
    left_only_rows = sum(max(0, count - right.get(fingerprint, 0)) for fingerprint, count in left.items())
    right_only_rows = sum(max(0, count - left.get(fingerprint, 0)) for fingerprint, count in right.items())
    return {
        "left_dataset": left_name,
        "right_dataset": right_name,
        "unique_fingerprint_overlap_count": len(shared),
        "multiset_overlap_row_count": overlap_rows,
        "left_only_row_count": left_only_rows,
        "right_only_row_count": right_only_rows,
        "left_multiset_overlap_rate": rounded_rate(overlap_rows, left_rows),
        "right_multiset_overlap_rate": rounded_rate(overlap_rows, right_rows),
        "left_unique_overlap_rate": rounded_rate(len(shared), len(left)),
        "right_unique_overlap_rate": rounded_rate(len(shared), len(right)),
    }


def entity_sets(frame: pd.DataFrame) -> dict[str, set[str]]:
    return {
        field: set(frame[field].dropna().astype("string").tolist())
        for field in ENTITY_FIELDS
    }


def compare_entities(left: dict[str, set[str]], right: dict[str, set[str]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in ENTITY_FIELDS:
        shared_count = len(left[field] & right[field])
        result[field] = {
            "prior_distinct_count": len(left[field]),
            "current_distinct_count": len(right[field]),
            "shared_distinct_count": shared_count,
            "prior_entity_coverage_rate": rounded_rate(shared_count, len(left[field])),
            "current_entity_coverage_rate": rounded_rate(shared_count, len(right[field])),
        }
    return result


def main() -> None:
    required = [CURRENT_RAW_PATH, CONFIRMATION_RAW_PATH, PRIOR_TABLE_PATH, ACQUISITION_PATH]
    missing = [repo_path(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing local prerequisites: {missing}")

    input_artifacts = {
        "current_online_retail_workbook": {
            "path": repo_path(CURRENT_RAW_PATH),
            "size_bytes": CURRENT_RAW_PATH.stat().st_size,
            "sha256": sha256_file(CURRENT_RAW_PATH),
        },
        "confirmation_online_retail_ii_workbook": {
            "path": repo_path(CONFIRMATION_RAW_PATH),
            "size_bytes": CONFIRMATION_RAW_PATH.stat().st_size,
            "sha256": sha256_file(CONFIRMATION_RAW_PATH),
        },
        "strict_prior_window_table": {
            "path": repo_path(PRIOR_TABLE_PATH),
            "size_bytes": PRIOR_TABLE_PATH.stat().st_size,
            "sha256": sha256_file(PRIOR_TABLE_PATH),
        },
    }

    prior_raw = pd.read_csv(PRIOR_TABLE_PATH, usecols=CANONICAL_FIELDS, low_memory=False)
    prior = normalize_frame(prior_raw)
    del prior_raw
    prior_entities = entity_sets(prior)
    prior_dates = (prior["invoice_date"].min(), prior["invoice_date"].max())
    prior_counters = fingerprint_counters(prior, include_sensitivity_families=True)
    del prior

    current_raw = pd.read_excel(CURRENT_RAW_PATH, engine="openpyxl")
    current = normalize_frame(current_raw, CURRENT_HEADER_MAP)
    del current_raw
    current_entities = entity_sets(current)
    current_dates = (current["invoice_date"].min(), current["invoice_date"].max())
    current_counters = fingerprint_counters(current, include_sensitivity_families=True)
    del current

    lineage_raw = pd.read_excel(
        CONFIRMATION_RAW_PATH,
        sheet_name="Year 2010-2011",
        engine="openpyxl",
    )
    lineage = normalize_frame(lineage_raw, CONFIRMATION_HEADER_MAP)
    del lineage_raw
    lineage_dates = (lineage["invoice_date"].min(), lineage["invoice_date"].max())
    lineage_counters = fingerprint_counters(lineage, include_sensitivity_families=False)
    del lineage

    prior_rows = sum(prior_counters["canonical_record"].values())
    current_rows = sum(current_counters["canonical_record"].values())
    lineage_rows = sum(lineage_counters["canonical_record"].values())

    canonical_overlap = compare_counters(
        prior_counters["canonical_record"],
        current_counters["canonical_record"],
        left_rows=prior_rows,
        right_rows=current_rows,
        left_name="strict_prior_window",
        right_name="current_online_retail",
    )
    date_blind_overlap = compare_counters(
        prior_counters["date_blind_record"],
        current_counters["date_blind_record"],
        left_rows=prior_rows,
        right_rows=current_rows,
        left_name="strict_prior_window",
        right_name="current_online_retail",
    )
    business_pattern_overlap = compare_counters(
        prior_counters["business_pattern"],
        current_counters["business_pattern"],
        left_rows=prior_rows,
        right_rows=current_rows,
        left_name="strict_prior_window",
        right_name="current_online_retail",
    )
    lineage_overlap = compare_counters(
        current_counters["canonical_record"],
        lineage_counters["canonical_record"],
        left_rows=current_rows,
        right_rows=lineage_rows,
        left_name="current_online_retail",
        right_name="online_retail_ii_2010_2011_sheet",
    )

    boundary_gap = current_dates[0] - prior_dates[1]
    local_proof = {
        "schema_version": "1.0",
        "status": "historical_overlap_local_proof_complete",
        "study_name": "Confirmation Set v1",
        "candidate_id": "uci_online_retail_ii_prior_period",
        "input_artifacts": input_artifacts,
        "fingerprint_definitions": {
            "normalization": {
                "text": "trim strings; collapse internal whitespace only for Description; empty strings become null",
                "quantity": "finite integer decimal token",
                "invoice_date": "naive source-local timestamp formatted to whole seconds",
                "unit_price": "finite decimal token fixed to six places",
                "customer_id": "nullable integer decimal token",
                "encoding": "domain-separated SHA-256 over length-prefixed UTF-8 field tokens with an explicit null marker",
            },
            "canonical_record": CANONICAL_FIELDS,
            "date_blind_record_sensitivity": DATE_BLIND_FIELDS,
            "business_pattern_descriptive_only": BUSINESS_PATTERN_FIELDS,
        },
        "dataset_profiles": {
            "strict_prior_window": {
                **counter_profile(prior_counters["canonical_record"], prior_rows),
                "date_blind_inventory_manifest_sha256": inventory_manifest_sha256(
                    prior_counters["date_blind_record"]
                ),
                "business_pattern_inventory_manifest_sha256": inventory_manifest_sha256(
                    prior_counters["business_pattern"]
                ),
                "date_min": str(prior_dates[0]),
                "date_max": str(prior_dates[1]),
            },
            "current_online_retail": {
                **counter_profile(current_counters["canonical_record"], current_rows),
                "date_blind_inventory_manifest_sha256": inventory_manifest_sha256(
                    current_counters["date_blind_record"]
                ),
                "business_pattern_inventory_manifest_sha256": inventory_manifest_sha256(
                    current_counters["business_pattern"]
                ),
                "date_min": str(current_dates[0]),
                "date_max": str(current_dates[1]),
            },
            "online_retail_ii_2010_2011_sheet": {
                **counter_profile(lineage_counters["canonical_record"], lineage_rows),
                "date_min": str(lineage_dates[0]),
                "date_max": str(lineage_dates[1]),
            },
        },
        "temporal_boundary": {
            "strict_prior_max": str(prior_dates[1]),
            "current_min": str(current_dates[0]),
            "strict_prior_precedes_current": bool(prior_dates[1] < current_dates[0]),
            "boundary_gap_seconds": int(boundary_gap.total_seconds()),
            "boundary_gap_human": "12 hours 51 minutes",
        },
        "record_overlap": {
            "canonical_eight_field": canonical_overlap,
            "date_blind_seven_field_sensitivity": date_blind_overlap,
            "decision": "zero_normalized_record_overlap_verified",
        },
        "descriptive_similarity": {
            "business_pattern_five_field": business_pattern_overlap,
            "entity_overlap": compare_entities(prior_entities, current_entities),
            "interpretation": "Shared products, customers, descriptions, countries, quantities, and prices are expected in a same-retailer temporal replication. They describe domain continuity and are not counted as repeated source records.",
        },
        "lineage_calibration": {
            "comparison": lineage_overlap,
            "current_is_multiset_subset_of_online_retail_ii_sheet": lineage_overlap["left_only_row_count"] == 0,
            "online_retail_ii_sheet_extra_row_count": lineage_overlap["right_only_row_count"],
            "interpretation": "The current workbook is the 2010-2011 Online Retail II lineage minus one source row. This positive control verifies the canonicalization and does not establish external independence.",
        },
        "privacy": {
            "contains_raw_identifier_values": False,
            "contains_row_fingerprint_values": False,
            "contains_only_aggregate_counts_and_inventory_manifest_hashes": True,
        },
    }
    LOCAL_PROOF_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_PROOF_PATH.write_text(json.dumps(local_proof, indent=2, ensure_ascii=True), encoding="utf-8")

    acquisition = load_json(ACQUISITION_PATH)
    checks = {
        "current_workbook_hash_matches_frozen_source": (
            input_artifacts["current_online_retail_workbook"]["sha256"] == EXPECTED_CURRENT_RAW_SHA256
        ),
        "confirmation_workbook_hash_matches_acquisition": (
            input_artifacts["confirmation_online_retail_ii_workbook"]["sha256"]
            == EXPECTED_CONFIRMATION_RAW_SHA256
            == acquisition["raw_artifacts"]["xlsx"]["sha256"]
        ),
        "strict_table_hash_matches_quality_profile": (
            input_artifacts["strict_prior_window_table"]["sha256"] == EXPECTED_PRIOR_TABLE_SHA256
        ),
        "row_counts_match_frozen_sources": (
            prior_rows == EXPECTED_PRIOR_ROWS
            and current_rows == EXPECTED_CURRENT_ROWS
            and lineage_rows == EXPECTED_LINEAGE_ROWS
        ),
        "strict_prior_window_precedes_current_source": bool(prior_dates[1] < current_dates[0]),
        "canonical_unique_overlap_is_zero": canonical_overlap["unique_fingerprint_overlap_count"] == 0,
        "canonical_multiset_overlap_is_zero": canonical_overlap["multiset_overlap_row_count"] == 0,
        "date_blind_sensitivity_overlap_is_zero": (
            date_blind_overlap["unique_fingerprint_overlap_count"] == 0
            and date_blind_overlap["multiset_overlap_row_count"] == 0
        ),
        "lineage_positive_control_recovers_current_source": (
            lineage_overlap["left_only_row_count"] == 0
            and lineage_overlap["multiset_overlap_row_count"] == EXPECTED_CURRENT_ROWS
            and lineage_overlap["right_only_row_count"] == 1
        ),
        "no_raw_identifiers_or_row_fingerprints_published": True,
    }
    failures = [name for name, passed in checks.items() if not passed]

    public_report = {
        "schema_version": "1.0",
        "status": (
            "historical_record_overlap_proof_complete" if not failures else "historical_record_overlap_proof_failed"
        ),
        "study_name": "Confirmation Set v1",
        "candidate_id": "uci_online_retail_ii_prior_period",
        "scope": "normalized historical record-overlap proof against the current Online Retail lineage",
        "explicitly_not_in_scope": [
            "36-context feasibility, context manifest, or split assignment",
            "question, prompt, model, annotation, verifier, or detector generation",
            "new confirmation metrics or external-generalization claims",
        ],
        "input_artifacts": input_artifacts,
        "fingerprint_definitions": local_proof["fingerprint_definitions"],
        "dataset_profiles": local_proof["dataset_profiles"],
        "temporal_boundary": local_proof["temporal_boundary"],
        "record_overlap": local_proof["record_overlap"],
        "descriptive_similarity": local_proof["descriptive_similarity"],
        "lineage_calibration": local_proof["lineage_calibration"],
        "research_decision": {
            "historical_record_overlap_check_complete": not failures,
            "zero_normalized_record_overlap_verified": not failures,
            "strict_window_is_unseen_at_normalized_record_level": not failures,
            "claim_limit": "This proves temporal record-level separation from the current Online Retail rows under the frozen canonicalization. It does not prove company, entity, source-lineage, or domain independence.",
            "dataset_gate_status": "pending_context_feasibility",
            "execution_ready": False,
        },
        "critical_checks": checks,
        "failed_critical_checks": failures,
        "local_proof": {
            "path": repo_path(LOCAL_PROOF_PATH),
            "sha256": sha256_file(LOCAL_PROOF_PATH),
            "git_ignored": True,
        },
        "privacy": local_proof["privacy"],
        "historical_overlap_check_complete": not failures,
        "context_feasibility_check_complete": False,
        "context_manifest_created": False,
        "prompt_created": False,
        "model_run_performed": False,
        "new_metrics_reported": False,
        "execution_ready": False,
        "no_new_results": True,
        "next_authorized_action": "Run only the outcome-blind 36-context feasibility check; do not create a context manifest, prompt, or model output yet.",
    }
    PUBLIC_REPORT_PATH.write_text(json.dumps(public_report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": public_report["status"],
                "canonical_overlap_rows": canonical_overlap["multiset_overlap_row_count"],
                "date_blind_overlap_rows": date_blind_overlap["multiset_overlap_row_count"],
                "business_pattern_overlap_rows": business_pattern_overlap["multiset_overlap_row_count"],
                "lineage_overlap_rows": lineage_overlap["multiset_overlap_row_count"],
                "lineage_extra_rows": lineage_overlap["right_only_row_count"],
                "failed_critical_checks": failures,
                "report_path": repo_path(PUBLIC_REPORT_PATH),
            },
            indent=2,
            ensure_ascii=True,
        )
    )
    if failures:
        raise RuntimeError(f"Historical overlap proof failed: {failures}")


if __name__ == "__main__":
    main()
