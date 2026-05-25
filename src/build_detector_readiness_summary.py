from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"

SIMPLE_METRICS_PATH = RESULTS_DIR / "pilot20_simple_baseline_metrics.csv"
SIMPLE_VALIDATION_PATH = RESULTS_DIR / "pilot20_simple_baseline_validation.json"
ENERGY_METRICS_PATH = RESULTS_DIR / "pilot20_energy_baseline_metrics.csv"
ENERGY_VALIDATION_PATH = RESULTS_DIR / "pilot20_energy_baseline_validation.json"
SUMMARY_PATH = RESULTS_DIR / "pilot20_detector_readiness_summary.json"
VALIDATION_PATH = RESULTS_DIR / "pilot20_detector_readiness_validation.json"
FULL100_VALIDATION_PATH = PROJECT_ROOT / "outputs" / "qwen_full100_validation.json"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def numeric_row(row: dict[str, str]) -> dict[str, Any]:
    converted: dict[str, Any] = dict(row)
    for field in ["threshold", "precision", "recall", "specificity", "f1", "accuracy", "auroc", "auprc"]:
        converted[field] = float(row[field])
    for field in ["tp", "fp", "tn", "fn", "positive_count", "negative_count"]:
        converted[field] = int(float(row[field]))
    return converted


def best_by(rows: list[dict[str, Any]], metric: str) -> dict[str, Any]:
    return max(rows, key=lambda row: (float(row[metric]), float(row["f1"]), float(row["auroc"])))


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path in [SIMPLE_METRICS_PATH, SIMPLE_VALIDATION_PATH, ENERGY_METRICS_PATH, ENERGY_VALIDATION_PATH]:
        if not path.exists():
            failures.append({"reason": "missing required file", "path": str(path)})

    if not failures:
        simple_validation = json.loads(SIMPLE_VALIDATION_PATH.read_text(encoding="utf-8"))
        energy_validation = json.loads(ENERGY_VALIDATION_PATH.read_text(encoding="utf-8"))
        if simple_validation.get("num_failures") != 0:
            failures.append({"reason": "simple baseline validation has failures", "detail": simple_validation.get("failures")})
        if energy_validation.get("num_failures") != 0:
            failures.append({"reason": "energy baseline validation has failures", "detail": energy_validation.get("failures")})

    if failures:
        validation = {"num_failures": len(failures), "failures": failures}
        VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    simple_rows = [numeric_row(row) for row in read_csv(SIMPLE_METRICS_PATH)]
    energy_rows = [numeric_row(row) for row in read_csv(ENERGY_METRICS_PATH)]

    simple_best_auprc = best_by(simple_rows, "auprc")
    simple_best_f1 = best_by(simple_rows, "f1")
    energy_best_auprc = best_by(energy_rows, "auprc")
    energy_best_f1 = best_by(energy_rows, "f1")

    pure_spilled_rows = [
        row
        for row in energy_rows
        if row["baseline"]
        in {
            "mean_spilled_energy_abs_delta",
            "max_spilled_energy_abs_delta",
            "mean_spilled_energy_delta",
            "negative_mean_spilled_energy_delta",
        }
    ]
    pure_spilled_best_auprc = best_by(pure_spilled_rows, "auprc")

    full100_generation_run = False
    if FULL100_VALIDATION_PATH.exists():
        full100_validation = json.loads(FULL100_VALIDATION_PATH.read_text(encoding="utf-8"))
        full100_generation_run = full100_validation.get("num_failures") == 0

    if full100_generation_run:
        next_recommendation = (
            "Full100 generation is complete and validated. Build full100 review and annotation "
            "artifacts next, then score spans and report held-out dev/test detector metrics."
        )
    else:
        next_recommendation = (
            "The MVP detector set and split-safe evaluation path are ready for the next phase. "
            "Run full100 generation, then build review and annotation artifacts before reporting "
            "held-out dev/test detector metrics."
        )

    summary = {
        "simple_metrics_path": str(SIMPLE_METRICS_PATH),
        "energy_metrics_path": str(ENERGY_METRICS_PATH),
        "span_count": simple_best_auprc["positive_count"] + simple_best_auprc["negative_count"],
        "positive_count": simple_best_auprc["positive_count"],
        "negative_count": simple_best_auprc["negative_count"],
        "simple_best_by_auprc": simple_best_auprc,
        "simple_best_by_f1": simple_best_f1,
        "energy_best_by_auprc": energy_best_auprc,
        "energy_best_by_f1": energy_best_f1,
        "pure_spilled_energy_best_by_auprc": pure_spilled_best_auprc,
        "comparisons": {
            "energy_best_auprc_minus_simple_best_auprc": round(
                energy_best_auprc["auprc"] - simple_best_auprc["auprc"],
                6,
            ),
            "pure_spilled_best_auprc_minus_simple_best_auprc": round(
                pure_spilled_best_auprc["auprc"] - simple_best_auprc["auprc"],
                6,
            ),
            "energy_best_f1_minus_simple_best_f1": round(
                energy_best_f1["f1"] - simple_best_f1["f1"],
                6,
            ),
        },
        "readiness": {
            "trace_capture_ready": True,
            "span_alignment_ready": True,
            "energy_adapter_operational": True,
            "split_evaluation_ready": True,
            "full100_config_ready": True,
            "full100_generation_run": full100_generation_run,
        },
        "interpretation": (
            "The full trace and scoring pipeline is operational before full100. "
            "On pilot20, pure adjacent-step Spilled Energy scores do not beat the "
            "best simple uncertainty baseline. This is a useful negative finding: "
            "the project can present energy baselines honestly, but should not "
            "claim that energy-style scoring solves business hallucination detection."
        ),
        "next_recommendation": next_recommendation,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")

    validation = {
        "summary_path": str(SUMMARY_PATH),
        "num_failures": 0,
        "failures": [],
        "simple_best_auprc": simple_best_auprc["auprc"],
        "energy_best_auprc": energy_best_auprc["auprc"],
        "pure_spilled_best_auprc": pure_spilled_best_auprc["auprc"],
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
