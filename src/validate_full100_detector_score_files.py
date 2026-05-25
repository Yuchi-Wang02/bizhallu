from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RESULTS_DIR = PROJECT_ROOT / "results"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CONFIG_DIR = PROJECT_ROOT / "configs"

DEFAULT_ALIGNMENT_PATH = OUTPUT_DIR / "full100_draft_span_token_alignment.jsonl"
DEFAULT_QUESTIONS_PATH = PROCESSED_DIR / "business_questions_gold.jsonl"
DEFAULT_BASELINE_CONFIG_PATH = CONFIG_DIR / "detector_baseline_suite.json"
DEFAULT_SCORES_PATH = RESULTS_DIR / "full100_draft_detector_scores.csv"
DEFAULT_BY_SPLIT_PATH = RESULTS_DIR / "full100_draft_detector_scores_by_split.csv"
DEFAULT_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_scores_report.json"
DEFAULT_VALIDATION_PATH = RESULTS_DIR / "full100_draft_detector_scores_validation.json"

POSITIVE_LABELS = {"hallucinated_key_fact", "unsupported_claim"}
NEGATIVE_LABELS = {"correct_key_fact"}
BASELINE_FAMILIES = ["simple", "energy"]
DISALLOWED_METRIC_OUTPUTS = [
    RESULTS_DIR / "full100_draft_detector_metrics.csv",
    RESULTS_DIR / "full100_draft_detector_report.json",
    RESULTS_DIR / "full100_draft_simple_baselines_metrics.csv",
    RESULTS_DIR / "full100_draft_simple_baselines_report.json",
    RESULTS_DIR / "full100_draft_energy_baselines_metrics.csv",
    RESULTS_DIR / "full100_draft_energy_baselines_report.json",
]

REQUIRED_COLUMNS = [
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
    "token_start_position",
    "token_end_position",
]


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


def expected_binary_label(label: str) -> str:
    if label in POSITIVE_LABELS:
        return "1"
    if label in NEGATIVE_LABELS:
        return "0"
    return "INVALID"


