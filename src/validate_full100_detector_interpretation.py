from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"

HTML_PATH = REPORTS_DIR / "full100_detector_interpretation.html"
SUMMARY_PATH = REPORTS_DIR / "full100_detector_interpretation_summary.json"
VALIDATION_PATH = REPORTS_DIR / "full100_detector_interpretation_validation.json"

FAMILY_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_family_comparison_report.json"
ERROR_REVIEW_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_error_review_report.json"
ERROR_REVIEW_VALIDATION_PATH = RESULTS_DIR / "full100_draft_detector_error_review_validation.json"


class StrictEnoughHTMLParser(HTMLParser):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add_failure(failures: list[dict[str, Any]], message: str, detail: Any = None) -> None:
    failures.append({"message": message, "detail": detail})


def approx_equal(left: Any, right: Any, tolerance: float = 1e-9) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def main() -> None:
    failures: list[dict[str, Any]] = []

    for path in (HTML_PATH, SUMMARY_PATH, FAMILY_REPORT_PATH, ERROR_REVIEW_REPORT_PATH, ERROR_REVIEW_VALIDATION_PATH):
        if not path.exists():
            add_failure(failures, "missing required file", str(path))

    html_text = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""
    if html_text:
        try:
            StrictEnoughHTMLParser().feed(html_text)
        except Exception as exc:  # pragma: no cover - defensive parser guard
            add_failure(failures, "html parser failed", repr(exc))

    summary = load_json(SUMMARY_PATH) if SUMMARY_PATH.exists() else {}
    family_report = load_json(FAMILY_REPORT_PATH) if FAMILY_REPORT_PATH.exists() else {}
    error_report = load_json(ERROR_REVIEW_REPORT_PATH) if ERROR_REVIEW_REPORT_PATH.exists() else {}
    error_validation = load_json(ERROR_REVIEW_VALIDATION_PATH) if ERROR_REVIEW_VALIDATION_PATH.exists() else {}

    if summary.get("status") != "report_ready_draft":
        add_failure(failures, "unexpected interpretation status", summary.get("status"))

    if error_validation.get("num_failures") != 0:
        add_failure(failures, "source error review validation is not clean", error_validation)

    source_best_auprc = family_report.get("best_overall_by_test_auprc", {})
    source_best_f1 = family_report.get("best_overall_by_test_f1", {})
    summary_best_auprc = summary.get("best_overall_by_test_auprc", {})
    summary_best_f1 = summary.get("best_overall_by_test_f1", {})

    if summary_best_auprc.get("baseline") != source_best_auprc.get("baseline"):
        add_failure(failures, "best AUPRC baseline mismatch", {"summary": summary_best_auprc, "source": source_best_auprc})
    if summary_best_f1.get("baseline") != source_best_f1.get("baseline"):
        add_failure(failures, "best F1 baseline mismatch", {"summary": summary_best_f1, "source": source_best_f1})
    if source_best_auprc and not approx_equal(summary_best_auprc.get("test_auprc"), source_best_auprc.get("test_auprc")):
        add_failure(failures, "best AUPRC value mismatch", {"summary": summary_best_auprc, "source": source_best_auprc})
    if source_best_f1 and not approx_equal(summary_best_f1.get("test_f1"), source_best_f1.get("test_f1")):
        add_failure(failures, "best F1 value mismatch", {"summary": summary_best_f1, "source": source_best_f1})

    if summary.get("error_row_count") != error_report.get("error_row_count"):
        add_failure(
            failures,
            "error row count mismatch",
            {"summary": summary.get("error_row_count"), "source": error_report.get("error_row_count")},
        )
    if summary.get("selected_baseline_count") != error_report.get("selected_baseline_count"):
        add_failure(
            failures,
            "selected baseline count mismatch",
            {"summary": summary.get("selected_baseline_count"), "source": error_report.get("selected_baseline_count")},
        )

    required_fragments = [
        "Best AUPRC",
        "0.835",
        "Best F1",
        "0.779",
        "Best energy F1",
        "0.773",
        "57",
        "not pure Spilled Energy",
        "Labels locked after assistant full review",
        "Dev selected, test reported",
    ]
    for fragment in required_fragments:
        if fragment not in html_text:
            add_failure(failures, "html missing required fragment", fragment)

    stale_fragments = [
        "best test F1 0.761",
        "Best overall held-out test F1 is 0.773",
        "Review detector errors.",
        "presentation-level confirmation required",
    ]
    for fragment in stale_fragments:
        if fragment in html_text:
            add_failure(failures, "html contains stale fragment", fragment)

    validation = {
        "html_path": str(HTML_PATH),
        "summary_path": str(SUMMARY_PATH),
        "source_family_report_path": str(FAMILY_REPORT_PATH),
        "source_error_review_report_path": str(ERROR_REVIEW_REPORT_PATH),
        "ready_for_presentation_label_confirmation": len(failures) == 0,
        "ready_for_locked_presentation": len(failures) == 0,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
