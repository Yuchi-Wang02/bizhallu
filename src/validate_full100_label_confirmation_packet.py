from __future__ import annotations

import csv
import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"
RESULTS_DIR = PROJECT_ROOT / "results"

PACKET_CSV_PATH = REPORTS_DIR / "full100_label_confirmation_packet.csv"
PACKET_JSONL_PATH = REPORTS_DIR / "full100_label_confirmation_packet.jsonl"
PACKET_HTML_PATH = REPORTS_DIR / "full100_label_confirmation_packet.html"
PACKET_SUMMARY_PATH = REPORTS_DIR / "full100_label_confirmation_packet_summary.json"
VALIDATION_PATH = REPORTS_DIR / "full100_label_confirmation_packet_validation.json"
ERROR_EXAMPLES_PATH = RESULTS_DIR / "full100_draft_detector_error_review_examples.csv"

OFFSET_REGRESSION_ANNOTATION_IDS = {
    "ann_full100_draft_q_0063_010",
    "ann_full100_draft_q_0068_008",
    "ann_full100_draft_q_0064_008",
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
    for path in (PACKET_CSV_PATH, PACKET_JSONL_PATH, PACKET_HTML_PATH, PACKET_SUMMARY_PATH, ERROR_EXAMPLES_PATH):
        if not path.exists():
            add_failure(failures, "missing required file", repo_path(path))

    packet_rows = load_jsonl(PACKET_JSONL_PATH) if PACKET_JSONL_PATH.exists() else []
    packet_csv_rows = load_csv(PACKET_CSV_PATH) if PACKET_CSV_PATH.exists() else []
    summary = load_json(PACKET_SUMMARY_PATH) if PACKET_SUMMARY_PATH.exists() else {}
    error_examples = load_csv(ERROR_EXAMPLES_PATH) if ERROR_EXAMPLES_PATH.exists() else []
    html_text = PACKET_HTML_PATH.read_text(encoding="utf-8") if PACKET_HTML_PATH.exists() else ""

    if html_text:
        try:
            StrictEnoughHTMLParser().feed(html_text)
        except Exception as exc:  # pragma: no cover - defensive parser guard
            add_failure(failures, "html parser failed", repr(exc))

    if summary.get("status") != "confirmation_packet_ready_not_locked":
        add_failure(failures, "unexpected summary status", summary.get("status"))
    if summary.get("human_confirmation_required") is not True:
        add_failure(failures, "summary must require human confirmation", summary)
    if summary.get("all_items_confirmation_status") != "pending_human_review":
        add_failure(failures, "summary should remain pending human review", summary.get("all_items_confirmation_status"))

    if len(packet_rows) != len(packet_csv_rows):
        add_failure(failures, "CSV/JSONL row-count mismatch", {"csv": len(packet_csv_rows), "jsonl": len(packet_rows)})
    if summary.get("selected_annotation_count") != len(packet_rows):
        add_failure(
            failures,
            "summary selected_annotation_count mismatch",
            {"summary": summary.get("selected_annotation_count"), "actual": len(packet_rows)},
        )

    example_annotation_ids = {row["annotation_id"] for row in error_examples}
    packet_annotation_ids = {row["annotation_id"] for row in packet_rows}
    missing_error_examples = sorted(example_annotation_ids - packet_annotation_ids)
    if missing_error_examples:
        add_failure(failures, "packet missing error-example annotations", missing_error_examples)
    missing_offset_checks = sorted(OFFSET_REGRESSION_ANNOTATION_IDS - packet_annotation_ids)
    if missing_offset_checks:
        add_failure(failures, "packet missing offset-regression annotations", missing_offset_checks)

    if len(error_examples) != summary.get("source_error_example_row_count"):
        add_failure(
            failures,
            "source error example count mismatch",
            {"summary": summary.get("source_error_example_row_count"), "actual": len(error_examples)},
        )
    if len(packet_rows) < 15:
        add_failure(failures, "packet is unexpectedly small", len(packet_rows))

    for row in packet_rows:
        if row.get("requires_human_confirmation") is not True:
            add_failure(failures, "row does not require human confirmation", row.get("annotation_id"))
        if row.get("confirmation_status") != "pending_human_review":
            add_failure(failures, "row confirmation status is not pending", row.get("annotation_id"))
        if row.get("precheck_status") != "pass":
            add_failure(failures, "row precheck did not pass", row.get("annotation_id"))
        if "[[" not in row.get("highlighted_excerpt", "") or "]]" not in row.get("highlighted_excerpt", ""):
            add_failure(failures, "highlighted excerpt missing marker", row.get("annotation_id"))
        if not row.get("confirmation_checklist"):
            add_failure(failures, "row missing confirmation checklist", row.get("annotation_id"))

    offset_contexts = {row["annotation_id"]: row["highlighted_excerpt"] for row in packet_rows if row["annotation_id"] in OFFSET_REGRESSION_ANNOTATION_IDS}
    bad_offset_fragments = ["585[[3.]]80", "4,728.7[[3.]]", "10,32[[3.]]87"]
    for annotation_id, context in offset_contexts.items():
        if any(fragment in context for fragment in bad_offset_fragments):
            add_failure(failures, "offset regression context still points at currency decimal", {annotation_id: context})
        if "\n[[3.]]" not in context and "  \n[[3.]]" not in context:
            add_failure(failures, "offset regression context does not look like a list marker", {annotation_id: context})

    required_html_fragments = [
        "Presentation-level label confirmation",
        "Pending human review",
        "Selected confirmation items",
        "Detector interpretation",
        "57",
        "15",
    ]
    for fragment in required_html_fragments:
        if fragment not in html_text:
            add_failure(failures, "html missing required fragment", fragment)

    validation = {
        "packet_csv_path": repo_path(PACKET_CSV_PATH),
        "packet_jsonl_path": repo_path(PACKET_JSONL_PATH),
        "packet_html_path": repo_path(PACKET_HTML_PATH),
        "packet_summary_path": repo_path(PACKET_SUMMARY_PATH),
        "selected_annotation_count": len(packet_rows),
        "selected_question_count": len({row["question_id"] for row in packet_rows}),
        "source_error_example_row_count": len(error_examples),
        "ready_for_human_confirmation": len(failures) == 0,
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
