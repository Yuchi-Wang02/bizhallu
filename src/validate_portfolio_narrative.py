from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
RESULTS_DIR = PROJECT_ROOT / "results"

HTML_PATH = REPORTS_DIR / "bizhallu_portfolio_narrative.html"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_narrative_summary.json"
VALIDATION_PATH = REPORTS_DIR / "bizhallu_portfolio_narrative_validation.json"

DEMO_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_summary.json"
INTERPRETATION_SUMMARY_PATH = REPORTS_DIR / "full100_detector_interpretation_summary.json"
LABEL_LOCK_SUMMARY_PATH = REPORTS_DIR / "full100_label_lock_summary.json"
PREFLIGHT_VALIDATION_PATH = RESULTS_DIR / "full100_preflight_validation.json"


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
    for path in (
        HTML_PATH,
        SUMMARY_PATH,
        DEMO_SUMMARY_PATH,
        INTERPRETATION_SUMMARY_PATH,
        LABEL_LOCK_SUMMARY_PATH,
        PREFLIGHT_VALIDATION_PATH,
    ):
        if not path.exists():
            add_failure(failures, "missing required file", repo_path(path))

    html_text = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""
    if html_text:
        try:
            StrictEnoughHTMLParser().feed(html_text)
        except Exception as exc:  # pragma: no cover - defensive parser guard
            add_failure(failures, "html parser failed", repr(exc))

    summary = load_json(SUMMARY_PATH) if SUMMARY_PATH.exists() else {}
    demo = load_json(DEMO_SUMMARY_PATH) if DEMO_SUMMARY_PATH.exists() else {}
    interpretation = load_json(INTERPRETATION_SUMMARY_PATH) if INTERPRETATION_SUMMARY_PATH.exists() else {}
    label_lock = load_json(LABEL_LOCK_SUMMARY_PATH) if LABEL_LOCK_SUMMARY_PATH.exists() else {}
    preflight = load_json(PREFLIGHT_VALIDATION_PATH) if PREFLIGHT_VALIDATION_PATH.exists() else {}

    if summary.get("status") != "portfolio_narrative_ready":
        add_failure(failures, "unexpected narrative status", summary.get("status"))
    if preflight.get("current_stage") not in {"portfolio_demo_ready", "portfolio_narrative_ready", "github_pages_ready"}:
        add_failure(
            failures,
            "preflight must be portfolio_demo_ready, portfolio_narrative_ready, or github_pages_ready",
            preflight.get("current_stage"),
        )
    if preflight.get("ready_for_current_stage") is not True:
        add_failure(failures, "preflight is not ready", preflight)

    if summary.get("primary_question_ids") != demo.get("primary_question_ids"):
        add_failure(
            failures,
            "primary question IDs mismatch demo summary",
            {"summary": summary.get("primary_question_ids"), "demo": demo.get("primary_question_ids")},
        )
    if summary.get("locked_primary_span_count") != demo.get("locked_primary_span_count"):
        add_failure(failures, "locked primary span count mismatch demo", summary.get("locked_primary_span_count"))
    if summary.get("locked_selected_span_count") != label_lock.get("selected_annotation_count"):
        add_failure(failures, "locked selected span count mismatch label lock", summary.get("locked_selected_span_count"))
    if summary.get("labels_locked") is not True:
        add_failure(failures, "summary labels_locked must be true", summary.get("labels_locked"))
    if summary.get("label_lock_basis") != "assistant_full_review":
        add_failure(failures, "unexpected label lock basis", summary.get("label_lock_basis"))

    if not approx_equal(summary.get("best_test_auprc"), interpretation.get("best_overall_by_test_auprc", {}).get("test_auprc")):
        add_failure(failures, "best test AUPRC mismatch", summary.get("best_test_auprc"))
    if not approx_equal(summary.get("best_test_f1"), interpretation.get("best_overall_by_test_f1", {}).get("test_f1")):
        add_failure(failures, "best test F1 mismatch", summary.get("best_test_f1"))
    if summary.get("error_row_count") != interpretation.get("error_row_count"):
        add_failure(failures, "error row count mismatch", summary.get("error_row_count"))

    if summary.get("question_count") != 100:
        add_failure(failures, "expected 100 gold questions", summary.get("question_count"))
    if summary.get("qwen_record_count") != 100:
        add_failure(failures, "expected 100 Qwen generations", summary.get("qwen_record_count"))
    if summary.get("annotated_span_count") != 205:
        add_failure(failures, "expected 205 annotated spans", summary.get("annotated_span_count"))
    if summary.get("aligned_span_count") != 205:
        add_failure(failures, "expected 205 aligned spans", summary.get("aligned_span_count"))
    if summary.get("resume_bullet_count", 0) < 5:
        add_failure(failures, "resume bullet count is too small", summary.get("resume_bullet_count"))
    if summary.get("slide_count", 0) < 7:
        add_failure(failures, "slide outline count is too small", summary.get("slide_count"))

    required_fragments = [
        "BizHallu Portfolio Narrative",
        "Auditing hallucinated business facts",
        "Personal Branding",
        "One-minute pitch",
        "Resume bullets",
        "LinkedIn / portfolio blurb",
        "Slide outline",
        "Presentation guardrails",
        "q_0064",
        "q_0069",
        "0.835",
        "0.779",
        "assistant_full_review",
        "span-level hallucination detection",
        "evidence-aware validation",
        "business analytics and AI reliability",
        "Qwen3-0.6B",
        "205",
        "100",
    ]
    html_lower = html_text.lower()
    for fragment in required_fragments:
        if fragment.lower() not in html_lower:
            add_failure(failures, "html missing required fragment", fragment)

    stale_fragments = [
        "pending human review",
        "requires human confirmation",
        "presentation-level confirmation required",
    ]
    for fragment in stale_fragments:
        if fragment in html_lower:
            add_failure(failures, "html contains stale confirmation wording", fragment)

    validation = {
        "html_path": repo_path(HTML_PATH),
        "summary_path": repo_path(SUMMARY_PATH),
        "source_portfolio_demo_summary_path": repo_path(DEMO_SUMMARY_PATH),
        "status": summary.get("status"),
        "primary_question_ids": summary.get("primary_question_ids"),
        "resume_bullet_count": summary.get("resume_bullet_count"),
        "slide_count": summary.get("slide_count"),
        "ready_for_portfolio_narrative": len(failures) == 0,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
