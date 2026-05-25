from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None) -> None:
    failure: dict[str, Any] = {"reason": reason}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-prefix", required=True)
    parser.add_argument("--expected-baseline-count", type=int, required=True)
    parser.add_argument("--dev-split", default="dev")
    parser.add_argument("--test-split", default="test")
    args = parser.parse_args()

    metrics_path = RESULTS_DIR / f"{args.output_prefix}_metrics.csv"
    report_path = RESULTS_DIR / f"{args.output_prefix}_report.json"
    validation_path = RESULTS_DIR / f"{args.output_prefix}_validation.json"

    failures: list[dict[str, Any]] = []
    for path in [metrics_path, report_path]:
        if not path.exists():
            add_failure(failures, "missing split evaluation file", str(path))

    if failures:
        validation = {"num_failures": len(failures), "failures": failures}
        validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    rows = read_csv(metrics_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    baselines = sorted({row["baseline"] for row in rows})
    if len(baselines) != args.expected_baseline_count:
        add_failure(failures, "baseline count mismatch", {"actual": len(baselines), "expected": args.expected_baseline_count})
    expected_metric_rows = args.expected_baseline_count * 2
    if len(rows) != expected_metric_rows:
        add_failure(failures, "metric row count mismatch", {"actual": len(rows), "expected": expected_metric_rows})
    if not report.get("ready_for_split_metrics"):
        add_failure(failures, "report is not ready_for_split_metrics")
    if report.get("num_failures") != 0:
        add_failure(failures, "report contains failures", report.get("failures"))
    if report.get("dev_split") != args.dev_split or report.get("test_split") != args.test_split:
        add_failure(
            failures,
            "split names mismatch",
            {"dev": report.get("dev_split"), "test": report.get("test_split")},
        )

    rows_by_baseline: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        rows_by_baseline.setdefault(row["baseline"], {})[row["evaluated_split"]] = row
        if row["threshold_source_split"] != args.dev_split:
            add_failure(failures, "threshold source is not dev", row)
        if row["selection_policy"] != "threshold_selected_on_dev_split_max_f1":
            add_failure(failures, "unexpected selection policy", row)
        for field in ["precision", "recall", "specificity", "f1", "accuracy", "auroc", "auprc"]:
            value = float(row[field])
            if not 0.0 <= value <= 1.0:
                add_failure(failures, "metric outside [0, 1]", {"field": field, "value": value, "row": row})
        for field in ["tp", "fp", "tn", "fn", "positive_count", "negative_count"]:
            if int(float(row[field])) < 0:
                add_failure(failures, "negative count", {"field": field, "row": row})

    for baseline, split_rows in rows_by_baseline.items():
        if set(split_rows) != {args.dev_split, args.test_split}:
            add_failure(failures, "baseline missing dev/test row", {"baseline": baseline, "splits": sorted(split_rows)})
            continue
        if split_rows[args.dev_split]["threshold"] != split_rows[args.test_split]["threshold"]:
            add_failure(failures, "test threshold does not reuse dev threshold", {"baseline": baseline})
        for split_name, row in split_rows.items():
            total = int(float(row["tp"])) + int(float(row["fp"])) + int(float(row["tn"])) + int(float(row["fn"]))
            expected_total = int(float(row["positive_count"])) + int(float(row["negative_count"]))
            if total != expected_total:
                add_failure(failures, "confusion total mismatch", {"baseline": baseline, "split": split_name})

    validation = {
        "metrics_path": str(metrics_path),
        "report_path": str(report_path),
        "metric_row_count": len(rows),
        "baseline_count": len(baselines),
        "dev_split": args.dev_split,
        "test_split": args.test_split,
        "num_failures": len(failures),
        "failures": failures,
    }
    validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
