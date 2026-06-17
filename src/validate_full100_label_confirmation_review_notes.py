from __future__ import annotations

import csv
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"

PACKET_JSONL_PATH = REPORTS_DIR / "full100_label_confirmation_packet.jsonl"
NOTES_CSV_PATH = REPORTS_DIR / "full100_label_confirmation_review_notes.csv"
NOTES_JSONL_PATH = REPORTS_DIR / "full100_label_confirmation_review_notes.jsonl"
NOTES_HTML_PATH = REPORTS_DIR / "full100_label_confirmation_review_notes.html"
NOTES_SUMMARY_PATH = REPORTS_DIR / "full100_label_confirmation_review_notes_summary.json"
VALIDATION_PATH = REPORTS_DIR / "full100_label_confirmation_review_notes_validation.json"


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
    for path in (PACKET_JSONL_PATH, NOTES_CSV_PATH, NOTES_JSONL_PATH, NOTES_HTML_PATH, NOTES_SUMMARY_PATH):
        if not path.exists():
            add_failure(failures, "missing required file", repo_path(path))

    packet_rows = load_jsonl(PACKET_JSONL_PATH) if PACKET_JSONL_PATH.exists() else []
    notes_rows = load_jsonl(NOTES_JSONL_PATH) if NOTES_JSONL_PATH.exists() else []
    notes_csv_rows = load_csv(NOTES_CSV_PATH) if NOTES_CSV_PATH.exists() else []
    summary = load_json(NOTES_SUMMARY_PATH) if NOTES_SUMMARY_PATH.exists() else {}
    html_text = NOTES_HTML_PATH.read_text(encoding="utf-8") if NOTES_HTML_PATH.exists() else ""

    if html_text:
        try:
            StrictEnoughHTMLParser().feed(html_text)
        except Exception as exc:  # pragma: no cover - defensive parser guard
            add_failure(failures, "html parser failed", repr(exc))

    packet_ids = {row["confirmation_item_id"] for row in packet_rows}
    notes_ids = {row["confirmation_item_id"] for row in notes_rows}
    if packet_ids != notes_ids:
        add_failure(failures, "review notes do not cover the same confirmation IDs as packet", {
            "missing": sorted(packet_ids - notes_ids),
            "extra": sorted(notes_ids - packet_ids),
        })

    if len(notes_rows) != len(notes_csv_rows):
        add_failure(failures, "CSV/JSONL row-count mismatch", {"csv": len(notes_csv_rows), "jsonl": len(notes_rows)})
    if summary.get("status") != "assistant_review_complete_not_human_locked":
        add_failure(failures, "unexpected summary status", summary.get("status"))
    if summary.get("selected_annotation_count") != len(notes_rows):
        add_failure(failures, "summary selected_annotation_count mismatch", summary.get("selected_annotation_count"))
    if summary.get("source_fix_required_count") != 0:
        add_failure(failures, "source fixes are required before presentation", summary.get("source_fix_required_count"))
    if summary.get("labels_locked") is not False:
        add_failure(failures, "labels must not be locked by assistant review", summary.get("labels_locked"))
    if summary.get("human_confirmation_required") is not True:
        add_failure(failures, "summary must still require human confirmation", summary.get("human_confirmation_required"))

    high_priority_count = sum(1 for row in notes_rows if row.get("demo_priority") == "high")
    if high_priority_count < 7:
        add_failure(failures, "too few high-priority demo examples", high_priority_count)

    expected_uses = {
        "span_level_caveat",
        "paired_contrast_example",
        "offset_check_only",
        "strong_false_negative_example",
    }
    actual_uses = {row.get("presentation_use") for row in notes_rows}
    missing_uses = sorted(expected_uses - actual_uses)
    if missing_uses:
        add_failure(failures, "missing expected presentation-use categories", missing_uses)

    for row in notes_rows:
        if row.get("assistant_label_verdict") != "label_supported":
            add_failure(failures, "row label is not supported by assistant review", row.get("confirmation_item_id"))
        if row.get("source_action") != "none":
            add_failure(failures, "row requires source action", row.get("confirmation_item_id"))
        if row.get("human_confirmation_required") is not True:
            add_failure(failures, "row must still require human confirmation", row.get("confirmation_item_id"))
        if row.get("labels_locked") is not False:
            add_failure(failures, "row labels_locked must be false", row.get("confirmation_item_id"))
        if "[[" not in row.get("highlighted_excerpt", "") or "]]" not in row.get("highlighted_excerpt", ""):
            add_failure(failures, "row highlighted excerpt missing marker", row.get("confirmation_item_id"))
        if len(row.get("review_note", "")) < 50:
            add_failure(failures, "row review note is too short", row.get("confirmation_item_id"))

    required_html_fragments = [
        "Assistant review notes",
        "Labels look supported",
        "span-level",
        "Source fixes",
        "Per-item review notes",
    ]
    for fragment in required_html_fragments:
        if fragment not in html_text:
            add_failure(failures, "html missing required fragment", fragment)

    validation = {
        "review_notes_csv_path": repo_path(NOTES_CSV_PATH),
        "review_notes_jsonl_path": repo_path(NOTES_JSONL_PATH),
        "review_notes_html_path": repo_path(NOTES_HTML_PATH),
        "review_notes_summary_path": repo_path(NOTES_SUMMARY_PATH),
        "selected_annotation_count": len(notes_rows),
        "selected_question_count": len({row["question_id"] for row in notes_rows}),
        "assistant_review_complete": len(failures) == 0,
        "human_confirmation_required": True,
        "labels_locked": False,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
