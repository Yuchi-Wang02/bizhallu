from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALIGNMENT_PATH = PROJECT_ROOT / "outputs" / "pilot20_span_token_alignment.jsonl"
ALIGNMENT_REPORT_PATH = PROJECT_ROOT / "outputs" / "pilot20_span_token_alignment_report.json"
RESULTS_DIR = PROJECT_ROOT / "results"
CONFUSION_DIR = RESULTS_DIR / "confusion_matrices"

SCORES_PATH = RESULTS_DIR / "pilot20_simple_baseline_scores.csv"
METRICS_PATH = RESULTS_DIR / "pilot20_simple_baseline_metrics.csv"
CONFUSION_PATH = CONFUSION_DIR / "pilot20_simple_baselines_confusion_matrices.csv"
REPORT_PATH = RESULTS_DIR / "pilot20_simple_baseline_report.json"

POSITIVE_LABELS = {"hallucinated_key_fact", "unsupported_claim"}
NEGATIVE_LABELS = {"correct_key_fact"}
EXCLUDED_LABELS = {"ambiguous_or_unverifiable", "ignore"}

BASELINES = [
    {
        "baseline": "mean_token_nll",
        "score_field": "mean_token_nll",
        "description": "Higher mean token negative log probability indicates more uncertainty.",
    },
    {
        "baseline": "mean_token_entropy",
        "score_field": "mean_token_entropy",
        "description": "Higher mean token entropy indicates more uncertainty.",
    },
    {
        "baseline": "max_token_entropy",
        "score_field": "max_token_entropy",
        "description": "Higher maximum token entropy catches one uncertain token inside a span.",
    },
    {
        "baseline": "one_minus_mean_top2_margin",
        "score_field": "one_minus_mean_top2_margin",
        "description": "Higher value means lower average top-2 margin across the span.",
    },
    {
        "baseline": "one_minus_min_top2_margin",
        "score_field": "one_minus_min_top2_margin",
        "description": "Higher value means at least one token has a low top-2 margin.",
    },
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def binary_label(label: str) -> int | None:
    if label in POSITIVE_LABELS:
        return 1
    if label in NEGATIVE_LABELS:
        return 0
    if label in EXCLUDED_LABELS:
        return None
    raise ValueError(f"Unknown label: {label}")


def safe_float(value: Any, field: str, annotation_id: str) -> float:
    if value is None:
        raise ValueError(f"{annotation_id} has null {field}")
    return float(value)


def build_score_rows(alignment_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in alignment_records:
        label = str(record["label"])
        y_true = binary_label(label)
        if y_true is None:
            continue
        annotation_id = str(record["annotation_id"])
        mean_top2_margin = safe_float(record["mean_top2_margin"], "mean_top2_margin", annotation_id)
        min_top2_margin = safe_float(record["min_top2_margin"], "min_top2_margin", annotation_id)
        rows.append(
            {
                "annotation_id": annotation_id,
                "question_id": record["question_id"],
                "prompt_id": record["prompt_id"],
                "fact_type": record["fact_type"],
                "label": label,
                "binary_label": y_true,
                "span_text": record["span_text"],
                "token_count": int(record["token_count"]),
                "mean_token_nll": safe_float(record["mean_token_nll"], "mean_token_nll", annotation_id),
                "mean_token_entropy": safe_float(record["mean_token_entropy"], "mean_token_entropy", annotation_id),
                "max_token_entropy": safe_float(record["max_token_entropy"], "max_token_entropy", annotation_id),
                "mean_top2_margin": mean_top2_margin,
                "min_top2_margin": min_top2_margin,
                "one_minus_mean_top2_margin": 1.0 - mean_top2_margin,
                "one_minus_min_top2_margin": 1.0 - min_top2_margin,
            }
        )
    return rows


def confusion_at_threshold(y_true: list[int], scores: list[float], threshold: float) -> dict[str, int]:
    tp = fp = tn = fn = 0
    for label, score in zip(y_true, scores):
        prediction = 1 if score >= threshold else 0
        if prediction == 1 and label == 1:
            tp += 1
        elif prediction == 1 and label == 0:
            fp += 1
        elif prediction == 0 and label == 0:
            tn += 1
        elif prediction == 0 and label == 1:
            fn += 1
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def metrics_from_confusion(confusion: dict[str, int]) -> dict[str, float]:
    tp = confusion["tp"]
    fp = confusion["fp"]
    tn = confusion["tn"]
    fn = confusion["fn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    accuracy = (tp + tn) / (tp + fp + tn + fn) if tp + fp + tn + fn else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "f1": f1,
        "accuracy": accuracy,
    }


def average_ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    index = 0
    while index < len(indexed):
        end = index + 1
        while end < len(indexed) and indexed[end][1] == indexed[index][1]:
            end += 1
        average_rank = (index + 1 + end) / 2.0
        for original_index, _ in indexed[index:end]:
            ranks[original_index] = average_rank
        index = end
    return ranks


def auroc(y_true: list[int], scores: list[float]) -> float | None:
    positives = sum(y_true)
    negatives = len(y_true) - positives
    if positives == 0 or negatives == 0:
        return None
    ranks = average_ranks(scores)
    positive_rank_sum = sum(rank for rank, label in zip(ranks, y_true) if label == 1)
    auc = (positive_rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)
    return auc


def average_precision(y_true: list[int], scores: list[float]) -> float | None:
    positives = sum(y_true)
    if positives == 0:
        return None
    ordered = sorted(zip(scores, y_true), key=lambda item: item[0], reverse=True)
    true_positives = 0
    precision_sum = 0.0
    for rank, (_, label) in enumerate(ordered, start=1):
        if label == 1:
            true_positives += 1
            precision_sum += true_positives / rank
    return precision_sum / positives


def best_threshold_metrics(y_true: list[int], scores: list[float]) -> tuple[float, dict[str, int], dict[str, float]]:
    best_threshold: float | None = None
    best_confusion: dict[str, int] | None = None
    best_metrics: dict[str, float] | None = None
    for threshold in sorted(set(scores)):
        confusion = confusion_at_threshold(y_true, scores, threshold)
        metrics = metrics_from_confusion(confusion)
        candidate_key = (
            metrics["f1"],
            metrics["precision"],
            metrics["recall"],
            metrics["accuracy"],
            -threshold,
        )
        if best_metrics is None:
            best_threshold = threshold
            best_confusion = confusion
            best_metrics = metrics
            best_key = candidate_key
            continue
        if candidate_key > best_key:
            best_threshold = threshold
            best_confusion = confusion
            best_metrics = metrics
            best_key = candidate_key

    if best_threshold is None or best_confusion is None or best_metrics is None:
        raise ValueError("No threshold candidates available")
    return best_threshold, best_confusion, best_metrics


def rounded_metrics(metrics: dict[str, float]) -> dict[str, float]:
    return {key: round(value, 6) for key, value in metrics.items()}


def reference_baselines(y_true: list[int]) -> dict[str, Any]:
    positive_count = sum(y_true)
    negative_count = len(y_true) - positive_count
    all_positive_confusion = {"tp": positive_count, "fp": negative_count, "tn": 0, "fn": 0}
    all_negative_confusion = {"tp": 0, "fp": 0, "tn": negative_count, "fn": positive_count}
    prevalence = positive_count / len(y_true) if y_true else 0.0
    return {
        "positive_prevalence": round(prevalence, 6),
        "all_positive": {
            **all_positive_confusion,
            **rounded_metrics(metrics_from_confusion(all_positive_confusion)),
        },
        "all_negative": {
            **all_negative_confusion,
            **rounded_metrics(metrics_from_confusion(all_negative_confusion)),
        },
    }


def write_scores(rows: list[dict[str, Any]]) -> None:
    SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "annotation_id",
        "question_id",
        "prompt_id",
        "fact_type",
        "label",
        "binary_label",
        "span_text",
        "token_count",
        "mean_token_nll",
        "mean_token_entropy",
        "max_token_entropy",
        "mean_top2_margin",
        "min_top2_margin",
        "one_minus_mean_top2_margin",
        "one_minus_min_top2_margin",
    ]
    with SCORES_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    alignment_report = json.loads(ALIGNMENT_REPORT_PATH.read_text(encoding="utf-8"))
    if not alignment_report.get("ready_for_simple_logit_baselines"):
        raise SystemExit("Span-token alignment is not ready for simple baselines")

    score_rows = build_score_rows(load_jsonl(ALIGNMENT_PATH))
    y_true = [int(row["binary_label"]) for row in score_rows]
    positive_count = sum(y_true)
    negative_count = len(y_true) - positive_count
    if positive_count == 0 or negative_count == 0:
        raise SystemExit("Need both positive and negative spans for pilot baseline metrics")

    write_scores(score_rows)

    metric_rows: list[dict[str, Any]] = []
    confusion_rows: list[dict[str, Any]] = []
    for baseline_config in BASELINES:
        baseline = baseline_config["baseline"]
        score_field = baseline_config["score_field"]
        scores = [float(row[score_field]) for row in score_rows]
        threshold, confusion, metrics = best_threshold_metrics(y_true, scores)
        roc = auroc(y_true, scores)
        prc = average_precision(y_true, scores)
        rounded = rounded_metrics(metrics)

        metric_rows.append(
            {
                "baseline": baseline,
                "score_field": score_field,
                "threshold": round(threshold, 6),
                "threshold_rule": "predict_positive_if_score_gte_threshold",
                "precision": rounded["precision"],
                "recall": rounded["recall"],
                "specificity": rounded["specificity"],
                "f1": rounded["f1"],
                "accuracy": rounded["accuracy"],
                "auroc": round(roc, 6) if roc is not None else "",
                "auprc": round(prc, 6) if prc is not None else "",
                "tp": confusion["tp"],
                "fp": confusion["fp"],
                "tn": confusion["tn"],
                "fn": confusion["fn"],
                "positive_count": positive_count,
                "negative_count": negative_count,
                "selection_policy": "threshold_selected_on_pilot20_max_f1_optimistic",
                "description": baseline_config["description"],
            }
        )
        confusion_rows.extend(
            [
                {"baseline": baseline, "actual": "positive", "predicted": "positive", "count": confusion["tp"]},
                {"baseline": baseline, "actual": "positive", "predicted": "negative", "count": confusion["fn"]},
                {"baseline": baseline, "actual": "negative", "predicted": "positive", "count": confusion["fp"]},
                {"baseline": baseline, "actual": "negative", "predicted": "negative", "count": confusion["tn"]},
            ]
        )

    write_csv(
        METRICS_PATH,
        [
            "baseline",
            "score_field",
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
    write_csv(CONFUSION_PATH, ["baseline", "actual", "predicted", "count"], confusion_rows)

    best_by_f1 = max(metric_rows, key=lambda row: (float(row["f1"]), float(row["auprc"]), float(row["auroc"])))
    best_by_auprc = max(metric_rows, key=lambda row: (float(row["auprc"]), float(row["f1"])))
    references = reference_baselines(y_true)
    best_f1_lift_over_all_positive = float(best_by_f1["f1"]) - float(references["all_positive"]["f1"])
    best_auprc_lift_over_prevalence = float(best_by_auprc["auprc"]) - float(references["positive_prevalence"])
    report = {
        "input_alignment_path": str(ALIGNMENT_PATH),
        "scores_path": str(SCORES_PATH),
        "metrics_path": str(METRICS_PATH),
        "confusion_matrix_path": str(CONFUSION_PATH),
        "span_count": len(score_rows),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "excluded_count": alignment_report["annotation_count"] - len(score_rows),
        "baseline_count": len(metric_rows),
        "reference_baselines": references,
        "best_by_f1": best_by_f1,
        "best_by_auprc": best_by_auprc,
        "best_f1_lift_over_all_positive": round(best_f1_lift_over_all_positive, 6),
        "best_auprc_lift_over_positive_prevalence": round(best_auprc_lift_over_prevalence, 6),
        "interpretation": (
            "The simple token-logit signals show weak-to-moderate ranking signal on pilot20. "
            "Thresholded F1 is only slightly above the all-positive reference because the pilot "
            "set is nearly balanced, while AUPRC is more clearly above positive prevalence."
        ),
        "evaluation_note": (
            "Pilot20 thresholds are selected and evaluated on the same annotated pilot set. "
            "Use these numbers as a baseline sanity check, not as final held-out performance."
        ),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
