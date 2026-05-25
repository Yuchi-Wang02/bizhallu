from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from evaluate_pilot_simple_baselines import (
        average_precision,
        auroc,
        best_threshold_metrics,
        confusion_at_threshold,
        metrics_from_confusion,
        rounded_metrics,
    )
except ModuleNotFoundError as exc:
    if exc.name != "evaluate_pilot_simple_baselines":
        raise
    from src.evaluate_pilot_simple_baselines import (
        average_precision,
        auroc,
        best_threshold_metrics,
        confusion_at_threshold,
        metrics_from_confusion,
        rounded_metrics,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTION_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
DEFAULT_BASELINE_CONFIG_PATH = PROJECT_ROOT / "configs" / "detector_baseline_suite.json"
RESULTS_DIR = PROJECT_ROOT / "results"


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


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


def binary_label(row: dict[str, str]) -> int:
    value = row.get("binary_label", "")
    if value not in {"0", "1"}:
        raise ValueError(f"{row.get('annotation_id', 'UNKNOWN')} has invalid binary_label: {value}")
    return int(value)


def add_splits(score_rows: list[dict[str, str]], questions_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    questions = load_jsonl(questions_path)
    split_by_qid = {str(record["question_id"]): str(record["split"]) for record in questions}
    failures: list[dict[str, Any]] = []
    enriched: list[dict[str, Any]] = []
    for row in score_rows:
        qid = str(row.get("question_id", ""))
        split = split_by_qid.get(qid)
        if split is None:
            failures.append({"annotation_id": row.get("annotation_id"), "question_id": qid, "reason": "missing question split"})
            continue
        enriched.append({**row, "split": split, "binary_label_int": binary_label(row)})
    return enriched, failures


def validate_baseline_fields(rows: list[dict[str, Any]], baseline_configs: list[dict[str, str]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    fields = set(rows[0]) if rows else set()
    for baseline_config in baseline_configs:
        score_field = baseline_config["score_field"]
        if score_field not in fields:
            failures.append({"baseline": baseline_config["baseline"], "reason": "missing score field", "score_field": score_field})
            continue
        for row in rows:
            try:
                float(row[score_field])
            except ValueError:
                failures.append(
                    {
                        "baseline": baseline_config["baseline"],
                        "annotation_id": row.get("annotation_id"),
                        "reason": "non-numeric score",
                        "score_field": score_field,
                        "value": row.get(score_field),
                    }
                )
                break
    return failures


def split_rows(rows: list[dict[str, Any]], split_name: str) -> list[dict[str, Any]]:
    return [row for row in rows if row["split"] == split_name]


def check_binary_coverage(rows: list[dict[str, Any]], split_name: str) -> dict[str, Any] | None:
    labels = [int(row["binary_label_int"]) for row in rows]
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        return {
            "split": split_name,
            "reason": "split must contain both positive and negative spans",
            "row_count": len(rows),
            "positive_count": positives,
            "negative_count": negatives,
        }
    return None


def metric_record(
    baseline_config: dict[str, str],
    threshold: float,
    rows: list[dict[str, Any]],
    split_name: str,
    threshold_source_split: str,
) -> dict[str, Any]:
    score_field = baseline_config["score_field"]
    y_true = [int(row["binary_label_int"]) for row in rows]
    scores = [float(row[score_field]) for row in rows]
    confusion = confusion_at_threshold(y_true, scores, threshold)
    metrics = rounded_metrics(metrics_from_confusion(confusion))
    roc = auroc(y_true, scores)
    prc = average_precision(y_true, scores)
    return {
        "baseline": baseline_config["baseline"],
        "score_field": score_field,
        "evaluated_split": split_name,
        "threshold_source_split": threshold_source_split,
        "threshold": round(threshold, 6),
        "threshold_rule": "predict_positive_if_score_gte_threshold",
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "specificity": metrics["specificity"],
        "f1": metrics["f1"],
        "accuracy": metrics["accuracy"],
        "auroc": round(roc, 6) if roc is not None else "",
        "auprc": round(prc, 6) if prc is not None else "",
        "tp": confusion["tp"],
        "fp": confusion["fp"],
        "tn": confusion["tn"],
        "fn": confusion["fn"],
        "positive_count": sum(y_true),
        "negative_count": len(y_true) - sum(y_true),
        "selection_policy": "threshold_selected_on_dev_split_max_f1",
        "description": baseline_config.get("description", ""),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores-path", required=True)
    parser.add_argument("--baseline-family", required=True)
    parser.add_argument("--baseline-config", default=str(DEFAULT_BASELINE_CONFIG_PATH))
    parser.add_argument("--questions-path", default=str(DEFAULT_QUESTION_PATH))
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--dev-split", default=None)
    parser.add_argument("--test-split", default=None)
    args = parser.parse_args()

    scores_path = resolve_project_path(args.scores_path)
    baseline_config_path = resolve_project_path(args.baseline_config)
    questions_path = resolve_project_path(args.questions_path)
    metrics_path = RESULTS_DIR / f"{args.output_prefix}_metrics.csv"
    report_path = RESULTS_DIR / f"{args.output_prefix}_report.json"

    config = json.loads(baseline_config_path.read_text(encoding="utf-8"))
    dev_split = args.dev_split or config.get("default_dev_split", "dev")
    test_split = args.test_split or config.get("default_test_split", "test")
    family_configs = config.get("families", {}).get(args.baseline_family)

    failures: list[dict[str, Any]] = []
    if not family_configs:
        failures.append({"reason": "unknown or empty baseline family", "baseline_family": args.baseline_family})

    score_rows_raw = read_csv(scores_path) if scores_path.exists() else []
    if not scores_path.exists():
        failures.append({"reason": "missing scores file", "path": str(scores_path)})
    if not score_rows_raw:
        failures.append({"reason": "scores file has no rows", "path": str(scores_path)})

    rows, split_failures = add_splits(score_rows_raw, questions_path) if score_rows_raw else ([], [])
    failures.extend(split_failures)
    if family_configs and rows:
        failures.extend(validate_baseline_fields(rows, family_configs))

    dev_rows = split_rows(rows, dev_split)
    test_rows = split_rows(rows, test_split)
    if not dev_rows:
        failures.append({"split": dev_split, "reason": "no dev rows available for threshold selection"})
    if not test_rows:
        failures.append({"split": test_split, "reason": "no test rows available for held-out evaluation"})
    if dev_rows:
        coverage_failure = check_binary_coverage(dev_rows, dev_split)
        if coverage_failure:
            failures.append(coverage_failure)
    if test_rows:
        coverage_failure = check_binary_coverage(test_rows, test_split)
        if coverage_failure:
            failures.append(coverage_failure)

    if failures:
        report = {
            "scores_path": str(scores_path),
            "baseline_config_path": str(baseline_config_path),
            "questions_path": str(questions_path),
            "baseline_family": args.baseline_family,
            "dev_split": dev_split,
            "test_split": test_split,
            "row_count": len(rows),
            "split_counts": dict(Counter(row.get("split") for row in rows)),
            "num_failures": len(failures),
            "failures": failures,
            "ready_for_split_metrics": False,
        }
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    metric_rows: list[dict[str, Any]] = []
    threshold_rows: list[dict[str, Any]] = []
    for baseline_config in family_configs:
        score_field = baseline_config["score_field"]
        dev_labels = [int(row["binary_label_int"]) for row in dev_rows]
        dev_scores = [float(row[score_field]) for row in dev_rows]
        threshold, dev_confusion, dev_metrics = best_threshold_metrics(dev_labels, dev_scores)
        threshold_rows.append(
            {
                "baseline": baseline_config["baseline"],
                "score_field": score_field,
                "threshold": round(threshold, 6),
                "dev_f1_at_selected_threshold": round(dev_metrics["f1"], 6),
                "dev_tp": dev_confusion["tp"],
                "dev_fp": dev_confusion["fp"],
                "dev_tn": dev_confusion["tn"],
                "dev_fn": dev_confusion["fn"],
            }
        )
        metric_rows.append(metric_record(baseline_config, threshold, dev_rows, dev_split, dev_split))
        metric_rows.append(metric_record(baseline_config, threshold, test_rows, test_split, dev_split))

    write_csv(
        metrics_path,
        [
            "baseline",
            "score_field",
            "evaluated_split",
            "threshold_source_split",
            "threshold",
            "threshold_rule",
            "precision",
            "recall",
            "specificity",
            "f1",
            "accuracy",
            "auroc",
            "auprc",
            "tp",
            "fp",
            "tn",
            "fn",
            "positive_count",
            "negative_count",
            "selection_policy",
            "description",
        ],
        metric_rows,
    )

    test_rows_by_metric = [row for row in metric_rows if row["evaluated_split"] == test_split]
    best_test_by_auprc = max(test_rows_by_metric, key=lambda row: (float(row["auprc"]), float(row["f1"]), float(row["auroc"])))
    best_test_by_f1 = max(test_rows_by_metric, key=lambda row: (float(row["f1"]), float(row["auprc"]), float(row["auroc"])))
    report = {
        "scores_path": str(scores_path),
        "baseline_config_path": str(baseline_config_path),
        "questions_path": str(questions_path),
        "metrics_path": str(metrics_path),
        "baseline_family": args.baseline_family,
        "dev_split": dev_split,
        "test_split": test_split,
        "row_count": len(rows),
        "split_counts": dict(sorted(Counter(row["split"] for row in rows).items())),
        "dev_row_count": len(dev_rows),
        "test_row_count": len(test_rows),
        "baseline_count": len(family_configs),
        "metric_row_count": len(metric_rows),
        "thresholds": threshold_rows,
        "best_test_by_auprc": best_test_by_auprc,
        "best_test_by_f1": best_test_by_f1,
        "num_failures": 0,
        "failures": [],
        "ready_for_split_metrics": True,
        "evaluation_note": (
            "Thresholds are selected only on dev spans. Test metrics reuse the fixed dev threshold "
            "and should be treated as held-out detector results."
        ),
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
