from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"

ERROR_REVIEW_PATH = RESULTS_DIR / "pilot20_baseline_error_review.csv"
ERROR_SUMMARY_PATH = RESULTS_DIR / "pilot20_baseline_error_summary.json"
VALIDATION_PATH = RESULTS_DIR / "pilot20_baseline_error_review_validation.json"

EXPECTED_ERROR_TYPES = {"false_positive", "false_negative"}
EXPECTED_BASELINES = {"max_token_entropy", "one_minus_min_top2_margin"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None) -> None:
    failure: dict[str, Any] = {"reason": reason}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path in [ERROR_REVIEW_PATH, ERROR_SUMMARY_PATH]:
        if not path.exists():
            add_failure(failures, "missing error review file", str(path))

    if failures:
        validation = {"num_failures": len(failures), "failures": failures}
        VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    rows = read_csv(ERROR_REVIEW_PATH)
    summary = json.loads(ERROR_SUMMARY_PATH.read_text(encoding="utf-8"))

    baselines = {row["baseline"] for row in rows}
    if baselines != EXPECTED_BASELINES:
        add_failure(failures, "unexpected baseline set", sorted(baselines))

    error_types = {row["error_type"] for row in rows}
    if error_types != EXPECTED_ERROR_TYPES:
        add_failure(failures, "unexpected error type set", sorted(error_types))

    if len(rows) != int(summary.get("error_row_count", -1)):
        add_failure(failures, "row count mismatch with summary", {"csv": len(rows), "summary": summary.get("error_row_count")})

    by_baseline: dict[str, dict[str, int]] = {}
    for row in rows:
        baseline = row["baseline"]
        error_type = row["error_type"]
        by_baseline.setdefault(baseline, {"false_positive": 0, "false_negative": 0})
        by_baseline[baseline][error_type] += 1

        score = float(row["score"])
        threshold = float(row["threshold"])
        actual = row["actual_class"]
        predicted = row["predicted_class"]
        if row["error_type"] == "false_positive" and not (actual == "negative" and predicted == "positive" and score >= threshold):
            add_failure(failures, "invalid false positive row", row["annotation_id"])
        if row["error_type"] == "false_negative" and not (actual == "positive" and predicted == "negative" and score < threshold):
            add_failure(failures, "invalid false negative row", row["annotation_id"])
        if "[[" not in row["generated_excerpt"] or "]]" not in row["generated_excerpt"]:
            add_failure(failures, "generated excerpt missing span markers", row["annotation_id"])
        for required in ["question", "gold_short_answer", "annotation_reason", "gold_reference", "span_text"]:
            if not row.get(required):
                add_failure(failures, "missing context field", {"annotation_id": row["annotation_id"], "field": required})

    summary_counts = summary.get("error_counts_by_baseline", {})
    for baseline, counts in by_baseline.items():
        expected = summary_counts.get(baseline)
        if expected != counts:
            add_failure(failures, "summary baseline count mismatch", {"baseline": baseline, "csv": counts, "summary": expected})

    if "pilot-only" not in str(summary.get("interpretation", "")):
        add_failure(failures, "summary missing pilot-only caveat")

    validation = {
        "error_review_path": str(ERROR_REVIEW_PATH),
        "error_summary_path": str(ERROR_SUMMARY_PATH),
        "error_row_count": len(rows),
        "baseline_count": len(baselines),
        "error_counts_by_baseline": by_baseline,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
