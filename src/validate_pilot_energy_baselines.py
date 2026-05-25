from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"

SCORES_PATH = RESULTS_DIR / "pilot20_energy_baseline_scores.csv"
METRICS_PATH = RESULTS_DIR / "pilot20_energy_baseline_metrics.csv"
CONFUSION_PATH = RESULTS_DIR / "confusion_matrices" / "pilot20_energy_baselines_confusion_matrices.csv"
REPORT_PATH = RESULTS_DIR / "pilot20_energy_baseline_report.json"
VALIDATION_PATH = RESULTS_DIR / "pilot20_energy_baseline_validation.json"

EXPECTED_BASELINES = {
    "mean_spilled_energy_abs_delta",
    "max_spilled_energy_abs_delta",
    "mean_spilled_energy_delta",
    "negative_mean_spilled_energy_delta",
    "mean_spilled_probability_mass_after_top1",
    "mean_spilled_probability_mass_after_top2",
    "max_selected_step_energy_gap",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None) -> None:
    failure: dict[str, Any] = {"reason": reason}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def as_int(value: str) -> int:
    return int(float(value))


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path in [SCORES_PATH, METRICS_PATH, CONFUSION_PATH, REPORT_PATH]:
        if not path.exists():
            add_failure(failures, "missing result file", str(path))

    if failures:
        report = {"num_failures": len(failures), "failures": failures}
        VALIDATION_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    scores = read_csv(SCORES_PATH)
    metrics = read_csv(METRICS_PATH)
    confusion_rows = read_csv(CONFUSION_PATH)
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    score_count = len(scores)
    positive_count = sum(1 for row in scores if row.get("binary_label") == "1")
    negative_count = sum(1 for row in scores if row.get("binary_label") == "0")
    if score_count != int(report.get("span_count", -1)):
        add_failure(failures, "score row count mismatch with report", {"scores": score_count, "report": report.get("span_count")})
    if positive_count != int(report.get("positive_count", -1)):
        add_failure(failures, "positive count mismatch with report", {"scores": positive_count, "report": report.get("positive_count")})
    if negative_count != int(report.get("negative_count", -1)):
        add_failure(failures, "negative count mismatch with report", {"scores": negative_count, "report": report.get("negative_count")})
    if positive_count + negative_count != score_count:
        add_failure(failures, "scores contain labels outside binary classes")

    metric_baselines = {row.get("baseline", "") for row in metrics}
    if metric_baselines != EXPECTED_BASELINES:
        add_failure(failures, "metric baseline set mismatch", sorted(metric_baselines))
    if len(metrics) != int(report.get("baseline_count", -1)):
        add_failure(failures, "metric row count mismatch with report", {"metrics": len(metrics), "report": report.get("baseline_count")})

    score_fields = {
        "mean_spilled_energy_delta",
        "negative_mean_spilled_energy_delta",
        "mean_spilled_energy_abs_delta",
        "max_spilled_energy_abs_delta",
        "mean_selected_step_energy_gap",
        "max_selected_step_energy_gap",
        "mean_spilled_probability_mass_after_top1",
        "mean_spilled_probability_mass_after_top2",
    }
    for row in scores:
        for field in score_fields:
            value = float(row[field])
            if value != value:
                add_failure(failures, "NaN score value", {"annotation_id": row["annotation_id"], "field": field})

    confusion_by_baseline: dict[str, dict[tuple[str, str], int]] = {}
    for row in confusion_rows:
        baseline = row["baseline"]
        key = (row["actual"], row["predicted"])
        confusion_by_baseline.setdefault(baseline, {})[key] = as_int(row["count"])

    for row in metrics:
        baseline = row["baseline"]
        confusion = confusion_by_baseline.get(baseline)
        if confusion is None:
            add_failure(failures, "missing confusion rows for baseline", baseline)
            continue
        tp = confusion.get(("positive", "positive"), 0)
        fn = confusion.get(("positive", "negative"), 0)
        fp = confusion.get(("negative", "positive"), 0)
        tn = confusion.get(("negative", "negative"), 0)
        if tp + fp + tn + fn != score_count:
            add_failure(failures, "confusion count does not sum to score rows", {"baseline": baseline, "sum": tp + fp + tn + fn})
        for field, expected in [("tp", tp), ("fp", fp), ("tn", tn), ("fn", fn)]:
            if as_int(row[field]) != expected:
                add_failure(failures, "metric confusion count mismatch", {"baseline": baseline, "field": field})
        for field in ["precision", "recall", "specificity", "f1", "accuracy", "auroc", "auprc"]:
            value = float(row[field])
            if not 0.0 <= value <= 1.0:
                add_failure(failures, "metric outside [0, 1]", {"baseline": baseline, "field": field, "value": value})

    if "not as final held-out performance" not in str(report.get("evaluation_note", "")):
        add_failure(failures, "report missing pilot-only evaluation caveat")
    if report.get("best_by_f1", {}).get("baseline") not in EXPECTED_BASELINES:
        add_failure(failures, "best_by_f1 baseline not recognized", report.get("best_by_f1"))
    if report.get("best_by_auprc", {}).get("baseline") not in EXPECTED_BASELINES:
        add_failure(failures, "best_by_auprc baseline not recognized", report.get("best_by_auprc"))

    validation = {
        "scores_path": str(SCORES_PATH),
        "metrics_path": str(METRICS_PATH),
        "confusion_path": str(CONFUSION_PATH),
        "report_path": str(REPORT_PATH),
        "score_count": score_count,
        "metric_count": len(metrics),
        "confusion_row_count": len(confusion_rows),
        "positive_count": positive_count,
        "negative_count": negative_count,
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
