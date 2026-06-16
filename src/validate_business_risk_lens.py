from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"

HTML_PATH = REPORTS_DIR / "bizhallu_business_risk_lens.html"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_business_risk_lens_summary.json"
VALIDATION_PATH = REPORTS_DIR / "bizhallu_business_risk_lens_validation.json"

REQUIRED_FRAGMENTS = [
    "Accounting and supply-management extension",
    "Net revenue reconciliation",
    "Returns impact and margin-risk triage",
    "Product concentration and inventory priority",
    "Country exposure and market comparison",
    "10-20 question business-risk extension",
    "no new model run",
]

FORBIDDEN_FRAGMENTS = [
    "production-ready",
    "large human-labeled benchmark",
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
            add_failure(failures, "required_file_missing", str(path))

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
        "status": "business_risk_lens_ready",
        "question_count": 100,
        "question_type_count": 7,
        "lens_count": 4,
        "next_question_count": 10,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            add_failure(
                failures,
                "summary_value_mismatch",
                {"field": key, "expected": value, "actual": summary.get(key)},
            )

    if summary.get("cancellation_or_return_rows", 0) <= 0:
        add_failure(failures, "missing_return_context", summary.get("cancellation_or_return_rows"))
    if summary.get("net_revenue", 0) <= 0:
        add_failure(failures, "missing_net_revenue_context", summary.get("net_revenue"))

    validation = {
        "business_risk_lens_html_path": str(HTML_PATH),
        "ready_for_public_business_lens": len(failures) == 0,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
