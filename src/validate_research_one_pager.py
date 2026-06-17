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
    "Best AUPRC / F1",
    "0.835",
    "0.779",
    "Internal uncertainty has signal",
    "evidence-aware verifier",
    "Possible JHU extensions",
    "Research backlog",
    "Semantic Entropy",
    "TOHA",
    "Real-time hallucinated entity detection",
    "Spilled Energy",
    "compare internal-state signals with evidence-aware verification",
    "assistant-reviewed presentation labels",
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
        "research_track_count": 3,
        "baseline_backlog_count": 4,
        "next_stage_scope": "design-only evidence-aware verifier; no full100 rerun",
        "label_lock_basis": "assistant_full_review",
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
