from __future__ import annotations

import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import contains_local_path, repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = PROJECT_ROOT / "configs" / "confirmation_dataset_source_audit_v1.json"
PROTOCOL_PATH = PROJECT_ROOT / "configs" / "confirmation_set_v1_protocol.json"
ACQUISITION_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_acquisition_report.json"
STRUCTURE_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_structure_report.json"
QUALITY_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_quality_report.json"
QUALITY_HTML_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_quality.html"
OVERLAP_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_overlap_report.json"
OVERLAP_HTML_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_overlap.html"
FEASIBILITY_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility_report.json"
FEASIBILITY_HTML_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility.html"
FEASIBILITY_VALIDATION_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility_validation.json"
LOCAL_QUALITY_PATH = PROJECT_ROOT / "data" / "processed" / "data_quality_report.json"
REPORTS_DIR = PROJECT_ROOT / "reports"
HTML_PATH = REPORTS_DIR / "bizhallu_confirmation_dataset_source_audit.html"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_confirmation_dataset_source_audit_summary.json"
VALIDATION_PATH = REPORTS_DIR / "bizhallu_confirmation_dataset_source_audit_validation.json"


EXPECTED_CANDIDATE_IDS = {
    "current_online_retail_new_contexts",
    "uci_online_retail_ii_prior_period",
    "completejourney_external",
    "olist_external",
    "nyc_tlc_domain_transfer",
    "jhu_future_domain_extension",
}

EXPECTED_CRITERION_STATUSES = {
    "pass_metadata": 3,
    "conditional_pass": 1,
    "pass_local_profile_with_controls": 1,
    "pass_outcome_blind_capacity_profile": 1,
}

REQUIRED_HTML_FRAGMENTS = [
    "Confirmation Dataset Source Audit v1",
    "Source quality and historical record separation are verified.",
    "Online Retail II",
    "2009-12-01T00:00:00",
    "2010-12-01T00:00:00",
    "prospective_temporal_internal_replication",
    "Complete Journey",
    "Metadata conflict matters.",
    "135,080 missing customer IDs",
    "502,938",
    "Schema drift recorded.",
    "Aggregate use is conditionally suitable after documented controls.",
    "100,207 customer IDs",
    "6,544 normalized exact duplicate extra rows",
    "2,057 negative-quantity rows",
    "GBP 9,266,060.76",
    "Nine checks are complete; public privacy stays active.",
    "Freeze the manifest and split next; do not generate.",
    "Read the aggregate-only overlap proof.",
    "Read the aggregate-only capacity proof.",
    "48 unique complete-week context slots",
    "The raw files remain local and Git-ignored.",
    ".panel { min-width:0;",
    "overflow-x:auto;",
    "overflow-wrap:anywhere;",
    "@media (max-width:820px)",
    "h1 { font-size:40px; } h2 { font-size:28px; }",
]

FORBIDDEN_HTML_FRAGMENTS = [
    "Confirmation Set v1 has started.",
    "The selected source is execution-ready.",
    "Thirty-six final contexts have already been selected or assigned.",
    "production-ready hallucination detector",
    "new confirmation AUPRC",
    "clamp(",
    "No candidate file was downloaded",
]


class HTMLCheckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.seen_tags = 0
        self.tag_counts: Counter[str] = Counter()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.seen_tags += 1
        self.tag_counts[tag] += 1
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.hrefs.append(href)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add_failure(failures: list[dict[str, Any]], name: str, detail: Any) -> None:
    failures.append({"name": name, "detail": detail})


