from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"

HTML_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_v2.html"
DATA_PATH = REPORTS_DIR / "bizhallu_demo_v2_data.json"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_v2_summary.json"
VALIDATION_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_v2_validation.json"

REQUIRED_HTML_FRAGMENTS = [
    "Interactive demo v2",
    "Filter hallucinated business facts",
    "Open JSON data bundle",
    "detectorFilter",
    "factTypeFilter",
    "labelFilter",
    "outcomeFilter",
    "q_0064",
    "q_0069",
    "assistant-reviewed presentation labels",
]

FORBIDDEN_FRAGMENTS = [
    "pending human review",
    "requires human confirmation",
    "large human-labeled benchmark",
    "production-ready detector",
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
    for path in [HTML_PATH, DATA_PATH, SUMMARY_PATH]:
        if not path.exists():
            add_failure(failures, "required_file_missing", repo_path(path))

    html_text = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""
    data = load_json(DATA_PATH) if DATA_PATH.exists() else {}
    summary = load_json(SUMMARY_PATH) if SUMMARY_PATH.exists() else {}

    if html_text:
        parser = HTMLCheckParser()
        parser.feed(html_text)
        if parser.seen_tags == 0:
            add_failure(failures, "html_parse", "no HTML tags parsed")
        for fragment in REQUIRED_HTML_FRAGMENTS:
            if fragment not in html_text:
                add_failure(failures, "required_html_fragment_missing", fragment)
        for fragment in FORBIDDEN_FRAGMENTS:
            if fragment in html_text:
                add_failure(failures, "forbidden_html_fragment", fragment)

    meta = data.get("meta", {})
    cases = data.get("cases", [])
    all_spans = [span for case in cases for span in case.get("spans", [])]
    case_ids = {case.get("question_id") for case in cases}

    if meta.get("status") != "portfolio_demo_v2_ready":
        add_failure(failures, "data_status", meta.get("status"))
    for question_id in ["q_0064", "q_0069"]:
        if question_id not in case_ids:
            add_failure(failures, "primary_case_missing", question_id)
    if len(cases) < 9:
        add_failure(failures, "case_count_too_small", len(cases))
    if len(all_spans) != 15:
        add_failure(failures, "locked_span_count", len(all_spans))
    if not data.get("filters", {}).get("fact_types"):
        add_failure(failures, "missing_fact_type_filters", data.get("filters"))
    if not data.get("filters", {}).get("outcomes"):
        add_failure(failures, "missing_outcome_filters", data.get("filters"))
    if {span.get("label") for span in all_spans} != {"correct_key_fact", "hallucinated_key_fact"}:
        add_failure(failures, "unexpected_label_set", sorted({span.get("label") for span in all_spans}))
    for span in all_spans:
        for field in ["simple_outcome", "entropy_outcome", "energy_outcome"]:
            if span.get(field) not in {"caught", "missed", "false alarm", "cleared"}:
                add_failure(failures, "bad_detector_outcome", {"annotation_id": span.get("annotation_id"), "field": field})

    expected_summary = {
        "status": "portfolio_demo_v2_ready",
        "case_count": len(cases),
        "locked_span_count": 15,
        "primary_case_count": 2,
        "label_lock_basis": "assistant_full_review",
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            add_failure(
                failures,
                "summary_value_mismatch",
                {"field": key, "expected": expected, "actual": summary.get(key)},
            )

    validation = {
        "portfolio_demo_v2_html_path": repo_path(HTML_PATH),
        "portfolio_demo_v2_data_path": repo_path(DATA_PATH),
        "ready_for_public_demo_v2": len(failures) == 0,
        "case_count": len(cases),
        "locked_span_count": len(all_spans),
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
