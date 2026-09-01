from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from build_methodology_hardening_report import (
    PROTOCOL_PATH,
    audit_current_methodology,
    load_questions,
    load_scores,
)
from public_paths import contains_local_path, repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
HTML_PATH = REPORTS_DIR / "bizhallu_methodology_hardening.html"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_methodology_hardening_summary.json"
VALIDATION_PATH = REPORTS_DIR / "bizhallu_methodology_hardening_validation.json"

REQUIRED_HTML_FRAGMENTS = [
    "Methodology Hardening v1",
    "What the current result proves, and what it does not.",
    "Outcome-informed annotation subset",
    "Post-hoc headline signal selection",
    "Context overlap across splits",
    "Provisional labels without independent agreement",
    "Oracle span boundary",
    "35 / 36",
    "q_0048",
    "0.835",
    "0.779",
    "exploratory maxima",
    "error-enriched subset",
    "exact fingerprints",
    "fresh confirmation study",
    "internal uncertainty",
    "literature-grounded baselines",
    "evidence-aware verifier",
    "No result was recomputed in this phase.",
]

FORBIDDEN_HTML_FRAGMENTS = [
    "confirmatory generalization is established",
    "unbiased held-out model-selection result was achieved",
    "production-ready hallucination detector",
    "independently human-annotated benchmark is complete",
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
    for path in [PROTOCOL_PATH, HTML_PATH, SUMMARY_PATH]:
        if not path.exists():
            add_failure(failures, "required_file_missing", repo_path(path))

    protocol = load_json(PROTOCOL_PATH) if PROTOCOL_PATH.exists() else {}
    summary = load_json(SUMMARY_PATH) if SUMMARY_PATH.exists() else {}
    html_text = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""

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

    current_audit = audit_current_methodology(load_questions(), load_scores())
    expected_audit_values = {
        "question_count": 100,
        "heldout_question_count": 36,
        "annotated_heldout_question_count": 35,
        "missing_heldout_question_ids": ["q_0048"],
        "annotated_span_count": 205,
        "span_split_counts": {"dev": 102, "test": 103},
        "period_overlap": {
            "dev_test": ["2011-04", "2011-05", "2011-06", "2011-09", "2011-10"],
            "train_dev": ["2011-03", "2011-04", "2011-05", "2011-06", "2011-08", "2011-09", "2011-10"],
            "train_test": ["2011-04", "2011-05", "2011-06", "2011-09", "2011-10", "2011-11"],
        },
        "exact_evidence_row_cross_split_group_count": 9,
        "exact_evidence_row_cross_split_question_count": 28,
        "exact_filter_cross_split_group_count": 0,
    }
    for key, expected in expected_audit_values.items():
        actual = current_audit.get(key)
        if actual != expected:
            add_failure(
                failures,
                "source_audit_value_mismatch",
                {"field": key, "expected": expected, "actual": actual},
            )

    for key, actual in current_audit.get("source_code_checks", {}).items():
        if actual is not True:
            add_failure(failures, "source_code_check_failed", key)

    expected_summary_values = {
        "status": "methodology_hardening_v1_ready",
        "share_status": "share_with_caveats",
        "study_classification": "exploratory_retrospective",
        "finding_count": 5,
        "high_severity_finding_count": 4,
        "confirmation_protocol_status": "design_only_not_yet_executed",
        "primary_confirmation_metric": "AUPRC",
        "num_failures": 0,
    }
    for key, expected in expected_summary_values.items():
        if summary.get(key) != expected:
            add_failure(
                failures,
                "summary_value_mismatch",
                {"field": key, "expected": expected, "actual": summary.get(key)},
            )

    if summary.get("audit") != current_audit:
        add_failure(failures, "summary_audit_stale", "summary audit does not match source artifacts")

    locked = summary.get("locked_public_results", {})
    expected_locked = {
        "exploratory_max_test_auprc": 0.835073,
        "exploratory_max_test_auprc_signal": "one_minus_min_top2_margin",
        "exploratory_max_test_f1": 0.779412,
        "exploratory_max_test_f1_signal": "mean_token_entropy",
        "aligned_span_count": 205,
        "test_span_count": 103,
    }
    if locked != expected_locked:
        add_failure(
            failures,
            "locked_result_mismatch",
            {"expected": expected_locked, "actual": locked},
        )

    current_study = protocol.get("current_study", {})
    if current_study.get("sample_selection") != "heldout_high_priority_queue_conditioned_on_generated_answer_auto_status":
        add_failure(failures, "protocol_sample_selection", current_study.get("sample_selection"))
    if current_study.get("split_assignment") != "within_question_type_periodic_position_mod_5":
        add_failure(failures, "protocol_split_assignment", current_study.get("split_assignment"))
    if current_study.get("headline_signal_selection") != "post_hoc_maximum_after_comparing_test_results":
        add_failure(failures, "protocol_headline_selection", current_study.get("headline_signal_selection"))

    confirmation = protocol.get("future_confirmation_protocol", {})
    if confirmation.get("status") != "design_only_not_yet_executed":
        add_failure(failures, "confirmation_status", confirmation.get("status"))
    if set(confirmation.get("evaluation_tracks", {})) != {
        "oracle_span_diagnostics",
        "claim_extraction",
        "end_to_end_verification",
    }:
        add_failure(failures, "confirmation_tracks", confirmation.get("evaluation_tracks"))

    validation = {
        "status": "methodology_hardening_validation_passed" if not failures else "methodology_hardening_validation_failed",
        "html_path": repo_path(HTML_PATH),
        "summary_path": repo_path(SUMMARY_PATH),
        "protocol_path": repo_path(PROTOCOL_PATH),
        "recomputed_question_count": current_audit.get("question_count"),
        "recomputed_annotated_span_count": current_audit.get("annotated_span_count"),
        "recomputed_cross_split_evidence_group_count": current_audit.get("exact_evidence_row_cross_split_group_count"),
        "ready_to_share_with_caveats": len(failures) == 0,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
