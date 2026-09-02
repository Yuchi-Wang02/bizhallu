from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from public_paths import contains_local_path, repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "confirmation_question_design_v1.json"
PROTOCOL_PATH = PROJECT_ROOT / "configs" / "confirmation_set_v1_protocol.json"
CONTEXT_REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_manifest_report.json"
REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_question_design_report.json"
VALIDATION_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_question_design_validation.json"
PRIVATE_CONTEXT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "confirmation_online_retail_ii"
    / "context_manifest_v1_private.json"
)
PRIVATE_QUESTIONS_PATH = PRIVATE_CONTEXT_PATH.parent / "questions_gold_v1_private.json"
HISTORICAL_QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"

EXPECTED_CONTEXT_COMMITMENT = "002b484b3b59c52db0a2213b8d896750cdb2bb9157998d48bf015eff27f19e5a"
EXPECTED_SPLIT_COUNTS = {
    "protocol_pilot": 12,
    "development": 30,
    "confirmation": 54,
}
EXPECTED_FAMILY_COUNTS = {
    "net_revenue_reconciliation_by_period": 32,
    "product_return_rate_comparison": 32,
    "country_product_exposure": 32,
}
EXPECTED_TEMPLATE_COUNTS = {
    "nrr_weekly_reconciliation_v1": 16,
    "nrr_daily_cancellation_hotspot_v1": 16,
    "prr_pair_comparison_1_v1": 16,
    "prr_pair_comparison_2_v1": 16,
    "cpe_candidate_product_exposure_1_v1": 16,
    "cpe_candidate_product_exposure_2_v1": 16,
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def canonical_json_sha256(value: Any, domain: str) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def normalize_text(value: Any) -> str:
    return " ".join(str(value).strip().split())


def evidence_table_projection(
    evidence: dict[str, Any],
    field_aliases: dict[str, str],
) -> dict[str, Any]:
    normalized_rows: list[dict[str, Any]] = []
    for source_row in evidence.get("rows", []):
        normalized_row: dict[str, Any] = {}
        for source_key, value in source_row.items():
            key = field_aliases.get(source_key, source_key)
            normalized_value = normalize_evidence_value(value)
            if key in normalized_row and normalized_row[key] != normalized_value:
                raise ValueError(f"Conflicting evidence field alias for {source_key} -> {key}")
            normalized_row[key] = normalized_value
        normalized_rows.append(dict(sorted(normalized_row.items())))
    normalized_rows.sort(
        key=lambda row: json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    )
    return {"rows": normalized_rows}


def normalize_evidence_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        numeric = Decimal(str(value))
        if not numeric.is_finite():
            raise ValueError(f"Non-finite evidence value: {value}")
        normalized = format(numeric.normalize(), "f")
        return "0" if normalized in {"-0", "-0.0"} else normalized
    if isinstance(value, str):
        return normalize_text(value)
    return value


def evidence_content_sha256(evidence: dict[str, Any], config: dict[str, Any]) -> str:
    return canonical_json_sha256(
        evidence_table_projection(
            evidence,
            config["fingerprint_policy"]["content_field_aliases"],
        ),
        config["assignment"]["evidence_content_comparison_domain"],
    )


def add_failure(failures: list[dict[str, Any]], name: str, detail: Any = None) -> None:
    row: dict[str, Any] = {"name": name}
    if detail is not None:
        row["detail"] = detail
    failures.append(row)


def check_equal(
    failures: list[dict[str, Any]],
    name: str,
    actual: Any,
    expected: Any,
) -> None:
    if actual != expected:
        add_failure(failures, name, {"expected": expected, "actual": actual})


def close(actual: Any, expected: Any, tolerance: float = 0.011) -> bool:
    try:
        return math.isclose(float(actual), float(expected), rel_tol=0, abs_tol=tolerance)
    except (TypeError, ValueError):
        return False


def validate_gold_record(record: dict[str, Any], failures: list[dict[str, Any]]) -> None:
    question_id = record.get("question_id")
    template_id = record.get("template_id")
    evidence = record.get("evidence", {})
    rows = evidence.get("rows", [])
    gold = record.get("gold_answer", {})
    if not rows:
        add_failure(failures, "private_question_empty_evidence", question_id)
        return

    if template_id == "nrr_weekly_reconciliation_v1":
        if len(rows) != 1:
            add_failure(failures, "weekly_reconciliation_evidence_row_count", question_id)
            return
        gross = rows[0].get("gross_positive_revenue_gbp")
        cancellation = rows[0].get("cancellation_return_revenue_gbp")
        if not close(float(gross) + float(cancellation), gold.get("net_revenue_gbp")):
            add_failure(failures, "weekly_reconciliation_gold_mismatch", question_id)
        if not close(abs(float(cancellation)), gold.get("cancellation_return_reduction_gbp")):
            add_failure(failures, "weekly_reduction_gold_mismatch", question_id)
    elif template_id == "nrr_daily_cancellation_hotspot_v1":
        eligible = [
            row
            for row in rows
            if float(row.get("gross_positive_revenue_gbp", 0)) > 0
            and float(row.get("cancellation_return_revenue_gbp", 0)) < 0
        ]
        if not eligible:
            add_failure(failures, "daily_hotspot_no_eligible_rows", question_id)
            return
        expected = sorted(
            eligible,
            key=lambda row: (
                -abs(float(row["cancellation_return_revenue_gbp"])),
                row["business_date"],
            ),
        )[0]
        expected_reduction = abs(float(expected["cancellation_return_revenue_gbp"]))
        expected_pct = round(expected_reduction / float(expected["gross_positive_revenue_gbp"]) * 100, 2)
        if gold.get("business_date") != expected["business_date"]:
            add_failure(failures, "daily_hotspot_date_mismatch", question_id)
        if not close(gold.get("cancellation_return_reduction_gbp"), expected_reduction):
            add_failure(failures, "daily_hotspot_reduction_mismatch", question_id)
        if not close(gold.get("reduction_percentage_of_gross"), expected_pct):
            add_failure(failures, "daily_hotspot_percentage_mismatch", question_id)
    elif template_id in {"prr_pair_comparison_1_v1", "prr_pair_comparison_2_v1"}:
        if len(rows) != 2:
            add_failure(failures, "product_pair_evidence_row_count", question_id)
            return
        ratios = {
            row["stock_code"]: float(row["returned_units"]) / float(row["positive_units"]) * 100
            for row in rows
        }
        expected_higher = max(ratios, key=lambda code: ratios[code])
        expected_difference = round(abs(ratios[rows[0]["stock_code"]] - ratios[rows[1]["stock_code"]]), 2)
        if gold.get("higher_ratio_stock_code") != expected_higher:
            add_failure(failures, "product_pair_higher_ratio_mismatch", question_id)
        if not close(gold.get("percentage_point_difference"), expected_difference):
            add_failure(failures, "product_pair_difference_mismatch", question_id)
        for side, row in zip(["product_a", "product_b"], rows):
            if gold.get(side, {}).get("stock_code") != row["stock_code"]:
                add_failure(failures, "product_pair_side_binding_mismatch", {"question_id": question_id, "side": side})
            if not close(gold.get(side, {}).get("ratio_percentage"), round(ratios[row["stock_code"]], 2)):
                add_failure(failures, "product_pair_ratio_mismatch", {"question_id": question_id, "side": side})
    elif template_id in {
        "cpe_candidate_product_exposure_1_v1",
        "cpe_candidate_product_exposure_2_v1",
    }:
        if len(rows) != 5:
            add_failure(failures, "country_exposure_evidence_row_count", question_id)
            return
        expected = sorted(
            rows,
            key=lambda row: (-float(row["product_merchandise_net_revenue_gbp"]), row["stock_code"]),
        )[0]
        total_values = {float(row["country_merchandise_net_revenue_gbp"]) for row in rows}
        countries = {row["country"] for row in rows}
        if len(total_values) != 1 or len(countries) != 1:
            add_failure(failures, "country_exposure_evidence_scope_mismatch", question_id)
            return
        total = next(iter(total_values))
        expected_share = round(float(expected["product_merchandise_net_revenue_gbp"]) / total * 100, 2)
        for key in ["stock_code", "product_name", "country"]:
            if gold.get(key) != expected.get(key):
                add_failure(failures, "country_exposure_gold_binding_mismatch", {"question_id": question_id, "field": key})
        if not close(
            gold.get("product_merchandise_net_revenue_gbp"),
            expected["product_merchandise_net_revenue_gbp"],
        ):
            add_failure(failures, "country_exposure_revenue_mismatch", question_id)
        if not close(gold.get("share_of_country_merchandise_net_revenue_percentage"), expected_share):
            add_failure(failures, "country_exposure_share_mismatch", question_id)
    else:
        add_failure(failures, "unexpected_private_template_id", {"question_id": question_id, "template_id": template_id})


def validate_private_artifacts(
    *,
    config: dict[str, Any],
    report: dict[str, Any],
    public_text: str,
    failures: list[dict[str, Any]],
) -> dict[str, Any]:
    private_context = load_json(PRIVATE_CONTEXT_PATH)
    private_questions = load_json(PRIVATE_QUESTIONS_PATH)
    observed_commitment = canonical_json_sha256(
        private_questions,
        config["assignment"]["private_question_manifest_domain"],
    )
    check_equal(
        failures,
        "private_question_manifest_commitment",
        observed_commitment,
        report.get("private_question_manifest_commitment", {}).get("canonical_sha256"),
    )
    check_equal(
        failures,
        "private_question_manifest_status",
        private_questions.get("status"),
        "confirmation_question_design_v1_private_frozen",
    )
    check_equal(
        failures,
        "private_question_source_context_commitment",
        private_questions.get("source", {}).get("private_context_manifest_commitment_sha256"),
        EXPECTED_CONTEXT_COMMITMENT,
    )
    questions = private_questions.get("questions", [])
    check_equal(failures, "private_question_count", len(questions), 96)
    split_counts = Counter(row.get("split") for row in questions)
    family_counts = Counter(row.get("question_family") for row in questions)
    template_counts = Counter(row.get("template_id") for row in questions)
    check_equal(failures, "private_split_counts", dict(split_counts), EXPECTED_SPLIT_COUNTS)
    check_equal(failures, "private_family_counts", dict(family_counts), EXPECTED_FAMILY_COUNTS)
    check_equal(failures, "private_template_counts", dict(template_counts), EXPECTED_TEMPLATE_COUNTS)

    question_ids = [row.get("question_id") for row in questions]
    if len(set(question_ids)) != 96 or not all(
        isinstance(value, str) and re.fullmatch(r"cv1q_[0-9a-f]{20}", value)
        for value in question_ids
    ):
        add_failure(failures, "private_question_id_integrity")
    context_counts = Counter(row.get("context_id") for row in questions)
    if len(context_counts) != 48 or set(context_counts.values()) != {2}:
        add_failure(failures, "private_questions_per_context", dict(context_counts))

    fingerprint_splits: dict[str, set[str]] = defaultdict(set)
    fingerprint_contexts: dict[str, set[str]] = defaultdict(set)
    content_fingerprint_splits: dict[str, set[str]] = defaultdict(set)
    content_fingerprint_contexts: dict[str, set[str]] = defaultdict(set)
    product_codes_by_context: dict[str, list[str]] = defaultdict(list)
    countries_by_context: dict[str, list[str]] = defaultdict(list)
    for row in questions:
        evidence = row.get("evidence", {})
        observed_fingerprint = canonical_json_sha256(
            evidence,
            config["assignment"]["question_evidence_payload_domain"],
        )
        expected_fingerprint = row.get("evidence_payload_sha256")
        if observed_fingerprint != expected_fingerprint:
            add_failure(failures, "private_evidence_payload_fingerprint_mismatch", row.get("question_id"))
        fingerprint_splits[observed_fingerprint].add(row.get("split"))
        fingerprint_contexts[observed_fingerprint].add(row.get("context_id"))
        try:
            observed_content_fingerprint = evidence_content_sha256(evidence, config)
        except (KeyError, TypeError, ValueError) as exc:
            add_failure(
                failures,
                "private_evidence_content_projection_error",
                {"question_id": row.get("question_id"), "detail": str(exc)},
            )
            observed_content_fingerprint = ""
        if observed_content_fingerprint != row.get("evidence_content_sha256"):
            add_failure(
                failures,
                "private_evidence_content_fingerprint_mismatch",
                row.get("question_id"),
            )
        content_fingerprint_splits[observed_content_fingerprint].add(row.get("split"))
        content_fingerprint_contexts[observed_content_fingerprint].add(row.get("context_id"))
        if "prompt" in row or "generated_text" in row or "model_output" in row:
            add_failure(failures, "forbidden_execution_field_in_private_question", row.get("question_id"))
        if not row.get("question") or not row.get("gold_answer") or not row.get("gold_facts"):
            add_failure(failures, "private_question_or_gold_missing", row.get("question_id"))
        if row.get("template_id", "").startswith("nrr_") and "line revenue" not in row.get("question", ""):
            add_failure(
                failures,
                "private_reconciliation_sign_wording_missing",
                row.get("question_id"),
            )
        if row.get("template_id", "").startswith("prr_"):
            product_codes_by_context[row["context_id"]].extend(
                evidence_row["stock_code"] for evidence_row in evidence.get("rows", [])
            )
        if row.get("template_id", "").startswith("cpe_"):
            countries_by_context[row["context_id"]].append(row.get("gold_answer", {}).get("country"))
        validate_gold_record(row, failures)

    if len(fingerprint_splits) != 96:
        add_failure(failures, "private_evidence_fingerprint_uniqueness", len(fingerprint_splits))
    if any(len(values) > 1 for values in fingerprint_splits.values()):
        add_failure(failures, "private_evidence_fingerprint_cross_split")
    if any(len(values) > 1 for values in fingerprint_contexts.values()):
        add_failure(failures, "private_evidence_fingerprint_cross_context")
    if len(content_fingerprint_splits) != 96:
        add_failure(
            failures,
            "private_evidence_content_fingerprint_uniqueness",
            len(content_fingerprint_splits),
        )
    if any(len(values) > 1 for values in content_fingerprint_splits.values()):
        add_failure(failures, "private_evidence_content_cross_split")
    if any(len(values) > 1 for values in content_fingerprint_contexts.values()):
        add_failure(failures, "private_evidence_content_cross_context")
    historical_content_fingerprints = {
        evidence_content_sha256(record.get("evidence", {}), config)
        for record in load_jsonl(HISTORICAL_QUESTIONS_PATH)
    }
    historical_overlap = set(content_fingerprint_splits).intersection(
        historical_content_fingerprints
    )
    if historical_overlap:
        add_failure(
            failures,
            "private_historical_evidence_content_overlap",
            len(historical_overlap),
        )
    if any(len(values) != 4 or len(set(values)) != 4 for values in product_codes_by_context.values()):
        add_failure(failures, "private_product_pair_reuse")
    if any(len(values) != 2 or len(set(values)) != 2 for values in countries_by_context.values()):
        add_failure(failures, "private_country_question_reuse")

    critical_checks = private_questions.get("critical_checks", {})
    if private_questions.get("failed_critical_checks") != [] or not critical_checks or not all(critical_checks.values()):
        add_failure(failures, "private_critical_checks")
    check_equal(
        failures,
        "private_execution_boundary",
        private_questions.get("execution_boundary"),
        {
            "questions_created": True,
            "gold_answers_created": True,
            "evidence_payloads_created": True,
            "prompts_created": False,
            "model_outputs_created": False,
            "labels_created": False,
            "detector_or_verifier_scores_created": False,
            "new_empirical_metrics_created": False,
        },
    )

    private_values = {
        *question_ids,
        *(row.get("context_id") for row in questions),
        *(row.get("period_start") for row in questions),
        *(row.get("period_end_exclusive") for row in questions),
    }
    private_values.update(
        str(value)
        for context in private_context.get("contexts", [])
        for value in context.get("scope_entities", [])
        if str(value) not in {"global"}
    )
    leaked = sorted(
        value
        for value in private_values
        if isinstance(value, str) and len(value) >= 6 and value in public_text
    )
    if leaked:
        add_failure(failures, "private_question_value_leak", {"count": len(leaked), "examples": leaked[:3]})
    return {
        "private_artifacts_available": True,
        "private_question_count_checked": len(questions),
        "private_gold_record_count_checked": len(questions),
        "private_evidence_content_fingerprint_count_checked": len(content_fingerprint_splits),
        "historical_unique_evidence_content_fingerprint_count_checked": len(
            historical_content_fingerprints
        ),
        "historical_evidence_content_overlap_count_checked": len(historical_overlap),
        "private_commitment_checked": observed_commitment,
    }


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path in [CONFIG_PATH, PROTOCOL_PATH, CONTEXT_REPORT_PATH, REPORT_PATH]:
        if not path.exists():
            add_failure(failures, "required_public_file_missing", repo_path(path))

    config = load_json(CONFIG_PATH) if CONFIG_PATH.exists() else {}
    protocol = load_json(PROTOCOL_PATH) if PROTOCOL_PATH.exists() else {}
    context_report = load_json(CONTEXT_REPORT_PATH) if CONTEXT_REPORT_PATH.exists() else {}
    report = load_json(REPORT_PATH) if REPORT_PATH.exists() else {}
    public_text = json.dumps([config, protocol, context_report, report], ensure_ascii=True)
    if contains_local_path(public_text):
        add_failure(failures, "local_path_in_public_question_design_artifact")

    check_equal(failures, "config_status", config.get("status"), "question_and_gold_rules_frozen")
    check_equal(failures, "config_total_question_count", config.get("question_inventory", {}).get("total_question_count"), 96)
    check_equal(
        failures,
        "config_split_counts",
        config.get("question_inventory", {}).get("question_counts_by_split"),
        EXPECTED_SPLIT_COUNTS,
    )
    expected_assignment = {
        "seed": 20260902,
        "question_id_domain": "bizhallu:confirmation-question-id:v1",
        "product_pair_order_domain": "bizhallu:confirmation-product-pair-order:v1",
        "country_order_domain": "bizhallu:confirmation-country-order:v1",
        "country_product_order_domain": "bizhallu:confirmation-country-product-order:v1",
        "question_evidence_payload_domain": "bizhallu:question-evidence-payload:v1",
        "evidence_content_comparison_domain": "bizhallu:evidence-table-content:v1",
        "private_question_manifest_domain": "bizhallu:confirmation-private-question-manifest:v1",
    }
    for key, expected in expected_assignment.items():
        check_equal(
            failures,
            f"config_assignment_{key}",
            config.get("assignment", {}).get(key),
            expected,
        )
    expected_aliases = {
        "description": "product_name",
        "gross_positive_revenue": "gross_positive_revenue_gbp",
        "cancellation_revenue": "cancellation_return_revenue_gbp",
        "net_revenue": "net_revenue_gbp",
        "product_merchandise_net_revenue_gbp": "net_revenue_gbp",
    }
    check_equal(
        failures,
        "config_content_field_aliases",
        config.get("fingerprint_policy", {}).get("content_field_aliases"),
        expected_aliases,
    )
    configured_templates = sorted(
        {
            template.get("template_id")
            for family in config.get("family_designs", [])
            for template in family.get("templates", [])
        }
    )
    check_equal(
        failures,
        "config_template_ids",
        configured_templates,
        sorted(EXPECTED_TEMPLATE_COUNTS),
    )
    check_equal(
        failures,
        "config_money_rounding",
        config.get("shared_calculation_rules", {}).get("money_rounding_decimals"),
        2,
    )
    check_equal(
        failures,
        "config_percentage_rounding",
        config.get("shared_calculation_rules", {}).get("percentage_rounding_decimals"),
        2,
    )
    check_equal(
        failures,
        "config_execution_boundary",
        config.get("execution_boundary"),
        {
            "question_and_gold_generation_allowed": True,
            "prompt_generation_allowed": False,
            "model_run_allowed": False,
            "annotation_allowed": False,
            "detector_or_verifier_scoring_allowed": False,
            "new_empirical_metrics_allowed": False,
        },
    )
    check_equal(
        failures,
        "config_context_commitment_source",
        context_report.get("private_manifest_commitment", {}).get("canonical_sha256"),
        EXPECTED_CONTEXT_COMMITMENT,
    )
    check_equal(failures, "report_status", report.get("status"), "confirmation_question_design_v1_frozen")
    expected_config_hash = canonical_json_sha256(
        config,
        "bizhallu:confirmation-question-design-config:v1",
    )
    check_equal(failures, "report_config_hash", report.get("config", {}).get("canonical_sha256"), expected_config_hash)
    commitment = report.get("private_question_manifest_commitment", {})
    if not isinstance(commitment.get("canonical_sha256"), str) or not re.fullmatch(
        r"[0-9a-f]{64}", commitment.get("canonical_sha256", "")
    ):
        add_failure(failures, "public_private_question_commitment_format")
    check_equal(failures, "public_private_question_git_ignored", commitment.get("git_ignored"), True)
    check_equal(failures, "public_private_question_published", commitment.get("published_contents"), False)

    inventory = report.get("frozen_inventory", {})
    check_equal(failures, "report_question_count", inventory.get("question_count"), 96)
    check_equal(failures, "report_context_count", inventory.get("context_count"), 48)
    check_equal(failures, "report_questions_per_context", inventory.get("questions_per_context"), 2)
    check_equal(failures, "report_split_counts", inventory.get("split_counts"), EXPECTED_SPLIT_COUNTS)
    check_equal(failures, "report_family_counts", inventory.get("family_counts"), EXPECTED_FAMILY_COUNTS)
    check_equal(failures, "report_template_counts", inventory.get("template_counts"), EXPECTED_TEMPLATE_COUNTS)

    evidence = report.get("evidence_payload_integrity", {})
    for key, expected in {
        "fingerprint_count": 96,
        "unique_fingerprint_count": 96,
        "cross_split_fingerprint_count": 0,
        "cross_context_fingerprint_count": 0,
        "content_comparison_domain": "bizhallu:evidence-table-content:v1",
        "content_fingerprint_count": 96,
        "unique_content_fingerprint_count": 96,
        "content_cross_split_fingerprint_count": 0,
        "content_cross_context_fingerprint_count": 0,
        "historical_full100_content_fingerprint_count": 66,
        "historical_full100_content_fingerprint_overlap_count": 0,
        "question_level_evidence_payload_fingerprint_check": "complete",
    }.items():
        check_equal(failures, f"report_evidence_{key}", evidence.get(key), expected)
    check_equal(
        failures,
        "report_historical_content_fingerprint_count",
        report.get("source_commitments", {}).get(
            "historical_full100_evidence_content_fingerprint_count"
        ),
        66,
    )
    gold_integrity = report.get("gold_calculation_integrity", {})
    check_equal(failures, "report_validated_question_count", gold_integrity.get("validated_question_count"), 96)
    check_equal(failures, "report_recomputed_context_hash_count", gold_integrity.get("recomputed_context_evidence_hash_count"), 48)
    if float(gold_integrity.get("maximum_weekly_reconciliation_error_gbp", 1)) > 0.01:
        add_failure(failures, "report_weekly_reconciliation_error", gold_integrity)
    check_equal(
        failures,
        "report_reconciliation_positive_cancel_flagged_row_count",
        gold_integrity.get("selected_reconciliation_positive_cancel_flagged_row_count"),
        1,
    )
    if int(gold_integrity.get("minimum_selected_product_count_per_context", 0)) != 4:
        add_failure(failures, "report_product_pair_selection_count", gold_integrity)
    if int(gold_integrity.get("minimum_country_positive_product_candidate_pool", 0)) < 5:
        add_failure(failures, "report_country_candidate_pool", gold_integrity)
    check_equal(
        failures,
        "report_selected_product_return_ratio_range",
        gold_integrity.get("selected_product_return_ratio_percentage_range"),
        [0.2, 156.25],
    )
    check_equal(
        failures,
        "report_selected_product_return_ratio_over_100_count",
        gold_integrity.get("selected_product_return_ratio_over_100_count"),
        1,
    )
    selection = report.get("selection_integrity", {})
    check_equal(
        failures,
        "report_evidence_order_selection_uses_gold",
        selection.get("evidence_order_selection_uses_gold_answer"),
        False,
    )
    check_equal(
        failures,
        "report_country_gold_position_counts",
        selection.get("country_gold_position_counts"),
        {"1": 9, "2": 5, "3": 3, "4": 6, "5": 9},
    )
    check_equal(
        failures,
        "report_country_accidentally_descending_count",
        selection.get("country_candidate_tables_accidentally_fully_descending"),
        1,
    )

    check_equal(
        failures,
        "report_privacy",
        report.get("privacy"),
        {
            "contains_question_text": False,
            "contains_question_ids": False,
            "contains_selected_periods": False,
            "contains_context_ids": False,
            "contains_scope_entity_values": False,
            "contains_evidence_rows": False,
            "contains_only_rules_aggregate_counts_and_whole_manifest_commitment": True,
        },
    )
    check_equal(
        failures,
        "report_execution_boundary",
        report.get("execution_boundary"),
        {
            "question_created": True,
            "gold_answer_created": True,
            "evidence_payload_created": True,
            "prompt_created": False,
            "model_run_performed": False,
            "annotation_created": False,
            "detector_or_verifier_scoring_performed": False,
            "new_metrics_reported": False,
            "execution_ready": False,
            "no_new_results": True,
        },
    )
    check_equal(
        failures,
        "report_next_gate",
        report.get("next_gate", {}).get("gate"),
        "model_prompt_and_detector_configs_frozen",
    )
    for key, expected in {
        "historical_exploratory_max_test_auprc": 0.835073,
        "historical_exploratory_max_test_f1": 0.779412,
        "new_confirmation_metric_reported": False,
        "detector_superiority_claim_authorized": False,
    }.items():
        check_equal(failures, f"historical_boundary_{key}", report.get("current_result_boundary", {}).get(key), expected)
    if report.get("num_failures") != 0 or report.get("failures") != []:
        add_failure(failures, "public_question_report_self_validation")
    if not report.get("critical_checks") or not all(report.get("critical_checks", {}).values()):
        add_failure(failures, "public_question_report_critical_checks")

    gates = {item.get("gate"): item.get("status") for item in protocol.get("execution_gates", [])}
    check_equal(
        failures,
        "protocol_question_gate_status",
        gates.get("question_templates_and_gold_calculations_validated"),
        "complete",
    )
    check_equal(
        failures,
        "protocol_question_family_status",
        protocol.get("question_design", {}).get("family_status"),
        "question_templates_gold_and_payload_fingerprints_frozen",
    )

    private_details = {
        "private_artifacts_available": False,
        "private_question_count_checked": 0,
        "private_gold_record_count_checked": 0,
        "private_evidence_content_fingerprint_count_checked": 0,
        "historical_unique_evidence_content_fingerprint_count_checked": 0,
        "historical_evidence_content_overlap_count_checked": None,
        "private_commitment_checked": None,
    }
    if PRIVATE_CONTEXT_PATH.exists() and PRIVATE_QUESTIONS_PATH.exists() and config and report:
        private_details = validate_private_artifacts(
            config=config,
            report=report,
            public_text=public_text,
            failures=failures,
        )
    elif PRIVATE_CONTEXT_PATH.exists() != PRIVATE_QUESTIONS_PATH.exists():
        add_failure(failures, "partial_private_gate3_artifact_availability")

    validation = {
        "status": (
            "confirmation_question_design_validation_passed"
            if not failures
            else "confirmation_question_design_validation_failed"
        ),
        "config_path": repo_path(CONFIG_PATH),
        "report_path": repo_path(REPORT_PATH),
        "question_count": report.get("frozen_inventory", {}).get("question_count"),
        "question_payload_fingerprint_check": report.get("evidence_payload_integrity", {}).get(
            "question_level_evidence_payload_fingerprint_check"
        ),
        **private_details,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
