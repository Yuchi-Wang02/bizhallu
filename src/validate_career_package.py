from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"

HTML_PATH = REPORTS_DIR / "bizhallu_career_package.html"
MD_PATH = REPORTS_DIR / "bizhallu_career_package.md"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_career_package_summary.json"
VALIDATION_PATH = REPORTS_DIR / "bizhallu_career_package_validation.json"

REQUIRED_HTML_FRAGMENTS = [
    "Career package for BA / DS / AI analyst roles",
    "One-page project brief",
    "Interview FAQ",
    "Resume bullets",
    "60-second version",
    "5-minute version",
    "assistant-reviewed presentation labels",
    "not a production detector",
    "large independent human-labeled benchmark",
    "0.835",
    "0.779",
    "q_0064",
    "q_0069",
]

REQUIRED_MD_FRAGMENTS = [
    "# BizHallu Career Package",
    "Project Brief",
    "Resume Bullets",
    "Interview FAQ",
    "Public Claim Guardrails",
]

FORBIDDEN_FRAGMENTS = [
    "is a large human-labeled benchmark",
    "production-ready hallucination detection system",
    "evaluates whole-answer correctness",
    "pending human review",
    "requires human confirmation",
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

    for path in [HTML_PATH, MD_PATH, SUMMARY_PATH]:
        if not path.exists():
            add_failure(failures, "required_file_missing", str(path))

    html_text = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""
    md_text = MD_PATH.read_text(encoding="utf-8") if MD_PATH.exists() else ""
    summary = load_json(SUMMARY_PATH) if SUMMARY_PATH.exists() else {}

    if html_text:
        parser = HTMLCheckParser()
        parser.feed(html_text)
        if parser.seen_tags == 0:
            add_failure(failures, "html_parse", "no HTML tags parsed")
        for fragment in REQUIRED_HTML_FRAGMENTS:
            if fragment not in html_text:
                add_failure(failures, "required_html_fragment_missing", fragment)

    if md_text:
        for fragment in REQUIRED_MD_FRAGMENTS:
            if fragment not in md_text:
                add_failure(failures, "required_markdown_fragment_missing", fragment)

    combined_public_text = f"{html_text}\n{md_text}"
    for fragment in FORBIDDEN_FRAGMENTS:
        if fragment in combined_public_text:
            add_failure(failures, "forbidden_fragment", fragment)

    expected = {
        "status": "career_package_ready",
        "question_count": 100,
        "annotated_span_count": 205,
        "best_test_auprc": 0.835073,
        "best_test_f1": 0.779412,
        "label_lock_basis": "assistant_full_review",
        "resume_bullet_count": 5,
        "faq_count": 10,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            add_failure(
                failures,
                "summary_value_mismatch",
                {"field": key, "expected": value, "actual": summary.get(key)},
            )

    validation = {
        "career_html_path": str(HTML_PATH),
        "career_markdown_path": str(MD_PATH),
        "ready_for_public_career_use": len(failures) == 0,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
