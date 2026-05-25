from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"

DEFAULT_ERROR_REVIEW_PATH = RESULTS_DIR / "full100_draft_detector_error_review.csv"
DEFAULT_BY_BASELINE_PATH = RESULTS_DIR / "full100_draft_detector_error_review_by_baseline.csv"
DEFAULT_BY_FACT_TYPE_PATH = RESULTS_DIR / "full100_draft_detector_error_review_by_fact_type.csv"
DEFAULT_BY_QUESTION_TYPE_PATH = RESULTS_DIR / "full100_draft_detector_error_review_by_question_type.csv"
DEFAULT_EXAMPLES_PATH = RESULTS_DIR / "full100_draft_detector_error_review_examples.csv"
DEFAULT_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_error_review_report.json"
DEFAULT_VALIDATION_PATH = RESULTS_DIR / "full100_draft_detector_error_review_validation.json"

EXPECTED_SELECTED = {
    ("simple", "simple_best_test_auprc", "one_minus_min_top2_margin"),
    ("energy", "energy_best_test_f1", "mean_spilled_probability_mass_after_top2"),
}
EXPECTED_ERROR_TYPES = {"false_positive", "false_negative"}


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None) -> None:
    failure: dict[str, Any] = {"reason": reason}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--error-review-path", default=str(DEFAULT_ERROR_REVIEW_PATH))
    parser.add_argument("--by-baseline-path", default=str(DEFAULT_BY_BASELINE_PATH))
    parser.add_argument("--by-fact-type-path", default=str(DEFAULT_BY_FACT_TYPE_PATH))
    parser.add_argument("--by-question-type-path", default=str(DEFAULT_BY_QUESTION_TYPE_PATH))
    parser.add_argument("--examples-path", default=str(DEFAULT_EXAMPLES_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--validation-path", default=str(DEFAULT_VALIDATION_PATH))
    args = parser.parse_args()

    error_review_path = resolve_project_path(args.error_review_path)
    by_baseline_path = resolve_project_path(args.by_baseline_path)
    by_fact_type_path = resolve_project_path(args.by_fact_type_path)
    by_question_type_path = resolve_project_path(args.by_question_type_path)
    examples_path = resolve_project_path(args.examples_path)
    report_path = resolve_project_path(args.report_path)
    validation_path = resolve_project_path(args.validation_path)

    failures: list[dict[str, Any]] = []
    for path in [error_review_path, by_baseline_path, by_fact_type_path, by_question_type_path, examples_path, report_path]:
        if not path.exists():
            add_failure(failures, "missing required file", str(path))

    if failures:
        validation = {"num_failures": len(failures), "failures": failures}
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    rows = read_csv(error_review_path)
    by_baseline_rows = read_csv(by_baseline_path)
    by_fact_type_rows = read_csv(by_fact_type_path)
    by_question_type_rows = read_csv(by_question_type_path)
    example_rows = read_csv(examples_path)
    report = load_json(report_path)

    selected = {(row["family"], row["baseline_role"], row["baseline"]) for row in by_baseline_rows}
    if selected != EXPECTED_SELECTED:
        add_failure(failures, "unexpected selected baseline set", sorted(selected))

    if {row["split"] for row in rows} != {"test"}:
        add_failure(failures, "error review must be test-only", sorted({row["split"] for row in rows}))

    error_types = {row["error_type"] for row in rows}
    if error_types != EXPECTED_ERROR_TYPES:
        add_failure(failures, "unexpected error type set", sorted(error_types))

    by_baseline_counts: dict[str, dict[str, int]] = {}
    for row in rows:
        key = row["baseline"]
        by_baseline_counts.setdefault(key, {"false_positive": 0, "false_negative": 0})
        by_baseline_counts[key][row["error_type"]] += 1

        score = float(row["score"])
        threshold = float(row["threshold"])
        if row["error_type"] == "false_positive":
            if not (row["actual_class"] == "negative" and row["predicted_class"] == "positive" and score >= threshold):
                add_failure(failures, "invalid false positive row", row["annotation_id"])
            if float(row["score_margin"]) < 0:
                add_failure(failures, "false positive has negative score margin", row["annotation_id"])
        if row["error_type"] == "false_negative":
            if not (row["actual_class"] == "positive" and row["predicted_class"] == "negative" and score < threshold):
                add_failure(failures, "invalid false negative row", row["annotation_id"])
            if float(row["score_margin"]) >= 0:
                add_failure(failures, "false negative has non-negative score margin", row["annotation_id"])
        if "[[" not in row["generated_excerpt"] or "]]" not in row["generated_excerpt"]:
            add_failure(failures, "generated excerpt missing span markers", row["annotation_id"])
        for field in ["question", "gold_short_answer", "annotation_reason", "gold_reference", "generated_text", "evidence_table_markdown"]:
            if not row.get(field):
                add_failure(failures, "missing review context field", {"annotation_id": row["annotation_id"], "field": field})

    for row in by_baseline_rows:
        baseline = row["baseline"]
        expected = {
            "false_positive": int(row["false_positive_count"]),
            "false_negative": int(row["false_negative_count"]),
        }
        if by_baseline_counts.get(baseline) != expected:
            add_failure(
                failures,
                "by-baseline count mismatch",
                {"baseline": baseline, "csv": by_baseline_counts.get(baseline), "summary": expected},
            )
        if int(row["test_fp"]) != int(row["false_positive_count"]) or int(row["test_fn"]) != int(row["false_negative_count"]):
            add_failure(failures, "baseline FP/FN does not match metric confusion", row)

    fact_type_sum = sum(int(row["count"]) for row in by_fact_type_rows)
    question_type_sum = sum(int(row["count"]) for row in by_question_type_rows)
    if fact_type_sum != len(rows):
        add_failure(failures, "fact-type summary count mismatch", {"summary": fact_type_sum, "rows": len(rows)})
    if question_type_sum != len(rows):
        add_failure(failures, "question-type summary count mismatch", {"summary": question_type_sum, "rows": len(rows)})

    example_keys = {(row["baseline"], row["error_type"], row["annotation_id"]) for row in example_rows}
    row_keys = {(row["baseline"], row["error_type"], row["annotation_id"]) for row in rows}
    if not example_keys.issubset(row_keys):
        add_failure(failures, "example rows are not subset of error review rows")
    if len(example_rows) > 20:
        add_failure(failures, "too many example rows", len(example_rows))

    if report.get("ready_for_error_pattern_review") is not True:
        add_failure(failures, "report is not ready_for_error_pattern_review")
    if report.get("num_failures") != 0:
        add_failure(failures, "report contains failures", report.get("failures"))
    if report.get("review_scope") != "heldout_test_split_only":
        add_failure(failures, "unexpected review scope", report.get("review_scope"))
    if report.get("error_row_count") != len(rows):
        add_failure(failures, "report error row count mismatch", {"report": report.get("error_row_count"), "actual": len(rows)})

    validation = {
        "error_review_path": str(error_review_path),
        "by_baseline_path": str(by_baseline_path),
        "by_fact_type_path": str(by_fact_type_path),
        "by_question_type_path": str(by_question_type_path),
        "examples_path": str(examples_path),
        "report_path": str(report_path),
        "error_row_count": len(rows),
        "by_baseline_counts": by_baseline_counts,
        "fact_type_group_row_count": len(by_fact_type_rows),
        "question_type_group_row_count": len(by_question_type_rows),
        "example_row_count": len(example_rows),
        "selected_baseline_count": len(selected),
        "ready_for_error_pattern_review": len(failures) == 0,
        "num_failures": len(failures),
        "failures": failures,
    }
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
