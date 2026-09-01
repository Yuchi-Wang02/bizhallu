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
    "72 generations",
    "only 60 enter the main study",
    "permanently excluded from confirmation metrics",
    "minimum planning targets",
    "outcome-blind precision review",
    "historical full100 evidence fingerprints are excluded",
    "every in-scope business-fact claim",
    "Do not hide oracle spans inside an end-to-end claim.",
    "Oracle-span diagnostics",
    "Claim extraction",
    "Evidence verification",
    "continuous unsupported-risk score",
    "End-to-end audit",
    "cluster bootstrap",
    "Semantic Entropy",
    "TOHA",
    "Every gate is intentionally pending.",
    "The current 0.835 / 0.779 values remain exploratory context.",
    "introduces no new detector metric",
    "The official Online Retail II workbook is acquired and hashed",
    "502,938-row strict prior-period boundary",
    "Invoice",
    "Customer ID",
    "Read the source audit.",
    ".panel { min-width:0;",
    "overflow-wrap:anywhere; word-break:break-word;",
]

FORBIDDEN_HTML_FRAGMENTS = [
    "Confirmation Set v1 achieved",
    "Confirmation Set v1 result is",
    "execution ready",
    "production-ready detector",
    "independent human labels are complete",
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
        HTML_PATH,
        SUMMARY_PATH,
    ]:
        if not path.exists():
            add_failure(failures, "required_file_missing", repo_path(path))

    protocol = load_json(PROTOCOL_PATH) if PROTOCOL_PATH.exists() else {}
    methodology = load_json(METHODOLOGY_SUMMARY_PATH) if METHODOLOGY_SUMMARY_PATH.exists() else {}
    dataset_audit = load_json(DATASET_AUDIT_SUMMARY_PATH) if DATASET_AUDIT_SUMMARY_PATH.exists() else {}
    summary = load_json(SUMMARY_PATH) if SUMMARY_PATH.exists() else {}
    html_text = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""

    for path, payload in [
        (PROTOCOL_PATH, protocol),
        (DATASET_AUDIT_SUMMARY_PATH, dataset_audit),
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
    if dataset_strategy.get("selection_status") != "provisional_selection_pending_local_profile":
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
        "selected_candidate_id": "uci_online_retail_ii_prior_period",
        "selected_candidate_role": "prospective_temporal_internal_replication",
        "selected_candidate_gate_status": "pending",
        "official_acquisition_verified": True,
        "structure_and_date_window_verified": True,
        "strict_window_row_count": 502938,
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
        "confirmation": 30,
    }
    for split, expected in expected_sampling.items():
        actual = sampling.get(split, {}).get("question_count")
        if actual != expected:
            add_failure(
                failures,
                "sampling_question_count",
                {"split": split, "expected": expected, "actual": actual},
            )
    if sampling.get("main_question_count") != 60:
        add_failure(failures, "main_question_count", sampling.get("main_question_count"))
    if sampling.get("total_generation_target_including_pilot") != 72:
        add_failure(
            failures,
            "total_generation_target",
            sampling.get("total_generation_target_including_pilot"),
        )
    if sampling.get("outcome_blind_selection") is not True:
        add_failure(failures, "outcome_blind_selection", sampling.get("outcome_blind_selection"))
    if sampling.get("counts_are_minimum_targets_pending_precision_review") is not True:
        add_failure(failures, "minimum_target_policy", sampling)
    if sampling.get("protocol_pilot", {}).get("included_in_confirmation_metrics") is not False:
        add_failure(failures, "pilot_metric_exclusion", sampling.get("protocol_pilot"))

    split_policy = protocol.get("context_split_policy", {})
    if split_policy.get("assignment_unit") != "evidence_context_id":
        add_failure(failures, "split_assignment_unit", split_policy.get("assignment_unit"))
    precision_review = protocol.get("precision_review", {})
    if precision_review.get("status") != "pending":
        add_failure(failures, "precision_review_status", precision_review.get("status"))
    if precision_review.get("effective_independent_unit") != "evidence_context_id":
        add_failure(failures, "precision_review_unit", precision_review)
    if precision_review.get("required_before_context_manifest_freeze") is not True:
        add_failure(failures, "precision_review_timing", precision_review)

    if split_policy.get("period_disjoint_across_all_new_study_splits") is not True:
        add_failure(failures, "period_disjoint_policy", split_policy)
    if split_policy.get("evidence_fingerprint_disjoint_across_all_splits") is not True:
        add_failure(failures, "evidence_disjoint_policy", split_policy)
    if split_policy.get("historical_exploratory_evidence_fingerprint_exclusion") is not True:
        add_failure(failures, "historical_evidence_exclusion", split_policy)
    if split_policy.get("historical_question_id_reuse") is not False:
        add_failure(failures, "historical_question_id_reuse", split_policy)
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
    if metric_policy.get("uncertainty_interval") != "cluster bootstrap by evidence_context_id":
        add_failure(failures, "uncertainty_interval", metric_policy.get("uncertainty_interval"))

    gates = protocol.get("execution_gates", [])
    if len(gates) != 7:
        add_failure(failures, "execution_gate_count", len(gates))
    if any(item.get("status") != "pending" for item in gates):
        add_failure(failures, "execution_gate_status", gates)

    expected_summary = {
        "status": "confirmation_set_v1_design_ready",
        "execution_ready": False,
        "no_new_results": True,
        "study_role": "prospective_confirmation_design",
        "dataset_selection_status": "provisional_selection_pending_local_profile",
        "selected_candidate_id": "uci_online_retail_ii_prior_period",
        "selected_candidate_role": "prospective_temporal_internal_replication",
        "dataset_gate_status": "pending",
        "dataset_acquisition_verified": True,
        "dataset_structure_profile_complete": True,
        "dataset_local_profile_complete": False,
        "strict_window_row_count": 502938,
        "metadata_header_drift_detected": True,
        "dataset_option_count": 4,
        "candidate_question_family_count": 4,
        "protocol_pilot_question_count": 12,
        "development_question_count": 30,
        "confirmation_question_count": 30,
        "main_question_count": 60,
        "total_generation_target_including_pilot": 72,
        "counts_are_minimum_targets_pending_precision_review": True,
        "precision_review_status": "pending",
        "historical_evidence_fingerprint_exclusion": True,
        "primary_metric": "AUPRC",
        "bootstrap_unit": "evidence_context_id",
        "reviewer_count": 2,
        "claim_inventory_policy": "exhaustive_business_fact_claim_inventory",
        "binary_positive_statuses": ["contradicted", "unmatched"],
        "evaluation_track_count": 4,
        "pending_gate_count": 7,
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
        "dataset_selection_provisional": dataset_strategy.get("selection_status") == "provisional_selection_pending_local_profile",
        "dataset_acquisition_verified": dataset_strategy.get("official_acquisition_verified") is True,
        "dataset_structure_and_date_window_verified": dataset_strategy.get("structure_and_date_window_verified") is True,
        "strict_window_row_count": dataset_strategy.get("strict_window_row_count"),
        "dataset_gate_pending": next(
            (item.get("status") for item in gates if item.get("gate") == "dataset_source_selected_and_audited"),
            None,
        ) == "pending",
        "precision_review_pending": precision_review.get("status") == "pending",
        "pending_gate_count": len(gates),
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
