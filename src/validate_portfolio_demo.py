from __future__ import annotations

import csv
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RESULTS_DIR = PROJECT_ROOT / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"

HTML_PATH = REPORTS_DIR / "bizhallu_portfolio_demo.html"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_summary.json"
VALIDATION_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_validation.json"

LOCK_DECISIONS_PATH = REPORTS_DIR / "full100_label_lock_decisions.jsonl"
LOCK_SUMMARY_PATH = REPORTS_DIR / "full100_label_lock_summary.json"
PACKET_PATH = REPORTS_DIR / "full100_label_confirmation_packet.jsonl"
REVIEW_PATH = OUTPUT_DIR / "full100_review.jsonl"
DETECTOR_SCORES_PATH = RESULTS_DIR / "full100_draft_detector_scores.csv"

PRIMARY_QUESTION_IDS = ["q_0064", "q_0069"]
EXPECTED_LOCK_STATUS = "presentation_labels_locked"
EXPECTED_LOCK_BASIS = "assistant_full_review"
EXPECTED_PRIMARY_SPAN_COUNT = 7


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


def outcome_text(label: str, predicted_positive: bool) -> str:
    is_positive = label != "correct_key_fact"
    if is_positive and predicted_positive:
        return "caught"
    if is_positive and not predicted_positive:
        return "missed"
    if not is_positive and predicted_positive:
        return "false alarm"
    return "cleared"


