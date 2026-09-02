from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

import pandas as pd

from profile_confirmation_context_feasibility import boolean_series
from profile_confirmation_dataset_overlap import (
    CANONICAL_FIELDS,
    fingerprint_counters,
    inventory_manifest_sha256,
    normalize_frame,
)
from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "confirmation_context_manifest_v1.json"
FEASIBILITY_CONFIG_PATH = (
    PROJECT_ROOT / "configs" / "confirmation_context_feasibility_v1.json"
)
FEASIBILITY_REPORT_PATH = (
    PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility_report.json"
)
OVERLAP_REPORT_PATH = (
    PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_overlap_report.json"
)
PRECISION_AMENDMENT_PATH = (
    PROJECT_ROOT / "configs" / "confirmation_precision_scope_amendment_v1.json"
)
METHODOLOGY_PATH = PROJECT_ROOT / "reports" / "bizhallu_methodology_hardening_summary.json"
LOCAL_DIR = PROJECT_ROOT / "data" / "processed" / "confirmation_online_retail_ii"
LOCAL_PROOF_PATH = LOCAL_DIR / "context_feasibility_local_proof.json"
STRICT_TABLE_PATH = LOCAL_DIR / "strict_window_lines.csv.gz"
PRIVATE_MANIFEST_PATH = LOCAL_DIR / "context_manifest_v1_private.json"
PUBLIC_REPORT_PATH = (
    PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_manifest_report.json"
)

TEXT_HASH_SUFFIXES = {".csv", ".html", ".json", ".md", ".txt", ".yml", ".yaml"}
REQUIRED_COLUMNS = [
    *CANONICAL_FIELDS,
    "source_sheet",
    "source_row_number",
    "line_revenue",
    "is_exact_duplicate",
    "is_valid_net_revenue_line",
    "is_merchandise_net_revenue_line",
    "is_cancellation_or_return_line",
]
SPLIT_ORDER = ["protocol_pilot", "development", "confirmation"]
FAMILY_CODES = {
    "net_revenue_reconciliation_by_period": "nrr",
    "product_return_rate_comparison": "prr",
    "country_product_exposure": "cpe",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    if path.suffix.lower() in TEXT_HASH_SUFFIXES:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Any, domain: str) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def seeded_hash(domain: str, seed: int, *parts: str) -> str:
    digest = hashlib.sha256(domain.encode("utf-8") + b"\x00")
    digest.update(str(seed).encode("ascii"))
    for part in parts:
        encoded = part.encode("utf-8")
        digest.update(b"\x00")
        digest.update(len(encoded).to_bytes(4, "big"))
        digest.update(encoded)
    return digest.hexdigest()


def family_rule(feasibility_config: dict[str, Any], family: str) -> dict[str, Any]:
    rule = next(
        (item for item in feasibility_config["family_eligibility"] if item["family"] == family),
        None,
    )
    if rule is None:
        raise RuntimeError(f"Missing family rule: {family}")
    return rule


def deterministic_family_matching(
    *,
    families: list[str],
    periods: list[str],
    eligible_periods: dict[str, set[str]],
    slots_per_family: int,
    seed: int,
    slot_domain: str,
    candidate_domain: str,
) -> dict[str, str]:
    slots = [f"{family}:{index:02d}" for family in families for index in range(1, slots_per_family + 1)]
    slot_order = sorted(
        slots,
        key=lambda slot: (seeded_hash(slot_domain, seed, slot), slot),
    )
    slot_to_period: dict[str, str] = {}
    period_to_slot: dict[str, str] = {}

    def assign(slot: str, visited_periods: set[str]) -> bool:
        family = slot.rsplit(":", 1)[0]
        candidates = sorted(
            eligible_periods[family],
            key=lambda period: (
                seeded_hash(candidate_domain, seed, slot, period),
                period,
            ),
        )
        for period in candidates:
            if period in visited_periods:
                continue
            visited_periods.add(period)
            previous_slot = period_to_slot.get(period)
            if previous_slot is None or assign(previous_slot, visited_periods):
                period_to_slot[period] = slot
                slot_to_period[slot] = period
                return True
        return False

    for slot in slot_order:
        if not assign(slot, set()):
            raise RuntimeError(f"Deterministic matching failed at slot {slot}")

    expected_slot_count = len(families) * slots_per_family
    if len(slot_to_period) != expected_slot_count or len(period_to_slot) != expected_slot_count:
        raise RuntimeError(
            f"Matching size mismatch: slots={len(slot_to_period)}, periods={len(period_to_slot)}"
        )
    if not set(period_to_slot).issubset(set(periods)):
        raise RuntimeError("Matching selected a period outside the frozen candidate inventory")
    return slot_to_period


