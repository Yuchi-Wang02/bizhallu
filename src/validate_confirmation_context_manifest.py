from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import contains_local_path, repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "confirmation_context_manifest_v1.json"
REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_manifest_report.json"
HTML_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_manifest.html"
VALIDATION_PATH = (
    PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_manifest_validation.json"
)
PRIVATE_MANIFEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "confirmation_online_retail_ii"
    / "context_manifest_v1_private.json"
)

EXPECTED_FAMILIES = [
    "net_revenue_reconciliation_by_period",
    "product_return_rate_comparison",
    "country_product_exposure",
]
EXPECTED_SPLIT_COUNTS = {
    "protocol_pilot": 6,
    "development": 15,
    "confirmation": 27,
}
EXPECTED_PER_FAMILY = {
    "protocol_pilot": 2,
    "development": 5,
    "confirmation": 9,
}
EXPECTED_STRICT_TABLE_SHA256 = "ab875caaf527d5d528f4edad4fd372b15d4e1ae9c39f6cea20f8211178e256fc"
EXPECTED_HISTORICAL_RESULTS = {
    "historical_exploratory_max_test_auprc": 0.835073,
    "historical_exploratory_max_test_f1": 0.779412,
    "historical_aligned_span_count": 205,
    "historical_test_span_count": 103,
}
REQUIRED_HTML_FRAGMENTS = [
    "The 48-context inventory and 6/15/27 split are now frozen.",
    "A deterministic, outcome-blind assignment",
    "All 48 selected periods are unique",
    "Each business family receives the same 2 / 5 / 9 split.",
    "Unassigned reserve",
    "The public hash commits to a private, Git-ignored manifest.",
    "Context pools are fixed now; question payloads are checked next.",
    "No new empirical result was created.",
    "No questions, gold answers, prompts, Qwen outputs",
    "0.835 AUPRC and 0.779 F1 remain exploratory maxima",
    "does not authorize a detector-superiority claim",
    "Define and validate questions and gold calculations, without running Qwen.",
    "overflow-x:auto;",
    "overflow-wrap:anywhere;",
    "@media (max-width:860px)",
]
FORBIDDEN_HTML_FRAGMENTS = [
    "production-ready detector",
    "large independent human-labeled benchmark",
    "whole-answer correctness",
    "external validation complete",
    "new confirmation AUPRC",
    "new confirmation F1",
    "clamp(",
]


class HTMLCheckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tag_counts: Counter[str] = Counter()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tag_counts[tag] += 1
        for key, value in attrs:
            if tag == "a" and key == "href" and value:
                self.hrefs.append(value)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_json_sha256(value: Any, domain: str) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


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


