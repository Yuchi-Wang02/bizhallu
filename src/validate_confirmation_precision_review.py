from __future__ import annotations

import hashlib
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import contains_local_path, repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_CONFIG_PATH = PROJECT_ROOT / "configs" / "confirmation_precision_review_v1.json"
REVIEW_REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_precision_review_report.json"
AMENDMENT_PATH = PROJECT_ROOT / "configs" / "confirmation_precision_scope_amendment_v1.json"
CAPACITY_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility_report.json"
HTML_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_precision_review.html"
VALIDATION_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_precision_review_validation.json"

EXPECTED_REVIEW_CONFIG_SHA256 = "e49ea86fe12749f261a36a4f3acf9498c50b17a2eddcff50a27a7a276a5d99e1"
EXPECTED_REVIEW_REPORT_SHA256 = "9a69bfc1a54f1757da8527ccda19f1ac2e9370090fe5cbccba25c789506d2643"
TEXT_HASH_SUFFIXES = {".csv", ".html", ".json", ".md", ".txt", ".yml", ".yaml"}
EXPECTED_CANDIDATES = {
    15: (5, 16, 0.3125, 0.103099, 0.14955, 0.126422, False, False),
    21: (10, 16, 0.625, 0.094613, 0.136085, 0.106863, False, False),
    24: (9, 16, 0.5625, 0.087154, 0.126603, 0.102429, True, False),
    27: (10, 16, 0.625, 0.082558, 0.121219, 0.097796, True, False),
}
REQUIRED_HTML_FRAGMENTS = [
    "The 15-context comparison plan was too fragile",
    "0 of 4",
    "Revised confirmation contexts",
    "27",
    "48/48",
    "thresholds were not relaxed",
    "Design sensitivity, not detector performance.",
    "10 of 16",
    "0.121219",
    "Estimate transparently; do not declare a winner.",
    "do not make this publication-grade",
    "Only the context manifest and seeded split may come next.",
    "No context manifest, split assignment, question, prompt, model output, label, detector score, or new empirical metric exists.",
    "overflow-x:auto;",
    "overflow-wrap:anywhere;",
    "@media (max-width:860px)",
]
FORBIDDEN_HTML_FRAGMENTS = [
    "precision review passed",
    "proves detector superiority",
    "demonstrates statistical superiority",
    "production-ready",
    "human-labeled benchmark",
    "new confirmation AUPRC",
    "new confirmation F1",
    "context manifest created",
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
    if path.suffix.lower() in TEXT_HASH_SUFFIXES:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def add_failure(failures: list[dict[str, Any]], check: str, detail: Any) -> None:
    failures.append({"check": check, "detail": detail})


def check_equal(failures: list[dict[str, Any]], check: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        add_failure(failures, check, {"expected": expected, "actual": actual})


def main() -> None:
    failures: list[dict[str, Any]] = []
    required = [REVIEW_CONFIG_PATH, REVIEW_REPORT_PATH, AMENDMENT_PATH, CAPACITY_PATH, HTML_PATH]
    missing = [repo_path(path) for path in required if not path.exists()]
    if missing:
        add_failure(failures, "required_files_exist", missing)
    if failures:
        payload = {
            "status": "confirmation_precision_review_validation_failed",
            "num_failures": len(failures),
            "failures": failures,
        }
        VALIDATION_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(json.dumps(payload, indent=2))
        raise SystemExit(1)

    config = load_json(REVIEW_CONFIG_PATH)
    report = load_json(REVIEW_REPORT_PATH)
    amendment = load_json(AMENDMENT_PATH)
    capacity = load_json(CAPACITY_PATH)
    html_text = HTML_PATH.read_text(encoding="utf-8")

    check_equal(failures, "review_config_sha256", file_sha256(REVIEW_CONFIG_PATH), EXPECTED_REVIEW_CONFIG_SHA256)
    check_equal(failures, "review_report_sha256", file_sha256(REVIEW_REPORT_PATH), EXPECTED_REVIEW_REPORT_SHA256)
    check_equal(failures, "review_config_status", config.get("status"), "rules_frozen_simulation_pending")
    check_equal(failures, "review_report_status", report.get("status"), "outcome_blind_precision_review_blocked")
    check_equal(failures, "review_scenario_count", report.get("scenario_row_count"), 80)
    check_equal(failures, "review_simulation_only", report.get("simulation_only"), True)
    check_equal(failures, "review_confirmation_access", report.get("confirmation_data_accessed"), False)
    check_equal(failures, "review_new_metrics", report.get("new_empirical_metrics_created"), False)
    check_equal(failures, "review_decision", report.get("planning_decision", {}).get("status"), "no_candidate_passed")
    check_equal(failures, "review_manifest_authorization", report.get("planning_decision", {}).get("context_manifest_authorized"), False)

    summaries = {row["confirmation_context_count"]: row for row in report["candidate_summaries"]}
    check_equal(failures, "candidate_counts", sorted(summaries), sorted(EXPECTED_CANDIDATES))
    for context_count, expected in EXPECTED_CANDIDATES.items():
        row = summaries.get(context_count, {})
        actual = (
            row.get("central_preferred_scenario_count"),
            row.get("central_scenario_count"),
            row.get("central_preferred_scenario_share"),
            row.get("central_median_of_median_auprc_half_widths"),
            row.get("central_worst_median_auprc_half_width"),
            row.get("central_worst_median_paired_difference_half_width"),
            row.get("structural_pass"),
            row.get("candidate_pass"),
        )
        check_equal(failures, f"candidate_{context_count}_summary", actual, expected)

    check_equal(
        failures,
        "amendment_input_hashes",
        {
            "config": amendment.get("inputs", {}).get("precision_review_config_sha256"),
            "report": amendment.get("inputs", {}).get("precision_review_report_sha256"),
        },
        {"config": EXPECTED_REVIEW_CONFIG_SHA256, "report": EXPECTED_REVIEW_REPORT_SHA256},
    )
    check_equal(
        failures,
        "amendment_status",
        amendment.get("status"),
        "scope_downgrade_frozen_capacity_recheck_complete_manifest_pending",
    )
    check_equal(
        failures,
        "amendment_claim_decision",
        amendment.get("scope_amendment", {}).get("decision"),
        "downgrade_from_superiority_to_estimation",
    )
    check_equal(
        failures,
        "amendment_counts",
        {
            "pilot": amendment["revised_planning_counts"]["protocol_pilot_context_count"],
            "development": amendment["revised_planning_counts"]["development_context_count"],
            "confirmation": amendment["revised_planning_counts"]["confirmation_context_count"],
            "total": amendment["revised_planning_counts"]["total_context_count"],
            "questions": amendment["revised_planning_counts"]["total_question_count"],
            "reserve": amendment["revised_planning_counts"]["unassigned_source_period_reserve"],
        },
        {"pilot": 6, "development": 15, "confirmation": 27, "total": 48, "questions": 96, "reserve": 2},
    )
    check_equal(failures, "amendment_thresholds_changed", amendment["failed_strong_comparison_design"]["thresholds_changed_after_simulation"], False)
    check_equal(failures, "amendment_capacity_recheck_status", amendment["required_capacity_recheck"]["status"], "complete")
    check_equal(failures, "amendment_capacity_matching", amendment["required_capacity_recheck"]["observed_maximum_matching_count"], 48)
    check_equal(failures, "amendment_capacity_hall_slack", amendment["required_capacity_recheck"]["observed_minimum_hall_slack_for_all_families"], 2)
    check_equal(failures, "amendment_capacity_assignment_retained", amendment["required_capacity_recheck"]["context_assignment_retained"], False)
    check_equal(failures, "amendment_manifest_authorized", amendment["gate_effect"]["context_manifest_authorized_now"], True)

    capacity_proof = capacity.get("capacity_proof", {})
    check_equal(
        failures,
        "revised_capacity",
        {
            "required": capacity_proof.get("required_total_context_count"),
            "matching": capacity_proof.get("maximum_slot_matching_count"),
            "slots": capacity_proof.get("required_slot_count"),
            "per_family": capacity_proof.get("required_contexts_per_eligible_family"),
            "slack": capacity_proof.get("minimum_hall_capacity_slack"),
            "assignment_retained": capacity_proof.get("matching_assignment_retained_or_published"),
        },
        {"required": 48, "matching": 48, "slots": 48, "per_family": 16, "slack": 2, "assignment_retained": False},
    )
    check_equal(failures, "capacity_manifest_created", capacity.get("context_manifest_created"), False)
    check_equal(failures, "capacity_new_metrics", capacity.get("new_metrics_reported"), False)

    public_objects = [config, report, amendment, capacity]
    for index, value in enumerate(public_objects):
        if contains_local_path(value):
            add_failure(failures, f"public_object_{index}_contains_local_path", True)
    serialized = json.dumps(public_objects, ensure_ascii=True).lower()
    forbidden_data_keys = [
        "selected_periods",
        "candidate_periods",
        "context_assignments",
        "split_assignments",
        "invoice_values",
        "customer_values",
    ]
    for key in forbidden_data_keys:
        if f'"{key}"' in serialized:
            add_failure(failures, f"forbidden_public_key_{key}", True)

    for fragment in REQUIRED_HTML_FRAGMENTS:
        if fragment not in html_text:
            add_failure(failures, "required_html_fragment", fragment)
    lower_html = html_text.lower()
    for fragment in FORBIDDEN_HTML_FRAGMENTS:
        if fragment.lower() in lower_html:
            add_failure(failures, "forbidden_html_fragment", fragment)
    parser = HTMLCheckParser()
    parser.feed(html_text)
    if parser.tag_counts["html"] != 1 or parser.tag_counts["body"] != 1:
        add_failure(failures, "html_structure", dict(parser.tag_counts))

    artifact_boundaries = report.get("artifact_boundaries", {})
    if any(artifact_boundaries.values()):
        add_failure(failures, "review_artifact_boundaries", artifact_boundaries)

    payload = {
        "schema_version": "1.0",
        "status": (
            "confirmation_precision_review_validation_ready"
            if not failures
            else "confirmation_precision_review_validation_failed"
        ),
        "review_status": report.get("status"),
        "scope_amendment_status": amendment.get("status"),
        "revised_confirmation_context_count": amendment["revised_planning_counts"][
            "confirmation_context_count"
        ],
        "revised_total_context_count": amendment["revised_planning_counts"]["total_context_count"],
        "revised_capacity_matching_count": capacity_proof.get("maximum_slot_matching_count"),
        "context_manifest_created": False,
        "new_empirical_metrics_created": False,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