def eligible_product_entities(period_frame: pd.DataFrame, rule: dict[str, Any]) -> list[str]:
    merchandise = period_frame.loc[period_frame["is_merchandise_net_revenue_line"]].copy()
    merchandise["stock_code"] = merchandise["stock_code"].astype("string").str.strip()
    merchandise["positive_units"] = merchandise["quantity"].clip(lower=0)
    merchandise["returned_units"] = -merchandise["quantity"].clip(upper=0)
    product = merchandise.groupby("stock_code", dropna=True).agg(
        positive_units=("positive_units", "sum"),
        returned_units=("returned_units", "sum"),
    )
    product["positive_invoice_count"] = (
        merchandise.loc[merchandise["quantity"] > 0]
        .groupby("stock_code")["invoice_no"]
        .nunique()
        .reindex(product.index, fill_value=0)
    )
    product["return_invoice_count"] = (
        merchandise.loc[merchandise["quantity"] < 0]
        .groupby("stock_code")["invoice_no"]
        .nunique()
        .reindex(product.index, fill_value=0)
    )
    eligible = product.loc[
        product["positive_units"].ge(rule["minimum_positive_units_per_product"])
        & product["returned_units"].ge(rule["minimum_returned_units_per_product"])
        & product["positive_invoice_count"].ge(rule["minimum_positive_invoices_per_product"])
        & product["return_invoice_count"].ge(rule["minimum_return_invoices_per_product"])
    ]
    return sorted(str(value) for value in eligible.index.tolist())


def eligible_country_entities(period_frame: pd.DataFrame, rule: dict[str, Any]) -> list[str]:
    merchandise = period_frame.loc[period_frame["is_merchandise_net_revenue_line"]].copy()
    merchandise["country"] = merchandise["country"].astype("string").str.strip()
    excluded = {str(value).strip().casefold() for value in rule["excluded_country_values"]}
    merchandise = merchandise.loc[~merchandise["country"].str.casefold().isin(excluded)]
    country = merchandise.groupby("country", dropna=True).agg(
        line_count=("source_row_number", "size"),
        distinct_product_count=("stock_code", "nunique"),
        net_revenue=("line_revenue", "sum"),
    )
    eligible = country.loc[
        country["line_count"].ge(rule["minimum_lines_per_country"])
        & country["distinct_product_count"].ge(rule["minimum_distinct_products_per_country"])
        & country["net_revenue"].gt(0)
    ]
    return sorted(str(value) for value in eligible.index.tolist())


def context_evidence(
    period_frame: pd.DataFrame,
    family: str,
    feasibility_config: dict[str, Any],
) -> tuple[list[str], pd.DataFrame]:
    rule = family_rule(feasibility_config, family)
    if family == "net_revenue_reconciliation_by_period":
        return ["global"], period_frame.loc[period_frame["is_valid_net_revenue_line"]].copy()
    if family == "product_return_rate_comparison":
        entities = eligible_product_entities(period_frame, rule)
        stock_codes = period_frame["stock_code"].astype("string").str.strip()
        evidence = period_frame.loc[
            period_frame["is_merchandise_net_revenue_line"] & stock_codes.isin(entities)
        ].copy()
        return entities, evidence
    if family == "country_product_exposure":
        entities = eligible_country_entities(period_frame, rule)
        countries = period_frame["country"].astype("string").str.strip()
        evidence = period_frame.loc[
            period_frame["is_merchandise_net_revenue_line"] & countries.isin(entities)
        ].copy()
        return entities, evidence
    raise RuntimeError(f"Unsupported family: {family}")