def main() -> None:
    failures: list[dict[str, Any]] = []
    required_paths = [
        AUDIT_PATH,
        PROTOCOL_PATH,
        ACQUISITION_PATH,
        STRUCTURE_PATH,
        QUALITY_PATH,
        QUALITY_HTML_PATH,
        OVERLAP_PATH,
        OVERLAP_HTML_PATH,
        FEASIBILITY_PATH,
        FEASIBILITY_HTML_PATH,
        FEASIBILITY_VALIDATION_PATH,
        LOCAL_QUALITY_PATH,
        HTML_PATH,
        SUMMARY_PATH,
    ]
    for path in required_paths:
        if not path.exists():
            add_failure(failures, "required_file_missing", repo_path(path))

    audit = load_json(AUDIT_PATH) if AUDIT_PATH.exists() else {}
    protocol = load_json(PROTOCOL_PATH) if PROTOCOL_PATH.exists() else {}
    acquisition = load_json(ACQUISITION_PATH) if ACQUISITION_PATH.exists() else {}
    structure = load_json(STRUCTURE_PATH) if STRUCTURE_PATH.exists() else {}
    quality = load_json(QUALITY_PATH) if QUALITY_PATH.exists() else {}
    overlap = load_json(OVERLAP_PATH) if OVERLAP_PATH.exists() else {}
    feasibility = load_json(FEASIBILITY_PATH) if FEASIBILITY_PATH.exists() else {}
    local_quality = load_json(LOCAL_QUALITY_PATH) if LOCAL_QUALITY_PATH.exists() else {}
    summary = load_json(SUMMARY_PATH) if SUMMARY_PATH.exists() else {}
    html_text = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""

    if html_text:
        parser = HTMLCheckParser()
        parser.feed(html_text)
        if parser.seen_tags == 0:
            add_failure(failures, "html_parse", "no tags parsed")
        expected_tag_counts = {"html": 1, "head": 1, "body": 1, "main": 1, "h1": 1}
        for tag, expected_count in expected_tag_counts.items():
            if parser.tag_counts[tag] != expected_count:
                add_failure(
                    failures,
                    "html_tag_count",
                    {"tag": tag, "expected": expected_count, "actual": parser.tag_counts[tag]},
                )
        if parser.tag_counts["section"] < 9 or parser.tag_counts["table"] != 4:
            add_failure(
                failures,
                "html_report_structure",
                {
                    "section_count": parser.tag_counts["section"],
                    "table_count": parser.tag_counts["table"],
                },
            )
        for href in parser.hrefs:
            if href.startswith("./") and not (HTML_PATH.parent / href[2:]).exists():
                add_failure(failures, "broken_internal_html_link", href)
        for fragment in REQUIRED_HTML_FRAGMENTS:
            if fragment not in html_text:
                add_failure(failures, "required_html_fragment_missing", fragment)
        for fragment in FORBIDDEN_HTML_FRAGMENTS:
            if fragment in html_text:
                add_failure(failures, "forbidden_html_fragment", fragment)
        if contains_local_path(html_text):
            add_failure(failures, "local_path_in_html", repo_path(HTML_PATH))

    expected_audit_boundary = {
        "status": "dataset_source_selected_and_audited_context_manifest_pending",
        "audit_date": "2026-09-01",
        "no_new_results": True,
        "download_performed": True,
        "acquisition_verified": True,
        "structure_profile_complete": True,
        "quality_profile_complete": True,
        "historical_overlap_check_complete": True,
        "context_feasibility_check_complete": True,
        "local_profile_complete": True,
        "execution_ready": False,
    }
    for key, expected in expected_audit_boundary.items():
        if audit.get(key) != expected:
            add_failure(
                failures,
                "audit_boundary_mismatch",
                {"field": key, "expected": expected, "actual": audit.get(key)},
            )

    decision = audit.get("decision", {})
    expected_decision = {
        "selection_status": "selected_source_audited_context_manifest_pending",
        "selected_candidate_id": "uci_online_retail_ii_prior_period",
        "selected_role": "prospective_temporal_internal_replication",
        "dataset_gate_status": "complete",
    }
    for key, expected in expected_decision.items():
        if decision.get(key) != expected:
            add_failure(
                failures,
                "decision_mismatch",
                {"field": key, "expected": expected, "actual": decision.get(key)},
            )

    expected_window = {
        "start_inclusive": "2009-12-01T00:00:00",
        "end_exclusive": "2010-12-01T00:00:00",
        "reason": (
            "The current BizHallu source begins on 2010-12-01. The strict end-exclusive cutoff creates "
            "a 12-hour-51-minute source boundary, and the completed canonical plus date-blind fingerprint "
            "checks verify zero repeated records across it."
        ),
    }
    if decision.get("allowed_time_window") != expected_window:
        add_failure(failures, "selected_window_mismatch", decision.get("allowed_time_window"))

    candidates = audit.get("candidates", [])
    candidate_ids = {item.get("candidate_id") for item in candidates}
    if candidate_ids != EXPECTED_CANDIDATE_IDS:
        add_failure(failures, "candidate_ids", sorted(str(item) for item in candidate_ids))
    if len(candidates) != 6:
        add_failure(failures, "candidate_count", len(candidates))

    selected = next(
        (item for item in candidates if item.get("candidate_id") == decision.get("selected_candidate_id")),
        {},
    )
    selected_identity = selected.get("source_identity", {})
    expected_selected_identity = {
        "doi": "10.24432/C5CG6D",
        "documented_instances_full_workbook": 1067371,
        "documented_period_full_workbook": "2009-12-01 through 2011-12-09",
        "documented_file": "online_retail_II.xlsx",
        "documented_file_size": "43.5 MB",
        "license": "CC BY 4.0",
        "official_missing_value_flag": True,
    }
    if selected_identity != expected_selected_identity:
        add_failure(failures, "selected_source_identity", selected_identity)
    if selected.get("official_source_url") != "https://archive.ics.uci.edu/dataset/502/online+retail":
        add_failure(failures, "selected_source_url", selected.get("official_source_url"))
    if selected.get("decision_status") != "selected_source_audited_context_manifest_pending":
        add_failure(failures, "selected_decision_status", selected.get("decision_status"))

    criteria = audit.get("source_acceptance_criteria", [])
    criterion_counts = dict(
        Counter(item.get("selected_candidate_status") for item in criteria)
    )
    if criterion_counts != EXPECTED_CRITERION_STATUSES:
        add_failure(failures, "criterion_status_counts", criterion_counts)
    expected_criterion_ids = {
        "row_level_deterministic_gold",
        "documented_time_entity_quantity_value",
        "completeness_and_duplicates_auditable",
        "permitted_research_use",
        "no_sensitive_personal_data_required",
        "minimum_48_disjoint_contexts",
    }
    if {item.get("criterion_id") for item in criteria} != expected_criterion_ids:
        add_failure(failures, "criterion_ids", criteria)

    checks = audit.get("required_local_profile_checks", [])
    if len(checks) != 10:
        add_failure(failures, "local_profile_check_count", len(checks))
    expected_check_ids = {
        "official_acquisition_and_hash",
        "workbook_structure",
        "strict_prior_period_filter",
        "completeness",
        "duplicates_and_grain",
        "business_rule_validity",
        "historical_overlap",
        "monthly_coverage",
        "context_feasibility",
        "public_privacy_boundary",
    }
    check_ids = {item.get("check_id") for item in checks}
    if check_ids != expected_check_ids:
        add_failure(
            failures,
            "local_profile_check_ids",
            {
                "missing": sorted(expected_check_ids - check_ids),
                "unexpected": sorted(str(item) for item in check_ids - expected_check_ids),
            },
        )

    references = audit.get("source_references", [])
    if len(references) != 10:
        add_failure(failures, "source_reference_count", len(references))
    reference_ids = [item.get("source_id") for item in references]
    if len(reference_ids) != len(set(reference_ids)):
        add_failure(failures, "duplicate_source_reference_id", reference_ids)
    for item in references:
        url = item.get("url")
        if not isinstance(url, str) or not url:
            add_failure(failures, "invalid_source_reference_url", item)
        elif not (url.startswith("https://") or url == "data/processed/data_quality_report.json"):
            add_failure(failures, "noncanonical_source_reference_url", url)

    expected_local_quality = {
        "raw_shape": [541909, 8],
        "date_min": "2010-12-01 08:26:00",
        "missing_description": 1454,
        "missing_customer_id": 135080,
        "duplicate_rows": 5268,
    }
    observed_local_quality = {
        "raw_shape": local_quality.get("raw_shape"),
        "date_min": local_quality.get("date_min"),
        "missing_description": local_quality.get("missing_values", {}).get("Description"),
        "missing_customer_id": local_quality.get("missing_values", {}).get("CustomerID"),
        "duplicate_rows": local_quality.get("duplicate_rows"),
    }
    if observed_local_quality != expected_local_quality:
        add_failure(failures, "local_quality_evidence_drift", observed_local_quality)

    strategy = protocol.get("dataset_strategy", {})
    expected_strategy = {
        "selection_status": "selected_source_audited_context_manifest_pending",
        "source_audit": "configs/confirmation_dataset_source_audit_v1.json",
        "acquisition_report": "reports/bizhallu_confirmation_dataset_acquisition_report.json",
        "structure_report": "reports/bizhallu_confirmation_dataset_structure_report.json",
        "quality_report": "reports/bizhallu_confirmation_dataset_quality_report.json",
        "quality_html": "reports/bizhallu_confirmation_dataset_quality.html",
        "overlap_report": "reports/bizhallu_confirmation_dataset_overlap_report.json",
        "overlap_html": "reports/bizhallu_confirmation_dataset_overlap.html",
        "context_feasibility_config": "configs/confirmation_context_feasibility_v1.json",
        "context_feasibility_report": "reports/bizhallu_confirmation_context_feasibility_report.json",
        "context_feasibility_html": "reports/bizhallu_confirmation_context_feasibility.html",
        "context_feasibility_validation": "reports/bizhallu_confirmation_context_feasibility_validation.json",
        "precision_review_config": "configs/confirmation_precision_review_v1.json",
        "precision_review_report": "reports/bizhallu_confirmation_precision_review_report.json",
        "precision_review_html": "reports/bizhallu_confirmation_precision_review.html",
        "precision_scope_amendment": "configs/confirmation_precision_scope_amendment_v1.json",
        "selected_candidate_id": "uci_online_retail_ii_prior_period",
        "selected_candidate_role": "prospective_temporal_internal_replication",
        "selected_candidate_gate_status": "complete",
        "official_acquisition_verified": True,
        "structure_and_date_window_verified": True,
        "quality_profile_verified": True,
        "historical_record_overlap_verified": True,
        "outcome_blind_context_feasibility_verified": True,
        "outcome_blind_precision_review_completed": True,
        "precision_review_scope_downgraded_to_estimation": True,
        "canonical_record_overlap_row_count": 0,
        "date_blind_record_overlap_row_count": 0,
        "business_pattern_overlap_row_count": 195814,
        "lineage_positive_control_overlap_row_count": 541909,
        "strict_window_row_count": 502938,
        "strict_window_missing_description_rows": 2821,
        "strict_window_missing_customer_id_rows": 100207,
        "strict_window_normalized_exact_duplicate_extra_rows": 6544,
        "strict_window_valid_net_revenue_line_count": 492887,
        "strict_window_net_revenue_gbp": 9266060.76,
        "complete_calendar_week_count": 51,
        "observed_complete_week_count": 50,
        "required_period_disjoint_context_count": 48,
        "maximum_period_to_slot_matching_count": 48,
        "minimum_hall_capacity_slack": 2,
        "source_feasible_question_families": [
            "net_revenue_reconciliation_by_period",
            "product_return_rate_comparison",
            "country_product_exposure",
        ],
        "blocked_question_families": ["customer_revenue_concentration"],
    }
    for key, expected in expected_strategy.items():
        if strategy.get(key) != expected:
            add_failure(
                failures,
                "protocol_dataset_strategy_mismatch",
                {"field": key, "expected": expected, "actual": strategy.get(key)},
            )
    option_ids = {item.get("option_id") for item in strategy.get("options", [])}
    expected_option_ids = {
        "same_dataset_new_contexts",
        "same_source_prior_period",
        "second_public_transaction_dataset",
        "jhu_domain_extension",
    }
    if option_ids != expected_option_ids:
        add_failure(failures, "protocol_option_ids", sorted(str(item) for item in option_ids))

    gates = protocol.get("execution_gates", [])
    dataset_gate = next(
        (item for item in gates if item.get("gate") == "dataset_source_selected_and_audited"),
        {},
    )
    if dataset_gate.get("status") != "complete":
        add_failure(failures, "dataset_gate_status", dataset_gate)
    if "official workbook acquired and hashed" not in dataset_gate.get("progress", ""):
        add_failure(failures, "dataset_gate_progress", dataset_gate)
    if "structure, strict-window completeness" not in dataset_gate.get("progress", ""):
        add_failure(failures, "dataset_gate_quality_progress", dataset_gate)
    if "capacity for 48 unique complete-week contexts verified" not in dataset_gate.get("progress", ""):
        add_failure(failures, "dataset_gate_capacity_progress", dataset_gate)
    if dataset_gate.get("blocking_requirements") != []:
        add_failure(failures, "dataset_gate_blockers", dataset_gate)
    if protocol.get("execution_ready") is not False or protocol.get("no_new_results") is not True:
        add_failure(failures, "protocol_execution_boundary", protocol)

    expected_summary = {
        "status": "confirmation_dataset_source_audit_v1_ready",
        "audit_date": "2026-09-01",
        "desk_audit_complete": True,
        "download_performed": True,
        "acquisition_verified": True,
        "structure_profile_complete": True,
        "quality_profile_complete": True,
        "historical_overlap_check_complete": True,
        "context_feasibility_check_complete": True,
        "local_profile_complete": True,
        "execution_ready": False,
        "no_new_results": True,
        "selection_status": "selected_source_audited_context_manifest_pending",
        "selected_candidate_id": "uci_online_retail_ii_prior_period",
        "selected_candidate_name": "UCI Online Retail II, strict prior-period window",
        "selected_candidate_role": "prospective_temporal_internal_replication",
        "selected_source_url": "https://archive.ics.uci.edu/dataset/502/online+retail",
        "selected_window": "2009-12-01 inclusive through 2010-12-01 exclusive",
        "dataset_gate_status": "complete",
        "zip_sha256": "572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb",
        "xlsx_sha256": "bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980",
        "workbook_total_data_rows": 1067371,
        "strict_window_row_count": 502938,
        "strict_window_date_min": "2009-12-01 07:45:00",
        "strict_window_date_max": "2010-11-30 19:35:00",
        "metadata_header_drift_detected": True,
        "required_header_aliases": {
            "Invoice": "InvoiceNo",
            "Price": "UnitPrice",
            "Customer ID": "CustomerID",
        },
        "quality_decision": "conditionally_suitable_for_aggregate_business_analysis_after_documented_controls",
        "month_count": 12,
        "missing_description_rows": 2821,
        "missing_customer_id_rows": 100207,
        "normalized_exact_duplicate_extra_rows": 6544,
        "negative_quantity_rows_without_cancel_prefix": 2057,
        "valid_net_revenue_line_count": 492887,
        "net_revenue_gbp": 9266060.76,
        "overlap_report_path": "reports/bizhallu_confirmation_dataset_overlap_report.json",
        "canonical_record_overlap_row_count": 0,
        "date_blind_record_overlap_row_count": 0,
        "business_pattern_overlap_row_count": 195814,
        "lineage_positive_control_overlap_row_count": 541909,
        "context_feasibility_report_path": "reports/bizhallu_confirmation_context_feasibility_report.json",
        "complete_calendar_week_count": 51,
        "observed_complete_week_count": 50,
        "required_context_count": 48,
        "maximum_slot_matching_count": 48,
        "minimum_hall_capacity_slack": 2,
        "source_feasible_family_count": 3,
        "blocked_family_count": 1,
        "candidate_count": 6,
        "external_shortlist_count": 2,
        "source_reference_count": 10,
        "selected_criterion_status_counts": EXPECTED_CRITERION_STATUSES,
        "pending_criterion_ids": [],
        "local_profile_check_count": 10,
        "next_authorized_action": "Freeze only the deterministic 6 pilot, 15 development, and 27 confirmation context manifest and seeded split. Do not create questions, prompts, or model outputs yet.",
        "num_failures": 0,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            add_failure(
                failures,
                "summary_value_mismatch",
                {"field": key, "expected": expected, "actual": summary.get(key)},
            )

    expected_check_statuses = {
        "official_acquisition_and_hash": "completed",
        "workbook_structure": "completed",
        "strict_prior_period_filter": "completed",
        "completeness": "completed",
        "duplicates_and_grain": "completed",
        "business_rule_validity": "completed",
        "historical_overlap": "completed",
        "monthly_coverage": "completed",
        "context_feasibility": "completed",
        "public_privacy_boundary": "active",
    }
    observed_check_statuses = {item.get("check_id"): item.get("status") for item in checks}
    if observed_check_statuses != expected_check_statuses:
        add_failure(failures, "local_profile_check_statuses", observed_check_statuses)

    expected_acquisition_evidence = {
        "zip_sha256": "572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb",
        "xlsx_sha256": "bcbe73b35f5b7babf197fb0cb983a11f5d9ff929078d4aa53d171b1f2df2e980",
        "workbook_total_data_rows": 1067371,
        "strict_window_row_count": 502938,
    }
    for key, expected in expected_acquisition_evidence.items():
        if audit.get("acquisition_evidence", {}).get(key) != expected:
            add_failure(
                failures,
                "acquisition_evidence",
                {"field": key, "expected": expected, "actual": audit.get("acquisition_evidence", {}).get(key)},
            )
    if acquisition.get("raw_artifacts", {}).get("xlsx", {}).get("sha256") != expected_acquisition_evidence["xlsx_sha256"]:
        add_failure(failures, "acquisition_report_hash", acquisition.get("raw_artifacts"))
    if structure.get("date_scan", {}).get("strict_window_row_count") != 502938:
        add_failure(failures, "structure_report_window_count", structure.get("date_scan"))

    expected_quality_evidence = {
        "quality_decision": "conditionally_suitable_for_aggregate_business_analysis_after_documented_controls",
        "strict_window_row_count": 502938,
        "month_count": 12,
        "missing_description_rows": 2821,
        "missing_customer_id_rows": 100207,
        "normalized_exact_duplicate_extra_rows": 6544,
        "cancel_prefix_rows": 9877,
        "negative_quantity_rows": 11933,
        "negative_quantity_rows_without_cancel_prefix": 2057,
        "valid_net_revenue_line_count": 492887,
        "net_revenue_gbp": 9266060.76,
        "local_strict_table_sha256": "ab875caaf527d5d528f4edad4fd372b15d4e1ae9c39f6cea20f8211178e256fc",
    }
    observed_quality_report = {
        "quality_decision": quality.get("quality_decision"),
        "strict_window_row_count": quality.get("source", {}).get("strict_window_row_count"),
        "month_count": quality.get("monthly_coverage", {}).get("month_count"),
        "missing_description_rows": quality.get("completeness", {}).get("by_column", {}).get("Description", {}).get("missing_or_blank_count"),
        "missing_customer_id_rows": quality.get("completeness", {}).get("by_column", {}).get("CustomerID", {}).get("missing_or_blank_count"),
        "normalized_exact_duplicate_extra_rows": quality.get("duplicates_and_grain", {}).get("normalized_exact_row_profile", {}).get("duplicate_extra_rows"),
        "cancel_prefix_rows": quality.get("business_rules", {}).get("cancel_invoice_row_count"),
        "negative_quantity_rows": quality.get("business_rules", {}).get("negative_quantity_row_count"),
        "negative_quantity_rows_without_cancel_prefix": quality.get("business_rules", {}).get("cancellation_prefix_crosscheck", {}).get("no_cancel_prefix_and_negative_quantity"),
        "valid_net_revenue_line_count": quality.get("analysis_policy_reconciliation", {}).get("valid_net_revenue_line_count"),
        "net_revenue_gbp": quality.get("analysis_policy_reconciliation", {}).get("net_revenue"),
        "local_strict_table_sha256": quality.get("local_strict_table", {}).get("sha256"),
    }
    if observed_quality_report != expected_quality_evidence:
        add_failure(failures, "quality_report_evidence_drift", observed_quality_report)
    observed_audit_quality = {
        key: audit.get("quality_evidence", {}).get(key) for key in expected_quality_evidence
    }
    if observed_audit_quality != expected_quality_evidence:
        add_failure(failures, "audit_quality_evidence_drift", observed_audit_quality)
    if quality.get("quality_profile_complete") is not True:
        add_failure(failures, "quality_profile_not_complete", quality.get("quality_profile_complete"))
    if quality.get("historical_overlap_check_complete") is not False:
        add_failure(failures, "quality_overlap_boundary", quality.get("historical_overlap_check_complete"))
    if quality.get("context_feasibility_check_complete") is not False:
        add_failure(failures, "quality_context_boundary", quality.get("context_feasibility_check_complete"))

    expected_overlap_evidence = {
        "status": "historical_record_overlap_proof_complete",
        "canonical_overlap_rows": 0,
        "date_blind_overlap_rows": 0,
        "business_pattern_overlap_rows": 195814,
        "lineage_overlap_rows": 541909,
        "context_feasibility_check_complete": False,
        "execution_ready": False,
        "no_new_results": True,
    }
    observed_overlap_evidence = {
        "status": overlap.get("status"),
        "canonical_overlap_rows": overlap.get("record_overlap", {}).get("canonical_eight_field", {}).get("multiset_overlap_row_count"),
        "date_blind_overlap_rows": overlap.get("record_overlap", {}).get("date_blind_seven_field_sensitivity", {}).get("multiset_overlap_row_count"),
        "business_pattern_overlap_rows": overlap.get("descriptive_similarity", {}).get("business_pattern_five_field", {}).get("multiset_overlap_row_count"),
        "lineage_overlap_rows": overlap.get("lineage_calibration", {}).get("comparison", {}).get("multiset_overlap_row_count"),
        "context_feasibility_check_complete": overlap.get("context_feasibility_check_complete"),
        "execution_ready": overlap.get("execution_ready"),
        "no_new_results": overlap.get("no_new_results"),
    }
    if observed_overlap_evidence != expected_overlap_evidence:
        add_failure(failures, "overlap_report_evidence_drift", observed_overlap_evidence)

    expected_feasibility_evidence = {
        "status": "outcome_blind_context_feasibility_complete",
        "observed_complete_period_count": 50,
        "required_total_context_count": 48,
        "maximum_slot_matching_count": 48,
        "minimum_hall_capacity_slack": 2,
        "context_manifest_created": False,
        "execution_ready": False,
        "no_new_results": True,
    }
    observed_feasibility_evidence = {
        "status": feasibility.get("status"),
        "observed_complete_period_count": feasibility.get("source_capacity", {}).get("observed_complete_period_count"),
        "required_total_context_count": feasibility.get("capacity_proof", {}).get("required_total_context_count"),
        "maximum_slot_matching_count": feasibility.get("capacity_proof", {}).get("maximum_slot_matching_count"),
        "minimum_hall_capacity_slack": feasibility.get("capacity_proof", {}).get("minimum_hall_capacity_slack"),
        "context_manifest_created": feasibility.get("context_manifest_created"),
        "execution_ready": feasibility.get("execution_ready"),
        "no_new_results": feasibility.get("no_new_results"),
    }
    if observed_feasibility_evidence != expected_feasibility_evidence:
        add_failure(failures, "context_feasibility_evidence_drift", observed_feasibility_evidence)

    for artifact_path, payload in [
        (AUDIT_PATH, audit),
        (ACQUISITION_PATH, acquisition),
        (STRUCTURE_PATH, structure),
        (QUALITY_PATH, quality),
        (OVERLAP_PATH, overlap),
        (FEASIBILITY_PATH, feasibility),
        (SUMMARY_PATH, summary),
    ]:
        if contains_local_path(json.dumps(payload, ensure_ascii=True)):
            add_failure(failures, "local_path_in_json", repo_path(artifact_path))

    validation = {
        "status": (
            "confirmation_dataset_source_audit_validation_passed"
            if not failures
            else "confirmation_dataset_source_audit_validation_failed"
        ),
        "audit_path": repo_path(AUDIT_PATH),
        "protocol_path": repo_path(PROTOCOL_PATH),
        "html_path": repo_path(HTML_PATH),
        "summary_path": repo_path(SUMMARY_PATH),
        "desk_audit_complete": True,
        "selected_candidate_id": decision.get("selected_candidate_id"),
        "dataset_gate_status": dataset_gate.get("status"),
        "download_performed": True,
        "acquisition_verified": True,
        "structure_profile_complete": True,
        "quality_profile_complete": True,
        "historical_overlap_check_complete": True,
        "context_feasibility_check_complete": True,
        "local_profile_complete": True,
        "execution_ready": False,
        "no_new_results": True,
        "candidate_count": len(candidates),
        "local_profile_check_count": len(checks),
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(
        json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
