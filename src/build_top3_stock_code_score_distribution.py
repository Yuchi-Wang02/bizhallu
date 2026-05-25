from __future__ import annotations

import csv
import json
from pathlib import Path
from statistics import mean, median
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"

SIGNAL_SPANS_CSV = RESULTS_DIR / "top3_sorted_control_token_signal_spans.csv"
DISTRIBUTION_CSV = RESULTS_DIR / "top3_stock_code_score_distribution.csv"
SUMMARY_JSON = RESULTS_DIR / "top3_stock_code_score_distribution_summary.json"
VALIDATION_JSON = RESULTS_DIR / "top3_stock_code_score_distribution_validation.json"

EXPECTED_QUESTION_IDS = ["q_0060", "q_0065", "q_0072"]
SCORE_FIELDS = ["max_token_entropy", "one_minus_min_top2_margin", "mean_token_nll"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None) -> None:
    failure: dict[str, Any] = {"reason": reason}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def as_float(row: dict[str, Any], field: str) -> float:
    value = row[field]
    if value == "" or value is None:
        raise ValueError(f"Missing score field {field} for {row.get('question_id')} {row.get('span_text')}")
    return float(value)


def binary_label(label: str) -> int:
    return 1 if label != "correct" else 0


def pairwise_auc(rows: list[dict[str, Any]], score_field: str) -> float:
    positives = [as_float(row, score_field) for row in rows if int(row["binary_label"]) == 1]
    negatives = [as_float(row, score_field) for row in rows if int(row["binary_label"]) == 0]
    if not positives or not negatives:
        return 0.0
    wins = 0.0
    total = 0
    for positive in positives:
        for negative in negatives:
            total += 1
            if positive > negative:
                wins += 1.0
            elif positive == negative:
                wins += 0.5
    return round(wins / total, 6)


def confusion_at_threshold(rows: list[dict[str, Any]], score_field: str, threshold: float) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for row in rows:
        label = int(row["binary_label"])
        prediction = 1 if as_float(row, score_field) >= threshold else 0
        if prediction == 1 and label == 1:
            tp += 1
        elif prediction == 1 and label == 0:
            fp += 1
        elif prediction == 0 and label == 0:
            tn += 1
        elif prediction == 0 and label == 1:
            fn += 1

    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    specificity = tn / (tn + fp) if tn + fp else 0.0
    return {
        "threshold": round(threshold, 6),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "specificity": round(specificity, 6),
        "f1": round(f1, 6),
    }


def best_threshold(rows: list[dict[str, Any]], score_field: str) -> dict[str, Any]:
    thresholds = sorted({as_float(row, score_field) for row in rows}, reverse=True)
    candidates = [confusion_at_threshold(rows, score_field, threshold) for threshold in thresholds]
    candidates.sort(key=lambda item: (-float(item["f1"]), -float(item["recall"]), int(item["fp"]), -float(item["threshold"])))
    return candidates[0]


def describe_values(values: list[float]) -> dict[str, float]:
    return {
        "min": round(min(values), 6),
        "mean": round(mean(values), 6),
        "median": round(median(values), 6),
        "max": round(max(values), 6),
    }


def metric_summary(rows: list[dict[str, Any]], score_field: str) -> dict[str, Any]:
    correct_values = [as_float(row, score_field) for row in rows if row["label"] == "correct"]
    incorrect_values = [as_float(row, score_field) for row in rows if row["label"] != "correct"]
    best = best_threshold(rows, score_field)
    sorted_rows = sorted(rows, key=lambda row: as_float(row, score_field), reverse=True)
    top3 = [
        {
            "rank_by_score": index,
            "question_id": row["question_id"],
            "answer_rank": int(row["rank"]),
            "stock_code": row["stock_code"],
            "label": row["label"],
            "score": round(as_float(row, score_field), 6),
        }
        for index, row in enumerate(sorted_rows[:3], start=1)
    ]
    overlap = {
        "incorrect_min": round(min(incorrect_values), 6),
        "correct_max": round(max(correct_values), 6),
        "has_overlap": min(incorrect_values) <= max(correct_values),
    }
    return {
        "score_field": score_field,
        "pairwise_auc_on_9_stock_code_spans": pairwise_auc(rows, score_field),
        "correct": describe_values(correct_values),
        "incorrect_rank_binding": describe_values(incorrect_values),
        "best_threshold_on_9_spans_optimistic": best,
        "top3_by_score": top3,
        "overlap_check": overlap,
    }