def main() -> None:
    required_files = [
        CONFIG_PATH,
        FEASIBILITY_CONFIG_PATH,
        FEASIBILITY_REPORT_PATH,
        OVERLAP_REPORT_PATH,
        PRECISION_AMENDMENT_PATH,
        METHODOLOGY_PATH,
        LOCAL_PROOF_PATH,
        STRICT_TABLE_PATH,
    ]
    missing = [repo_path(path) for path in required_files if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing manifest-freeze prerequisites: {missing}")

    config = load_json(CONFIG_PATH)
    feasibility_config = load_json(FEASIBILITY_CONFIG_PATH)
    feasibility = load_json(FEASIBILITY_REPORT_PATH)
    overlap = load_json(OVERLAP_REPORT_PATH)
    precision_amendment = load_json(PRECISION_AMENDMENT_PATH)
    methodology = load_json(METHODOLOGY_PATH)
    local_proof = load_json(LOCAL_PROOF_PATH)

    prechecks = {
        "assignment_rules_are_frozen": config["status"] == "assignment_rules_frozen",
        "strict_table_hash_matches": (
            sha256_file(STRICT_TABLE_PATH) == config["inputs"]["strict_window_table_sha256"]
        ),
        "local_feasibility_proof_passed": (
            local_proof["status"] == "context_feasibility_local_proof_complete"
            and local_proof["failed_critical_checks"] == []
        ),
        "public_feasibility_report_passed": (
            feasibility["status"] == "outcome_blind_context_feasibility_complete"
        ),
        "precision_scope_is_estimation_only": (
            precision_amendment["scope_amendment"]["decision"]
            == "downgrade_from_superiority_to_estimation"
            and "Do not claim" in precision_amendment["scope_amendment"]["prohibited_primary_claim"]
        ),
        "historical_canonical_record_overlap_is_zero": (
            overlap["record_overlap"]["canonical_eight_field"]["multiset_overlap_row_count"] == 0
        ),
        "historical_date_blind_record_overlap_is_zero": (
            overlap["record_overlap"]["date_blind_seven_field_sensitivity"][
                "multiset_overlap_row_count"
            ]
            == 0
        ),
        "historical_metrics_remain_exploratory_and_locked": (
            methodology["locked_public_results"]["exploratory_max_test_auprc"] == 0.835073
            and methodology["locked_public_results"]["exploratory_max_test_f1"] == 0.779412
            and methodology["locked_public_results"]["aligned_span_count"] == 205
            and methodology["locked_public_results"]["test_span_count"] == 103
        ),
    }
    failed_prechecks = [name for name, passed in prechecks.items() if not passed]
    if failed_prechecks:
        raise RuntimeError(f"Manifest-freeze prechecks failed: {failed_prechecks}")

    frame = pd.read_csv(STRICT_TABLE_PATH, usecols=REQUIRED_COLUMNS, low_memory=False)
    frame["invoice_date"] = pd.to_datetime(frame["invoice_date"], errors="coerce")
    if frame["invoice_date"].isna().any():
        raise RuntimeError("Strict table contains invalid invoice dates")
    frame["quantity"] = pd.to_numeric(frame["quantity"], errors="raise")
    frame["line_revenue"] = pd.to_numeric(frame["line_revenue"], errors="raise")
    for column in [
        "is_exact_duplicate",
        "is_valid_net_revenue_line",
        "is_merchandise_net_revenue_line",
        "is_cancellation_or_return_line",
    ]:
        frame[column] = boolean_series(frame[column], column)
    frame["period_start"] = frame["invoice_date"].dt.to_period("W-SUN").dt.start_time
    period_frames = {
        str(period.date()): group.copy()
        for period, group in frame.groupby("period_start", sort=True)
    }

    profiles = local_proof["period_profiles"]
    profile_by_period = {item["period_start"]: item for item in profiles}
    candidate_periods = sorted(profile_by_period)
    families = config["candidate_policy"]["allowed_question_families"]
    eligible_periods = {
        family: {
            period
            for period, profile in profile_by_period.items()
            if profile["family_eligibility"][family]
        }
        for family in families
    }

    target = config["target"]
    if len(candidate_periods) != target["candidate_period_count"]:
        raise RuntimeError("Candidate period count drifted from the frozen target")
    slots_per_family = target["per_family"]["total"]
    assignment = config["assignment"]
    slot_to_period = deterministic_family_matching(
        families=families,
        periods=candidate_periods,
        eligible_periods=eligible_periods,
        slots_per_family=slots_per_family,
        seed=assignment["seed"],
        slot_domain=assignment["family_slot_order_domain"],
        candidate_domain=assignment["candidate_order_domain"],
    )

    family_periods: dict[str, list[str]] = {family: [] for family in families}
    for slot, period in slot_to_period.items():
        family = slot.rsplit(":", 1)[0]
        family_periods[family].append(period)

    split_by_family_period: dict[tuple[str, str], tuple[str, int]] = {}
    split_targets = target["per_family"]
    for family in families:
        ordered = sorted(
            family_periods[family],
            key=lambda period: (
                seeded_hash(assignment["split_order_domain"], assignment["seed"], family, period),
                period,
            ),
        )
        cursor = 0
        for split in SPLIT_ORDER:
            count = split_targets[split]
            for split_index, period in enumerate(ordered[cursor : cursor + count], start=1):
                split_by_family_period[(family, period)] = (split, split_index)
            cursor += count
        if cursor != slots_per_family:
            raise RuntimeError(f"Split allocation mismatch for {family}: {cursor}")

    contexts: list[dict[str, Any]] = []
    for family in families:
        business_scope = family_rule(feasibility_config, family)["business_scope"]
        for period in family_periods[family]:
            period_frame = period_frames.get(period)
            if period_frame is None:
                raise RuntimeError(f"Selected period is absent from strict source table: {period}")
            scope_entities, evidence = context_evidence(period_frame, family, feasibility_config)
            if evidence.empty or not scope_entities:
                raise RuntimeError(f"Empty context evidence for {family} / {period}")
            normalized_evidence = normalize_frame(evidence[CANONICAL_FIELDS])
            evidence_counter = fingerprint_counters(
                normalized_evidence,
                include_sensitivity_families=False,
            )["canonical_record"]
            evidence_hash = inventory_manifest_sha256(evidence_counter)
            scope_hash = canonical_json_sha256(
                scope_entities,
                config["assignment"]["scope_entity_domain"],
            )
            period_end = (pd.Timestamp(period) + pd.Timedelta(days=7)).date().isoformat()
            context_payload = {
                "dataset_version": "uci_online_retail_ii_strict_prior_period_v1",
                "evidence_source_table": repo_path(STRICT_TABLE_PATH),
                "business_period": {
                    "start_inclusive": period,
                    "end_exclusive": period_end,
                },
                "question_family": family,
                "business_scope": business_scope,
                "scope_entities": scope_entities,
                "canonical_evidence_rows_sha256": evidence_hash,
            }
            context_digest = canonical_json_sha256(
                context_payload,
                config["assignment"]["context_id_domain"],
            )
            split, split_index = split_by_family_period[(family, period)]
            profile = profile_by_period[period]
            contexts.append(
                {
                    "context_id": f"cv1_{FAMILY_CODES[family]}_{context_digest[:16]}",
                    "context_id_sha256": context_digest,
                    "question_family": family,
                    "business_scope": business_scope,
                    "split": split,
                    "split_index_within_family": split_index,
                    "period_start": period,
                    "period_end_exclusive": period_end,
                    "scope_entity_count": len(scope_entities),
                    "scope_entities": scope_entities,
                    "scope_entities_sha256": scope_hash,
                    "canonical_evidence_row_count": int(sum(evidence_counter.values())),
                    "canonical_evidence_unique_row_fingerprint_count": len(evidence_counter),
                    "canonical_evidence_rows_sha256": evidence_hash,
                    "candidate_profile_sha256": canonical_json_sha256(
                        profile,
                        "bizhallu:confirmation-candidate-profile:v1",
                    ),
                    "source_support": {
                        key: profile[key]
                        for key in [
                            "source_row_count",
                            "valid_net_revenue_line_count",
                            "cancellation_or_return_row_count",
                            "eligible_product_count",
                            "eligible_country_count",
                        ]
                    },
                }
            )

    split_rank = {name: index for index, name in enumerate(SPLIT_ORDER)}
    contexts.sort(
        key=lambda item: (
            split_rank[item["split"]],
            item["question_family"],
            item["split_index_within_family"],
        )
    )
    selected_periods = {item["period_start"] for item in contexts}
    reserve_periods = sorted(set(candidate_periods) - selected_periods)
    reserves = [
        {
            "reserve_id": f"reserve_{index:02d}",
            "period_start": period,
            "period_end_exclusive": (
                pd.Timestamp(period) + pd.Timedelta(days=7)
            ).date().isoformat(),
            "candidate_profile_sha256": canonical_json_sha256(
                profile_by_period[period],
                "bizhallu:confirmation-candidate-profile:v1",
            ),
            "substitution_policy": "not_available_after_model_outcome_access",
        }
        for index, period in enumerate(reserve_periods, start=1)
    ]

    family_counts = Counter(item["question_family"] for item in contexts)
    split_counts = Counter(item["split"] for item in contexts)
    family_split_counts = {
        family: {
            split: sum(
                item["question_family"] == family and item["split"] == split
                for item in contexts
            )
            for split in SPLIT_ORDER
        }
        for family in families
    }
    checks = {
        **prechecks,
        "selected_context_count_matches_target": len(contexts) == target["selected_context_count"],
        "reserve_period_count_matches_target": len(reserves) == target["reserve_period_count"],
        "all_selected_periods_are_unique": len(selected_periods) == len(contexts),
        "selected_and_reserve_periods_cover_candidate_inventory": (
            selected_periods | set(reserve_periods) == set(candidate_periods)
            and not selected_periods.intersection(reserve_periods)
        ),
        "family_counts_match_target": all(
            family_counts[family] == target["per_family"]["total"] for family in families
        ),
        "split_counts_match_target": all(
            split_counts[split] == target["all_families"][split] for split in SPLIT_ORDER
        ),
        "family_split_counts_match_target": all(
            family_split_counts[family][split] == target["per_family"][split]
            for family in families
            for split in SPLIT_ORDER
        ),
        "context_ids_are_unique": len({item["context_id"] for item in contexts}) == len(contexts),
        "context_evidence_hashes_are_unique": (
            len({item["canonical_evidence_rows_sha256"] for item in contexts}) == len(contexts)
        ),
        "every_context_has_scope_entities": all(item["scope_entity_count"] > 0 for item in contexts),
        "every_context_has_canonical_evidence_rows": all(
            item["canonical_evidence_row_count"] > 0 for item in contexts
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        raise RuntimeError(f"Manifest-freeze checks failed: {failures}")

    private_manifest = {
        "schema_version": "1.0",
        "status": "confirmation_context_manifest_v1_private_frozen",
        "study_name": config["study_name"],
        "frozen_on": config["frozen_on"],
        "public_config_path": repo_path(CONFIG_PATH),
        "public_config_canonical_sha256": canonical_json_sha256(
            config,
            "bizhallu:confirmation-context-manifest-config:v1",
        ),
        "source": {
            "strict_window_table": repo_path(STRICT_TABLE_PATH),
            "strict_window_table_sha256": sha256_file(STRICT_TABLE_PATH),
            "strict_window_row_count": len(frame),
            "local_feasibility_proof_canonical_sha256": canonical_json_sha256(
                local_proof,
                "bizhallu:confirmation-feasibility-local-proof:v1",
            ),
            "historical_canonical_record_overlap_row_count": 0,
            "historical_date_blind_record_overlap_row_count": 0,
        },
        "assignment": {
            "seed": assignment["seed"],
            "family_matching_algorithm": assignment["family_matching_algorithm"],
            "split_assignment_policy": assignment["split_assignment_policy"],
            "selected_context_count": len(contexts),
            "reserve_period_count": len(reserves),
            "family_counts": dict(sorted(family_counts.items())),
            "split_counts": {split: split_counts[split] for split in SPLIT_ORDER},
            "family_split_counts": family_split_counts,
        },
        "contexts": contexts,
        "source_reserve_periods": reserves,
        "next_gate": {
            "gate": "question_templates_and_gold_calculations_validated",
            "question_ids_created": False,
            "question_evidence_payload_fingerprint_check_pending": True,
        },
        "execution_boundary": {
            "questions_created": False,
            "prompts_created": False,
            "model_outputs_created": False,
            "labels_created": False,
            "detector_or_verifier_scores_created": False,
            "new_empirical_metrics_created": False,
        },
        "critical_checks": checks,
        "failed_critical_checks": [],
    }
    PRIVATE_MANIFEST_PATH.write_text(
        json.dumps(private_manifest, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    private_commitment = canonical_json_sha256(
        private_manifest,
        "bizhallu:confirmation-private-context-manifest:v1",
    )

    public_report = {
        "schema_version": "1.0",
        "status": "confirmation_context_manifest_v1_frozen",
        "study_name": config["study_name"],
        "frozen_on": config["frozen_on"],
        "scope": "aggregate public commitment to an outcome-blind private context manifest and period-disjoint 6/15/27 split",
        "config": {
            "path": repo_path(CONFIG_PATH),
            "canonical_sha256": canonical_json_sha256(
                config,
                "bizhallu:confirmation-context-manifest-config:v1",
            ),
            "status": config["status"],
        },
        "private_manifest_commitment": {
            "path": repo_path(PRIVATE_MANIFEST_PATH),
            "git_ignored": True,
            "canonical_sha256": private_commitment,
            "commitment_domain": "bizhallu:confirmation-private-context-manifest:v1",
            "contains_selected_periods_and_scope_entities": True,
            "published_contents": False,
        },
        "input_evidence": {
            "strict_window_table_sha256": sha256_file(STRICT_TABLE_PATH),
            "strict_window_row_count": len(frame),
            "local_feasibility_proof_canonical_sha256": private_manifest["source"][
                "local_feasibility_proof_canonical_sha256"
            ],
            "observed_complete_period_count": len(candidate_periods),
            "maximum_feasible_matching_count": feasibility["capacity_proof"][
                "maximum_slot_matching_count"
            ],
            "minimum_hall_capacity_slack": feasibility["capacity_proof"][
                "minimum_hall_capacity_slack"
            ],
            "historical_canonical_record_overlap_row_count": 0,
            "historical_date_blind_record_overlap_row_count": 0,
        },
        "frozen_inventory": {
            "candidate_period_count": len(candidate_periods),
            "selected_context_count": len(contexts),
            "reserve_period_count": len(reserves),
            "questions_per_context": target["questions_per_context"],
            "future_question_target": target["selected_question_target"],
            "family_count": len(families),
            "family_counts": dict(sorted(family_counts.items())),
            "split_counts": {split: split_counts[split] for split in SPLIT_ORDER},
            "family_split_counts": family_split_counts,
        },
        "assignment_integrity": {
            "seed": assignment["seed"],
            "algorithm": assignment["family_matching_algorithm"],
            "outcome_blind": True,
            "all_selected_periods_unique": True,
            "period_disjoint_across_all_contexts_and_splits": True,
            "one_family_per_selected_period": True,
            "reserve_substitution_after_outcome_access_allowed": False,
        },
        "context_evidence_integrity": {
            "canonical_context_pool_hash_count": len(contexts),
            "unique_canonical_context_pool_hash_count": len(
                {item["canonical_evidence_rows_sha256"] for item in contexts}
            ),
            "context_pool_hashes_disjoint_across_selected_contexts": True,
            "historical_source_records_disjoint": True,
            "final_question_evidence_payload_fingerprint_check": "pending_next_gate",
            "interpretation": "Context-level source pools are frozen and disjoint. Exact question-level evidence payload fingerprints cannot be checked until deterministic question templates and gold payloads are defined.",
        },
        "privacy": {
            "contains_selected_period_list": False,
            "contains_context_ids": False,
            "contains_scope_entity_values": False,
            "contains_invoice_or_customer_values": False,
            "contains_row_fingerprint_values": False,
            "contains_only_aggregate_counts_and_whole_manifest_commitment": True,
        },
        "current_result_boundary": {
            "historical_exploratory_max_test_auprc": 0.835073,
            "historical_exploratory_max_test_f1": 0.779412,
            "historical_aligned_span_count": 205,
            "historical_test_span_count": 103,
            "new_confirmation_metric_reported": False,
            "detector_superiority_claim_authorized": False,
        },
        "execution_boundary": {
            "context_manifest_created": True,
            "split_assignment_created": True,
            "question_created": False,
            "gold_answer_created": False,
            "prompt_created": False,
            "model_run_performed": False,
            "annotation_created": False,
            "detector_or_verifier_scoring_performed": False,
            "new_metrics_reported": False,
            "execution_ready": False,
            "no_new_results": True,
        },
        "next_gate": {
            "gate": "question_templates_and_gold_calculations_validated",
            "authorized_scope": "Define deterministic question templates, scope-entity selection rules, gold calculations, and question-level evidence payload fingerprints without running the model.",
            "still_forbidden": [
                "prompt generation",
                "Qwen execution",
                "annotation",
                "detector or verifier scoring",
                "new empirical metrics",
            ],
        },
        "claim_limits": [
            "This is a same-retailer, same-lineage temporal internal replication design, not an external replication.",
            "The manifest commitment proves a frozen inventory; it is not an experiment result.",
            "No detector family is authorized to claim superiority in Confirmation Set v1.",
            "Final question-level evidence payload separation remains a next-gate requirement.",
        ],
        "num_failures": 0,
        "failures": [],
    }
    PUBLIC_REPORT_PATH.write_text(
        json.dumps(public_report, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": public_report["status"],
                "public_report_path": repo_path(PUBLIC_REPORT_PATH),
                "private_manifest_path": repo_path(PRIVATE_MANIFEST_PATH),
                "private_manifest_canonical_sha256": private_commitment,
                "selected_context_count": len(contexts),
                "reserve_period_count": len(reserves),
                "split_counts": public_report["frozen_inventory"]["split_counts"],
                "num_failures": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
