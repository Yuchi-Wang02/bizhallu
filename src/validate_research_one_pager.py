from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"

HTML_PATH = REPORTS_DIR / "bizhallu_research_one_pager.html"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_research_one_pager_summary.json"
VALIDATION_PATH = REPORTS_DIR / "bizhallu_research_one_pager_validation.json"

REQUIRED_FRAGMENTS = [
    "Professor / research advisor one-pager",
    "BizHallu: Auditing Evidence Binding Errors in LLM-Generated Business Analysis",
    "Research problem",
    "Dataset and task",
    "Pipeline from transaction evidence",
    "Exploratory test maxima",
    "0.835",
    "0.779",
    "Internal uncertainty has signal",
    "evidence-aware verifier",
    "Open claim-evidence schema",
    "Open methodology audit",
    "Claim-Evidence Review Schema v0",
    "Possible JHU extensions",
    "Research backlog",
    "Semantic Entropy",
    "TOHA",
    "Real-time hallucinated entity detection",
    "Spilled Energy",
    "compare internal-state signals with evidence-aware verification",
    "AI-assisted and provisional",
    "pre-identified spans",
    "exploratory test-set maxima",
    "35 of 36 dev/test questions",
    "outcome-informed high-priority queue",
    "fresh context-separated confirmation protocol",
    "Prospective confirmation design",
    "0/4 tested strong-design candidates",
    "Thresholds were not relaxed",
    "estimation rather than detector superiority",
    "6/15/27",
    "48 period-disjoint contexts",
    "96 frozen private questions",
    "48/48 slots",
    "minimum Hall slack +2",
    "A second private manifest freezes 96 deterministic questions and gold answers across 6 templates",
    "All 96 full payloads and normalized evidence-table contents are unique",
    "match 0 of 66 unique historical full100 contents",
    "No prompt, model output, annotation, detector score, or new empirical metric exists",
    "Next freeze model, tokenizer, prompt, decoding, detector-family, and metric configurations",
    "Open manifest commitment",
    "Open precision review",
    "Open prospective study design",
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
        "next_stage_scope": "freeze model, tokenizer, prompt, decoding, detector-family, and metric configurations; no model execution, labels, scores, or new metrics yet",
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
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            add_failure(
                failures,
                "summary_value_mismatch",
                {"field": key, "expected": value, "actual": summary.get(key)},
            )

    validation = {
        "research_one_pager_html_path": repo_path(HTML_PATH),
        "ready_for_research_outreach": len(failures) == 0,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
