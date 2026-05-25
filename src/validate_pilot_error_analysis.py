from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"

ERROR_REVIEW_PATH = RESULTS_DIR / "pilot20_baseline_error_review.csv"
ANALYSIS_SUMMARY_PATH = RESULTS_DIR / "pilot20_error_analysis_summary.json"
ANALYSIS_BY_FAMILY_PATH = RESULTS_DIR / "pilot20_error_analysis_by_family.csv"
ANALYSIS_EXAMPLES_PATH = RESULTS_DIR / "pilot20_error_analysis_examples.csv"
VALIDATION_PATH = RESULTS_DIR / "pilot20_error_analysis_validation.json"


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
    for path in [ERROR_REVIEW_PATH, ANALYSIS_SUMMARY_PATH, ANALYSIS_BY_FAMILY_PATH, ANALYSIS_EXAMPLES_PATH]:
        if not path.exists():
            add_failure(failures, "missing file", str(path))

    if failures:
        validation = {"num_failures": len(failures), "failures": failures}
        VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    review_rows = read_csv(ERROR_REVIEW_PATH)
    family_rows = read_csv(ANALYSIS_BY_FAMILY_PATH)
    example_rows = read_csv(ANALYSIS_EXAMPLES_PATH)
    summary = json.loads(ANALYSIS_SUMMARY_PATH.read_text(encoding="utf-8"))

    review_count = len(review_rows)
    unique_annotation_count = len({row["annotation_id"] for row in review_rows})
    false_positive_count = sum(1 for row in review_rows if row["error_type"] == "false_positive")
    false_negative_count = sum(1 for row in review_rows if row["error_type"] == "false_negative")

    if int(summary.get("baseline_error_rows", -1)) != review_count:
        add_failure(failures, "baseline_error_rows mismatch", {"summary": summary.get("baseline_error_rows"), "review": review_count})
    if int(summary.get("unique_annotation_errors", -1)) != unique_annotation_count:
        add_failure(
            failures,
            "unique_annotation_errors mismatch",
            {"summary": summary.get("unique_annotation_errors"), "review": unique_annotation_count},
        )
    if int(summary.get("false_positive_rows", -1)) != false_positive_count:
        add_failure(failures, "false_positive_rows mismatch")
    if int(summary.get("false_negative_rows", -1)) != false_negative_count:
        add_failure(failures, "false_negative_rows mismatch")
    if int(summary.get("family_count", -1)) != len(family_rows):
        add_failure(failures, "family_count mismatch")

    family_total = sum(int(row["baseline_error_rows"]) for row in family_rows)
    if family_total != review_count:
        add_failure(failures, "family rows do not sum to review rows", {"family_total": family_total, "review": review_count})

    families = {row["error_family"] for row in family_rows}
    if not families:
        add_failure(failures, "no families produced")
    for row in family_rows:
        for field in ["short_name", "diagnosis", "next_action", "top_fact_types", "top_question_types"]:
            if not row.get(field):
                add_failure(failures, "empty family field", {"family": row.get("error_family"), "field": field})

    example_families = {row["error_family"] for row in example_rows}
    missing_examples = sorted(families - example_families)
    if missing_examples:
        add_failure(failures, "families without examples", missing_examples)
    for row in example_rows:
        if "[[" not in row["generated_excerpt"] or "]]" not in row["generated_excerpt"]:
            add_failure(failures, "example missing span markers", row["annotation_id"])
        if float(row["severity"]) < 0:
            add_failure(failures, "negative severity", row["annotation_id"])

    if len(summary.get("main_findings", [])) < 3:
        add_failure(failures, "summary needs at least three main findings")
    if "Spilled Energy" not in str(summary.get("recommended_next_step", "")):
        add_failure(failures, "summary missing next detector decision")

    validation = {
        "analysis_summary_path": str(ANALYSIS_SUMMARY_PATH),
        "analysis_by_family_path": str(ANALYSIS_BY_FAMILY_PATH),
        "analysis_examples_path": str(ANALYSIS_EXAMPLES_PATH),
        "baseline_error_rows": review_count,
        "unique_annotation_errors": unique_annotation_count,
        "family_count": len(family_rows),
        "example_count": len(example_rows),
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
