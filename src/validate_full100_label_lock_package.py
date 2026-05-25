from __future__ import annotations

import csv
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"

REVIEW_NOTES_JSONL_PATH = REPORTS_DIR / "full100_label_confirmation_review_notes.jsonl"
LOCK_DECISIONS_CSV_PATH = REPORTS_DIR / "full100_label_lock_decisions.csv"
LOCK_DECISIONS_JSONL_PATH = REPORTS_DIR / "full100_label_lock_decisions.jsonl"
LOCK_SUMMARY_PATH = REPORTS_DIR / "full100_label_lock_summary.json"
LOCK_REPORT_HTML_PATH = REPORTS_DIR / "full100_label_lock_report.html"
VALIDATION_PATH = REPORTS_DIR / "full100_label_lock_validation.json"

EXPECTED_STATUS = "presentation_labels_locked"
EXPECTED_LOCK_BASIS = "assistant_full_review"
EXPECTED_REVIEW_STATUS = "locked_after_assistant_full_review"
EXPECTED_PRESENTATION_USES = {
    "paired_contrast_example",
    "strong_false_negative_example",
    "span_level_caveat",
    "offset_check_only",
}


class StrictEnoughHTMLParser(HTMLParser):
    pass


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def add_failure(failures: list[dict[str, Any]], message: str, detail: Any = None) -> None:
    failures.append({"message": message, "detail": detail})


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path in (
        REVIEW_NOTES_JSONL_PATH,
        LOCK_DECISIONS_CSV_PATH,
        LOCK_DECISIONS_JSONL_PATH,
        LOCK_SUMMARY_PATH,
        LOCK_REPORT_HTML_PATH,
    ):
        if not path.exists():
            add_failure(failures, "missing required file", str(path))

    review_rows = load_jsonl(REVIEW_NOTES_JSONL_PATH) if REVIEW_NOTES_JSONL_PATH.exists() else []
    lock_rows = load_jsonl(LOCK_DECISIONS_JSONL_PATH) if LOCK_DECISIONS_JSONL_PATH.exists() else []
    lock_csv_rows = load_csv(LOCK_DECISIONS_CSV_PATH) if LOCK_DECISIONS_CSV_PATH.exists() else []
    summary = load_json(LOCK_SUMMARY_PATH) if LOCK_SUMMARY_PATH.exists() else {}
    html_text = LOCK_REPORT_HTML_PATH.read_text(encoding="utf-8") if LOCK_REPORT_HTML_PATH.exists() else ""

    if html_text:
        try:
            StrictEnoughHTMLParser().feed(html_text)
        except Exception as exc:  # pragma: no cover - defensive parser guard
            add_failure(failures, "html parser failed", repr(exc))

    review_ids = {row["confirmation_item_id"] for row in review_rows}
    lock_ids = {row["confirmation_item_id"] for row in lock_rows}
    if review_ids != lock_ids:
        add_failure(
            failures,
            "lock decisions do not cover the same confirmation IDs as review notes",
            {"missing": sorted(review_ids - lock_ids), "extra": sorted(lock_ids - review_ids)},
        )
    if len(lock_rows) != len(lock_csv_rows):
        add_failure(failures, "CSV/JSONL row-count mismatch", {"csv": len(lock_csv_rows), "jsonl": len(lock_rows)})

    if summary.get("status") != EXPECTED_STATUS:
        add_failure(failures, "unexpected lock status", summary.get("status"))
    if summary.get("review_status") != EXPECTED_REVIEW_STATUS:
        add_failure(failures, "unexpected review status", summary.get("review_status"))
    if summary.get("lock_basis") != EXPECTED_LOCK_BASIS:
        add_failure(failures, "unexpected lock basis", summary.get("lock_basis"))
    if summary.get("labels_locked") is not True:
        add_failure(failures, "summary labels_locked must be true", summary.get("labels_locked"))
    if summary.get("human_confirmation_required") is not False:
        add_failure(
            failures,
            "summary human_confirmation_required must be false after assistant lock",
            summary.get("human_confirmation_required"),
        )
    if summary.get("selected_annotation_count") != len(lock_rows):
        add_failure(failures, "summary selected_annotation_count mismatch", summary.get("selected_annotation_count"))
    if summary.get("locked_label_count") != len(lock_rows):
        add_failure(failures, "summary locked_label_count mismatch", summary.get("locked_label_count"))
    if summary.get("source_fix_required_count") != 0:
        add_failure(failures, "source fixes remain before lock", summary.get("source_fix_required_count"))
    if summary.get("assistant_supported_count") != len(lock_rows):
        add_failure(failures, "not every locked row is assistant-supported", summary.get("assistant_supported_count"))

    publish_counts = summary.get("by_publish_use", {})
    if publish_counts.get("primary_demo") != 7:
        add_failure(failures, "expected 7 primary demo rows", publish_counts)
    if publish_counts.get("caveat_demo") != 6:
        add_failure(failures, "expected 6 caveat demo rows", publish_counts)
    if publish_counts.get("qa_regression_only") != 2:
        add_failure(failures, "expected 2 QA regression rows", publish_counts)

    primary_questions = set(summary.get("primary_demo_question_ids", []))
    if primary_questions != {"q_0064", "q_0069"}:
        add_failure(failures, "unexpected primary demo question IDs", sorted(primary_questions))

    actual_presentation_uses = {row.get("presentation_use") for row in lock_rows}
    missing_uses = sorted(EXPECTED_PRESENTATION_USES - actual_presentation_uses)
    if missing_uses:
        add_failure(failures, "missing expected presentation-use categories", missing_uses)

    for row in lock_rows:
        row_id = row.get("confirmation_item_id")
        if row.get("lock_decision") != "locked":
            add_failure(failures, "row lock_decision is not locked", row_id)
        if row.get("lock_status") != EXPECTED_STATUS:
            add_failure(failures, "row lock_status mismatch", row_id)
        if row.get("lock_basis") != EXPECTED_LOCK_BASIS:
            add_failure(failures, "row lock_basis mismatch", row_id)
        if row.get("labels_locked") is not True:
            add_failure(failures, "row labels_locked must be true", row_id)
        if row.get("source_fix_required") is not False:
            add_failure(failures, "row source_fix_required must be false", row_id)
        if row.get("source_action") != "none":
            add_failure(failures, "row source_action is not none", row_id)
        if row.get("assistant_label_verdict") != "label_supported":
            add_failure(failures, "row assistant verdict is not supported", row_id)
        if "[[" not in row.get("highlighted_excerpt", "") or "]]" not in row.get("highlighted_excerpt", ""):
            add_failure(failures, "row highlighted excerpt missing marker", row_id)
        if len(row.get("lock_reason", "")) < 40:
            add_failure(failures, "row lock_reason is too short", row_id)

    required_html_fragments = [
        "Label lock report",
        "Presentation labels are locked",
        "assistant_full_review",
        "Locked label decisions",
        "q_0064",
        "q_0069",
    ]
    for fragment in required_html_fragments:
        if fragment not in html_text:
            add_failure(failures, "html missing required fragment", fragment)
    forbidden_html_fragments = ["human confirmation", "pending human review", "Human-confirm"]
    for fragment in forbidden_html_fragments:
        if fragment.lower() in html_text.lower():
            add_failure(failures, "lock report contains stale human-confirmation wording", fragment)

    validation = {
        "label_lock_decisions_csv_path": str(LOCK_DECISIONS_CSV_PATH),
        "label_lock_decisions_jsonl_path": str(LOCK_DECISIONS_JSONL_PATH),
        "label_lock_summary_path": str(LOCK_SUMMARY_PATH),
        "label_lock_report_html_path": str(LOCK_REPORT_HTML_PATH),
        "selected_annotation_count": len(lock_rows),
        "selected_question_count": len({row["question_id"] for row in lock_rows}),
        "labels_locked": len(failures) == 0,
        "lock_basis": EXPECTED_LOCK_BASIS,
        "ready_for_portfolio_packaging": len(failures) == 0,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
