from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"

DEFAULT_SIMPLE_METRICS_PATH = RESULTS_DIR / "full100_draft_simple_split_metrics.csv"
DEFAULT_SIMPLE_REPORT_PATH = RESULTS_DIR / "full100_draft_simple_split_report.json"
DEFAULT_SIMPLE_VALIDATION_PATH = RESULTS_DIR / "full100_draft_simple_split_validation.json"
DEFAULT_ENERGY_METRICS_PATH = RESULTS_DIR / "full100_draft_energy_split_metrics.csv"
DEFAULT_ENERGY_REPORT_PATH = RESULTS_DIR / "full100_draft_energy_split_report.json"
DEFAULT_ENERGY_VALIDATION_PATH = RESULTS_DIR / "full100_draft_energy_split_validation.json"
DEFAULT_COMPARISON_PATH = RESULTS_DIR / "full100_draft_detector_family_comparison.csv"
DEFAULT_SUMMARY_PATH = RESULTS_DIR / "full100_draft_detector_family_summary.csv"
DEFAULT_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_family_comparison_report.json"

METRIC_FIELDS = ["precision", "recall", "specificity", "f1", "accuracy", "auroc", "auprc"]
COUNT_FIELDS = ["tp", "fp", "tn", "fn", "positive_count", "negative_count"]
COMPARISON_FIELDS = [
    "family",
    "baseline",
    "score_field",
    "score_group",
    "threshold",
    "dev_f1",
    "dev_precision",
    "dev_recall",
    "dev_specificity",
    "test_auprc",
    "test_auroc",
    "test_f1",
    "test_precision",
    "test_recall",
    "test_specificity",
    "test_accuracy",
    "test_tp",
    "test_fp",
    "test_tn",
    "test_fn",
    "test_positive_count",
    "test_negative_count",
    "all_positive_like",
    "threshold_source_split",
    "selection_policy",
    "description",
]
SUMMARY_FIELDS = [
    "family",
    "baseline_count",
    "best_test_auprc_baseline",
    "best_test_auprc",
    "best_test_auprc_f1",
    "best_test_f1_baseline",
    "best_test_f1",
    "best_test_f1_auprc",
    "all_positive_like_count",
]


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def as_float(row: dict[str, str], field: str) -> float:
    return float(row[field])


def rounded(value: float) -> float:
    return round(value, 6)


def score_group(family: str, baseline: str) -> str:
    if family == "simple":
        return "simple_uncertainty"
    if baseline in {"mean_spilled_energy_abs_delta", "max_spilled_energy_abs_delta"}:
        return "pure_adjacent_step_abs_energy"
    if baseline in {"mean_spilled_energy_delta", "negative_mean_spilled_energy_delta"}:
        return "pure_adjacent_step_signed_energy"
    if baseline in {"mean_spilled_probability_mass_after_top1", "mean_spilled_probability_mass_after_top2"}:
        return "probability_mass_control"
    if baseline == "max_selected_step_energy_gap":
        return "same_step_nll_control"
    return "energy_other"


def rows_by_baseline(rows: list[dict[str, str]]) -> dict[str, dict[str, dict[str, str]]]:
    grouped: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        grouped[row["baseline"]][row["evaluated_split"]] = row
    return dict(grouped)


def validate_source(
    failures: list[dict[str, Any]],
    family: str,
    metrics_path: Path,
    report_path: Path,
    validation_path: Path,
    expected_baseline_count: int,
) -> tuple[list[dict[str, str]], dict[str, Any], dict[str, Any]]:
    for path in [metrics_path, report_path, validation_path]:
        if not path.exists():
            failures.append({"family": family, "reason": "missing source file", "path": str(path)})
    if failures and any(failure.get("family") == family for failure in failures):
        return [], {}, {}

    rows = read_csv(metrics_path)
    report = load_json(report_path)
    validation = load_json(validation_path)
    if validation.get("num_failures") != 0:
        failures.append({"family": family, "reason": "source validation has failures", "detail": validation})
    if validation.get("baseline_count") != expected_baseline_count:
        failures.append(
            {
                "family": family,
                "reason": "source baseline count mismatch",
                "actual": validation.get("baseline_count"),
                "expected": expected_baseline_count,
            }
        )
    if validation.get("metric_row_count") != expected_baseline_count * 2:
        failures.append(
            {
                "family": family,
                "reason": "source metric row count mismatch",
                "actual": validation.get("metric_row_count"),
                "expected": expected_baseline_count * 2,
            }
        )
    if report.get("baseline_family") != family:
        failures.append({"family": family, "reason": "report baseline_family mismatch", "actual": report.get("baseline_family")})
    if report.get("ready_for_split_metrics") is not True:
        failures.append({"family": family, "reason": "report not ready_for_split_metrics"})
    return rows, report, validation