def validate_private_manifest(
    manifest: dict[str, Any],
    report: dict[str, Any],
    public_text: str,
    failures: list[dict[str, Any]],
) -> None:
    commitment = report.get("private_manifest_commitment", {}).get("canonical_sha256")
    observed_commitment = canonical_json_sha256(
        manifest,
        "bizhallu:confirmation-private-context-manifest:v1",
    )
    check_equal(failures, "private_manifest_commitment", observed_commitment, commitment)
    check_equal(
        failures,
        "private_manifest_status",
        manifest.get("status"),
        "confirmation_context_manifest_v1_private_frozen",
    )

    contexts = manifest.get("contexts", [])
    reserves = manifest.get("source_reserve_periods", [])
    check_equal(failures, "private_context_count", len(contexts), 48)
    check_equal(failures, "private_reserve_count", len(reserves), 2)

    selected_periods = [item.get("period_start") for item in contexts]
    reserve_periods = [item.get("period_start") for item in reserves]
    if len(set(selected_periods)) != 48:
        add_failure(failures, "private_selected_period_uniqueness")
    if len(set(reserve_periods)) != 2 or set(selected_periods).intersection(reserve_periods):
        add_failure(failures, "private_reserve_period_separation")
    if len(set(selected_periods + reserve_periods)) != 50:
        add_failure(failures, "private_candidate_inventory_coverage")

    context_ids = [item.get("context_id") for item in contexts]
    evidence_hashes = [item.get("canonical_evidence_rows_sha256") for item in contexts]
    if len(set(context_ids)) != 48:
        add_failure(failures, "private_context_id_uniqueness")
    if len(set(evidence_hashes)) != 48 or not all(
        isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
        for value in evidence_hashes
    ):
        add_failure(failures, "private_context_evidence_hash_integrity")
    if not all(
        isinstance(item.get("scope_entities"), list)
        and item.get("scope_entity_count") == len(item.get("scope_entities", []))
        and item.get("scope_entity_count", 0) > 0
        and item.get("canonical_evidence_row_count", 0) > 0
        for item in contexts
    ):
        add_failure(failures, "private_context_scope_or_evidence_empty")

    family_counts = Counter(item.get("question_family") for item in contexts)
    split_counts = Counter(item.get("split") for item in contexts)
    check_equal(failures, "private_family_counts", dict(family_counts), {family: 16 for family in EXPECTED_FAMILIES})
    check_equal(failures, "private_split_counts", dict(split_counts), EXPECTED_SPLIT_COUNTS)
    for family in EXPECTED_FAMILIES:
        observed = Counter(
            item.get("split") for item in contexts if item.get("question_family") == family
        )
        check_equal(
            failures,
            f"private_family_split_counts_{family}",
            dict(observed),
            EXPECTED_PER_FAMILY,
        )

    if manifest.get("failed_critical_checks") != [] or not all(
        manifest.get("critical_checks", {}).values()
    ):
        add_failure(failures, "private_manifest_critical_checks")
    check_equal(
        failures,
        "private_next_gate",
        manifest.get("next_gate"),
        {
            "gate": "question_templates_and_gold_calculations_validated",
            "question_ids_created": False,
            "question_evidence_payload_fingerprint_check_pending": True,
        },
    )
    check_equal(
        failures,
        "private_execution_boundary",
        manifest.get("execution_boundary"),
        {
            "questions_created": False,
            "prompts_created": False,
            "model_outputs_created": False,
            "labels_created": False,
            "detector_or_verifier_scores_created": False,
            "new_empirical_metrics_created": False,
        },
    )

    selected_period_leaks = sum(
        isinstance(period, str) and period in public_text for period in selected_periods
    )
    context_id_leaks = sum(
        isinstance(context_id, str) and context_id in public_text for context_id in context_ids
    )
    if selected_period_leaks:
        add_failure(failures, "selected_period_leak_in_public_artifacts", selected_period_leaks)
    if context_id_leaks:
        add_failure(failures, "context_id_leak_in_public_artifacts", context_id_leaks)


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path in [CONFIG_PATH, REPORT_PATH, HTML_PATH]:
        if not path.exists():
            add_failure(failures, "required_file_missing", repo_path(path))

    config = load_json(CONFIG_PATH) if CONFIG_PATH.exists() else {}
    report = load_json(REPORT_PATH) if REPORT_PATH.exists() else {}
    html_text = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""
    public_text = json.dumps(config, ensure_ascii=True) + json.dumps(report, ensure_ascii=True) + html_text

    if contains_local_path(public_text):
        add_failure(failures, "local_path_in_public_manifest_artifact")

    check_equal(failures, "config_status", config.get("status"), "assignment_rules_frozen")
    check_equal(failures, "config_frozen_on", config.get("frozen_on"), "2026-09-02")
    check_equal(
        failures,
        "config_allowed_families",
        config.get("candidate_policy", {}).get("allowed_question_families"),
        EXPECTED_FAMILIES,
    )
    check_equal(failures, "config_blocked_family", config.get("candidate_policy", {}).get("blocked_question_families"), ["customer_revenue_concentration"])
    check_equal(failures, "config_seed", config.get("assignment", {}).get("seed"), 20260901)
    check_equal(
        failures,
        "config_algorithm",
        config.get("assignment", {}).get("family_matching_algorithm"),
        "deterministic_hash_ordered_bipartite_augmenting_path_v1",
    )
    check_equal(failures, "config_target", config.get("target", {}).get("all_families"), {**EXPECTED_SPLIT_COUNTS, "total": 48})
    check_equal(failures, "config_per_family", config.get("target", {}).get("per_family"), {**EXPECTED_PER_FAMILY, "total": 16})
    check_equal(failures, "config_candidate_count", config.get("target", {}).get("candidate_period_count"), 50)
    check_equal(failures, "config_reserve_count", config.get("target", {}).get("reserve_period_count"), 2)
    check_equal(failures, "config_future_question_target", config.get("target", {}).get("selected_question_target"), 96)
    check_equal(
        failures,
        "config_strict_table_hash",
        config.get("inputs", {}).get("strict_window_table_sha256"),
        EXPECTED_STRICT_TABLE_SHA256,
    )

    check_equal(
        failures,
        "report_status",
        report.get("status"),
        "confirmation_context_manifest_v1_frozen",
    )
    expected_config_hash = canonical_json_sha256(
        config,
        "bizhallu:confirmation-context-manifest-config:v1",
    )
    check_equal(
        failures,
        "report_config_hash",
        report.get("config", {}).get("canonical_sha256"),
        expected_config_hash,
    )
    commitment = report.get("private_manifest_commitment", {})
    commitment_hash = commitment.get("canonical_sha256")
    if not isinstance(commitment_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", commitment_hash):
        add_failure(failures, "public_manifest_commitment_format")
    check_equal(failures, "private_manifest_git_ignored", commitment.get("git_ignored"), True)
    check_equal(failures, "private_manifest_published", commitment.get("published_contents"), False)

    inventory = report.get("frozen_inventory", {})
    check_equal(failures, "public_candidate_count", inventory.get("candidate_period_count"), 50)
    check_equal(failures, "public_selected_count", inventory.get("selected_context_count"), 48)
    check_equal(failures, "public_reserve_count", inventory.get("reserve_period_count"), 2)
    check_equal(failures, "public_split_counts", inventory.get("split_counts"), EXPECTED_SPLIT_COUNTS)
    check_equal(failures, "public_family_counts", inventory.get("family_counts"), {family: 16 for family in sorted(EXPECTED_FAMILIES)})
    for family in EXPECTED_FAMILIES:
        check_equal(
            failures,
            f"public_family_split_counts_{family}",
            inventory.get("family_split_counts", {}).get(family),
            EXPECTED_PER_FAMILY,
        )

    check_equal(
        failures,
        "public_input_evidence",
        {
            "strict_hash": report.get("input_evidence", {}).get("strict_window_table_sha256"),
            "strict_rows": report.get("input_evidence", {}).get("strict_window_row_count"),
            "candidate_periods": report.get("input_evidence", {}).get("observed_complete_period_count"),
            "matching": report.get("input_evidence", {}).get("maximum_feasible_matching_count"),
            "hall_slack": report.get("input_evidence", {}).get("minimum_hall_capacity_slack"),
            "canonical_overlap": report.get("input_evidence", {}).get("historical_canonical_record_overlap_row_count"),
            "date_blind_overlap": report.get("input_evidence", {}).get("historical_date_blind_record_overlap_row_count"),
        },
        {
            "strict_hash": EXPECTED_STRICT_TABLE_SHA256,
            "strict_rows": 502938,
            "candidate_periods": 50,
            "matching": 48,
            "hall_slack": 2,
            "canonical_overlap": 0,
            "date_blind_overlap": 0,
        },
    )
    check_equal(
        failures,
        "assignment_integrity",
        report.get("assignment_integrity"),
        {
            "seed": 20260901,
            "algorithm": "deterministic_hash_ordered_bipartite_augmenting_path_v1",
            "outcome_blind": True,
            "all_selected_periods_unique": True,
            "period_disjoint_across_all_contexts_and_splits": True,
            "one_family_per_selected_period": True,
            "reserve_substitution_after_outcome_access_allowed": False,
        },
    )
    evidence = report.get("context_evidence_integrity", {})
    check_equal(failures, "context_pool_hash_count", evidence.get("canonical_context_pool_hash_count"), 48)
    check_equal(failures, "unique_context_pool_hash_count", evidence.get("unique_canonical_context_pool_hash_count"), 48)
    check_equal(failures, "context_pool_hashes_disjoint", evidence.get("context_pool_hashes_disjoint_across_selected_contexts"), True)
    check_equal(failures, "question_payload_check_pending", evidence.get("final_question_evidence_payload_fingerprint_check"), "pending_next_gate")
    for key, value in EXPECTED_HISTORICAL_RESULTS.items():
        check_equal(failures, f"historical_result_{key}", report.get("current_result_boundary", {}).get(key), value)
    check_equal(failures, "new_confirmation_metric_reported", report.get("current_result_boundary", {}).get("new_confirmation_metric_reported"), False)
    check_equal(failures, "detector_superiority_authorized", report.get("current_result_boundary", {}).get("detector_superiority_claim_authorized"), False)

    check_equal(
        failures,
        "public_privacy",
        report.get("privacy"),
        {
            "contains_selected_period_list": False,
            "contains_context_ids": False,
            "contains_scope_entity_values": False,
            "contains_invoice_or_customer_values": False,
            "contains_row_fingerprint_values": False,
            "contains_only_aggregate_counts_and_whole_manifest_commitment": True,
        },
    )
    check_equal(
        failures,
        "execution_boundary",
        report.get("execution_boundary"),
        {
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
    )
    check_equal(
        failures,
        "next_gate",
        report.get("next_gate", {}).get("gate"),
        "question_templates_and_gold_calculations_validated",
    )
    if report.get("num_failures") != 0 or report.get("failures") != []:
        add_failure(failures, "public_report_self_validation")

    if html_text:
        parser = HTMLCheckParser()
        parser.feed(html_text)
        if parser.tag_counts["html"] != 1 or parser.tag_counts["main"] != 1 or parser.tag_counts["h1"] != 1:
            add_failure(failures, "html_structure", dict(parser.tag_counts))
        if parser.tag_counts["section"] < 7 or parser.tag_counts["table"] != 1:
            add_failure(
                failures,
                "html_section_or_table_count",
                {"sections": parser.tag_counts["section"], "tables": parser.tag_counts["table"]},
            )
        for fragment in REQUIRED_HTML_FRAGMENTS:
            if fragment not in html_text:
                add_failure(failures, "required_html_fragment_missing", fragment)
        for fragment in FORBIDDEN_HTML_FRAGMENTS:
            if fragment in html_text:
                add_failure(failures, "forbidden_html_fragment", fragment)
        for href in parser.hrefs:
            if href.startswith("./") and not (HTML_PATH.parent / href[2:]).exists():
                add_failure(failures, "broken_internal_html_link", href)

    if PRIVATE_MANIFEST_PATH.exists() and report:
        private_manifest = load_json(PRIVATE_MANIFEST_PATH)
        validate_private_manifest(private_manifest, report, public_text, failures)

    validation = {
        "status": (
            "confirmation_context_manifest_validation_passed"
            if not failures
            else "confirmation_context_manifest_validation_failed"
        ),
        "config_path": repo_path(CONFIG_PATH),
        "report_path": repo_path(REPORT_PATH),
        "html_path": repo_path(HTML_PATH),
        "private_manifest_policy": "Git-ignored private manifest is verified when locally available; clean-clone CI validates the public commitment and frozen aggregate contract.",
        "private_manifest_commitment_sha256": commitment_hash,
        "selected_context_count": inventory.get("selected_context_count"),
        "reserve_period_count": inventory.get("reserve_period_count"),
        "split_counts": inventory.get("split_counts"),
        "context_manifest_created": report.get("execution_boundary", {}).get("context_manifest_created"),
        "split_assignment_created": report.get("execution_boundary", {}).get("split_assignment_created"),
        "question_created": False,
        "model_run_performed": False,
        "new_metrics_reported": False,
        "execution_ready": False,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(
        json.dumps(validation, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
