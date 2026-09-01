from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import contains_local_path, repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_overlap_report.json"
HTML_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_overlap.html"
VALIDATION_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_overlap_validation.json"
LOCAL_PROOF_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "confirmation_online_retail_ii"
    / "historical_overlap_local_proof.json"
)
METHODOLOGY_PATH = PROJECT_ROOT / "reports" / "bizhallu_methodology_hardening_summary.json"

EXPECTED_PROFILES = {
    "strict_prior_window": (502_938, 496_394, 6_544),
    "current_online_retail": (541_909, 536_641, 5_268),
    "online_retail_ii_2010_2011_sheet": (541_910, 536_642, 5_268),
}
EXPECTED_MANIFESTS = {
    "strict_prior_window": {
        "fingerprint_inventory_manifest_sha256": "727bdfca9f58f937ce71b6497e2c7e9978b647772025f8cd98decded2a010ebd",
        "date_blind_inventory_manifest_sha256": "45c4b92a5d6a2d6d6e669f82c5b62789272a8138de3d45231931e5448f652bb0",
        "business_pattern_inventory_manifest_sha256": "6d78ef21808bb91349419b9d2d777db5283fa17734cb9e6b92db015d71bf1002",
    },
    "current_online_retail": {
        "fingerprint_inventory_manifest_sha256": "983dcf3ee53cdd6793f88d291880d34e2dcec656989fd4433deec20aeb2f2685",
        "date_blind_inventory_manifest_sha256": "f7ec12a30b2ad671b7d7b90c1560ffda7dadc95d4569e3a3b441034d5d871113",
        "business_pattern_inventory_manifest_sha256": "223db40fad5cac94e6784a4b675766daa95cf298c69bde5a864b746393a45682",
    },
    "online_retail_ii_2010_2011_sheet": {
        "fingerprint_inventory_manifest_sha256": "58f70499c8d40d39209e696bf95febe831f74c8d8b7c1f04e61cb64320abd685",
    },
}
EXPECTED_ENTITIES = {
    "invoice_no": (27_728, 25_900, 0),
    "stock_code": (4_621, 4_070, 3_387),
    "description": (4_624, 4_203, 3_183),
    "customer_id": (4_336, 4_372, 2_766),
    "country": (40, 38, 35),
}
EXPECTED_LOCAL_PROOF_SHA256 = "adba5365af6b2f01724e4149377a7d8d462f4e1200607ba70c415cafef553048"

