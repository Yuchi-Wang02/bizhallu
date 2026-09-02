from __future__ import annotations

import hashlib
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import contains_local_path, repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "confirmation_context_feasibility_v1.json"
REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility_report.json"
HTML_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility.html"
VALIDATION_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility_validation.json"
OVERLAP_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_overlap_report.json"
METHODOLOGY_PATH = PROJECT_ROOT / "reports" / "bizhallu_methodology_hardening_summary.json"
PRECISION_AMENDMENT_PATH = (
    PROJECT_ROOT / "configs" / "confirmation_precision_scope_amendment_v1.json"
)
LOCAL_PROOF_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "confirmation_online_retail_ii"
    / "context_feasibility_local_proof.json"
)
STRICT_TABLE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "confirmation_online_retail_ii"
    / "strict_window_lines.csv.gz"
)

EXPECTED_CONFIG_SHA256 = "fce09f569c1ebebbf0e913f362af4f79732eb7292f769048d40f8843c8d8f28a"
EXPECTED_PRECISION_AMENDMENT_SHA256 = "7bdcd6c368aad4abc22df793a6480052274fedda6c204f7711b8437c73fa2ca4"
EXPECTED_STRICT_TABLE_SHA256 = "ab875caaf527d5d528f4edad4fd372b15d4e1ae9c39f6cea20f8211178e256fc"
EXPECTED_STRICT_ROW_COUNT = 502938
EXPECTED_ALLOWED_FAMILIES = [
    "net_revenue_reconciliation_by_period",
    "product_return_rate_comparison",
    "country_product_exposure",
]
EXPECTED_SUPPORT_DISTRIBUTIONS = {
    "source_rows_per_observed_complete_period": {
        "minimum": 3238,
        "median": 8646.5,
        "maximum": 19111,
    },
    "valid_net_revenue_lines_per_observed_complete_period": {
        "minimum": 3067,
        "median": 8348.0,
        "maximum": 18724,
    },
    "cancellation_or_return_rows_per_observed_complete_period": {
        "minimum": 48,
        "median": 178.5,
        "maximum": 496,
    },
    "eligible_products_per_observed_complete_period": {
        "minimum": 17,
        "median": 72.0,
        "maximum": 206,
    },
    "eligible_countries_per_observed_complete_period": {
        "minimum": 3,
        "median": 9.0,
        "maximum": 15,
    },
}
EXPECTED_HALL_BY_SUBSET_SIZE = {
    1: {"check_count": 3, "available": 50, "required": 16, "slack": 34},
    2: {"check_count": 3, "available": 50, "required": 32, "slack": 18},
    3: {"check_count": 1, "available": 50, "required": 48, "slack": 2},
}
EXPECTED_HISTORICAL_RESULTS = {
    "exploratory_max_test_auprc": 0.835073,
    "exploratory_max_test_f1": 0.779412,
    "aligned_span_count": 205,
    "test_span_count": 103,
}

REQUIRED_HTML_FRAGMENTS = [
    "The source can support 48 period-disjoint contexts without looking at model outcomes.",
    "Complete Monday-through-Sunday weeks",
    "no context manifest was created",
    "48/48",
    "50",
    "+2",
    "100,207",
    "customer concentration stays blocked",
    "recorded return-to-positive-sales unit ratio",
    "Freeze only the context manifest and seeded split.",
    "precision review is complete with a narrower estimation claim",
    "No question, prompt, Qwen output",
    "No context manifest or experiment result.",
    "overflow-x:auto;",
    "overflow-wrap:anywhere;",
    "@media (max-width:860px)",
]
FORBIDDEN_HTML_FRAGMENTS = [
    "production-ready",
    "human-labeled benchmark",
    "independent external replication",
    "context manifest created",
    "split assignment created",
    "new confirmation AUPRC",
    "new confirmation F1",
    "clamp(",
]


class HTMLCheckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tag_counts: Counter[str] = Counter()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tag_counts[tag] += 1


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def add_failure(failures: list[dict[str, Any]], name: str, detail: Any) -> None:
    failures.append({"check": name, "detail": detail})


def check_equal(
    failures: list[dict[str, Any]], name: str, actual: Any, expected: Any
) -> None:
    if actual != expected:
        add_failure(failures, name, {"expected": expected, "actual": actual})


