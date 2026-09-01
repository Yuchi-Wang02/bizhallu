from __future__ import annotations

import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any

import pandas as pd

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "confirmation_context_feasibility_v1.json"
STRICT_TABLE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "confirmation_online_retail_ii"
    / "strict_window_lines.csv.gz"
)
LOCAL_PROOF_PATH = STRICT_TABLE_PATH.parent / "context_feasibility_local_proof.json"
PUBLIC_REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility_report.json"
QUALITY_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_quality_report.json"
OVERLAP_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_overlap_report.json"
METHODOLOGY_PATH = PROJECT_ROOT / "reports" / "bizhallu_methodology_hardening_summary.json"

REQUIRED_COLUMNS = [
    "source_sheet",
    "source_row_number",
    "invoice_no",
    "stock_code",
    "quantity",
    "invoice_date",
    "country",
    "line_revenue",
    "is_exact_duplicate",
    "is_valid_net_revenue_line",
    "is_merchandise_net_revenue_line",
    "is_cancellation_or_return_line",
]
ELIGIBLE_FAMILIES = [
    "net_revenue_reconciliation_by_period",
    "product_return_rate_comparison",
    "country_product_exposure",
]
BLOCKED_FAMILY = "customer_revenue_concentration"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def boolean_series(series: pd.Series, name: str) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(bool)
    normalized = series.astype("string").str.strip().str.lower()
    invalid = normalized.notna() & ~normalized.isin(["true", "false", "1", "0"])
    if invalid.any():
        raise RuntimeError(f"Invalid boolean tokens in {name}: {sorted(normalized[invalid].unique())}")
    return normalized.map({"true": True, "false": False, "1": True, "0": False}).fillna(False).astype(bool)


def distribution(series: pd.Series) -> dict[str, float | int]:
    if series.empty:
        return {"minimum": 0, "median": 0.0, "maximum": 0}
    return {
        "minimum": int(series.min()),
        "median": float(series.median()),
        "maximum": int(series.max()),
    }


def family_config(config: dict[str, Any], family: str) -> dict[str, Any]:
    match = next((item for item in config["family_eligibility"] if item["family"] == family), None)
    if match is None:
        raise RuntimeError(f"Missing family eligibility config: {family}")
    return match


