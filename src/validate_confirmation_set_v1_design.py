from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import contains_local_path, repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = PROJECT_ROOT / "configs" / "confirmation_set_v1_protocol.json"
METHODOLOGY_SUMMARY_PATH = PROJECT_ROOT / "reports" / "bizhallu_methodology_hardening_summary.json"
DATASET_AUDIT_SUMMARY_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_source_audit_summary.json"
CONTEXT_FEASIBILITY_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility_report.json"
PRECISION_REVIEW_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_precision_review_report.json"
CONTEXT_MANIFEST_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_manifest_report.json"
QUESTION_DESIGN_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_question_design_report.json"
REPORTS_DIR = PROJECT_ROOT / "reports"
HTML_PATH = REPORTS_DIR / "bizhallu_confirmation_set_v1_design.html"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_confirmation_set_v1_design_summary.json"
VALIDATION_PATH = REPORTS_DIR / "bizhallu_confirmation_set_v1_design_validation.json"

REQUIRED_HTML_FRAGMENTS = [
    "Confirmation Set v1 starts before the model answers.",
    "Not execution-ready.",
    "Outcome-blind sampling",
    "Context-separated evaluation",
    "Two human reviewers",
    "sealed confirmation labels",
    "same_dataset_new_contexts",
    "same_source_prior_period",
    "second_public_transaction_dataset",
    "jhu_domain_extension",
    "96 generations",
    "only 84 enter the main study",
    "permanently excluded from confirmation metrics",
    "The precision review rejected a superiority design",
    "does not preregister a superiority claim",
    "All 96 full payloads and all 96 normalized evidence-table contents have unique fingerprints",
    "matches 0 of 66 unique historical full100 evidence contents",
    "One selected reconciliation row has a cancellation invoice prefix but positive quantity and revenue",
    "One of 64 selected product evidence rows",
    "maximum 156.25%",
    "one of 32 candidate tables happens to be fully revenue-descending by chance",
    "The ordering algorithm never reads the gold rank",
    "every in-scope business-fact claim",
    "Do not hide oracle spans inside an end-to-end claim.",
    "Oracle-span diagnostics",
    "Claim extraction",
    "Evidence verification",
    "continuous unsupported-risk score",
    "End-to-end audit",
    "context-level BCa bootstrap",
    "Semantic Entropy",
    "TOHA",
    "3 gates are complete; 4 remain pending.",
    "The current 0.835 / 0.779 values remain exploratory context.",
    "introduces no new detector metric",
    "The source, context-manifest, and question-design gates are complete",
    "96 deterministic questions with gold answers and evidence payloads",
    "conditionally suitable for aggregate business analysis",
    "Zero historical record overlap",
    "48-slot aggregate capacity",
    "Customer ID",
    "Read the source audit.",
    "Read the quality profile.",
    "Read the overlap proof.",
    "Read the capacity proof.",
    "Read the precision review.",
    "Read the manifest commitment.",
    "Freeze the model revision, tokenizer revision, prompt template",
    ".panel { min-width:0;",
    "overflow-wrap:anywhere; word-break:break-word;",
]

FORBIDDEN_HTML_FRAGMENTS = [
    "Confirmation Set v1 achieved",
    "Confirmation Set v1 result is",
    "execution ready",
    "production-ready detector",
    "independent human labels are complete",
    "clamp(",
]


class HTMLCheckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.seen_tags = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.seen_tags += 1


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add_failure(failures: list[dict[str, Any]], name: str, detail: Any) -> None:
    failures.append({"name": name, "detail": detail})


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path in [
        PROTOCOL_PATH,
        METHODOLOGY_SUMMARY_PATH,
        DATASET_AUDIT_SUMMARY_PATH,
        CONTEXT_FEASIBILITY_PATH,
        PRECISION_REVIEW_PATH,
        CONTEXT_MANIFEST_PATH,
        QUESTION_DESIGN_PATH,
        HTML_PATH,
        SUMMARY_PATH,
    ]:
        if not path.exists():
            add_failure(failures, "required_file_missing", repo_path(path))

    protocol = load_json(PROTOCOL_PATH) if PROTOCOL_PATH.exists() else {}
    methodology = load_json(METHODOLOGY_SUMMARY_PATH) if METHODOLOGY_SUMMARY_PATH.exists() else {}
    dataset_audit = load_json(DATASET_AUDIT_SUMMARY_PATH) if DATASET_AUDIT_SUMMARY_PATH.exists() else {}
    feasibility = load_json(CONTEXT_FEASIBILITY_PATH) if CONTEXT_FEASIBILITY_PATH.exists() else {}
    precision_report = load_json(PRECISION_REVIEW_PATH) if PRECISION_REVIEW_PATH.exists() else {}
    context_manifest = load_json(CONTEXT_MANIFEST_PATH) if CONTEXT_MANIFEST_PATH.exists() else {}
    question_design = load_json(QUESTION_DESIGN_PATH) if QUESTION_DESIGN_PATH.exists() else {}
    summary = load_json(SUMMARY_PATH) if SUMMARY_PATH.exists() else {}
    html_text = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""

    for path, payload in [
        (PROTOCOL_PATH, protocol),
        (DATASET_AUDIT_SUMMARY_PATH, dataset_audit),
        (CONTEXT_FEASIBILITY_PATH, feasibility),
        (PRECISION_REVIEW_PATH, precision_report),
        (CONTEXT_MANIFEST_PATH, context_manifest),
        (QUESTION_DESIGN_PATH, question_design),
        (SUMMARY_PATH, summary),
    ]:
        if payload and contains_local_path(json.dumps(payload, ensure_ascii=True)):
            add_failure(failures, "local_path_in_public_json", repo_path(path))

    if html_text:
        parser = HTMLCheckParser()
        parser.feed(html_text)
        if parser.seen_tags == 0:
            add_failure(failures, "html_parse", "no tags parsed")
        for fragment in REQUIRED_HTML_FRAGMENTS:
            if fragment not in html_text:
                add_failure(failures, "required_html_fragment_missing", fragment)
        for fragment in FORBIDDEN_HTML_FRAGMENTS:
            if fragment in html_text:
                add_failure(failures, "forbidden_html_fragment", fragment)
        if contains_local_path(html_text):
            add_failure(failures, "local_path_in_html", repo_path(HTML_PATH))

        unique_protocol_values = [
            *(item.get("option_id", "") for item in protocol.get("dataset_strategy", {}).get("options", [])),
            *(item.get("family", "") for item in protocol.get("question_design", {}).get("candidate_families", [])),
            *(item.get("gate", "") for item in protocol.get("execution_gates", [])),
        ]
        for value in unique_protocol_values:
            if value and html_text.count(value) != 1:
                add_failure(
                    failures,
                    "protocol_value_html_occurrence_count",
                    {"value": value, "expected": 1, "actual": html_text.count(value)},
                )

    expected_top_level = {
        "status": "design_ready_not_execution_ready",
        "study_role": "prospective_confirmation_design",
        "execution_ready": False,
        "no_new_results": True,
    }
    for key, expected in expected_top_level.items():
        if protocol.get(key) != expected:
            add_failure(
                failures,
                "protocol_value_mismatch",
                {"field": key, "expected": expected, "actual": protocol.get(key)},
            )

    boundary = protocol.get("current_result_boundary", {})
    expected_boundary = {
        "classification": "exploratory_retrospective",
        "exploratory_max_test_auprc": 0.835073,
        "exploratory_max_test_f1": 0.779412,
    }
    for key, expected in expected_boundary.items():
        if boundary.get(key) != expected:
            add_failure(
                failures,
                "current_result_boundary_mismatch",
                {"field": key, "expected": expected, "actual": boundary.get(key)},
            )

    if methodology.get("share_status") != "share_with_caveats":
        add_failure(failures, "methodology_share_status", methodology.get("share_status"))
    if methodology.get("locked_public_results", {}).get("exploratory_max_test_auprc") != 0.835073:
        add_failure(failures, "methodology_auprc_drift", methodology.get("locked_public_results"))
    if methodology.get("locked_public_results", {}).get("exploratory_max_test_f1") != 0.779412:
        add_failure(failures, "methodology_f1_drift", methodology.get("locked_public_results"))

    dataset_strategy = protocol.get("dataset_strategy", {})
    if dataset_strategy.get("selection_status") != "selected_source_audited_context_manifest_and_question_design_frozen":
        add_failure(failures, "dataset_selection_status", dataset_strategy.get("selection_status"))
    option_ids = {item.get("option_id") for item in dataset_strategy.get("options", [])}
    expected_option_ids = {
        "same_dataset_new_contexts",
        "same_source_prior_period",
        "second_public_transaction_dataset",
        "jhu_domain_extension",
    }
    if option_ids != expected_option_ids:
        add_failure(failures, "dataset_option_ids", sorted(option_ids))
    expected_selected_strategy = {
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
        "context_manifest_config": "configs/confirmation_context_manifest_v1.json",
        "context_manifest_report": "reports/bizhallu_confirmation_context_manifest_report.json",
        "context_manifest_html": "reports/bizhallu_confirmation_context_manifest.html",
        "context_manifest_validation": "reports/bizhallu_confirmation_context_manifest_validation.json",
        "question_design_config": "configs/confirmation_question_design_v1.json",
        "question_design_report": "reports/bizhallu_confirmation_question_design_report.json",
        "question_design_validation": "reports/bizhallu_confirmation_question_design_validation.json",
        "private_question_manifest": "data/processed/confirmation_online_retail_ii/questions_gold_v1_private.json",
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
        "outcome_blind_context_manifest_frozen": True,
        "period_disjoint_split_frozen": True,
        "context_manifest_commitment_sha256": "002b484b3b59c52db0a2213b8d896750cdb2bb9157998d48bf015eff27f19e5a",
        "question_level_evidence_payload_fingerprint_check_pending": False,
        "question_level_evidence_payload_fingerprint_check_complete": True,
        "private_question_manifest_commitment_sha256": "b72ffaf715afef85867522fb0c7264377350ce146709962e420c16eaa6d9e80c",
        "normalized_evidence_content_fingerprint_check_complete": True,
        "historical_full100_unique_evidence_content_fingerprint_count": 66,
        "historical_full100_evidence_content_overlap_count": 0,
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
    for key, expected in expected_selected_strategy.items():
        if dataset_strategy.get(key) != expected:
            add_failure(
                failures,
                "selected_dataset_strategy",
                {"field": key, "expected": expected, "actual": dataset_strategy.get(key)},
            )

    sampling = protocol.get("sampling_plan", {})
    expected_sampling = {
        "protocol_pilot": 12,
        "development": 30,
        "confirmation": 54,
    }
    for split, expected in expected_sampling.items():
        actual = sampling.get(split, {}).get("question_count")
        if actual != expected:
            add_failure(
                failures,
                "sampling_question_count",
                {"split": split, "expected": expected, "actual": actual},
            )
    if sampling.get("main_question_count") != 84:
        add_failure(failures, "main_question_count", sampling.get("main_question_count"))
    if sampling.get("total_generation_target_including_pilot") != 96:
        add_failure(
            failures,
            "total_generation_target",
            sampling.get("total_generation_target_including_pilot"),
        )
    if sampling.get("outcome_blind_selection") is not True:
        add_failure(failures, "outcome_blind_selection", sampling.get("outcome_blind_selection"))
    if sampling.get("counts_are_minimum_targets_pending_precision_review") is not False:
        add_failure(failures, "minimum_target_policy", sampling)
    if sampling.get("counts_frozen_after_precision_scope_amendment") is not True:
        add_failure(failures, "frozen_count_policy", sampling)
    if sampling.get("protocol_pilot", {}).get("included_in_confirmation_metrics") is not False:
        add_failure(failures, "pilot_metric_exclusion", sampling.get("protocol_pilot"))

    split_policy = protocol.get("context_split_policy", {})
    if split_policy.get("status") != "context_manifest_and_period_disjoint_split_frozen":
        add_failure(failures, "split_policy_status", split_policy.get("status"))
    if split_policy.get("assignment_unit") != "evidence_context_id":
        add_failure(failures, "split_assignment_unit", split_policy.get("assignment_unit"))
    precision_review = protocol.get("precision_review", {})
    if precision_review.get("status") != "complete_with_scope_downgrade":
        add_failure(failures, "precision_review_status", precision_review.get("status"))
    if precision_review.get("effective_independent_unit") != "evidence_context_id":
        add_failure(failures, "precision_review_unit", precision_review)
    if precision_review.get("required_before_context_manifest_freeze") is not False:
        add_failure(failures, "precision_review_timing", precision_review)
    if precision_review.get("selected_confirmation_contexts") != 27:
        add_failure(failures, "precision_review_selected_contexts", precision_review)
    if precision_report.get("status") != "outcome_blind_precision_review_blocked":
        add_failure(failures, "precision_review_source_status", precision_report.get("status"))
    expected_manifest_evidence = {
        "status": "confirmation_context_manifest_v1_frozen",
        "selected_context_count": 48,
        "reserve_period_count": 2,
        "split_counts": {
            "protocol_pilot": 6,
            "development": 15,
            "confirmation": 27,
        },
        "commitment": "002b484b3b59c52db0a2213b8d896750cdb2bb9157998d48bf015eff27f19e5a",
        "context_manifest_created": True,
        "split_assignment_created": True,
        "question_created": False,
        "model_run_performed": False,
        "new_metrics_reported": False,
    }
    observed_manifest_evidence = {
        "status": context_manifest.get("status"),
        "selected_context_count": context_manifest.get("frozen_inventory", {}).get("selected_context_count"),
        "reserve_period_count": context_manifest.get("frozen_inventory", {}).get("reserve_period_count"),
        "split_counts": context_manifest.get("frozen_inventory", {}).get("split_counts"),
        "commitment": context_manifest.get("private_manifest_commitment", {}).get("canonical_sha256"),
        "context_manifest_created": context_manifest.get("execution_boundary", {}).get("context_manifest_created"),
        "split_assignment_created": context_manifest.get("execution_boundary", {}).get("split_assignment_created"),
        "question_created": context_manifest.get("execution_boundary", {}).get("question_created"),
        "model_run_performed": context_manifest.get("execution_boundary", {}).get("model_run_performed"),
        "new_metrics_reported": context_manifest.get("execution_boundary", {}).get("new_metrics_reported"),
    }
    if observed_manifest_evidence != expected_manifest_evidence:
        add_failure(failures, "context_manifest_source_status", observed_manifest_evidence)

    expected_question_design_evidence = {
        "status": "confirmation_question_design_v1_frozen",
        "question_count": 96,
        "split_counts": {
            "protocol_pilot": 12,
            "development": 30,
            "confirmation": 54,
        },
        "family_counts": {
            "net_revenue_reconciliation_by_period": 32,
            "product_return_rate_comparison": 32,
            "country_product_exposure": 32,
        },
        "commitment": "b72ffaf715afef85867522fb0c7264377350ce146709962e420c16eaa6d9e80c",
        "payload_check": "complete",
        "cross_split_overlap": 0,
        "content_fingerprint_count": 96,
        "content_cross_split_overlap": 0,
        "historical_content_fingerprint_count": 66,
        "historical_content_overlap": 0,
        "prompt_created": False,
        "model_run_performed": False,
        "new_metrics_reported": False,
    }
    observed_question_design_evidence = {
        "status": question_design.get("status"),
        "question_count": question_design.get("frozen_inventory", {}).get("question_count"),
        "split_counts": question_design.get("frozen_inventory", {}).get("split_counts"),
        "family_counts": question_design.get("frozen_inventory", {}).get("family_counts"),
        "commitment": question_design.get("private_question_manifest_commitment", {}).get("canonical_sha256"),
        "payload_check": question_design.get("evidence_payload_integrity", {}).get("question_level_evidence_payload_fingerprint_check"),
        "cross_split_overlap": question_design.get("evidence_payload_integrity", {}).get("cross_split_fingerprint_count"),
        "content_fingerprint_count": question_design.get("evidence_payload_integrity", {}).get("unique_content_fingerprint_count"),
        "content_cross_split_overlap": question_design.get("evidence_payload_integrity", {}).get("content_cross_split_fingerprint_count"),
        "historical_content_fingerprint_count": question_design.get("evidence_payload_integrity", {}).get("historical_full100_content_fingerprint_count"),
        "historical_content_overlap": question_design.get("evidence_payload_integrity", {}).get("historical_full100_content_fingerprint_overlap_count"),
        "prompt_created": question_design.get("execution_boundary", {}).get("prompt_created"),
        "model_run_performed": question_design.get("execution_boundary", {}).get("model_run_performed"),
        "new_metrics_reported": question_design.get("execution_boundary", {}).get("new_metrics_reported"),
    }
    if observed_question_design_evidence != expected_question_design_evidence:
        add_failure(failures, "question_design_source_status", observed_question_design_evidence)

    if split_policy.get("period_disjoint_across_all_new_study_splits") is not True:
        add_failure(failures, "period_disjoint_policy", split_policy)
    if split_policy.get("evidence_fingerprint_disjoint_across_all_splits") is not True:
        add_failure(failures, "evidence_disjoint_policy", split_policy)
    if split_policy.get("historical_exploratory_evidence_fingerprint_exclusion") is not True:
        add_failure(failures, "historical_evidence_exclusion", split_policy)
    if split_policy.get("historical_question_id_reuse") is not False:
        add_failure(failures, "historical_question_id_reuse", split_policy)
    if split_policy.get("selected_context_count") != 48 or split_policy.get("reserve_period_count") != 2:
        add_failure(failures, "split_inventory_counts", split_policy)
    if split_policy.get("context_pool_fingerprint_check_complete") is not True:
        add_failure(failures, "context_pool_fingerprint_check", split_policy)
    if split_policy.get("question_payload_fingerprint_check_pending") is not False:
        add_failure(failures, "question_payload_fingerprint_pending_boundary", split_policy)
    if split_policy.get("question_payload_fingerprint_check_complete") is not True:
        add_failure(failures, "question_payload_fingerprint_complete_boundary", split_policy)
    if split_policy.get("question_payload_fingerprint_count") != 96:
        add_failure(failures, "question_payload_fingerprint_count", split_policy)
    if split_policy.get("question_payload_cross_split_overlap_count") != 0:
        add_failure(failures, "question_payload_cross_split_overlap", split_policy)
    if split_policy.get("question_evidence_content_fingerprint_count") != 96:
        add_failure(failures, "question_evidence_content_fingerprint_count", split_policy)
    if split_policy.get("question_evidence_content_cross_split_overlap_count") != 0:
        add_failure(failures, "question_evidence_content_cross_split_overlap", split_policy)
    if split_policy.get("historical_full100_unique_evidence_content_fingerprint_count") != 66:
        add_failure(failures, "historical_evidence_content_fingerprint_count", split_policy)
    if split_policy.get("question_evidence_content_historical_full100_overlap_count") != 0:
        add_failure(failures, "question_evidence_content_historical_overlap", split_policy)
    if split_policy.get("private_question_manifest_commitment_sha256") != "b72ffaf715afef85867522fb0c7264377350ce146709962e420c16eaa6d9e80c":
        add_failure(failures, "question_manifest_commitment", split_policy)
    if split_policy.get("public_manifest_commitment_sha256") != "002b484b3b59c52db0a2213b8d896750cdb2bb9157998d48bf015eff27f19e5a":
        add_failure(failures, "manifest_commitment", split_policy.get("public_manifest_commitment_sha256"))
    forbidden_assignment = set(split_policy.get("forbidden_assignment_methods", []))
    for required in ["periodic row position", "generated-answer auto-status"]:
        if required not in forbidden_assignment:
            add_failure(failures, "forbidden_assignment_method_missing", required)

    annotation = protocol.get("annotation_protocol", {})
    if annotation.get("reviewer_count") != 2:
        add_failure(failures, "reviewer_count", annotation.get("reviewer_count"))
    if annotation.get("reviewer_type") != "independent_human_reviewers":
        add_failure(failures, "reviewer_type", annotation.get("reviewer_type"))
    if set(annotation.get("claim_statuses", [])) != {
        "supported",
        "contradicted",
        "unmatched",
        "needs_review",
    }:
        add_failure(failures, "claim_statuses", annotation.get("claim_statuses"))
    expected_binary_mapping = {
        "supported": 0,
        "contradicted": 1,
        "unmatched": 1,
        "needs_review": "exclude_from_binary_metrics_after_adjudication_attempt_and_report_count",
    }
    if annotation.get("binary_mapping") != expected_binary_mapping:
        add_failure(failures, "binary_mapping", annotation.get("binary_mapping"))
    if "every in-scope business-fact claim" not in annotation.get("claim_inventory_policy", ""):
        add_failure(failures, "claim_inventory_policy", annotation.get("claim_inventory_policy"))

    expected_tracks = {
        "oracle_span_diagnostics",
        "claim_extraction",
        "evidence_verification",
        "end_to_end_audit",
    }
    if set(protocol.get("evaluation_tracks", {})) != expected_tracks:
        add_failure(failures, "evaluation_tracks", protocol.get("evaluation_tracks"))
    verifier_outputs = set(
        protocol.get("evaluation_tracks", {})
        .get("evidence_verification", {})
        .get("required_outputs", [])
    )
    if "continuous unsupported-risk score on a frozen scale for AUPRC comparison" not in verifier_outputs:
        add_failure(failures, "verifier_risk_score_output", sorted(verifier_outputs))

    metric_policy = protocol.get("metric_policy", {})
    if metric_policy.get("primary_metric") != "AUPRC":
        add_failure(failures, "primary_metric", metric_policy.get("primary_metric"))
    if metric_policy.get("uncertainty_interval") != "context-level BCa bootstrap when defined, with paired percentile context bootstrap as sensitivity":
        add_failure(failures, "uncertainty_interval", metric_policy.get("uncertainty_interval"))
    if metric_policy.get("planned_bootstrap_replicates") != 5000:
        add_failure(failures, "planned_bootstrap_replicates", metric_policy.get("planned_bootstrap_replicates"))

    family_statuses = {
        item.get("family"): item.get("source_feasibility_status")
        for item in protocol.get("question_design", {}).get("candidate_families", [])
    }
    expected_family_statuses = {
        "net_revenue_reconciliation_by_period": "verified",
        "customer_revenue_concentration": "blocked_by_preexisting_quality_control",
        "product_return_rate_comparison": "verified",
        "country_product_exposure": "verified",
    }
    if family_statuses != expected_family_statuses:
        add_failure(failures, "question_family_source_feasibility", family_statuses)
    question_design_protocol = protocol.get("question_design", {})
    if question_design_protocol.get("family_status") != "question_templates_gold_and_payload_fingerprints_frozen":
        add_failure(failures, "question_design_family_status", question_design_protocol.get("family_status"))
    if question_design_protocol.get("question_count") != 96 or question_design_protocol.get("template_count") != 6:
        add_failure(failures, "question_design_inventory", question_design_protocol)
    for key, expected in {
        "full_payload_fingerprint_count": 96,
        "normalized_evidence_content_fingerprint_count": 96,
        "historical_full100_unique_evidence_content_fingerprint_count": 66,
        "historical_full100_evidence_content_overlap_count": 0,
    }.items():
        if question_design_protocol.get(key) != expected:
            add_failure(
                failures,
                "question_design_fingerprint_inventory",
                {"field": key, "expected": expected, "actual": question_design_protocol.get(key)},
            )
    if question_design_protocol.get("private_question_manifest_commitment_sha256") != "b72ffaf715afef85867522fb0c7264377350ce146709962e420c16eaa6d9e80c":
        add_failure(failures, "question_design_protocol_commitment", question_design_protocol)

    gates = protocol.get("execution_gates", [])
    if len(gates) != 7:
        add_failure(failures, "execution_gate_count", len(gates))
    gate_statuses = {item.get("gate"): item.get("status") for item in gates}
    expected_gate_statuses = {
        "dataset_source_selected_and_audited": "complete",
        "context_manifest_split_and_precision_review_frozen": "complete",
        "question_templates_and_gold_calculations_validated": "complete",
        "model_prompt_and_detector_configs_frozen": "pending",
        "two_independent_human_reviewers_assigned": "pending",
        "claim_extraction_and_verifier_protocols_implemented_on_non_confirmation_data": "pending",
        "sealed_confirmation_run_authorized": "pending",
    }
    if gate_statuses != expected_gate_statuses:
        add_failure(failures, "execution_gate_status", gate_statuses)

    expected_summary = {
        "status": "confirmation_set_v1_design_ready",
        "execution_ready": False,
        "no_new_results": True,
        "study_role": "prospective_confirmation_design",
        "dataset_selection_status": "selected_source_audited_context_manifest_and_question_design_frozen",
        "selected_candidate_id": "uci_online_retail_ii_prior_period",
        "selected_candidate_role": "prospective_temporal_internal_replication",
        "dataset_gate_status": "complete",
        "dataset_acquisition_verified": True,
        "dataset_structure_profile_complete": True,
        "dataset_quality_profile_complete": True,
        "dataset_historical_overlap_check_complete": True,
        "dataset_context_feasibility_check_complete": True,
        "dataset_local_profile_complete": True,
        "strict_window_row_count": 502938,
        "metadata_header_drift_detected": True,
        "dataset_quality_decision": "conditionally_suitable_for_aggregate_business_analysis_after_documented_controls",
        "strict_window_missing_description_rows": 2821,
        "strict_window_missing_customer_id_rows": 100207,
        "strict_window_normalized_exact_duplicate_extra_rows": 6544,
        "strict_window_valid_net_revenue_line_count": 492887,
        "strict_window_net_revenue_gbp": 9266060.76,
        "canonical_record_overlap_row_count": 0,
        "date_blind_record_overlap_row_count": 0,
        "business_pattern_overlap_row_count": 195814,
        "context_feasibility_report_path": "reports/bizhallu_confirmation_context_feasibility_report.json",
        "complete_calendar_week_count": 51,
        "observed_complete_week_count": 50,
        "required_context_count": 48,
        "maximum_slot_matching_count": 48,
        "minimum_hall_capacity_slack": 2,
        "precision_review_report_path": "reports/bizhallu_confirmation_precision_review_report.json",
        "precision_review_original_status": "outcome_blind_precision_review_blocked",
        "precision_scope_amendment_status": "complete_with_scope_downgrade",
        "context_manifest_report_path": "reports/bizhallu_confirmation_context_manifest_report.json",
        "context_manifest_status": "confirmation_context_manifest_v1_frozen",
        "context_manifest_created": True,
        "split_assignment_created": True,
        "context_manifest_commitment_sha256": "002b484b3b59c52db0a2213b8d896750cdb2bb9157998d48bf015eff27f19e5a",
        "selected_context_count": 48,
        "reserve_period_count": 2,
        "question_design_report_path": "reports/bizhallu_confirmation_question_design_report.json",
        "question_design_status": "confirmation_question_design_v1_frozen",
        "question_design_config_path": "configs/confirmation_question_design_v1.json",
        "question_design_commitment_sha256": "b72ffaf715afef85867522fb0c7264377350ce146709962e420c16eaa6d9e80c",
        "question_count_frozen": 96,
        "question_template_count": 6,
        "question_payload_fingerprint_check_pending": False,
        "question_payload_fingerprint_check_complete": True,
        "question_payload_cross_split_overlap_count": 0,
        "question_evidence_content_fingerprint_count": 96,
        "question_evidence_content_cross_split_overlap_count": 0,
        "historical_unique_evidence_content_fingerprint_count": 66,
        "question_evidence_content_historical_overlap_count": 0,
        "selected_reconciliation_positive_cancel_flagged_row_count": 1,
        "selected_product_return_ratio_percentage_range": [0.2, 156.25],
        "selected_product_return_ratio_over_100_count": 1,
        "country_gold_position_counts": {"1": 9, "2": 5, "3": 3, "4": 6, "5": 9},
        "country_candidate_tables_accidentally_fully_descending": 1,
        "dataset_option_count": 4,
        "candidate_question_family_count": 4,
        "protocol_pilot_question_count": 12,
        "development_question_count": 30,
        "confirmation_question_count": 54,
        "main_question_count": 84,
        "total_generation_target_including_pilot": 96,
        "counts_are_minimum_targets_pending_precision_review": False,
        "precision_review_status": "complete_with_scope_downgrade",
        "historical_evidence_fingerprint_exclusion": True,
        "primary_metric": "AUPRC",
        "bootstrap_unit": "evidence_context_id",
        "reviewer_count": 2,
        "claim_inventory_policy": "exhaustive_business_fact_claim_inventory",
        "binary_positive_statuses": ["contradicted", "unmatched"],
        "evaluation_track_count": 4,
        "pending_gate_count": 4,
        "current_study_classification": "exploratory_retrospective",
        "current_share_status": "share_with_caveats",
        "historical_exploratory_max_test_auprc": 0.835073,
        "historical_exploratory_max_test_f1": 0.779412,
        "num_failures": 0,
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            add_failure(
                failures,
                "summary_value_mismatch",
                {"field": key, "expected": expected, "actual": summary.get(key)},
            )

    validation = {
        "status": "confirmation_set_v1_design_validation_passed" if not failures else "confirmation_set_v1_design_validation_failed",
        "protocol_path": repo_path(PROTOCOL_PATH),
        "html_path": repo_path(HTML_PATH),
        "summary_path": repo_path(SUMMARY_PATH),
        "execution_ready": False,
        "no_new_results": True,
        "dataset_source_selected": dataset_strategy.get("selection_status") == "selected_source_audited_context_manifest_and_question_design_frozen",
        "dataset_acquisition_verified": dataset_strategy.get("official_acquisition_verified") is True,
        "dataset_structure_and_date_window_verified": dataset_strategy.get("structure_and_date_window_verified") is True,
        "dataset_quality_profile_verified": dataset_strategy.get("quality_profile_verified") is True,
        "dataset_historical_overlap_verified": dataset_strategy.get("historical_record_overlap_verified") is True,
        "dataset_context_feasibility_verified": dataset_strategy.get("outcome_blind_context_feasibility_verified") is True,
        "strict_window_row_count": dataset_strategy.get("strict_window_row_count"),
        "dataset_gate_complete": next(
            (item.get("status") for item in gates if item.get("gate") == "dataset_source_selected_and_audited"),
            None,
        ) == "complete",
        "precision_review_complete_with_scope_downgrade": precision_review.get("status") == "complete_with_scope_downgrade",
        "pending_gate_count": sum(item.get("status") == "pending" for item in gates),
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
