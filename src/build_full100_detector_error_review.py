from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
ANNOTATION_DIR = PROJECT_ROOT / "data" / "annotations"

DEFAULT_SCORES_PATH = RESULTS_DIR / "full100_draft_detector_scores.csv"
DEFAULT_COMPARISON_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_family_comparison_report.json"
DEFAULT_ANNOTATIONS_PATH = ANNOTATION_DIR / "span_annotations_full100_draft.jsonl"
DEFAULT_GENERATIONS_PATH = OUTPUT_DIR / "qwen_full100_generations.jsonl"
DEFAULT_REVIEW_PATH = OUTPUT_DIR / "full100_review.jsonl"
DEFAULT_ERROR_REVIEW_PATH = RESULTS_DIR / "full100_draft_detector_error_review.csv"
DEFAULT_BY_BASELINE_PATH = RESULTS_DIR / "full100_draft_detector_error_review_by_baseline.csv"
DEFAULT_BY_FACT_TYPE_PATH = RESULTS_DIR / "full100_draft_detector_error_review_by_fact_type.csv"
DEFAULT_BY_QUESTION_TYPE_PATH = RESULTS_DIR / "full100_draft_detector_error_review_by_question_type.csv"
DEFAULT_EXAMPLES_PATH = RESULTS_DIR / "full100_draft_detector_error_review_examples.csv"
DEFAULT_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_error_review_report.json"

TEST_SPLIT = "test"
SELECTED_BASELINE_KEYS = [
    ("simple_best_test_auprc", "simple_best_by_test_auprc"),
    ("energy_best_test_f1", "energy_best_by_test_f1"),
]

ERROR_REVIEW_FIELDS = [
    "family",
    "baseline_role",
    "baseline",
    "score_group",
    "score_field",
    "threshold",
    "score",
    "score_margin",
    "error_type",
    "actual_class",
    "predicted_class",
    "annotation_id",
    "question_id",
    "prompt_id",
    "split",
    "question_type",
    "difficulty",
    "fact_type",
    "label",
    "binary_label",
    "span_text",
    "token_count",
    "question",
    "gold_short_answer",
    "annotation_reason",
    "annotation_confidence",
    "annotation_notes",
    "gold_reference",
    "generated_excerpt",
    "generated_text",
    "evidence_table_markdown",
]

BY_BASELINE_FIELDS = [
    "family",
    "baseline_role",
    "baseline",
    "score_field",
    "score_group",
    "threshold",
    "test_precision",
    "test_recall",
    "test_specificity",
    "test_f1",
    "test_auprc",
    "test_tp",
    "test_fp",
    "test_tn",
    "test_fn",
    "false_positive_count",
    "false_negative_count",
    "error_count",
]

GROUP_FIELDS = [
    "family",
    "baseline_role",
    "baseline",
    "error_type",
    "group_value",
    "count",
]

EXAMPLE_FIELDS = ERROR_REVIEW_FIELDS + ["example_rank", "selection_reason"]


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def make_excerpt(text: str, start: int, end: int, window: int = 110) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(text) else ""
    excerpt = f"{prefix}{text[left:start]}[[{text[start:end]}]]{text[end:right]}{suffix}"
    return " ".join(excerpt.split())


def selected_baselines(comparison_report: dict[str, Any]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for role, report_key in SELECTED_BASELINE_KEYS:
        baseline_row = dict(comparison_report[report_key])
        key = (str(baseline_row["family"]), str(baseline_row["baseline"]))
        if key in seen:
            continue
        seen.add(key)
        baseline_row["baseline_role"] = role
        selected.append(baseline_row)
    return selected


def prediction_error_type(binary_label: int, predicted: int) -> str | None:
    if binary_label == 1 and predicted == 0:
        return "false_negative"
    if binary_label == 0 and predicted == 1:
        return "false_positive"
    return None


def class_name(value: int) -> str:
    return "positive" if value == 1 else "negative"


def build_group_rows(
    error_rows: list[dict[str, Any]],
    group_field: str,
) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str, str, str, str, str]] = Counter()
    for row in error_rows:
        counts[
            (
                row["family"],
                row["baseline_role"],
                row["baseline"],
                row["error_type"],
                group_field,
                row[group_field],
            )
        ] += 1
    return [
        {
            "family": family,
            "baseline_role": role,
            "baseline": baseline,
            "error_type": error_type,
            "group_value": group_value,
            "count": count,
        }
        for (family, role, baseline, error_type, _group_field, group_value), count in sorted(counts.items())
    ]