def build_comparison_rows(family: str, rows: list[dict[str, str]], failures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output_rows: list[dict[str, Any]] = []
    for baseline, split_rows in sorted(rows_by_baseline(rows).items()):
        if set(split_rows) != {"dev", "test"}:
            failures.append({"family": family, "baseline": baseline, "reason": "missing dev/test metric row"})
            continue
        dev = split_rows["dev"]
        test = split_rows["test"]
        if dev["threshold"] != test["threshold"]:
            failures.append({"family": family, "baseline": baseline, "reason": "test threshold does not reuse dev threshold"})
        for row in [dev, test]:
            if row["threshold_source_split"] != "dev":
                failures.append({"family": family, "baseline": baseline, "reason": "threshold source is not dev", "row": row})
            for field in METRIC_FIELDS:
                value = as_float(row, field)
                if not 0.0 <= value <= 1.0:
                    failures.append(
                        {"family": family, "baseline": baseline, "reason": "metric outside [0, 1]", "field": field, "value": value}
                    )
            for field in COUNT_FIELDS:
                if int(float(row[field])) < 0:
                    failures.append({"family": family, "baseline": baseline, "reason": "negative count", "field": field})

        all_positive_like = as_float(test, "recall") >= 0.95 and as_float(test, "specificity") <= 0.05
        output_rows.append(
            {
                "family": family,
                "baseline": baseline,
                "score_field": test["score_field"],
                "score_group": score_group(family, baseline),
                "threshold": test["threshold"],
                "dev_f1": dev["f1"],
                "dev_precision": dev["precision"],
                "dev_recall": dev["recall"],
                "dev_specificity": dev["specificity"],
                "test_auprc": test["auprc"],
                "test_auroc": test["auroc"],
                "test_f1": test["f1"],
                "test_precision": test["precision"],
                "test_recall": test["recall"],
                "test_specificity": test["specificity"],
                "test_accuracy": test["accuracy"],
                "test_tp": test["tp"],
                "test_fp": test["fp"],
                "test_tn": test["tn"],
                "test_fn": test["fn"],
                "test_positive_count": test["positive_count"],
                "test_negative_count": test["negative_count"],
                "all_positive_like": str(all_positive_like).lower(),
                "threshold_source_split": test["threshold_source_split"],
                "selection_policy": test["selection_policy"],
                "description": test["description"],
            }
        )
    return sorted(output_rows, key=lambda row: (row["family"], row["baseline"]))


def best_row(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    return max(rows, key=lambda row: (float(row[metric]), float(row["test_f1"]), float(row["test_auprc"])))


def family_summary_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for family in sorted({row["family"] for row in rows}):
        family_rows = [row for row in rows if row["family"] == family]
        best_auprc = best_row(family_rows, "test_auprc")
        best_f1 = best_row(family_rows, "test_f1")
        summaries.append(
            {
                "family": family,
                "baseline_count": len(family_rows),
                "best_test_auprc_baseline": best_auprc["baseline"],
                "best_test_auprc": best_auprc["test_auprc"],
                "best_test_auprc_f1": best_auprc["test_f1"],
                "best_test_f1_baseline": best_f1["baseline"],
                "best_test_f1": best_f1["test_f1"],
                "best_test_f1_auprc": best_f1["test_auprc"],
                "all_positive_like_count": sum(row["all_positive_like"] == "true" for row in family_rows),
            }
        )
    return summaries


def metric_delta(left: dict[str, Any], right: dict[str, Any], metric: str) -> float:
    return rounded(float(left[metric]) - float(right[metric]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--simple-metrics-path", default=str(DEFAULT_SIMPLE_METRICS_PATH))
    parser.add_argument("--simple-report-path", default=str(DEFAULT_SIMPLE_REPORT_PATH))
    parser.add_argument("--simple-validation-path", default=str(DEFAULT_SIMPLE_VALIDATION_PATH))
    parser.add_argument("--energy-metrics-path", default=str(DEFAULT_ENERGY_METRICS_PATH))
    parser.add_argument("--energy-report-path", default=str(DEFAULT_ENERGY_REPORT_PATH))
    parser.add_argument("--energy-validation-path", default=str(DEFAULT_ENERGY_VALIDATION_PATH))
    parser.add_argument("--comparison-path", default=str(DEFAULT_COMPARISON_PATH))
    parser.add_argument("--summary-path", default=str(DEFAULT_SUMMARY_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    simple_metrics_path = resolve_project_path(args.simple_metrics_path)
    simple_report_path = resolve_project_path(args.simple_report_path)
    simple_validation_path = resolve_project_path(args.simple_validation_path)
    energy_metrics_path = resolve_project_path(args.energy_metrics_path)
    energy_report_path = resolve_project_path(args.energy_report_path)
    energy_validation_path = resolve_project_path(args.energy_validation_path)
    comparison_path = resolve_project_path(args.comparison_path)
    summary_path = resolve_project_path(args.summary_path)
    report_path = resolve_project_path(args.report_path)

    failures: list[dict[str, Any]] = []
    simple_rows, simple_report, simple_validation = validate_source(
        failures,
        "simple",
        simple_metrics_path,
        simple_report_path,
        simple_validation_path,
        expected_baseline_count=5,
    )
    energy_rows, energy_report, energy_validation = validate_source(
        failures,
        "energy",
        energy_metrics_path,
        energy_report_path,
        energy_validation_path,
        expected_baseline_count=7,
    )

    comparison_rows: list[dict[str, Any]] = []
    if simple_rows:
        comparison_rows.extend(build_comparison_rows("simple", simple_rows, failures))
    if energy_rows:
        comparison_rows.extend(build_comparison_rows("energy", energy_rows, failures))

    if len(comparison_rows) != 12:
        failures.append({"reason": "comparison row count mismatch", "actual": len(comparison_rows), "expected": 12})

    summary_rows = family_summary_rows(comparison_rows) if comparison_rows else []
    if not failures:
        write_csv(comparison_path, COMPARISON_FIELDS, comparison_rows)
        write_csv(summary_path, SUMMARY_FIELDS, summary_rows)

    best_overall_auprc = best_row(comparison_rows, "test_auprc") if comparison_rows else {}
    best_overall_f1 = best_row(comparison_rows, "test_f1") if comparison_rows else {}
    simple_best_auprc = best_row([row for row in comparison_rows if row["family"] == "simple"], "test_auprc") if comparison_rows else {}
    energy_best_auprc = best_row([row for row in comparison_rows if row["family"] == "energy"], "test_auprc") if comparison_rows else {}
    simple_best_f1 = best_row([row for row in comparison_rows if row["family"] == "simple"], "test_f1") if comparison_rows else {}
    energy_best_f1 = best_row([row for row in comparison_rows if row["family"] == "energy"], "test_f1") if comparison_rows else {}
    pure_energy_rows = [
        row
        for row in comparison_rows
        if row["score_group"] in {"pure_adjacent_step_abs_energy", "pure_adjacent_step_signed_energy"}
    ]
    pure_energy_best_auprc = best_row(pure_energy_rows, "test_auprc") if pure_energy_rows else {}
    all_positive_like_rows = [row for row in comparison_rows if row["all_positive_like"] == "true"]

    report = {
        "simple_metrics_path": str(simple_metrics_path),
        "simple_report_path": str(simple_report_path),
        "simple_validation_path": str(simple_validation_path),
        "energy_metrics_path": str(energy_metrics_path),
        "energy_report_path": str(energy_report_path),
        "energy_validation_path": str(energy_validation_path),
        "comparison_path": str(comparison_path),
        "summary_path": str(summary_path),
        "families_compared": ["simple", "energy"],
        "source_metric_row_count": len(simple_rows) + len(energy_rows),
        "comparison_row_count": len(comparison_rows),
        "summary_row_count": len(summary_rows),
        "best_overall_by_test_auprc": best_overall_auprc,
        "best_overall_by_test_f1": best_overall_f1,
        "simple_best_by_test_auprc": simple_best_auprc,
        "energy_best_by_test_auprc": energy_best_auprc,
        "simple_best_by_test_f1": simple_best_f1,
        "energy_best_by_test_f1": energy_best_f1,
        "energy_minus_simple_best_auprc_delta": metric_delta(energy_best_auprc, simple_best_auprc, "test_auprc")
        if comparison_rows
        else None,
        "energy_minus_simple_best_f1_delta": metric_delta(energy_best_f1, simple_best_f1, "test_f1")
        if comparison_rows
        else None,
        "pure_adjacent_step_energy_best_by_test_auprc": pure_energy_best_auprc,
        "all_positive_like_count": len(all_positive_like_rows),
        "all_positive_like_baselines": [
            {"family": row["family"], "baseline": row["baseline"], "test_recall": row["test_recall"], "test_specificity": row["test_specificity"]}
            for row in all_positive_like_rows
        ],
        "interpretation_guardrails": [
            "Compare families on held-out test metrics only after dev-threshold validation.",
            "Do not treat all-positive-like thresholds as evidence of useful specificity.",
            "Separate pure adjacent-step energy fields from probability-mass and same-step NLL controls.",
            "Keep public claims draft until labels are confirmed for presentation.",
        ],
        "simple_source_validation": simple_validation,
        "energy_source_validation": energy_validation,
        "simple_source_ready": simple_report.get("ready_for_split_metrics"),
        "energy_source_ready": energy_report.get("ready_for_split_metrics"),
        "ready_for_interpretation_review": len(failures) == 0,
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
