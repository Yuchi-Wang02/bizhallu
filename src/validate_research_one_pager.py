from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import repo_path
from presentation_evidence import statistical_context, b2_context, b2_note_html


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"

HTML_PATH = REPORTS_DIR / "bizhallu_research_one_pager.html"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_research_one_pager_summary.json"
VALIDATION_PATH = REPORTS_DIR / "bizhallu_research_one_pager_validation.json"

REQUIRED_FRAGMENTS = [
    "Research brief",
    "BizHallu: Auditing Evidence Binding Errors in LLM-Generated Business Analysis",
    "Research problem",
    "Dataset and method",
    "Historical B1 results",
    "Research question and immediate pilot",
    "Longer-term study design",
    "Related work and intended distinction",
    "Specific request:",
    "0.835",
    "0.779",
    "Flag every span",
    "crosses zero",
    "composition control",
    "AI-assisted provisional",
    "pre-identified spans",
    "q_0048",
    "token-time uncertainty",
    "Semantic Entropy",
    "FActScore",
    "TabFact",
    "not execution-ready",
    "Confirmation remains sealed",
    "evidence-aware verifier",
]

FORBIDDEN_FRAGMENTS = [
    "is a production-ready detector",
    "is a large independent human-labeled benchmark",
    "evaluates whole-answer correctness",
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

    for path in [HTML_PATH, SUMMARY_PATH]:
        if not path.exists():
            add_failure(failures, "required_file_missing", repo_path(path))

    html_text = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""
    summary = load_json(SUMMARY_PATH) if SUMMARY_PATH.exists() else {}
    if b2_note_html() not in html_text:
        add_failure(failures, 'B2 sensitivity note missing or stale', 'Source-backed note must remain visible')

    if html_text:
        parser = HTMLCheckParser()
        parser.feed(html_text)
        if parser.seen_tags == 0:
            add_failure(failures, "html_parse", "no HTML tags parsed")
        for fragment in REQUIRED_FRAGMENTS:
            if fragment not in html_text:
                add_failure(failures, "required_fragment_missing", fragment)
        for fragment in FORBIDDEN_FRAGMENTS:
            if fragment in html_text:
                add_failure(failures, "forbidden_fragment", fragment)

    expected = {
        "status": "research_one_pager_ready",
        "question_count": 100,
        "annotated_span_count": 205,
        "heldout_test_span_count": 103,
        "best_test_auprc": 0.835073,
        "best_test_f1": 0.779412,
        "demo_case_count": 9,
        "business_risk_lens_count": 4,
        "verifier_pilot_span_count": 15,
        "verifier_pilot_contradicted_count": 7,
        "research_track_count": 3,
        "baseline_backlog_count": 4,
        "next_stage_scope": "Proposed relation-annotation calibration and independent verifier design; no completed human review, model execution or confirmation evaluation",
        "confirmation_precision_review_status": "outcome_blind_precision_review_blocked",
        "confirmation_strong_candidate_pass_count": 0,
        "confirmation_candidate_count": 4,
        "confirmation_context_count": 27,
        "confirmation_total_context_count": 48,
        "confirmation_total_question_count": 96,
        "confirmation_capacity_matching_count": 48,
        "confirmation_capacity_hall_slack": 2,
        "confirmation_context_manifest_status": "confirmation_context_manifest_v1_frozen",
        "confirmation_context_manifest_created": True,
        "confirmation_split_assignment_created": True,
        "confirmation_context_manifest_commitment_sha256": "002b484b3b59c52db0a2213b8d896750cdb2bb9157998d48bf015eff27f19e5a",
        "confirmation_reserve_period_count": 2,
        "confirmation_question_design_status": "confirmation_question_design_v1_frozen",
        "confirmation_question_manifest_commitment_sha256": "b72ffaf715afef85867522fb0c7264377350ce146709962e420c16eaa6d9e80c",
        "confirmation_question_count_frozen": 96,
        "confirmation_question_template_count": 6,
        "confirmation_question_payload_fingerprint_check": "complete",
        "confirmation_question_payload_cross_split_overlap_count": 0,
        "confirmation_question_evidence_content_fingerprint_count": 96,
        "confirmation_question_evidence_content_cross_split_overlap_count": 0,
        "confirmation_historical_unique_evidence_content_fingerprint_count": 66,
        "confirmation_question_evidence_content_historical_overlap_count": 0,
        "confirmation_claim_scope": "estimation_only_no_detector_superiority",
        "label_lock_basis": "assistant_full_review",
        "methodology_status": "methodology_hardening_v1_ready",
        "methodology_share_status": "share_with_caveats",
        "presentation_revision": "professor_review_2026_09_06",
        "statistical_review": statistical_context(),
        "b2_sensitivity": b2_context(),
        "independent_human_annotation": False,
        "share_status": "exploratory_project_for_method_feedback",
        "research_question_count": 3,
        "immediate_pilot_status": "proposed_not_executed",
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            add_failure(
                failures,
                "summary_value_mismatch",
                {"field": key, "expected": value, "actual": summary.get(key)},
            )

    related_work = summary.get('related_work', [])
    expected_sources = {
        'FActScore': 'https://aclanthology.org/2023.emnlp-main.741/',
        'TabFact': 'https://openreview.net/pdf?id=rkeJRhNYDH',
        'Semantic Entropy': 'https://www.nature.com/articles/s41586-024-07421-0',
    }
    if {row.get('name'): row.get('url') for row in related_work} != expected_sources or any(
            row.get('evaluated_in_bizhallu') is not False for row in related_work):
        add_failure(failures, 'related_work_provenance', 'Three primary sources must remain unevaluated comparison context')
    for url in expected_sources.values():
        if url not in html_text:
            add_failure(failures, 'related_work_link_missing', url)

    validation = {
        "research_one_pager_html_path": repo_path(HTML_PATH),
        "ready_for_research_outreach": len(failures) == 0,
        "num_failures": len(failures),
        "failures": failures,
        "validation_scope": "content_and_source_consistency_only",
        "visual_review_verified": False,
        "independent_human_review_verified": False,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