def build_example_rows(error_rows: list[dict[str, Any]], per_bucket: int = 5) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in error_rows:
        grouped[(row["baseline"], row["error_type"])].append(row)

    examples: list[dict[str, Any]] = []
    for (baseline, error_type), rows in sorted(grouped.items()):
        ranked = sorted(rows, key=lambda row: abs(float(row["score_margin"])), reverse=True)
        for rank, row in enumerate(ranked[:per_bucket], start=1):
            examples.append(
                {
                    **row,
                    "example_rank": rank,
                    "selection_reason": f"largest absolute score margin for {baseline} {error_type}",
                }
            )
    return examples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores-path", default=str(DEFAULT_SCORES_PATH))
    parser.add_argument("--comparison-report-path", default=str(DEFAULT_COMPARISON_REPORT_PATH))
    parser.add_argument("--annotations-path", default=str(DEFAULT_ANNOTATIONS_PATH))
    parser.add_argument("--generations-path", default=str(DEFAULT_GENERATIONS_PATH))
    parser.add_argument("--review-path", default=str(DEFAULT_REVIEW_PATH))
    parser.add_argument("--error-review-path", default=str(DEFAULT_ERROR_REVIEW_PATH))
    parser.add_argument("--by-baseline-path", default=str(DEFAULT_BY_BASELINE_PATH))
    parser.add_argument("--by-fact-type-path", default=str(DEFAULT_BY_FACT_TYPE_PATH))
    parser.add_argument("--by-question-type-path", default=str(DEFAULT_BY_QUESTION_TYPE_PATH))
    parser.add_argument("--examples-path", default=str(DEFAULT_EXAMPLES_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    scores_path = resolve_project_path(args.scores_path)
    comparison_report_path = resolve_project_path(args.comparison_report_path)
    annotations_path = resolve_project_path(args.annotations_path)
    generations_path = resolve_project_path(args.generations_path)
    review_path = resolve_project_path(args.review_path)
    error_review_path = resolve_project_path(args.error_review_path)
    by_baseline_path = resolve_project_path(args.by_baseline_path)
    by_fact_type_path = resolve_project_path(args.by_fact_type_path)
    by_question_type_path = resolve_project_path(args.by_question_type_path)
    examples_path = resolve_project_path(args.examples_path)
    report_path = resolve_project_path(args.report_path)

    failures: list[dict[str, Any]] = []
    for path in [scores_path, comparison_report_path, annotations_path, generations_path, review_path]:
        if not path.exists():
            failures.append({"reason": "missing required input", "path": str(path)})

    if failures:
        report = {"num_failures": len(failures), "failures": failures}
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    score_rows = read_csv(scores_path)
    comparison_report = load_json(comparison_report_path)
    annotations = {record["annotation_id"]: record for record in load_jsonl(annotations_path)}
    generations = {record["question_id"]: record for record in load_jsonl(generations_path)}
    review_records = {record["question_id"]: record for record in load_jsonl(review_path)}
    selected = selected_baselines(comparison_report)

    error_rows: list[dict[str, Any]] = []
    confusion_counts: Counter[tuple[str, str]] = Counter()
    for baseline_config in selected:
        family = str(baseline_config["family"])
        role = str(baseline_config["baseline_role"])
        baseline = str(baseline_config["baseline"])
        score_group = str(baseline_config["score_group"])
        score_field = str(baseline_config["score_field"])
        threshold = float(baseline_config["threshold"])

        for score_row in score_rows:
            if score_row["split"] != TEST_SPLIT:
                continue
            annotation_id = score_row["annotation_id"]
            annotation = annotations.get(annotation_id)
            generation = generations.get(score_row["question_id"])
            review_record = review_records.get(score_row["question_id"])
            if annotation is None or generation is None or review_record is None:
                failures.append(
                    {
                        "reason": "missing annotation/generation/review context",
                        "annotation_id": annotation_id,
                        "question_id": score_row.get("question_id"),
                    }
                )
                continue

            binary_label = int(score_row["binary_label"])
            score = float(score_row[score_field])
            predicted = 1 if score >= threshold else 0
            actual_class = class_name(binary_label)
            predicted_class = class_name(predicted)
            confusion_counts[(baseline, f"{actual_class}->{predicted_class}")] += 1
            error_type = prediction_error_type(binary_label, predicted)
            if error_type is None:
                continue

            generated_text = str(generation["generated_text"])
            start = int(annotation["span_start_char"])
            end = int(annotation["span_end_char"])
            score_margin = score - threshold
            error_rows.append(
                {
                    "family": family,
                    "baseline_role": role,
                    "baseline": baseline,
                    "score_group": score_group,
                    "score_field": score_field,
                    "threshold": round(threshold, 6),
                    "score": round(score, 6),
                    "score_margin": round(score_margin, 6),
                    "error_type": error_type,
                    "actual_class": actual_class,
                    "predicted_class": predicted_class,
                    "annotation_id": annotation_id,
                    "question_id": score_row["question_id"],
                    "prompt_id": score_row["prompt_id"],
                    "split": score_row["split"],
                    "question_type": score_row["question_type"],
                    "difficulty": score_row["difficulty"],
                    "fact_type": score_row["fact_type"],
                    "label": score_row["label"],
                    "binary_label": score_row["binary_label"],
                    "span_text": score_row["span_text"],
                    "token_count": score_row["token_count"],
                    "question": review_record["question"],
                    "gold_short_answer": review_record["gold_short_answer"],
                    "annotation_reason": annotation.get("reason", ""),
                    "annotation_confidence": annotation.get("confidence", ""),
                    "annotation_notes": annotation.get("notes", ""),
                    "gold_reference": compact_json(annotation.get("gold_reference", {})),
                    "generated_excerpt": make_excerpt(generated_text, start, end),
                    "generated_text": generated_text,
                    "evidence_table_markdown": review_record.get("evidence_table_markdown", ""),
                }
            )

    by_baseline_rows: list[dict[str, Any]] = []
    for baseline_config in selected:
        baseline = str(baseline_config["baseline"])
        fp = sum(1 for row in error_rows if row["baseline"] == baseline and row["error_type"] == "false_positive")
        fn = sum(1 for row in error_rows if row["baseline"] == baseline and row["error_type"] == "false_negative")
        by_baseline_rows.append(
            {
                "family": baseline_config["family"],
                "baseline_role": baseline_config["baseline_role"],
                "baseline": baseline,
                "score_field": baseline_config["score_field"],
                "score_group": baseline_config["score_group"],
                "threshold": baseline_config["threshold"],
                "test_precision": baseline_config["test_precision"],
                "test_recall": baseline_config["test_recall"],
                "test_specificity": baseline_config["test_specificity"],
                "test_f1": baseline_config["test_f1"],
                "test_auprc": baseline_config["test_auprc"],
                "test_tp": baseline_config["test_tp"],
                "test_fp": baseline_config["test_fp"],
                "test_tn": baseline_config["test_tn"],
                "test_fn": baseline_config["test_fn"],
                "false_positive_count": fp,
                "false_negative_count": fn,
                "error_count": fp + fn,
            }
        )

    by_fact_type_rows = build_group_rows(error_rows, "fact_type")
    by_question_type_rows = build_group_rows(error_rows, "question_type")
    example_rows = build_example_rows(error_rows)

    if not failures:
        write_csv(error_review_path, ERROR_REVIEW_FIELDS, error_rows)
        write_csv(by_baseline_path, BY_BASELINE_FIELDS, by_baseline_rows)
        write_csv(by_fact_type_path, GROUP_FIELDS, by_fact_type_rows)
        write_csv(by_question_type_path, GROUP_FIELDS, by_question_type_rows)
        write_csv(examples_path, EXAMPLE_FIELDS, example_rows)

    report = {
        "scores_path": str(scores_path),
        "comparison_report_path": str(comparison_report_path),
        "annotations_path": str(annotations_path),
        "generations_path": str(generations_path),
        "review_path": str(review_path),
        "error_review_path": str(error_review_path),
        "by_baseline_path": str(by_baseline_path),
        "by_fact_type_path": str(by_fact_type_path),
        "by_question_type_path": str(by_question_type_path),
        "examples_path": str(examples_path),
        "review_scope": "heldout_test_split_only",
        "selected_baselines": selected,
        "selected_baseline_count": len(selected),
        "error_row_count": len(error_rows),
        "by_baseline_row_count": len(by_baseline_rows),
        "by_fact_type_row_count": len(by_fact_type_rows),
        "by_question_type_row_count": len(by_question_type_rows),
        "example_row_count": len(example_rows),
        "error_counts_by_baseline": {
            row["baseline"]: {
                "false_positive": row["false_positive_count"],
                "false_negative": row["false_negative_count"],
                "total": row["error_count"],
            }
            for row in by_baseline_rows
        },
        "confusion_counts_by_baseline": {
            str(config["baseline"]): {
                transition: confusion_counts[(str(config["baseline"]), transition)]
                for transition in ["positive->positive", "positive->negative", "negative->positive", "negative->negative"]
            }
            for config in selected
        },
        "top_fact_type_error_counts": sorted(
            by_fact_type_rows,
            key=lambda row: (int(row["count"]), row["baseline"]),
            reverse=True,
        )[:10],
        "top_question_type_error_counts": sorted(
            by_question_type_rows,
            key=lambda row: (int(row["count"]), row["baseline"]),
            reverse=True,
        )[:10],
        "interpretation_guardrails": [
            "This review is held-out test only; dev rows are excluded because dev selected thresholds.",
            "Rows are baseline-specific, so the same span can appear once per selected detector.",
            "Use false-positive and false-negative patterns to qualify detector claims before public reporting.",
            "Current labels remain draft until presentation-level label confirmation.",
        ],
        "ready_for_error_pattern_review": len(failures) == 0,
        "num_failures": len(failures),
        "failures": failures,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
