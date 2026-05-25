from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"

DEFAULT_COMPARISON_PATH = RESULTS_DIR / "full100_draft_detector_family_comparison.csv"
DEFAULT_SUMMARY_PATH = RESULTS_DIR / "full100_draft_detector_family_summary.csv"
DEFAULT_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_family_comparison_report.json"
DEFAULT_VALIDATION_PATH = RESULTS_DIR / "full100_draft_detector_family_comparison_validation.json"

METRIC_FIELDS = [
    "dev_f1",
    "dev_precision",
    "dev_recall",
    "dev_specificity",
    "test_auprc",
    "test_auroc",
    "test_f1",
    "test_precision",
    "test_recall",
    "test_specificity",
    "test_accuracy",
]


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


def best_row(rows: list[dict[str, str]], metric: str) -> dict[str, str]:
    return max(rows, key=lambda row: (float(row[metric]), float(row["test_f1"]), float(row["test_auprc"])))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comparison-path", default=str(DEFAULT_COMPARISON_PATH))
    parser.add_argument("--summary-path", default=str(DEFAULT_SUMMARY_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--validation-path", default=str(DEFAULT_VALIDATION_PATH))
    parser.add_argument("--expected-row-count", type=int, default=12)
    parser.add_argument("--expected-summary-row-count", type=int, default=2)
    args = parser.parse_args()

    comparison_path = resolve_project_path(args.comparison_path)
    summary_path = resolve_project_path(args.summary_path)
    report_path = resolve_project_path(args.report_path)
    validation_path = resolve_project_path(args.validation_path)

    failures: list[dict[str, Any]] = []
    for path in [comparison_path, summary_path, report_path]:
        if not path.exists():
            add_failure(failures, "missing required file", str(path))

    if failures:
        validation = {"num_failures": len(failures), "failures": failures}
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    rows = read_csv(comparison_path)
    summary_rows = read_csv(summary_path)
    report = load_json(report_path)

    if len(rows) != args.expected_row_count:
        add_failure(failures, "comparison row count mismatch", {"actual": len(rows), "expected": args.expected_row_count})
    if len(summary_rows) != args.expected_summary_row_count:
        add_failure(
            failures,
            "summary row count mismatch",
            {"actual": len(summary_rows), "expected": args.expected_summary_row_count},
        )

    family_counts = Counter(row["family"] for row in rows)
    if family_counts != {"simple": 5, "energy": 7}:
        add_failure(failures, "family counts mismatch", dict(family_counts))

    duplicate_keys = [
        key
        for key, count in Counter((row["family"], row["baseline"]) for row in rows).items()
        if count > 1
    ]
    if duplicate_keys:
        add_failure(failures, "duplicate family/baseline rows", duplicate_keys)

    for row in rows:
        if row["threshold_source_split"] != "dev":
            add_failure(failures, "threshold source is not dev", row)
        if row["selection_policy"] != "threshold_selected_on_dev_split_max_f1":
            add_failure(failures, "unexpected selection policy", row)
        if row["all_positive_like"] not in {"true", "false"}:
            add_failure(failures, "invalid all_positive_like flag", row)
        for field in METRIC_FIELDS:
            value = float(row[field])
            if not 0.0 <= value <= 1.0:
                add_failure(failures, "metric outside [0, 1]", {"field": field, "value": value, "row": row})
        for field in ["test_tp", "test_fp", "test_tn", "test_fn", "test_positive_count", "test_negative_count"]:
            if int(float(row[field])) < 0:
                add_failure(failures, "negative count", {"field": field, "row": row})
        confusion_total = int(float(row["test_tp"])) + int(float(row["test_fp"])) + int(float(row["test_tn"])) + int(float(row["test_fn"]))
        expected_total = int(float(row["test_positive_count"])) + int(float(row["test_negative_count"]))
        if confusion_total != expected_total:
            add_failure(failures, "test confusion total mismatch", row)

    if rows:
        best_by_auprc = best_row(rows, "test_auprc")
        best_by_f1 = best_row(rows, "test_f1")
        if report.get("best_overall_by_test_auprc", {}).get("baseline") != best_by_auprc["baseline"]:
            add_failure(failures, "report best_overall_by_test_auprc mismatch")
        if report.get("best_overall_by_test_f1", {}).get("baseline") != best_by_f1["baseline"]:
            add_failure(failures, "report best_overall_by_test_f1 mismatch")

    if report.get("ready_for_interpretation_review") is not True:
        add_failure(failures, "report is not ready_for_interpretation_review")
    if report.get("num_failures") != 0:
        add_failure(failures, "report contains failures", report.get("failures"))
    if report.get("comparison_row_count") != len(rows):
        add_failure(failures, "report comparison_row_count mismatch", {"report": report.get("comparison_row_count"), "actual": len(rows)})
    if report.get("summary_row_count") != len(summary_rows):
        add_failure(failures, "report summary_row_count mismatch", {"report": report.get("summary_row_count"), "actual": len(summary_rows)})

    validation = {
        "comparison_path": str(comparison_path),
        "summary_path": str(summary_path),
        "report_path": str(report_path),
        "row_count": len(rows),
        "summary_row_count": len(summary_rows),
        "family_counts": dict(sorted(family_counts.items())),
        "all_positive_like_count": sum(row["all_positive_like"] == "true" for row in rows),
        "best_overall_by_test_auprc": report.get("best_overall_by_test_auprc"),
        "best_overall_by_test_f1": report.get("best_overall_by_test_f1"),
        "ready_for_interpretation_review": len(failures) == 0,
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
