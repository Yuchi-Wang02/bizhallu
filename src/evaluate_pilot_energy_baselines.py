from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from evaluate_pilot_simple_baselines import (
    average_precision,
    auroc,
    best_threshold_metrics,
    binary_label,
    load_jsonl,
    reference_baselines,
    rounded_metrics,
    safe_float,
    write_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ALIGNMENT_PATH = PROJECT_ROOT / "outputs" / "pilot20_energy_span_token_alignment.jsonl"
ALIGNMENT_REPORT_PATH = PROJECT_ROOT / "outputs" / "pilot20_energy_span_token_alignment_report.json"
RESULTS_DIR = PROJECT_ROOT / "results"
CONFUSION_DIR = RESULTS_DIR / "confusion_matrices"

SCORES_PATH = RESULTS_DIR / "pilot20_energy_baseline_scores.csv"
METRICS_PATH = RESULTS_DIR / "pilot20_energy_baseline_metrics.csv"
CONFUSION_PATH = CONFUSION_DIR / "pilot20_energy_baselines_confusion_matrices.csv"
REPORT_PATH = RESULTS_DIR / "pilot20_energy_baseline_report.json"

BASELINES = [
    {
        "baseline": "mean_spilled_energy_abs_delta",
        "score_field": "mean_spilled_energy_abs_delta",
        "description": "Higher mean adjacent-step energy mismatch indicates more inconsistency.",
    },
    {
        "baseline": "max_spilled_energy_abs_delta",
        "score_field": "max_spilled_energy_abs_delta",
        "description": "Higher maximum adjacent-step energy mismatch catches one inconsistent token inside a span.",
    },
    {
        "baseline": "mean_spilled_energy_delta",
        "score_field": "mean_spilled_energy_delta",
        "description": "Signed Spilled Energy delta averaged over the span.",
    },
    {
        "baseline": "negative_mean_spilled_energy_delta",
        "score_field": "negative_mean_spilled_energy_delta",
        "description": "Opposite direction of signed Spilled Energy delta for direction-sensitivity checks.",
    },
    {
        "baseline": "mean_spilled_probability_mass_after_top1",
        "score_field": "mean_spilled_probability_mass_after_top1",
        "description": "Higher non-top1 probability mass indicates a less concentrated token distribution.",
    },
    {
        "baseline": "mean_spilled_probability_mass_after_top2",
        "score_field": "mean_spilled_probability_mass_after_top2",
        "description": "Higher probability mass outside the top two choices indicates diffuse token uncertainty.",
    },
    {
        "baseline": "max_selected_step_energy_gap",
        "score_field": "max_selected_step_energy_gap",
        "description": "Maximum same-step selected-token energy gap; equivalent to a max token NLL control.",
    },
]


def build_score_rows(alignment_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in alignment_records:
        label = str(record["label"])
        y_true = binary_label(label)
        if y_true is None:
            continue
        annotation_id = str(record["annotation_id"])
        mean_spilled_energy_delta = safe_float(
            record["mean_spilled_energy_delta"],
            "mean_spilled_energy_delta",
            annotation_id,
        )
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
                "mean_spilled_energy_delta": mean_spilled_energy_delta,
                "negative_mean_spilled_energy_delta": -mean_spilled_energy_delta,
                "mean_spilled_energy_abs_delta": safe_float(
                    record["mean_spilled_energy_abs_delta"],
                    "mean_spilled_energy_abs_delta",
                    annotation_id,
                ),
                "max_spilled_energy_abs_delta": safe_float(
                    record["max_spilled_energy_abs_delta"],
                    "max_spilled_energy_abs_delta",
                    annotation_id,
                ),
                "mean_selected_step_energy_gap": safe_float(
                    record["mean_selected_step_energy_gap"],
                    "mean_selected_step_energy_gap",
                    annotation_id,
                ),
                "max_selected_step_energy_gap": safe_float(
                    record["max_selected_step_energy_gap"],
                    "max_selected_step_energy_gap",
                    annotation_id,
                ),
                "mean_spilled_probability_mass_after_top1": safe_float(
                    record["mean_spilled_probability_mass_after_top1"],
                    "mean_spilled_probability_mass_after_top1",
                    annotation_id,
                ),
                "mean_spilled_probability_mass_after_top2": safe_float(
                    record["mean_spilled_probability_mass_after_top2"],
                    "mean_spilled_probability_mass_after_top2",
                    annotation_id,
                ),
                "mean_token_nll": safe_float(record["mean_token_nll"], "mean_token_nll", annotation_id),
                "max_token_entropy": safe_float(record["max_token_entropy"], "max_token_entropy", annotation_id),
            }
        )
    return rows


def write_scores(rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "annotation_id",
        "question_id",
        "prompt_id",
        "fact_type",
        "label",
        "binary_label",
        "span_text",
        "token_count",
        "mean_spilled_energy_delta",
        "negative_mean_spilled_energy_delta",
        "mean_spilled_energy_abs_delta",
        "max_spilled_energy_abs_delta",
        "mean_selected_step_energy_gap",
        "max_selected_step_energy_gap",
        "mean_spilled_probability_mass_after_top1",
        "mean_spilled_probability_mass_after_top2",
        "mean_token_nll",
        "max_token_entropy",
    ]
    SCORES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SCORES_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    alignment_report = json.loads(ALIGNMENT_REPORT_PATH.read_text(encoding="utf-8"))
    if not alignment_report.get("ready_for_energy_baselines"):
        raise SystemExit("Energy span-token alignment is not ready for energy baselines")

    score_rows = build_score_rows(load_jsonl(ALIGNMENT_PATH))
    y_true = [int(row["binary_label"]) for row in score_rows]
    positive_count = sum(y_true)
    negative_count = len(y_true) - positive_count
    if positive_count == 0 or negative_count == 0:
        raise SystemExit("Need both positive and negative spans for energy baseline metrics")

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
    report = {
        "input_alignment_path": str(ALIGNMENT_PATH),
        "input_alignment_report_path": str(ALIGNMENT_REPORT_PATH),
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
        "best_f1_lift_over_all_positive": round(float(best_by_f1["f1"]) - float(references["all_positive"]["f1"]), 6),
        "best_auprc_lift_over_positive_prevalence": round(
            float(best_by_auprc["auprc"]) - float(references["positive_prevalence"]),
            6,
        ),
        "interpretation": (
            "Energy-style fields are now usable for span-level baselines. These pilot20 "
            "numbers are diagnostic only because thresholds are selected and evaluated on "
            "the same annotated pilot set."
        ),
        "evaluation_note": (
            "Pilot20 thresholds are selected and evaluated on the same annotated pilot set. "
            "Use these numbers to decide whether the adapter is operational, not as final held-out performance."
        ),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