REQUIRED_HTML_FRAGMENTS = [
    "BizHallu Historical Record-Overlap Proof",
    "zero repeated current-source records",
    "Canonical overlap rows",
    "Date-blind overlap rows",
    "12 hours 51 minutes",
    "195,814 shared business patterns",
    "541,909 / 541,909",
    "The dataset gate is still pending.",
    "Record identity is not the same as business similarity.",
    "The method recovers the known current-source lineage.",
    "zero record overlap supports a temporal internal replication only",
    "No annotation, verifier, detector, AUPRC, F1, or other confirmation metric was created or changed.",
    "overflow-x:auto;",
    "overflow-wrap:anywhere;",
]
FORBIDDEN_HTML_FRAGMENTS = [
    "production-ready",
    "dataset gate passed",
    "external independence verified",
    "confirmation AUPRC",
    "confirmation F1",
    "new benchmark result",
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


def check_multiset_identity(
    failures: list[dict[str, Any]],
    name: str,
    comparison: dict[str, Any],
    left_rows: int,
    right_rows: int,
) -> None:
    if comparison["left_only_row_count"] + comparison["multiset_overlap_row_count"] != left_rows:
        add_failure(failures, f"{name}_left_reconciliation", comparison)
    if comparison["right_only_row_count"] + comparison["multiset_overlap_row_count"] != right_rows:
        add_failure(failures, f"{name}_right_reconciliation", comparison)


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path in [REPORT_PATH, HTML_PATH, METHODOLOGY_PATH]:
        if not path.exists():
            add_failure(failures, "missing_required_file", repo_path(path))
    if failures:
        validation = {
            "status": "confirmation_dataset_overlap_validation_failed",
            "num_failures": len(failures),
            "failures": failures,
        }
        VALIDATION_PATH.write_text(json.dumps(validation, indent=2), encoding="utf-8")
        raise SystemExit(1)

    report = load_json(REPORT_PATH)
    if report.get("status") != "historical_record_overlap_proof_complete":
        add_failure(failures, "report_status", report.get("status"))
    if report.get("scope") != "normalized historical record-overlap proof against the current Online Retail lineage":
        add_failure(failures, "report_scope", report.get("scope"))

    profiles = report.get("dataset_profiles", {})
    for name, expected in EXPECTED_PROFILES.items():
        profile = profiles.get(name, {})
        actual = (
            profile.get("row_count"),
            profile.get("unique_fingerprint_count"),
            profile.get("duplicate_extra_row_count"),
        )
        if actual != expected:
            add_failure(failures, f"profile_{name}", {"expected": expected, "actual": actual})
        for key, expected_hash in EXPECTED_MANIFESTS[name].items():
            if profile.get(key) != expected_hash:
                add_failure(
                    failures,
                    f"manifest_{name}_{key}",
                    {"expected": expected_hash, "actual": profile.get(key)},
                )

    canonical = report.get("record_overlap", {}).get("canonical_eight_field", {})
    date_blind = report.get("record_overlap", {}).get("date_blind_seven_field_sensitivity", {})
    business = report.get("descriptive_similarity", {}).get("business_pattern_five_field", {})
    lineage = report.get("lineage_calibration", {}).get("comparison", {})
    for name, values in [("canonical", canonical), ("date_blind", date_blind)]:
        if values.get("unique_fingerprint_overlap_count") != 0 or values.get("multiset_overlap_row_count") != 0:
            add_failure(failures, f"{name}_overlap_not_zero", values)
        check_multiset_identity(failures, name, values, 502_938, 541_909)

    expected_business = {
        "unique_fingerprint_overlap_count": 27_153,
        "multiset_overlap_row_count": 195_814,
        "left_only_row_count": 307_124,
        "right_only_row_count": 346_095,
    }
    for key, expected in expected_business.items():
        if business.get(key) != expected:
            add_failure(failures, f"business_pattern_{key}", {"expected": expected, "actual": business.get(key)})
    check_multiset_identity(failures, "business_pattern", business, 502_938, 541_909)

    expected_lineage = {
        "unique_fingerprint_overlap_count": 536_641,
        "multiset_overlap_row_count": 541_909,
        "left_only_row_count": 0,
        "right_only_row_count": 1,
    }
    for key, expected in expected_lineage.items():
        if lineage.get(key) != expected:
            add_failure(failures, f"lineage_{key}", {"expected": expected, "actual": lineage.get(key)})
    check_multiset_identity(failures, "lineage", lineage, 541_909, 541_910)

    entities = report.get("descriptive_similarity", {}).get("entity_overlap", {})
    for field, expected in EXPECTED_ENTITIES.items():
        values = entities.get(field, {})
        actual = (
            values.get("prior_distinct_count"),
            values.get("current_distinct_count"),
            values.get("shared_distinct_count"),
        )
        if actual != expected:
            add_failure(failures, f"entity_{field}", {"expected": expected, "actual": actual})

    temporal = report.get("temporal_boundary", {})
    if temporal.get("strict_prior_precedes_current") is not True or temporal.get("boundary_gap_seconds") != 46_260:
        add_failure(failures, "temporal_boundary", temporal)

    checks = report.get("critical_checks", {})
    if not checks or not all(value is True for value in checks.values()):
        add_failure(failures, "critical_checks", checks)
    if report.get("failed_critical_checks") != []:
        add_failure(failures, "failed_critical_checks", report.get("failed_critical_checks"))

    decision = report.get("research_decision", {})
    expected_flags = {
        "historical_record_overlap_check_complete": True,
        "zero_normalized_record_overlap_verified": True,
        "strict_window_is_unseen_at_normalized_record_level": True,
        "dataset_gate_status": "pending_context_feasibility",
        "execution_ready": False,
    }
    for key, expected in expected_flags.items():
        if decision.get(key) != expected:
            add_failure(failures, f"decision_{key}", {"expected": expected, "actual": decision.get(key)})

    for key, expected in {
        "historical_overlap_check_complete": True,
        "context_feasibility_check_complete": False,
        "context_manifest_created": False,
        "prompt_created": False,
        "model_run_performed": False,
        "new_metrics_reported": False,
        "execution_ready": False,
        "no_new_results": True,
    }.items():
        if report.get(key) != expected:
            add_failure(failures, f"boundary_{key}", {"expected": expected, "actual": report.get(key)})

    public_text = REPORT_PATH.read_text(encoding="utf-8")
    if contains_local_path(public_text):
        add_failure(failures, "public_report_contains_local_path", True)
    privacy = report.get("privacy", {})
    if privacy != {
        "contains_raw_identifier_values": False,
        "contains_row_fingerprint_values": False,
        "contains_only_aggregate_counts_and_inventory_manifest_hashes": True,
    }:
        add_failure(failures, "privacy_contract", privacy)

    local_status = "not_available_ci_public_validation_only"
    if LOCAL_PROOF_PATH.exists():
        local_status = "validated"
        actual_hash = sha256_file(LOCAL_PROOF_PATH)
        if actual_hash != EXPECTED_LOCAL_PROOF_SHA256:
            add_failure(
                failures,
                "local_proof_hash",
                {"expected": EXPECTED_LOCAL_PROOF_SHA256, "actual": actual_hash},
            )
        if report.get("local_proof", {}).get("sha256") != actual_hash:
            add_failure(failures, "local_proof_report_hash", report.get("local_proof"))
        local = load_json(LOCAL_PROOF_PATH)
        for key in [
            "fingerprint_definitions",
            "dataset_profiles",
            "temporal_boundary",
            "record_overlap",
            "descriptive_similarity",
            "lineage_calibration",
            "privacy",
        ]:
            if local.get(key) != report.get(key):
                add_failure(failures, f"local_public_reconciliation_{key}", True)

    methodology = load_json(METHODOLOGY_PATH)
    locked = methodology.get("locked_public_results", {})
    if locked != {
        "exploratory_max_test_auprc": 0.835073,
        "exploratory_max_test_auprc_signal": "one_minus_min_top2_margin",
        "exploratory_max_test_f1": 0.779412,
        "exploratory_max_test_f1_signal": "mean_token_entropy",
        "aligned_span_count": 205,
        "test_span_count": 103,
    }:
        add_failure(failures, "historical_metrics_drift", locked)

    html_text = HTML_PATH.read_text(encoding="utf-8")
    for fragment in REQUIRED_HTML_FRAGMENTS:
        if fragment not in html_text:
            add_failure(failures, "html_missing_fragment", fragment)
    lower_html = html_text.lower()
    for fragment in FORBIDDEN_HTML_FRAGMENTS:
        if fragment.lower() in lower_html:
            add_failure(failures, "html_forbidden_fragment", fragment)
    if contains_local_path(html_text):
        add_failure(failures, "html_contains_local_path", True)
    parser = StructureParser()
    parser.feed(html_text)
    for tag, minimum in {"section": 7, "table": 3, "h1": 1, "h2": 6}.items():
        if parser.tag_counts.get(tag, 0) < minimum:
            add_failure(failures, f"html_structure_{tag}", parser.tag_counts.get(tag, 0))

    validation = {
        "status": (
            "confirmation_dataset_overlap_validation_passed"
            if not failures
            else "confirmation_dataset_overlap_validation_failed"
        ),
        "report_path": repo_path(REPORT_PATH),
        "html_path": repo_path(HTML_PATH),
        "local_proof_status": local_status,
        "canonical_overlap_rows": canonical.get("multiset_overlap_row_count"),
        "date_blind_overlap_rows": date_blind.get("multiset_overlap_row_count"),
        "business_pattern_overlap_rows": business.get("multiset_overlap_row_count"),
        "lineage_overlap_rows": lineage.get("multiset_overlap_row_count"),
        "existing_metrics_unchanged": not any(item["name"] == "historical_metrics_drift" for item in failures),
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
