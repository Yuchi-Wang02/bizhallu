from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCORES_PATH = PROJECT_ROOT / "results" / "pilot20_simple_baseline_scores.csv"
BASELINE_REPORT_PATH = PROJECT_ROOT / "results" / "pilot20_simple_baseline_report.json"
ANNOTATION_PATH = PROJECT_ROOT / "data" / "annotations" / "span_annotations_pilot.jsonl"
QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
GENERATIONS_PATH = PROJECT_ROOT / "outputs" / "qwen_pilot20_generations.jsonl"

ERROR_REVIEW_PATH = PROJECT_ROOT / "results" / "pilot20_baseline_error_review.csv"
ERROR_SUMMARY_PATH = PROJECT_ROOT / "results" / "pilot20_baseline_error_summary.json"


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


def make_excerpt(text: str, start: int, end: int, window: int = 90) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(text) else ""
    excerpt = f"{prefix}{text[left:start]}[[{text[start:end]}]]{text[end:right]}{suffix}"
    return " ".join(excerpt.split())


def selected_baselines(report: dict[str, Any]) -> list[dict[str, Any]]:
    role_by_baseline: dict[str, list[str]] = defaultdict(list)
    configs: dict[str, dict[str, Any]] = {}
    for role, key in [("best_by_f1", "best_by_f1"), ("best_by_auprc", "best_by_auprc")]:
        config = dict(report[key])
        baseline = str(config["baseline"])
        role_by_baseline[baseline].append(role)
        configs[baseline] = config

    selected: list[dict[str, Any]] = []
    for baseline in sorted(configs):
        config = configs[baseline]
        config["baseline_role"] = "+".join(role_by_baseline[baseline])
        selected.append(config)
    return selected


def prediction_error_type(binary_label: int, predicted: int) -> str | None:
    if binary_label == 1 and predicted == 0:
        return "false_negative"
    if binary_label == 0 and predicted == 1:
        return "false_positive"
    return None


