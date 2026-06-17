"""Validate the BizHallu evidence-aware verifier pilot public artifacts."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import contains_local_path, repo_path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"

ROWS_CSV_PATH = REPORTS_DIR / "bizhallu_evidence_verifier_pilot_rows.csv"
ROWS_JSON_PATH = REPORTS_DIR / "bizhallu_evidence_verifier_pilot_rows.json"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_evidence_verifier_pilot_summary.json"
HTML_PATH = REPORTS_DIR / "bizhallu_evidence_verifier_pilot.html"
VALIDATION_PATH = REPORTS_DIR / "bizhallu_evidence_verifier_pilot_validation.json"

ALLOWED_LABELS = {"supported", "contradicted", "unmatched", "needs_review"}
EXPECTED_METRICS = {
    "best_test_auprc": 0.835073,
    "best_test_f1": 0.779412,
    "span_count": 15,
    "case_count": 9,
    "label_lock_basis": "assistant_full_review",
}

REQUIRED_HTML_FRAGMENTS = [
    "Evidence-Aware Verifier Pilot",
    "Demo v2 locked spans only",
    "not a production checker",
    "not a new benchmark result",
    "supported",
    "contradicted",
    "0.835",
    "0.779",
    "Confident wrong evidence binding",
]

FORBIDDEN_CLAIM_FRAGMENTS = [
    "production-ready",
    "beats internal",
    "beat internal",
    "new headline",
    "new benchmark metric",
    "large human-labeled benchmark",
]


class HTMLCheckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.seen_tags = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.seen_tags += 1


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def nearly_equal(actual: Any, expected: float, tolerance: float = 1e-9) -> bool:
    return isinstance(actual, (int, float)) and abs(float(actual) - expected) <= tolerance


def validate_html(path: Path, failures: list[dict[str, Any]]) -> None:
    if not path.exists():
        failures.append({"name": "html_exists", "path": repo_path(path), "reason": "missing"})
        return
    text = path.read_text(encoding="utf-8")
    parser = HTMLCheckParser()
    parser.feed(text)
    if parser.seen_tags == 0:
        failures.append({"name": "html_parse", "path": repo_path(path), "reason": "no HTML tags parsed"})
    for fragment in REQUIRED_HTML_FRAGMENTS:
        if fragment not in text:
            failures.append(
                {
                    "name": "html_required_fragment",
                    "path": repo_path(path),
                    "fragment": fragment,
                    "reason": "required verifier wording missing",
                }
            )
    for fragment in FORBIDDEN_CLAIM_FRAGMENTS:
        if fragment in text:
            failures.append(
                {
                    "name": "html_forbidden_claim",
                    "path": repo_path(path),
                    "fragment": fragment,
                    "reason": "verifier pilot overclaims its status",
                }
            )


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path in [ROWS_CSV_PATH, ROWS_JSON_PATH, SUMMARY_PATH, HTML_PATH]:
        if not path.exists():
            failures.append({"name": "required_file", "path": repo_path(path), "reason": "missing"})

    rows = load_json(ROWS_JSON_PATH) if ROWS_JSON_PATH.exists() else []
    summary = load_json(SUMMARY_PATH) if SUMMARY_PATH.exists() else {}

    if not isinstance(rows, list):
        failures.append({"name": "rows_shape", "reason": "rows JSON is not a list"})
        rows = []

    span_ids = [row.get("span_id") for row in rows if isinstance(row, dict)]
    if len(rows) != EXPECTED_METRICS["span_count"]:
        failures.append(
            {
                "name": "row_count",
                "expected": EXPECTED_METRICS["span_count"],
                "actual": len(rows),
                "reason": "all 15 locked Demo v2 spans must be represented exactly once",
            }
        )
    if len(set(span_ids)) != len(span_ids):
        failures.append({"name": "unique_span_ids", "reason": "span_id values are not unique"})

    labels = {str(row.get("verifier_label")) for row in rows if isinstance(row, dict)}
    unknown_labels = sorted(labels - ALLOWED_LABELS)
    if unknown_labels:
        failures.append(
            {
                "name": "verifier_label_set",
                "allowed": sorted(ALLOWED_LABELS),
                "unknown": unknown_labels,
                "reason": "verifier labels must stay in the pilot label set",
            }
        )

    expected_label_counts = {"supported": 8, "contradicted": 7}
    actual_label_counts = summary.get("verifier_label_counts", {})
    for label, expected_count in expected_label_counts.items():
        if actual_label_counts.get(label) != expected_count:
            failures.append(
                {
                    "name": "label_count",
                    "label": label,
                    "expected": expected_count,
                    "actual": actual_label_counts.get(label),
                    "reason": "Demo v2 locked labels should map to stable verifier pilot counts",
                }
            )

    if summary.get("status") != "evidence_verifier_pilot_ready":
        failures.append(
            {
                "name": "summary_status",
                "expected": "evidence_verifier_pilot_ready",
                "actual": summary.get("status"),
            }
        )
    for key, expected in EXPECTED_METRICS.items():
        actual = summary.get(key)
        ok = nearly_equal(actual, expected) if isinstance(expected, float) else actual == expected
        if not ok:
            failures.append(
                {
                    "name": "locked_metric_or_scope",
                    "field": key,
                    "expected": expected,
                    "actual": actual,
                    "reason": "verifier pilot must not alter current public result claims",
                }
            )

    for path in [ROWS_JSON_PATH, SUMMARY_PATH]:
        if path.exists() and contains_local_path(path.read_text(encoding="utf-8")):
            failures.append(
                {
                    "name": "public_json_local_path",
                    "path": repo_path(path),
                    "reason": "verifier pilot JSON must use repo-relative paths",
                }
            )

    validate_html(HTML_PATH, failures)

    validation = {
        "status": "evidence_verifier_pilot_validation_ready" if not failures else "evidence_verifier_pilot_validation_failed",
        "ready_for_public_verifier_pilot": not failures,
        "rows_csv_path": repo_path(ROWS_CSV_PATH),
        "rows_json_path": repo_path(ROWS_JSON_PATH),
        "summary_path": repo_path(SUMMARY_PATH),
        "html_path": repo_path(HTML_PATH),
        "row_count": len(rows),
        "case_count": summary.get("case_count"),
        "verifier_label_counts": summary.get("verifier_label_counts"),
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