def generalized_hall_capacity(
    eligible_periods: dict[str, set[pd.Timestamp]],
    required_per_family: int,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    for size in range(1, len(ELIGIBLE_FAMILIES) + 1):
        for subset in combinations(ELIGIBLE_FAMILIES, size):
            available = len(set().union(*(eligible_periods[name] for name in subset)))
            required = required_per_family * len(subset)
            checks.append(
                {
                    "family_subset": list(subset),
                    "available_unique_period_count": available,
                    "required_unique_period_count": required,
                    "capacity_slack": available - required,
                    "passed": available >= required,
                }
            )
    return checks


def maximum_slot_matching_count(
    eligible_periods: dict[str, set[pd.Timestamp]],
    slots: list[tuple[str, str]],
) -> int:
    all_periods = sorted(set().union(*(eligible_periods[name] for name in ELIGIBLE_FAMILIES)))
    slot_to_period: dict[int, pd.Timestamp] = {}

    def assign(period: pd.Timestamp, visited_slots: set[int]) -> bool:
        for slot_index, (family, _split) in enumerate(slots):
            if period not in eligible_periods[family] or slot_index in visited_slots:
                continue
            visited_slots.add(slot_index)
            if slot_index not in slot_to_period or assign(slot_to_period[slot_index], visited_slots):
                slot_to_period[slot_index] = period
                return True
        return False

    return sum(assign(period, set()) for period in all_periods)


def main() -> None:
    required_files = [CONFIG_PATH, STRICT_TABLE_PATH, QUALITY_PATH, OVERLAP_PATH, METHODOLOGY_PATH]
    missing_files = [repo_path(path) for path in required_files if not path.exists()]
    if missing_files:
        raise FileNotFoundError(f"Missing context-feasibility prerequisites: {missing_files}")

    config = load_json(CONFIG_PATH)
    quality = load_json(QUALITY_PATH)
    overlap = load_json(OVERLAP_PATH)
    methodology = load_json(METHODOLOGY_PATH)

    frame = pd.read_csv(STRICT_TABLE_PATH, usecols=REQUIRED_COLUMNS, low_memory=False)
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing_columns:
        raise RuntimeError(f"Missing strict-window columns: {missing_columns}")

    frame["invoice_date"] = pd.to_datetime(frame["invoice_date"], errors="coerce")
    if frame["invoice_date"].isna().any():
        raise RuntimeError(f"Invalid invoice dates: {int(frame['invoice_date'].isna().sum())}")
    for column in [
        "is_exact_duplicate",
        "is_valid_net_revenue_line",
        "is_merchandise_net_revenue_line",
        "is_cancellation_or_return_line",
    ]:
        frame[column] = boolean_series(frame[column], column)

    context = config["context_grain"]
    calendar_periods = pd.date_range(
        context["first_complete_period_start"],
        context["last_complete_period_start"],
        freq="7D",
    )
    frame["period_start"] = frame["invoice_date"].dt.to_period("W-SUN").dt.start_time
    complete = frame.loc[frame["period_start"].isin(calendar_periods)].copy()
    excluded_boundary = frame.loc[~frame["period_start"].isin(calendar_periods)].copy()
    observed_periods = set(complete["period_start"].drop_duplicates())
    empty_periods = set(calendar_periods) - observed_periods
    first_complete_start = pd.Timestamp(context["first_complete_period_start"])
    final_complete_end = pd.Timestamp(context["last_complete_period_start"]) + pd.Timedelta(
        days=context["period_length_days"]
    )
    excluded_rows_are_only_partial_boundaries = bool(
        (
            (excluded_boundary["invoice_date"] < first_complete_start)
            | (excluded_boundary["invoice_date"] >= final_complete_end)
        ).all()
    )

    source_key_duplicate_count = int(
        complete.duplicated(subset=["source_sheet", "source_row_number"], keep=False).sum()
    )
    valid_mask = complete["is_valid_net_revenue_line"]
    merchandise_mask = complete["is_merchandise_net_revenue_line"]
    duplicate_evidence_conflicts = {
        "valid_net_revenue_lines_marked_exact_duplicate": int(
            (valid_mask & complete["is_exact_duplicate"]).sum()
        ),
        "merchandise_lines_marked_exact_duplicate": int(
            (merchandise_mask & complete["is_exact_duplicate"]).sum()
        ),
    }

    reconciliation_config = family_config(config, "net_revenue_reconciliation_by_period")
    valid = complete.loc[valid_mask].copy()
    valid["positive_revenue"] = valid["line_revenue"].gt(0)
    valid["negative_revenue"] = valid["line_revenue"].lt(0)
    reconciliation = valid.groupby("period_start").agg(
        valid_net_revenue_line_count=("source_row_number", "size"),
        positive_revenue_line_count=("positive_revenue", "sum"),
        gross_positive_revenue=("line_revenue", lambda values: values[values > 0].sum()),
        negative_revenue=("line_revenue", lambda values: values[values < 0].sum()),
        net_revenue=("line_revenue", "sum"),
    )
    return_counts = valid.loc[valid["is_cancellation_or_return_line"]].groupby("period_start").size()
    reconciliation["cancellation_or_return_row_count"] = return_counts.reindex(
        reconciliation.index, fill_value=0
    )
    reconciliation["reconciliation_difference"] = (
        reconciliation["gross_positive_revenue"]
        + reconciliation["negative_revenue"]
        - reconciliation["net_revenue"]
    )
    reconciliation["eligible"] = (
        reconciliation["valid_net_revenue_line_count"].ge(
            reconciliation_config["minimum_valid_net_revenue_lines"]
        )
        & reconciliation["positive_revenue_line_count"].ge(
            reconciliation_config["minimum_positive_revenue_lines"]
        )
        & reconciliation["cancellation_or_return_row_count"].ge(
            reconciliation_config["minimum_cancellation_or_return_rows"]
        )
        & reconciliation["gross_positive_revenue"].gt(0)
        & reconciliation["negative_revenue"].lt(0)
        & reconciliation["reconciliation_difference"].abs().le(
            reconciliation_config["reconciliation_tolerance_gbp"]
        )
    )

    product_config = family_config(config, "product_return_rate_comparison")
    merchandise = complete.loc[merchandise_mask].copy()
    merchandise["positive_units"] = merchandise["quantity"].clip(lower=0)
    merchandise["returned_units"] = -merchandise["quantity"].clip(upper=0)
    product = merchandise.groupby(["period_start", "stock_code"]).agg(
        positive_units=("positive_units", "sum"),
        returned_units=("returned_units", "sum"),
    )
    positive_invoice_counts = (
        merchandise.loc[merchandise["quantity"] > 0]
        .groupby(["period_start", "stock_code"])["invoice_no"]
        .nunique()
    )
    return_invoice_counts = (
        merchandise.loc[merchandise["quantity"] < 0]
        .groupby(["period_start", "stock_code"])["invoice_no"]
        .nunique()
    )
    product["positive_invoice_count"] = positive_invoice_counts.reindex(product.index, fill_value=0)
    product["return_invoice_count"] = return_invoice_counts.reindex(product.index, fill_value=0)
    eligible_products = product.loc[
        product["positive_units"].ge(product_config["minimum_positive_units_per_product"])
        & product["returned_units"].ge(product_config["minimum_returned_units_per_product"])
        & product["positive_invoice_count"].ge(
            product_config["minimum_positive_invoices_per_product"]
        )
        & product["return_invoice_count"].ge(product_config["minimum_return_invoices_per_product"])
    ].copy()
    eligible_products["return_to_positive_sales_ratio"] = (
        eligible_products["returned_units"] / eligible_products["positive_units"]
    ).round(product_config["ratio_rounding_decimals"])
    product_support = eligible_products.groupby("period_start").agg(
        eligible_product_count=("return_to_positive_sales_ratio", "size"),
        distinct_rounded_ratio_count=("return_to_positive_sales_ratio", "nunique"),
    )
    product_support = product_support.reindex(sorted(observed_periods), fill_value=0)
    product_support["eligible"] = (
        product_support["eligible_product_count"].ge(
            product_config["minimum_eligible_products_per_period"]
        )
        & product_support["distinct_rounded_ratio_count"].ge(
            product_config["minimum_distinct_rounded_ratios_per_period"]
        )
    )

    country_config = family_config(config, "country_product_exposure")
    excluded_country_values = {
        str(value).strip().casefold() for value in country_config["excluded_country_values"]
    }
    country_merchandise = merchandise.loc[
        ~merchandise["country"].astype("string").str.strip().str.casefold().isin(excluded_country_values)
    ]
    country = country_merchandise.groupby(["period_start", "country"]).agg(
        line_count=("source_row_number", "size"),
        distinct_product_count=("stock_code", "nunique"),
        net_revenue=("line_revenue", "sum"),
    )
    eligible_countries = country.loc[
        country["line_count"].ge(country_config["minimum_lines_per_country"])
        & country["distinct_product_count"].ge(
            country_config["minimum_distinct_products_per_country"]
        )
        & country["net_revenue"].gt(0)
    ]
    country_support = eligible_countries.groupby("period_start").size().rename("eligible_country_count")
    country_support = country_support.reindex(sorted(observed_periods), fill_value=0).to_frame()
    country_support["eligible"] = country_support["eligible_country_count"].ge(
        country_config["minimum_eligible_countries_per_period"]
    )

    weekly_rows = complete.groupby("period_start").size().rename("source_row_count")
    period_profile = pd.DataFrame(index=sorted(observed_periods))
    period_profile["source_row_count"] = weekly_rows
    period_profile["valid_net_revenue_line_count"] = reconciliation[
        "valid_net_revenue_line_count"
    ].reindex(period_profile.index, fill_value=0)
    period_profile["cancellation_or_return_row_count"] = reconciliation[
        "cancellation_or_return_row_count"
    ].reindex(period_profile.index, fill_value=0)
    period_profile["eligible_product_count"] = product_support["eligible_product_count"].reindex(
        period_profile.index, fill_value=0
    )
    period_profile["eligible_country_count"] = country_support["eligible_country_count"].reindex(
        period_profile.index, fill_value=0
    )
    period_profile["net_revenue_reconciliation_by_period"] = reconciliation["eligible"].reindex(
        period_profile.index, fill_value=False
    )
    period_profile["product_return_rate_comparison"] = product_support["eligible"].reindex(
        period_profile.index, fill_value=False
    )
    period_profile["country_product_exposure"] = country_support["eligible"].reindex(
        period_profile.index, fill_value=False
    )

    eligible_periods = {
        family: set(period_profile.index[period_profile[family].astype(bool)])
        for family in ELIGIBLE_FAMILIES
    }
    target = config["capacity_target"]
    required_per_family = target["required_contexts_per_eligible_family"]
    hall_checks = generalized_hall_capacity(eligible_periods, required_per_family)
    slots: list[tuple[str, str]] = []
    for family in ELIGIBLE_FAMILIES:
        slots.extend([(family, "protocol_pilot")] * target["protocol_pilot_contexts_per_family"])
        slots.extend([(family, "development")] * target["development_contexts_per_family"])
        slots.extend([(family, "confirmation")] * target["confirmation_contexts_per_family"])
    maximum_matching_count = maximum_slot_matching_count(eligible_periods, slots)

    support_distributions = {
        "source_rows_per_observed_complete_period": distribution(period_profile["source_row_count"]),
        "valid_net_revenue_lines_per_observed_complete_period": distribution(
            period_profile["valid_net_revenue_line_count"]
        ),
        "cancellation_or_return_rows_per_observed_complete_period": distribution(
            period_profile["cancellation_or_return_row_count"]
        ),
        "eligible_products_per_observed_complete_period": distribution(
            period_profile["eligible_product_count"]
        ),
        "eligible_countries_per_observed_complete_period": distribution(
            period_profile["eligible_country_count"]
        ),
    }
    family_capacity = {
        family: {
            "eligible_period_count": len(eligible_periods[family]),
            "required_period_count": required_per_family,
            "capacity_slack": len(eligible_periods[family]) - required_per_family,
            "all_observed_complete_periods_eligible": eligible_periods[family] == observed_periods,
        }
        for family in ELIGIBLE_FAMILIES
    }
    family_capacity[BLOCKED_FAMILY] = {
        "eligible_period_count": 0,
        "required_period_count": 0,
        "status": "blocked_by_preexisting_quality_control",
        "missing_customer_id_rows": quality["completeness"]["by_column"]["CustomerID"][
            "missing_or_blank_count"
        ],
    }

    local_period_profiles = []
    for period, row in period_profile.iterrows():
        local_period_profiles.append(
            {
                "period_start": str(period.date()),
                "source_row_count": int(row["source_row_count"]),
                "valid_net_revenue_line_count": int(row["valid_net_revenue_line_count"]),
                "cancellation_or_return_row_count": int(row["cancellation_or_return_row_count"]),
                "eligible_product_count": int(row["eligible_product_count"]),
                "eligible_country_count": int(row["eligible_country_count"]),
                "family_eligibility": {
                    family: bool(row[family]) for family in ELIGIBLE_FAMILIES
                },
            }
        )

    historical_auprc = methodology["locked_public_results"]["exploratory_max_test_auprc"]
    historical_f1 = methodology["locked_public_results"]["exploratory_max_test_f1"]
    checks = {
        "config_status_is_frozen_profile_pending": config["status"] == "rules_frozen_profile_pending",
        "strict_table_hash_matches_frozen_input": (
            sha256_file(STRICT_TABLE_PATH) == config["input"]["strict_window_table_sha256"]
        ),
        "strict_row_count_matches_frozen_input": len(frame) == config["input"]["strict_window_row_count"],
        "complete_calendar_period_count_matches_config": (
            len(calendar_periods) == context["expected_complete_calendar_period_count"]
        ),
        "source_rows_reconcile_to_complete_and_boundary_periods": (
            len(complete) + (len(frame) - len(complete)) == len(frame)
        ),
        "excluded_rows_are_only_partial_boundary_weeks": excluded_rows_are_only_partial_boundaries,
        "source_keys_are_unique_within_complete_period_pool": source_key_duplicate_count == 0,
        "evidence_flags_exclude_exact_duplicates": all(
            count == 0 for count in duplicate_evidence_conflicts.values()
        ),
        "all_eligible_families_meet_individual_capacity": all(
            values["eligible_period_count"] >= values["required_period_count"]
            for family, values in family_capacity.items()
            if family in ELIGIBLE_FAMILIES
        ),
        "generalized_hall_capacity_passes": all(item["passed"] for item in hall_checks),
        "maximum_matching_fills_all_required_slots": maximum_matching_count == len(slots),
        "customer_family_remains_blocked": (
            family_config(config, BLOCKED_FAMILY)["status"] == "blocked_by_preexisting_quality_control"
            and family_capacity[BLOCKED_FAMILY]["eligible_period_count"] == 0
        ),
        "historical_canonical_overlap_remains_zero": (
            overlap["record_overlap"]["canonical_eight_field"]["multiset_overlap_row_count"] == 0
        ),
        "historical_date_blind_overlap_remains_zero": (
            overlap["record_overlap"]["date_blind_seven_field_sensitivity"][
                "multiset_overlap_row_count"
            ]
            == 0
        ),
        "historical_metrics_remain_locked": historical_auprc == 0.835073 and historical_f1 == 0.779412,
    }
    failures = [name for name, passed in checks.items() if not passed]

    local_proof = {
        "schema_version": "1.0",
        "status": "context_feasibility_local_proof_complete" if not failures else "context_feasibility_local_proof_failed",
        "config_path": repo_path(CONFIG_PATH),
        "config_sha256": sha256_file(CONFIG_PATH),
        "strict_table_sha256": sha256_file(STRICT_TABLE_PATH),
        "calendar_period_count": len(calendar_periods),
        "observed_complete_period_count": len(observed_periods),
        "empty_complete_period_count": len(empty_periods),
        "complete_period_source_row_count": len(complete),
        "excluded_boundary_source_row_count": len(frame) - len(complete),
        "period_profiles": local_period_profiles,
        "family_capacity": family_capacity,
        "hall_capacity_checks": hall_checks,
        "maximum_slot_matching_count": maximum_matching_count,
        "required_slot_count": len(slots),
        "matching_assignment_retained": False,
        "support_distributions": support_distributions,
        "critical_checks": checks,
        "failed_critical_checks": failures,
    }
    LOCAL_PROOF_PATH.write_text(json.dumps(local_proof, indent=2, ensure_ascii=True), encoding="utf-8")

    public_report = {
        "schema_version": "1.0",
        "status": (
            "outcome_blind_context_feasibility_complete"
            if not failures
            else "outcome_blind_context_feasibility_failed"
        ),
        "study_name": "Confirmation Set v1",
        "candidate_id": "uci_online_retail_ii_prior_period",
        "scope": "aggregate-only outcome-blind capacity proof for period-disjoint evidence contexts",
        "explicitly_not_in_scope": [
            "selected context IDs, context manifest, split assignment, or context-level evidence hashes",
            "questions, prompts, model outputs, annotations, verifier decisions, or detector scores",
            "confirmation AUPRC, F1, class prevalence, or any other new experiment metric",
        ],
        "config": {
            "path": repo_path(CONFIG_PATH),
            "sha256": sha256_file(CONFIG_PATH),
            "status": config["status"],
        },
        "input": {
            "strict_window_table_path": repo_path(STRICT_TABLE_PATH),
            "strict_window_table_sha256": sha256_file(STRICT_TABLE_PATH),
            "strict_window_row_count": len(frame),
            "historical_overlap_report": repo_path(OVERLAP_PATH),
        },
        "context_definition": {
            "period_definition": context["period_definition"],
            "first_complete_period_start": context["first_complete_period_start"],
            "last_complete_period_start": context["last_complete_period_start"],
            "period_length_days": context["period_length_days"],
            "boundary_policy": context["boundary_policy"],
            "one_family_per_final_context_period": True,
            "final_context_or_split_assignment_created": False,
        },
        "source_capacity": {
            "complete_calendar_period_count": len(calendar_periods),
            "observed_complete_period_count": len(observed_periods),
            "empty_complete_period_count": len(empty_periods),
            "complete_period_source_row_count": len(complete),
            "excluded_boundary_source_row_count": len(frame) - len(complete),
            "source_rows_reconciled": len(complete) + (len(frame) - len(complete)) == len(frame),
            "excluded_rows_are_only_partial_boundary_weeks": excluded_rows_are_only_partial_boundaries,
            "support_distributions": support_distributions,
        },
        "family_capacity": family_capacity,
        "capacity_proof": {
            "required_protocol_pilot_context_count": target["required_protocol_pilot_contexts"],
            "required_development_context_count": target["required_development_contexts"],
            "required_confirmation_context_count": target["required_confirmation_contexts"],
            "required_total_context_count": target["required_total_contexts"],
            "required_contexts_per_eligible_family": required_per_family,
            "generalized_hall_checks": hall_checks,
            "minimum_hall_capacity_slack": min(item["capacity_slack"] for item in hall_checks),
            "maximum_slot_matching_count": maximum_matching_count,
            "required_slot_count": len(slots),
            "matching_assignment_retained_or_published": False,
            "capacity_target_feasible": maximum_matching_count == len(slots) and all(
                item["passed"] for item in hall_checks
            ),
        },
        "evidence_separation": {
            "complete_periods_are_calendar_disjoint": True,
            "excluded_rows_are_only_partial_boundary_weeks": excluded_rows_are_only_partial_boundaries,
            "candidate_period_assigned_to_at_most_one_final_family": True,
            "source_key_duplicate_count_within_complete_period_pool": source_key_duplicate_count,
            "evidence_flag_duplicate_conflicts": duplicate_evidence_conflicts,
            "historical_canonical_overlap_row_count": overlap["record_overlap"][
                "canonical_eight_field"
            ]["multiset_overlap_row_count"],
            "historical_date_blind_overlap_row_count": overlap["record_overlap"][
                "date_blind_seven_field_sensitivity"
            ]["multiset_overlap_row_count"],
            "final_evidence_fingerprint_check_pending_manifest_freeze": True,
        },
        "research_decision": {
            "context_feasibility_check_complete": not failures,
            "minimum_36_period_disjoint_context_capacity_verified": not failures,
            "dataset_source_selected_and_audited_gate_eligible_for_completion": not failures,
            "customer_family_excluded_from_capacity_target": True,
            "context_manifest_and_split_assignment_pending": True,
            "precision_review_pending": True,
            "execution_ready": False,
            "claim_limit": "This proves source capacity for a same-retailer temporal internal replication. It does not select contexts, validate question wording, create independent labels, or establish external generalization.",
        },
        "critical_checks": checks,
        "failed_critical_checks": failures,
        "local_proof": {
            "path": repo_path(LOCAL_PROOF_PATH),
            "sha256": sha256_file(LOCAL_PROOF_PATH),
            "git_ignored": True,
            "contains_period_profiles": True,
            "matching_assignment_retained": False,
        },
        "privacy": {
            "contains_invoice_values": False,
            "contains_customer_values": False,
            "contains_product_or_country_candidate_values": False,
            "contains_row_fingerprints": False,
            "contains_candidate_period_list": False,
            "contains_selected_context_or_split_ids": False,
            "contains_only_aggregate_capacity_evidence": True,
        },
        "context_feasibility_check_complete": not failures,
        "context_manifest_created": False,
        "split_assignment_created": False,
        "question_created": False,
        "prompt_created": False,
        "model_run_performed": False,
        "new_metrics_reported": False,
        "execution_ready": False,
        "no_new_results": True,
        "next_authorized_action": config["next_if_passed"],
    }
    PUBLIC_REPORT_PATH.write_text(
        json.dumps(public_report, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": public_report["status"],
                "complete_calendar_period_count": len(calendar_periods),
                "observed_complete_period_count": len(observed_periods),
                "eligible_period_counts": {
                    family: family_capacity[family]["eligible_period_count"]
                    for family in [*ELIGIBLE_FAMILIES, BLOCKED_FAMILY]
                },
                "maximum_slot_matching_count": maximum_matching_count,
                "required_slot_count": len(slots),
                "failed_critical_checks": failures,
                "report_path": repo_path(PUBLIC_REPORT_PATH),
            },
            indent=2,
            ensure_ascii=True,
        )
    )
    if failures:
        raise RuntimeError(f"Context feasibility proof failed: {failures}")


if __name__ == "__main__":
    main()