def build_distribution_rows(stock_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in stock_rows:
        out = {
            "question_id": row["question_id"],
            "rank": int(row["rank"]),
            "stock_code": row["span_text"],
            "label": row["label"],
            "binary_label": binary_label(row["label"]),
            "generated_evidence_position": row["generated_evidence_position"],
            "expected_stock_code_at_rank": row["expected_stock_code_at_rank"],
            "reason": row["reason"],
        }
        for field in SCORE_FIELDS:
            out[field] = round(as_float(row, field), 6)
        rows.append(out)

    for field in SCORE_FIELDS:
        ranked = sorted(rows, key=lambda item: float(item[field]), reverse=True)
        for index, row in enumerate(ranked, start=1):
            row[f"{field}_rank_desc"] = index

    return sorted(rows, key=lambda item: (item["question_id"], int(item["rank"])))


def main() -> None:
    failures: list[dict[str, Any]] = []
    if not SIGNAL_SPANS_CSV.exists():
        add_failure(failures, "missing signal spans csv", str(SIGNAL_SPANS_CSV))
        validation = {"num_failures": len(failures), "failures": failures}
        VALIDATION_JSON.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    all_rows = read_csv(SIGNAL_SPANS_CSV)
    stock_rows = [row for row in all_rows if row["span_scope"] == "stock_code"]
    distribution_rows = build_distribution_rows(stock_rows)
    summary = {
        "source_signal_spans_csv": str(SIGNAL_SPANS_CSV),
        "distribution_csv_path": str(DISTRIBUTION_CSV),
        "stock_code_span_count": len(distribution_rows),
        "label_counts": {
            "correct": sum(1 for row in distribution_rows if row["label"] == "correct"),
            "incorrect_rank_binding": sum(1 for row in distribution_rows if row["label"] != "correct"),
        },
        "question_ids": sorted({row["question_id"] for row in distribution_rows}),
        "metric_summaries": [metric_summary(distribution_rows, field) for field in SCORE_FIELDS],
        "main_findings": [
            "Stock-code entropy has the best local ranking signal among the three simple scores, but the sample is only 9 spans.",
            "No simple score perfectly separates correct and incorrect stock-code rank bindings because the score ranges overlap.",
            "The pilot20 global thresholds were too low for stock-code specificity; they flagged every stock-code span in this control.",
            "This supports testing a stronger or more context-aware detector before scaling to full100.",
        ],
    }

    fieldnames = [
        "question_id",
        "rank",
        "stock_code",
        "label",
        "binary_label",
        "generated_evidence_position",
        "expected_stock_code_at_rank",
        "max_token_entropy",
        "max_token_entropy_rank_desc",
        "one_minus_min_top2_margin",
        "one_minus_min_top2_margin_rank_desc",
        "mean_token_nll",
        "mean_token_nll_rank_desc",
        "reason",
    ]
    write_csv(DISTRIBUTION_CSV, fieldnames, distribution_rows)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")

    if len(distribution_rows) != 9:
        add_failure(failures, "expected 9 stock-code spans", {"actual": len(distribution_rows)})
    if summary["label_counts"]["correct"] != 6 or summary["label_counts"]["incorrect_rank_binding"] != 3:
        add_failure(failures, "unexpected stock-code label counts", summary["label_counts"])
    if summary["question_ids"] != EXPECTED_QUESTION_IDS:
        add_failure(failures, "unexpected question ids", summary["question_ids"])
    for metric in summary["metric_summaries"]:
        auc = float(metric["pairwise_auc_on_9_stock_code_spans"])
        if not 0.0 <= auc <= 1.0:
            add_failure(failures, "metric auc outside [0,1]", metric)
        if not metric["overlap_check"]["has_overlap"]:
            add_failure(failures, "expected overlap for this tiny diagnostic set", metric["score_field"])

    with DISTRIBUTION_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    if len(csv_rows) != len(distribution_rows):
        add_failure(failures, "distribution csv row count mismatch", {"csv": len(csv_rows), "memory": len(distribution_rows)})

    validation = {
        "distribution_csv_path": str(DISTRIBUTION_CSV),
        "summary_path": str(SUMMARY_JSON),
        "stock_code_span_count": len(distribution_rows),
        "label_counts": summary["label_counts"],
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_JSON.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
