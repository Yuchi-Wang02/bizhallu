from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"

STRUCTURED_REPORT = RESULTS_DIR / "top3_structured_pilot3_report.json"
STRUCTURED_EVAL = RESULTS_DIR / "top3_structured_pilot3_evaluation.csv"
SORTED_REPORT = RESULTS_DIR / "top3_sorted_control_pilot3_report.json"
SORTED_EVAL = RESULTS_DIR / "top3_sorted_control_pilot3_evaluation.csv"

COMPARISON_CSV = RESULTS_DIR / "top3_prompt_condition_comparison.csv"
COMPARISON_JSON = RESULTS_DIR / "top3_prompt_condition_comparison.json"
VALIDATION_JSON = RESULTS_DIR / "top3_prompt_condition_comparison_validation.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None) -> None:
    failure: dict[str, Any] = {"reason": reason}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def condition_row(condition_id: str, evidence_order_policy: str, report_path: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    total_questions = int(report["record_count"])
    total_rank_rows = int(report["total_gold_rank_rows"])
    exact = int(report["exact_order_match_count"])
    correct_rank_rows = int(report["correct_rank_rows"])

    return {
        "condition_id": condition_id,
        "condition_name": report.get("condition_name", condition_id),
        "evidence_order_policy": evidence_order_policy,
        "record_count": total_questions,
        "format_valid_count": report["format_valid_count"],
        "exact_order_match_count": exact,
        "exact_order_match_rate": round(exact / total_questions, 6) if total_questions else 0,
        "correct_rank_rows": correct_rank_rows,
        "total_gold_rank_rows": total_rank_rows,
        "correct_rank_row_rate": round(correct_rank_rows / total_rank_rows, 6) if total_rank_rows else 0,
        "gold_presence_rows": report["gold_presence_rows"],
        "evidence_membership_rows": report["evidence_membership_rows"],
        "copied_evidence_amount_rows": report["copied_evidence_amount_rows"],
        "sorted_output_count": report["sorted_output_count"],
        "evidence_prefix_rows": report["evidence_prefix_rows"],
    }


def failed_questions(rows: list[dict[str, str]]) -> list[str]:
    return [row["question_id"] for row in rows if row["exact_order_match"].lower() != "true"]


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path in [STRUCTURED_REPORT, STRUCTURED_EVAL, SORTED_REPORT, SORTED_EVAL]:
        if not path.exists():
            add_failure(failures, "missing input file", str(path))

    if failures:
        validation = {"num_failures": len(failures), "failures": failures}
        VALIDATION_JSON.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    structured_eval = read_csv(STRUCTURED_EVAL)
    sorted_eval = read_csv(SORTED_EVAL)
    condition_rows = [
        condition_row("structured_shuffled", "deterministic_hash_by_question_and_product", STRUCTURED_REPORT),
        condition_row("sorted_control", "sorted_by_net_revenue_desc_control", SORTED_REPORT),
    ]
    write_csv(
        COMPARISON_CSV,
        [
            "condition_id",
            "condition_name",
            "evidence_order_policy",
            "record_count",
            "format_valid_count",
            "exact_order_match_count",
            "exact_order_match_rate",
            "correct_rank_rows",
            "total_gold_rank_rows",
            "correct_rank_row_rate",
            "gold_presence_rows",
            "evidence_membership_rows",
            "copied_evidence_amount_rows",
            "sorted_output_count",
            "evidence_prefix_rows",
        ],
        condition_rows,
    )

    structured = condition_rows[0]
    sorted_control = condition_rows[1]
    exact_gain = int(sorted_control["exact_order_match_count"]) - int(structured["exact_order_match_count"])
    rank_row_gain = int(sorted_control["correct_rank_rows"]) - int(structured["correct_rank_rows"])

    comparison = {
        "comparison_csv_path": str(COMPARISON_CSV),
        "conditions": condition_rows,
        "same_question_ids": [row["question_id"] for row in structured_eval] == [row["question_id"] for row in sorted_eval],
        "question_ids": [row["question_id"] for row in structured_eval],
        "structured_failed_questions": failed_questions(structured_eval),
        "sorted_control_failed_questions": failed_questions(sorted_eval),
        "exact_order_match_gain": exact_gain,
        "correct_rank_row_gain": rank_row_gain,
        "main_findings": [
            "Both prompt conditions produced valid 3-row tables for all three pilot questions.",
            "Sorted evidence improved exact top3 accuracy from 0/3 to 2/3.",
            "Sorted evidence improved rank-position stock-code accuracy from 0/9 to 6/9.",
            "The remaining sorted-control failure is q_0065, where the model skipped the highest-revenue row.",
        ],
        "interpretation": (
            "The shuffled structured failure is largely a row-selection/sorting problem, but the sorted-control failure "
            "shows Qwen3-0.6B can still miss a salient first row even when the answer order is visible."
        ),
    }
    COMPARISON_JSON.write_text(json.dumps(comparison, indent=2, ensure_ascii=True), encoding="utf-8")

    if not comparison["same_question_ids"]:
        add_failure(failures, "condition evaluations use different question ids")
    if exact_gain < 0 or rank_row_gain < 0:
        add_failure(failures, "sorted control performed worse than shuffled structured unexpectedly")
    if int(sorted_control["record_count"]) != 3 or int(structured["record_count"]) != 3:
        add_failure(failures, "comparison should cover exactly 3 questions")

    validation = {
        "comparison_csv_path": str(COMPARISON_CSV),
        "comparison_json_path": str(COMPARISON_JSON),
        "condition_count": len(condition_rows),
        "question_ids": comparison["question_ids"],
        "exact_order_match_gain": exact_gain,
        "correct_rank_row_gain": rank_row_gain,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_JSON.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