def build_error_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    report = json.loads(BASELINE_REPORT_PATH.read_text(encoding="utf-8"))
    scores = read_csv(SCORES_PATH)
    annotations = {record["annotation_id"]: record for record in load_jsonl(ANNOTATION_PATH)}
    questions = {record["question_id"]: record for record in load_jsonl(QUESTIONS_PATH)}
    generations = {record["question_id"]: record for record in load_jsonl(GENERATIONS_PATH)}
    selected = selected_baselines(report)

    error_rows: list[dict[str, Any]] = []
    confusion_counts: Counter[tuple[str, str]] = Counter()
    by_fact_type: Counter[tuple[str, str, str]] = Counter()
    by_question_type: Counter[tuple[str, str, str]] = Counter()

    for baseline_config in selected:
        baseline = str(baseline_config["baseline"])
        score_field = str(baseline_config["score_field"])
        threshold = float(baseline_config["threshold"])
        role = str(baseline_config["baseline_role"])

        for score_row in scores:
            annotation_id = score_row["annotation_id"]
            binary_label = int(score_row["binary_label"])
            score = float(score_row[score_field])
            predicted = 1 if score >= threshold else 0
            error_type = prediction_error_type(binary_label, predicted)
            actual_class = "positive" if binary_label == 1 else "negative"
            predicted_class = "positive" if predicted == 1 else "negative"
            confusion_counts[(baseline, f"{actual_class}->{predicted_class}")] += 1
            if error_type is None:
                continue

            annotation = annotations[annotation_id]
            question_id = score_row["question_id"]
            question = questions[question_id]
            generation = generations[question_id]
            generated_text = str(generation["generated_text"])
            start = int(annotation["span_start_char"])
            end = int(annotation["span_end_char"])

            fact_type = score_row["fact_type"]
            question_type = str(question["question_type"])
            by_fact_type[(baseline, error_type, fact_type)] += 1
            by_question_type[(baseline, error_type, question_type)] += 1

            error_rows.append(
                {
                    "baseline": baseline,
                    "baseline_role": role,
                    "score_field": score_field,
                    "threshold": round(threshold, 6),
                    "score": round(score, 6),
                    "score_minus_threshold": round(score - threshold, 6),
                    "error_type": error_type,
                    "actual_class": actual_class,
                    "predicted_class": predicted_class,
                    "annotation_id": annotation_id,
                    "question_id": question_id,
                    "prompt_id": score_row["prompt_id"],
                    "question_type": question_type,
                    "difficulty": question["difficulty"],
                    "split": question["split"],
                    "fact_type": fact_type,
                    "label": score_row["label"],
                    "span_text": score_row["span_text"],
                    "token_count": int(score_row["token_count"]),
                    "question": question["question"],
                    "gold_short_answer": question["gold_short_answer"],
                    "annotation_reason": annotation["reason"],
                    "gold_reference": compact_json(annotation.get("gold_reference", {})),
                    "generated_excerpt": make_excerpt(generated_text, start, end),
                }
            )

    error_rows.sort(
        key=lambda row: (
            row["baseline"],
            row["error_type"],
            row["question_id"],
            row["annotation_id"],
        )
    )

    summary = {
        "input_scores_path": str(SCORES_PATH),
        "input_baseline_report_path": str(BASELINE_REPORT_PATH),
        "error_review_path": str(ERROR_REVIEW_PATH),
        "selected_baselines": [
            {
                "baseline": item["baseline"],
                "baseline_role": item["baseline_role"],
                "score_field": item["score_field"],
                "threshold": item["threshold"],
                "precision": item["precision"],
                "recall": item["recall"],
                "specificity": item["specificity"],
                "f1": item["f1"],
                "auprc": item["auprc"],
                "tp": item["tp"],
                "fp": item["fp"],
                "tn": item["tn"],
                "fn": item["fn"],
            }
            for item in selected
        ],
        "error_row_count": len(error_rows),
        "error_counts_by_baseline": {
            baseline: {
                "false_positive": sum(1 for row in error_rows if row["baseline"] == baseline and row["error_type"] == "false_positive"),
                "false_negative": sum(1 for row in error_rows if row["baseline"] == baseline and row["error_type"] == "false_negative"),
            }
            for baseline in sorted({row["baseline"] for row in error_rows})
        },
        "confusion_counts_by_baseline": {
            baseline: {
                transition: confusion_counts[(baseline, transition)]
                for transition in ["positive->positive", "positive->negative", "negative->positive", "negative->negative"]
            }
            for baseline in sorted({item["baseline"] for item in selected})
        },
        "error_counts_by_fact_type": [
            {"baseline": baseline, "error_type": error_type, "fact_type": fact_type, "count": count}
            for (baseline, error_type, fact_type), count in sorted(by_fact_type.items())
        ],
        "error_counts_by_question_type": [
            {"baseline": baseline, "error_type": error_type, "question_type": question_type, "count": count}
            for (baseline, error_type, question_type), count in sorted(by_question_type.items())
        ],
        "interpretation": (
            "This file lists pilot-only false positives and false negatives for the best-F1 and best-AUPRC "
            "simple baselines. Use it to inspect failure patterns before running larger generation or adding "
            "paper-style baselines."
        ),
    }
    return error_rows, summary


def main() -> None:
    rows, summary = build_error_rows()
    fieldnames = [
        "baseline",
        "baseline_role",
        "score_field",
        "threshold",
        "score",
        "score_minus_threshold",
        "error_type",
        "actual_class",
        "predicted_class",
        "annotation_id",
        "question_id",
        "prompt_id",
        "question_type",
        "difficulty",
        "split",
        "fact_type",
        "label",
        "span_text",
        "token_count",
        "question",
        "gold_short_answer",
        "annotation_reason",
        "gold_reference",
        "generated_excerpt",
    ]
    write_csv(ERROR_REVIEW_PATH, fieldnames, rows)
    ERROR_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