def approx_equal(left: Any, right: Any, tolerance: float = 1e-9) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def main() -> None:
    failures: list[dict[str, Any]] = []
    required_paths = [
        HTML_PATH,
        SUMMARY_PATH,
        LOCK_DECISIONS_PATH,
        LOCK_SUMMARY_PATH,
        PACKET_PATH,
        REVIEW_PATH,
        DETECTOR_SCORES_PATH,
    ]
    for path in required_paths:
        if not path.exists():
            add_failure(failures, "missing required file", repo_path(path))

    html_text = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""
    if html_text:
        try:
            StrictEnoughHTMLParser().feed(html_text)
        except Exception as exc:  # pragma: no cover - defensive parser guard
            add_failure(failures, "html parser failed", repr(exc))

    summary = load_json(SUMMARY_PATH) if SUMMARY_PATH.exists() else {}
    lock_rows = load_jsonl(LOCK_DECISIONS_PATH) if LOCK_DECISIONS_PATH.exists() else []
    lock_summary = load_json(LOCK_SUMMARY_PATH) if LOCK_SUMMARY_PATH.exists() else {}
    packet_rows = load_jsonl(PACKET_PATH) if PACKET_PATH.exists() else []
    review_rows = load_jsonl(REVIEW_PATH) if REVIEW_PATH.exists() else []
    score_rows = load_csv(DETECTOR_SCORES_PATH) if DETECTOR_SCORES_PATH.exists() else []

    packet_by_annotation = {row["annotation_id"]: row for row in packet_rows}
    review_by_question = {row["question_id"]: row for row in review_rows}
    score_by_annotation = {row["annotation_id"]: row for row in score_rows}

    primary_rows = [
        row
        for row in lock_rows
        if row.get("publish_use") == "primary_demo" and row.get("question_id") in PRIMARY_QUESTION_IDS
    ]
    primary_question_ids = sorted({row.get("question_id") for row in primary_rows})
    label_counts = dict(sorted(Counter(row.get("label") for row in primary_rows).items()))

    if summary.get("status") != "portfolio_demo_ready":
        add_failure(failures, "unexpected portfolio status", summary.get("status"))
    if summary.get("case_count") != len(PRIMARY_QUESTION_IDS):
        add_failure(failures, "unexpected case count", summary.get("case_count"))
    if summary.get("locked_primary_span_count") != EXPECTED_PRIMARY_SPAN_COUNT:
        add_failure(failures, "unexpected locked primary span count", summary.get("locked_primary_span_count"))
    if summary.get("primary_question_ids") != PRIMARY_QUESTION_IDS:
        add_failure(failures, "summary primary question IDs mismatch", summary.get("primary_question_ids"))
    if primary_question_ids != PRIMARY_QUESTION_IDS:
        add_failure(failures, "source primary question IDs mismatch", primary_question_ids)
    if len(primary_rows) != EXPECTED_PRIMARY_SPAN_COUNT:
        add_failure(failures, "source primary row count mismatch", len(primary_rows))
    if summary.get("by_label") != label_counts:
        add_failure(failures, "label count mismatch", {"summary": summary.get("by_label"), "source": label_counts})

    if summary.get("label_lock_status") != EXPECTED_LOCK_STATUS:
        add_failure(failures, "summary label lock status mismatch", summary.get("label_lock_status"))
    if summary.get("label_lock_basis") != EXPECTED_LOCK_BASIS:
        add_failure(failures, "summary label lock basis mismatch", summary.get("label_lock_basis"))
    if summary.get("labels_locked") is not True:
        add_failure(failures, "summary labels_locked must be true", summary.get("labels_locked"))
    if summary.get("human_confirmation_required") is not False:
        add_failure(failures, "summary human_confirmation_required must be false", summary.get("human_confirmation_required"))
    if lock_summary.get("status") != EXPECTED_LOCK_STATUS:
        add_failure(failures, "source lock summary status mismatch", lock_summary.get("status"))
    if lock_summary.get("lock_basis") != EXPECTED_LOCK_BASIS:
        add_failure(failures, "source lock summary basis mismatch", lock_summary.get("lock_basis"))

    simple_threshold = float(summary.get("simple_threshold", "nan"))
    entropy_threshold = float(summary.get("entropy_threshold", "nan"))
    energy_threshold = float(summary.get("energy_threshold", "nan"))
    simple_outcomes: Counter[str] = Counter()
    entropy_outcomes: Counter[str] = Counter()
    energy_outcomes: Counter[str] = Counter()

    for row in primary_rows:
        annotation_id = row["annotation_id"]
        question_id = row["question_id"]
        if row.get("lock_status") != EXPECTED_LOCK_STATUS or row.get("lock_basis") != EXPECTED_LOCK_BASIS:
            add_failure(failures, "primary source row is not locked as expected", annotation_id)
        if annotation_id not in packet_by_annotation:
            add_failure(failures, "missing packet row for primary span", annotation_id)
            continue
        if annotation_id not in score_by_annotation:
            add_failure(failures, "missing score row for primary span", annotation_id)
            continue
        if question_id not in review_by_question:
            add_failure(failures, "missing review row for primary question", question_id)
            continue

        packet_row = packet_by_annotation[annotation_id]
        generated_text = review_by_question[question_id]["generation"]["generated_text"]
        start = int(packet_row["span_start_char"])
        end = int(packet_row["span_end_char"])
        actual_span_text = generated_text[start:end] if 0 <= start <= end <= len(generated_text) else None
        if actual_span_text != row["span_text"]:
            add_failure(
                failures,
                "primary span offset text mismatch",
                {"annotation_id": annotation_id, "expected": row["span_text"], "actual": actual_span_text},
            )

        score_row = score_by_annotation[annotation_id]
        simple_score = float(score_row["one_minus_min_top2_margin"])
        entropy_score = float(score_row["mean_token_entropy"])
        energy_score = float(score_row["mean_spilled_probability_mass_after_top2"])
        simple_outcomes[outcome_text(row["label"], simple_score >= simple_threshold)] += 1
        entropy_outcomes[outcome_text(row["label"], entropy_score >= entropy_threshold)] += 1
        energy_outcomes[outcome_text(row["label"], energy_score >= energy_threshold)] += 1

    if summary.get("simple_outcomes") != dict(sorted(simple_outcomes.items())):
        add_failure(failures, "simple outcome counts mismatch", summary.get("simple_outcomes"))
    if summary.get("entropy_outcomes") != dict(sorted(entropy_outcomes.items())):
        add_failure(failures, "entropy outcome counts mismatch", summary.get("entropy_outcomes"))
    if summary.get("energy_outcomes") != dict(sorted(energy_outcomes.items())):
        add_failure(failures, "energy outcome counts mismatch", summary.get("energy_outcomes"))

    if not approx_equal(summary.get("best_test_auprc"), 0.835073):
        add_failure(failures, "best test AUPRC drifted", summary.get("best_test_auprc"))
    if not approx_equal(summary.get("best_test_f1"), 0.779412):
        add_failure(failures, "best test F1 drifted", summary.get("best_test_f1"))

    required_html_fragments = [
        "BizHallu Portfolio Demo",
        "q_0064",
        "q_0069",
        "Presentation labels locked by assistant_full_review",
        "one_minus_min_top2_margin",
        "mean_token_entropy",
        "mean_spilled_probability_mass_after_top2",
        "GBP 4,173.18",
        "GBP 9315.03",
        "false alarm",
        "missed",
        "span-level",
    ]
    html_lower = html_text.lower()
    for fragment in required_html_fragments:
        if fragment.lower() not in html_lower:
            add_failure(failures, "html missing required fragment", fragment)

    stale_html_fragments = [
        "pending human review",
        "requires human confirmation",
        "presentation-level confirmation required",
    ]
    for fragment in stale_html_fragments:
        if fragment in html_lower:
            add_failure(failures, "html contains stale confirmation wording", fragment)

    validation = {
        "html_path": repo_path(HTML_PATH),
        "summary_path": repo_path(SUMMARY_PATH),
        "source_label_lock_summary_path": repo_path(LOCK_SUMMARY_PATH),
        "case_count": summary.get("case_count"),
        "primary_question_ids": summary.get("primary_question_ids"),
        "locked_primary_span_count": summary.get("locked_primary_span_count"),
        "ready_for_portfolio_demo": len(failures) == 0,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