def main() -> None:
    failures: list[dict[str, Any]] = []
    required_paths = [
        CONFIG_PATH,
        REPORT_PATH,
        HTML_PATH,
        OVERLAP_PATH,
        METHODOLOGY_PATH,
        PRECISION_AMENDMENT_PATH,
    ]
    missing = [repo_path(path) for path in required_paths if not path.exists()]
    if missing:
        add_failure(failures, "required_files_exist", missing)
        payload = {
            "status": "confirmation_context_feasibility_validation_failed",
            "num_failures": len(failures),
            "failures": failures,
        }
        VALIDATION_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        raise SystemExit(1)

    config = load_json(CONFIG_PATH)
    report = load_json(REPORT_PATH)
    overlap = load_json(OVERLAP_PATH)
    methodology = load_json(METHODOLOGY_PATH)
    precision_amendment = load_json(PRECISION_AMENDMENT_PATH)
    html = HTML_PATH.read_text(encoding="utf-8")

    config_sha256 = file_sha256(CONFIG_PATH)
    check_equal(failures, "config_sha256", config_sha256, EXPECTED_CONFIG_SHA256)
    check_equal(failures, "config_status", config.get("status"), "rules_frozen_profile_pending")
    check_equal(
        failures,
        "config_purpose_boundary",
        config.get("no_new_results"),
        True,
    )
    check_equal(
        failures,
        "config_allowed_families",
        config.get("capacity_target", {}).get("eligible_families"),
        EXPECTED_ALLOWED_FAMILIES,
    )
    check_equal(
        failures,
        "config_required_counts",
        {
            "pilot": config.get("capacity_target", {}).get("required_protocol_pilot_contexts"),
            "development": config.get("capacity_target", {}).get("required_development_contexts"),
            "confirmation": config.get("capacity_target", {}).get("required_confirmation_contexts"),
            "total": config.get("capacity_target", {}).get("required_total_contexts"),
            "per_family": config.get("capacity_target", {}).get("required_contexts_per_eligible_family"),
        },
        {"pilot": 6, "development": 15, "confirmation": 27, "total": 48, "per_family": 16},
    )

    check_equal(
        failures,
        "report_identity",
        {
            "status": report.get("status"),
            "candidate_id": report.get("candidate_id"),
            "scope": report.get("scope"),
        },
        {
            "status": "outcome_blind_context_feasibility_complete",
            "candidate_id": "uci_online_retail_ii_prior_period",
            "scope": "aggregate-only outcome-blind capacity proof for period-disjoint evidence contexts",
        },
    )
    check_equal(failures, "report_config_sha256", report.get("config", {}).get("sha256"), config_sha256)
    check_equal(
        failures,
        "strict_input_contract",
        {
            "sha256": report.get("input", {}).get("strict_window_table_sha256"),
            "rows": report.get("input", {}).get("strict_window_row_count"),
        },
        {"sha256": EXPECTED_STRICT_TABLE_SHA256, "rows": EXPECTED_STRICT_ROW_COUNT},
    )
    if STRICT_TABLE_PATH.exists():
        check_equal(
            failures,
            "local_strict_table_sha256",
            file_sha256(STRICT_TABLE_PATH),
            EXPECTED_STRICT_TABLE_SHA256,
        )

    source = report.get("source_capacity", {})
    check_equal(
        failures,
        "source_capacity_counts",
        {
            "calendar": source.get("complete_calendar_period_count"),
            "observed": source.get("observed_complete_period_count"),
            "empty": source.get("empty_complete_period_count"),
            "complete_rows": source.get("complete_period_source_row_count"),
            "boundary_rows": source.get("excluded_boundary_source_row_count"),
            "reconciled": source.get("source_rows_reconciled"),
            "boundary_only": source.get("excluded_rows_are_only_partial_boundary_weeks"),
        },
        {
            "calendar": 51,
            "observed": 50,
            "empty": 1,
            "complete_rows": 482166,
            "boundary_rows": 20772,
            "reconciled": True,
            "boundary_only": True,
        },
    )
    if source.get("complete_period_source_row_count", 0) + source.get(
        "excluded_boundary_source_row_count", 0
    ) != EXPECTED_STRICT_ROW_COUNT:
        add_failure(failures, "source_row_arithmetic", source)
    check_equal(
        failures,
        "support_distributions",
        source.get("support_distributions"),
        EXPECTED_SUPPORT_DISTRIBUTIONS,
    )

    family_capacity = report.get("family_capacity", {})
    for family in EXPECTED_ALLOWED_FAMILIES:
        check_equal(
            failures,
            f"family_capacity_{family}",
            family_capacity.get(family),
            {
                "eligible_period_count": 50,
                "required_period_count": 16,
                "capacity_slack": 34,
                "all_observed_complete_periods_eligible": True,
            },
        )
    check_equal(
        failures,
        "customer_family_block",
        family_capacity.get("customer_revenue_concentration"),
        {
            "eligible_period_count": 0,
            "required_period_count": 0,
            "status": "blocked_by_preexisting_quality_control",
            "missing_customer_id_rows": 100207,
        },
    )

    proof = report.get("capacity_proof", {})
    hall_checks = proof.get("generalized_hall_checks", [])
    check_equal(failures, "hall_check_count", len(hall_checks), 7)
    for subset_size, expected in EXPECTED_HALL_BY_SUBSET_SIZE.items():
        rows = [row for row in hall_checks if len(row.get("family_subset", [])) == subset_size]
        check_equal(failures, f"hall_subset_{subset_size}_count", len(rows), expected["check_count"])
        for row in rows:
            observed = {
                "available": row.get("available_unique_period_count"),
                "required": row.get("required_unique_period_count"),
                "slack": row.get("capacity_slack"),
                "passed": row.get("passed"),
            }
            check_equal(
                failures,
                f"hall_subset_{subset_size}_{'_'.join(row.get('family_subset', []))}",
                observed,
                {
                    "available": expected["available"],
                    "required": expected["required"],
                    "slack": expected["slack"],
                    "passed": True,
                },
            )
    check_equal(
        failures,
        "matching_capacity",
        {
            "minimum_slack": proof.get("minimum_hall_capacity_slack"),
            "matched": proof.get("maximum_slot_matching_count"),
            "required": proof.get("required_slot_count"),
            "assignment_retained": proof.get("matching_assignment_retained_or_published"),
            "feasible": proof.get("capacity_target_feasible"),
        },
        {"minimum_slack": 2, "matched": 48, "required": 48, "assignment_retained": False, "feasible": True},
    )

    separation = report.get("evidence_separation", {})
    check_equal(
        failures,
        "evidence_separation",
        {
            "calendar_disjoint": separation.get("complete_periods_are_calendar_disjoint"),
            "boundary_only": separation.get("excluded_rows_are_only_partial_boundary_weeks"),
            "one_family": separation.get("candidate_period_assigned_to_at_most_one_final_family"),
            "source_key_duplicates": separation.get("source_key_duplicate_count_within_complete_period_pool"),
            "flag_conflicts": separation.get("evidence_flag_duplicate_conflicts"),
            "canonical_overlap": separation.get("historical_canonical_overlap_row_count"),
            "date_blind_overlap": separation.get("historical_date_blind_overlap_row_count"),
            "fingerprint_pending": separation.get("final_evidence_fingerprint_check_pending_manifest_freeze"),
        },
        {
            "calendar_disjoint": True,
            "boundary_only": True,
            "one_family": True,
            "source_key_duplicates": 0,
            "flag_conflicts": {
                "valid_net_revenue_lines_marked_exact_duplicate": 0,
                "merchandise_lines_marked_exact_duplicate": 0,
            },
            "canonical_overlap": 0,
            "date_blind_overlap": 0,
            "fingerprint_pending": True,
        },
    )
    check_equal(
        failures,
        "overlap_source_reconciliation",
        {
            "canonical": overlap.get("record_overlap", {}).get("canonical_eight_field", {}).get("multiset_overlap_row_count"),
            "date_blind": overlap.get("record_overlap", {}).get("date_blind_seven_field_sensitivity", {}).get("multiset_overlap_row_count"),
        },
        {"canonical": 0, "date_blind": 0},
    )

    expected_boundary = {
        "context_feasibility_check_complete": True,
        "context_manifest_created": False,
        "split_assignment_created": False,
        "question_created": False,
        "prompt_created": False,
        "model_run_performed": False,
        "new_metrics_reported": False,
        "execution_ready": False,
        "no_new_results": True,
    }
    check_equal(
        failures,
        "experiment_boundary",
        {key: report.get(key) for key in expected_boundary},
        expected_boundary,
    )
    research = report.get("research_decision", {})
    check_equal(failures, "research_capacity_complete", research.get("required_48_period_disjoint_context_capacity_verified"), True)
    check_equal(failures, "research_precision_complete", research.get("precision_review_complete_with_scope_downgrade"), True)
    check_equal(failures, "research_manifest_pending", research.get("context_manifest_and_split_assignment_pending"), True)

    expected_privacy = {
        "contains_invoice_values": False,
        "contains_customer_values": False,
        "contains_product_or_country_candidate_values": False,
        "contains_row_fingerprints": False,
        "contains_candidate_period_list": False,
        "contains_selected_context_or_split_ids": False,
        "contains_only_aggregate_capacity_evidence": True,
    }
    check_equal(failures, "public_privacy_contract", report.get("privacy"), expected_privacy)
    check_equal(
        failures,
        "precision_amendment_sha256",
        file_sha256(PRECISION_AMENDMENT_PATH),
        EXPECTED_PRECISION_AMENDMENT_SHA256,
    )
    check_equal(
        failures,
        "precision_amendment_status",
        precision_amendment.get("status"),
        "scope_downgrade_frozen_capacity_recheck_complete_manifest_pending",
    )
    check_equal(
        failures,
        "precision_amendment_capacity_recheck_status",
        precision_amendment.get("required_capacity_recheck", {}).get("status"),
        "complete",
    )
    for artifact_path, payload in [
        (CONFIG_PATH, config),
        (REPORT_PATH, report),
        (PRECISION_AMENDMENT_PATH, precision_amendment),
    ]:
        if contains_local_path(json.dumps(payload, ensure_ascii=True)):
            add_failure(failures, "local_path_in_public_json", repo_path(artifact_path))

    locked_results = methodology.get("locked_public_results", {})
    check_equal(
        failures,
        "historical_results_remain_locked",
        {key: locked_results.get(key) for key in EXPECTED_HISTORICAL_RESULTS},
        EXPECTED_HISTORICAL_RESULTS,
    )

    parser = HTMLCheckParser()
    parser.feed(html)
    for fragment in REQUIRED_HTML_FRAGMENTS:
        if fragment not in html:
            add_failure(failures, "required_html_fragment", fragment)
    for fragment in FORBIDDEN_HTML_FRAGMENTS:
        if fragment.lower() in html.lower():
            add_failure(failures, "forbidden_html_fragment", fragment)
    if parser.tag_counts["h1"] != 1:
        add_failure(failures, "html_h1_count", parser.tag_counts["h1"])
    if parser.tag_counts["h2"] < 5:
        add_failure(failures, "html_h2_count", parser.tag_counts["h2"])
    if parser.tag_counts["table"] < 3:
        add_failure(failures, "html_table_count", parser.tag_counts["table"])

    local_proof_checked = False
    if LOCAL_PROOF_PATH.exists():
        local_proof_checked = True
        local_proof = load_json(LOCAL_PROOF_PATH)
        check_equal(
            failures,
            "local_proof_sha256",
            file_sha256(LOCAL_PROOF_PATH),
            report.get("local_proof", {}).get("sha256"),
        )
        check_equal(failures, "local_proof_period_profile_count", len(local_proof.get("period_profiles", [])), 50)
        check_equal(failures, "local_proof_assignment_not_retained", local_proof.get("matching_assignment_retained"), False)
        local_projection = {
            "calendar": local_proof.get("calendar_period_count"),
            "observed": local_proof.get("observed_complete_period_count"),
            "empty": local_proof.get("empty_complete_period_count"),
            "complete_rows": local_proof.get("complete_period_source_row_count"),
            "boundary_rows": local_proof.get("excluded_boundary_source_row_count"),
            "family_capacity": local_proof.get("family_capacity"),
            "hall": local_proof.get("hall_capacity_checks"),
            "matched": local_proof.get("maximum_slot_matching_count"),
            "required": local_proof.get("required_slot_count"),
            "support": local_proof.get("support_distributions"),
        }
        public_projection = {
            "calendar": source.get("complete_calendar_period_count"),
            "observed": source.get("observed_complete_period_count"),
            "empty": source.get("empty_complete_period_count"),
            "complete_rows": source.get("complete_period_source_row_count"),
            "boundary_rows": source.get("excluded_boundary_source_row_count"),
            "family_capacity": family_capacity,
            "hall": hall_checks,
            "matched": proof.get("maximum_slot_matching_count"),
            "required": proof.get("required_slot_count"),
            "support": source.get("support_distributions"),
        }
        check_equal(failures, "local_public_aggregate_reconciliation", local_projection, public_projection)

    validation = {
        "status": (
            "confirmation_context_feasibility_validation_passed"
            if not failures
            else "confirmation_context_feasibility_validation_failed"
        ),
        "config_path": repo_path(CONFIG_PATH),
        "report_path": repo_path(REPORT_PATH),
        "html_path": repo_path(HTML_PATH),
        "candidate_id": report.get("candidate_id"),
        "context_feasibility_check_complete": report.get("context_feasibility_check_complete"),
        "observed_complete_period_count": source.get("observed_complete_period_count"),
        "required_total_context_count": proof.get("required_total_context_count"),
        "maximum_slot_matching_count": proof.get("maximum_slot_matching_count"),
        "minimum_hall_capacity_slack": proof.get("minimum_hall_capacity_slack"),
        "eligible_family_count": len(EXPECTED_ALLOWED_FAMILIES),
        "blocked_family_count": 1,
        "local_proof_checked": local_proof_checked,
        "context_manifest_created": report.get("context_manifest_created"),
        "execution_ready": report.get("execution_ready"),
        "no_new_results": report.get("no_new_results"),
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