def baseline_score_fields(config: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    for family in BASELINE_FAMILIES:
        for item in config.get("families", {}).get(family, []):
            score_field = item["score_field"]
            if score_field not in fields:
                fields.append(score_field)
    return fields


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None) -> None:
    failure: dict[str, Any] = {"reason": reason}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def finite_float(value: str) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def almost_equal(left: float, right: float, tolerance: float = 1e-9) -> bool:
    return abs(left - right) <= tolerance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alignment-path", default=str(DEFAULT_ALIGNMENT_PATH))
    parser.add_argument("--questions-path", default=str(DEFAULT_QUESTIONS_PATH))
    parser.add_argument("--baseline-config", default=str(DEFAULT_BASELINE_CONFIG_PATH))
    parser.add_argument("--scores-path", default=str(DEFAULT_SCORES_PATH))
    parser.add_argument("--by-split-path", default=str(DEFAULT_BY_SPLIT_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--validation-path", default=str(DEFAULT_VALIDATION_PATH))
    parser.add_argument("--expected-row-count", type=int, default=205)
    parser.add_argument("--expected-question-count", type=int, default=35)
    parser.add_argument("--dev-split", default="dev")
    parser.add_argument("--test-split", default="test")
    args = parser.parse_args()

    alignment_path = resolve_project_path(args.alignment_path)
    questions_path = resolve_project_path(args.questions_path)
    baseline_config_path = resolve_project_path(args.baseline_config)
    scores_path = resolve_project_path(args.scores_path)
    by_split_path = resolve_project_path(args.by_split_path)
    report_path = resolve_project_path(args.report_path)
    validation_path = resolve_project_path(args.validation_path)

    failures: list[dict[str, Any]] = []
    required_paths = [alignment_path, questions_path, baseline_config_path, scores_path, by_split_path, report_path]
    for path in required_paths:
        if not path.exists():
            add_failure(failures, "missing required file", str(path))

    if failures:
        validation = {"num_failures": len(failures), "failures": failures}
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    alignment_rows = load_jsonl(alignment_path)
    questions = load_jsonl(questions_path)
    baseline_config = load_json(baseline_config_path)
    rows = read_csv(scores_path)
    by_split_rows = read_csv(by_split_path)
    report = load_json(report_path)

    questions_by_id = {str(record["question_id"]): record for record in questions}
    alignment_by_id = {str(record["annotation_id"]): record for record in alignment_rows}
    score_fields = baseline_score_fields(baseline_config)
    expected_columns = REQUIRED_COLUMNS + score_fields
    score_columns = set(rows[0].keys()) if rows else set()

    if len(rows) != args.expected_row_count:
        add_failure(failures, "score row count mismatch", {"actual": len(rows), "expected": args.expected_row_count})
    if len(alignment_rows) != args.expected_row_count:
        add_failure(
            failures,
            "alignment row count mismatch",
            {"actual": len(alignment_rows), "expected": args.expected_row_count},
        )
    question_count = len({row.get("question_id") for row in rows})
    if question_count != args.expected_question_count:
        add_failure(failures, "question count mismatch", {"actual": question_count, "expected": args.expected_question_count})

    missing_columns = sorted(column for column in expected_columns if column not in score_columns)
    if missing_columns:
        add_failure(failures, "missing score columns", missing_columns)

    annotation_ids = [row.get("annotation_id", "") for row in rows]
    duplicate_annotation_ids = sorted(annotation_id for annotation_id, count in Counter(annotation_ids).items() if count > 1)
    if duplicate_annotation_ids:
        add_failure(failures, "duplicate score annotation ids", duplicate_annotation_ids[:20])
    if set(annotation_ids) != set(alignment_by_id):
        add_failure(
            failures,
            "score annotation ids do not match alignment ids",
            {
                "missing_from_scores": sorted(set(alignment_by_id) - set(annotation_ids))[:20],
                "extra_in_scores": sorted(set(annotation_ids) - set(alignment_by_id))[:20],
            },
        )

    score_field_failures: list[dict[str, Any]] = []
    row_failures: list[dict[str, Any]] = []
    for row in rows:
        annotation_id = row.get("annotation_id", "")
        alignment = alignment_by_id.get(annotation_id)
        question = questions_by_id.get(row.get("question_id", ""))
        if not alignment:
            row_failures.append({"annotation_id": annotation_id, "reason": "missing matching alignment row"})
            continue
        if not question:
            row_failures.append({"annotation_id": annotation_id, "reason": "missing matching question row"})
            continue

        for field in ["question_id", "prompt_id", "fact_type", "label", "span_text"]:
            if str(row.get(field, "")) != str(alignment.get(field, "")):
                row_failures.append(
                    {
                        "annotation_id": annotation_id,
                        "reason": "field mismatch with alignment",
                        "field": field,
                        "score_value": row.get(field),
                        "alignment_value": alignment.get(field),
                    }
                )
        if row.get("split") != question.get("split"):
            row_failures.append({"annotation_id": annotation_id, "reason": "split mismatch with question metadata"})
        if row.get("question_type") != question.get("question_type"):
            row_failures.append({"annotation_id": annotation_id, "reason": "question_type mismatch with question metadata"})
        if row.get("binary_label") != expected_binary_label(str(row.get("label", ""))):
            row_failures.append({"annotation_id": annotation_id, "reason": "binary_label does not match span label"})
        if int(row.get("token_count", "-1")) != int(alignment.get("token_count", -2)):
            row_failures.append({"annotation_id": annotation_id, "reason": "token_count mismatch with alignment"})
        if row.get("split") not in {args.dev_split, args.test_split}:
            row_failures.append({"annotation_id": annotation_id, "reason": "unexpected split", "split": row.get("split")})

        for field in score_fields:
            value = finite_float(row.get(field, ""))
            if value is None:
                score_field_failures.append({"annotation_id": annotation_id, "field": field, "reason": "non-finite score"})
        mean_top2 = finite_float(row.get("mean_top2_margin", ""))
        min_top2 = finite_float(row.get("min_top2_margin", ""))
        one_minus_mean = finite_float(row.get("one_minus_mean_top2_margin", ""))
        one_minus_min = finite_float(row.get("one_minus_min_top2_margin", ""))
        mean_energy_delta = finite_float(row.get("mean_spilled_energy_delta", ""))
        negative_energy_delta = finite_float(row.get("negative_mean_spilled_energy_delta", ""))
        if mean_top2 is not None and one_minus_mean is not None and not almost_equal(one_minus_mean, 1.0 - mean_top2):
            row_failures.append({"annotation_id": annotation_id, "reason": "one_minus_mean_top2_margin derivation mismatch"})
        if min_top2 is not None and one_minus_min is not None and not almost_equal(one_minus_min, 1.0 - min_top2):
            row_failures.append({"annotation_id": annotation_id, "reason": "one_minus_min_top2_margin derivation mismatch"})
        if mean_energy_delta is not None and negative_energy_delta is not None and not almost_equal(
            negative_energy_delta,
            -mean_energy_delta,
        ):
            row_failures.append({"annotation_id": annotation_id, "reason": "negative_mean_spilled_energy_delta derivation mismatch"})

    if row_failures:
        add_failure(failures, "row-level validation failures", row_failures[:50])
    if score_field_failures:
        add_failure(failures, "score-field validation failures", score_field_failures[:50])

    split_counts = Counter(row["split"] for row in rows)
    label_counts = Counter(row["label"] for row in rows)
    binary_counts = Counter(row["binary_label"] for row in rows)
    by_split_binary_counts: dict[str, dict[str, int]] = {}
    for split_name in [args.dev_split, args.test_split]:
        split_rows = [row for row in rows if row["split"] == split_name]
        split_binary = Counter(row["binary_label"] for row in split_rows)
        by_split_binary_counts[split_name] = dict(sorted(split_binary.items()))
        if split_binary.get("1", 0) == 0 or split_binary.get("0", 0) == 0:
            add_failure(
                failures,
                "split must contain positive and negative score rows",
                {"split": split_name, "binary_counts": dict(split_binary)},
            )

    expected_by_split = {
        row["split"]: {
            "question_count": int(row["question_count"]),
            "span_count": int(row["span_count"]),
            "positive_count": int(row["positive_count"]),
            "negative_count": int(row["negative_count"]),
        }
        for row in by_split_rows
    }
    actual_by_split = {}
    for split_name in sorted(split_counts):
        split_rows = [row for row in rows if row["split"] == split_name]
        actual_by_split[split_name] = {
            "question_count": len({row["question_id"] for row in split_rows}),
            "span_count": len(split_rows),
            "positive_count": sum(1 for row in split_rows if row["binary_label"] == "1"),
            "negative_count": sum(1 for row in split_rows if row["binary_label"] == "0"),
        }
    if expected_by_split != actual_by_split:
        add_failure(
            failures,
            "by-split summary does not match score rows",
            {"by_split_file": expected_by_split, "actual": actual_by_split},
        )

    if report.get("metrics_reported") is not False:
        add_failure(failures, "score report must keep metrics_reported=false")
    if report.get("ready_for_score_validation") is not True:
        add_failure(failures, "score report is not ready_for_score_validation")
    if report.get("row_count") != len(rows):
        add_failure(failures, "score report row_count mismatch", {"report": report.get("row_count"), "actual": len(rows)})
    if report.get("baseline_score_field_count") != len(score_fields):
        add_failure(
            failures,
            "score report baseline_score_field_count mismatch",
            {"report": report.get("baseline_score_field_count"), "actual": len(score_fields)},
        )

    disallowed_present = [str(path) for path in DISALLOWED_METRIC_OUTPUTS if path.exists()]
    if disallowed_present:
        add_failure(failures, "full100 metric outputs exist before score-file validation step", disallowed_present)

    validation = {
        "scores_path": str(scores_path),
        "by_split_path": str(by_split_path),
        "report_path": str(report_path),
        "alignment_path": str(alignment_path),
        "baseline_config_path": str(baseline_config_path),
        "row_count": len(rows),
        "question_count": question_count,
        "split_counts": dict(sorted(split_counts.items())),
        "label_counts": dict(sorted(label_counts.items())),
        "binary_counts": dict(sorted(binary_counts.items())),
        "binary_counts_by_split": by_split_binary_counts,
        "baseline_families": BASELINE_FAMILIES,
        "baseline_score_fields": score_fields,
        "baseline_score_field_count": len(score_fields),
        "metrics_reported": False,
        "ready_for_split_safe_metrics": len(failures) == 0,
        "allowed_next_step": "run split-safe detector evaluation with dev-selected thresholds and held-out test reporting",
        "num_failures": len(failures),
        "failures": failures,
    }
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
