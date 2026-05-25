from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RESULTS_DIR = PROJECT_ROOT / "results"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
CONFIG_DIR = PROJECT_ROOT / "configs"

DEFAULT_ALIGNMENT_PATH = OUTPUT_DIR / "full100_draft_span_token_alignment.jsonl"
DEFAULT_ALIGNMENT_VALIDATION_PATH = OUTPUT_DIR / "full100_draft_span_token_alignment_validation.json"
DEFAULT_AUDIT_NOTE_REVIEW_VALIDATION_PATH = OUTPUT_DIR / "full100_audit_note_review_validation.json"
DEFAULT_QUESTIONS_PATH = PROCESSED_DIR / "business_questions_gold.jsonl"
DEFAULT_BASELINE_CONFIG_PATH = CONFIG_DIR / "detector_baseline_suite.json"
DEFAULT_SCORES_PATH = RESULTS_DIR / "full100_draft_detector_scores.csv"
DEFAULT_BY_SPLIT_PATH = RESULTS_DIR / "full100_draft_detector_scores_by_split.csv"
DEFAULT_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_scores_report.json"

POSITIVE_LABELS = {"hallucinated_key_fact", "unsupported_claim"}
NEGATIVE_LABELS = {"correct_key_fact"}
BASELINE_FAMILIES = ["simple", "energy"]

OUTPUT_FIELDS = [
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
    "mean_token_nll",
    "mean_token_entropy",
    "max_token_entropy",
    "mean_top2_margin",
    "min_top2_margin",
    "one_minus_mean_top2_margin",
    "one_minus_min_top2_margin",
    "mean_spilled_energy_delta",
    "negative_mean_spilled_energy_delta",
    "mean_spilled_energy_abs_delta",
    "max_spilled_energy_abs_delta",
    "mean_selected_step_energy_gap",
    "max_selected_step_energy_gap",
    "mean_spilled_probability_mass_after_top1",
    "mean_spilled_probability_mass_after_top2",
    "mean_token_logprob",
    "mean_token_energy",
    "mean_marginal_energy",
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


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def binary_label(label: str) -> int:
    if label in POSITIVE_LABELS:
        return 1
    if label in NEGATIVE_LABELS:
        return 0
    raise ValueError(f"Unsupported span label: {label}")


def as_float(record: dict[str, Any], field: str) -> float:
    value = float(record[field])
    if not math.isfinite(value):
        raise ValueError(f"{record.get('annotation_id', 'UNKNOWN')} has non-finite {field}: {value}")
    return value


def format_number(value: Any) -> str:
    if value is None or value == "":
        return ""
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Non-finite score value: {value}")
    return f"{number:.12g}"


def baseline_score_fields(config: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    for family in BASELINE_FAMILIES:
        for item in config.get("families", {}).get(family, []):
            score_field = item["score_field"]
            if score_field not in fields:
                fields.append(score_field)
    return fields


def count_by_split(rows: list[dict[str, Any]]) -> dict[str, Counter[str]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        counts[str(row["split"])][str(row["label"])] += 1
    return dict(counts)


def summarize_score_fields(rows: list[dict[str, Any]], score_fields: list[str]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for field in score_fields:
        values = [float(row[field]) for row in rows]
        summary[field] = {
            "min": round(min(values), 6),
            "max": round(max(values), 6),
            "mean": round(sum(values) / len(values), 6),
        }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--alignment-path", default=str(DEFAULT_ALIGNMENT_PATH))
    parser.add_argument("--alignment-validation-path", default=str(DEFAULT_ALIGNMENT_VALIDATION_PATH))
    parser.add_argument("--audit-note-review-validation-path", default=str(DEFAULT_AUDIT_NOTE_REVIEW_VALIDATION_PATH))
    parser.add_argument("--questions-path", default=str(DEFAULT_QUESTIONS_PATH))
    parser.add_argument("--baseline-config", default=str(DEFAULT_BASELINE_CONFIG_PATH))
    parser.add_argument("--scores-path", default=str(DEFAULT_SCORES_PATH))
    parser.add_argument("--by-split-path", default=str(DEFAULT_BY_SPLIT_PATH))
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT_PATH))
    args = parser.parse_args()

    alignment_path = resolve_project_path(args.alignment_path)
    alignment_validation_path = resolve_project_path(args.alignment_validation_path)
    audit_note_review_validation_path = resolve_project_path(args.audit_note_review_validation_path)
    questions_path = resolve_project_path(args.questions_path)
    baseline_config_path = resolve_project_path(args.baseline_config)
    scores_path = resolve_project_path(args.scores_path)
    by_split_path = resolve_project_path(args.by_split_path)
    report_path = resolve_project_path(args.report_path)

    failures: list[dict[str, Any]] = []
    required_paths = {
        "alignment": alignment_path,
        "alignment_validation": alignment_validation_path,
        "audit_note_review_validation": audit_note_review_validation_path,
        "questions": questions_path,
        "baseline_config": baseline_config_path,
    }
    for name, path in required_paths.items():
        if not path.exists():
            failures.append({"name": name, "reason": "missing required input", "path": str(path)})

    if failures:
        report = {
            "scores_path": str(scores_path),
            "by_split_path": str(by_split_path),
            "baseline_config_path": str(baseline_config_path),
            "metrics_reported": False,
            "ready_for_score_validation": False,
            "num_failures": len(failures),
            "failures": failures,
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    alignment_validation = load_json(alignment_validation_path)
    audit_note_review_validation = load_json(audit_note_review_validation_path)
    if alignment_validation.get("num_failures") != 0 or alignment_validation.get("ready_for_scoring_prep") is not True:
        failures.append(
            {
                "name": "alignment_validation",
                "reason": "alignment validation is not ready for score preparation",
                "detail": alignment_validation,
            }
        )
    if audit_note_review_validation.get("num_failures") != 0 or audit_note_review_validation.get("review_notes_resolved") is not True:
        failures.append(
            {
                "name": "audit_note_review_validation",
                "reason": "audit-note review validation is not resolved",
                "detail": audit_note_review_validation,
            }
        )

    alignment_rows = load_jsonl(alignment_path)
    questions = load_jsonl(questions_path)
    baseline_config = load_json(baseline_config_path)
    questions_by_id = {str(record["question_id"]): record for record in questions}
    score_fields = baseline_score_fields(baseline_config)
    required_alignment_fields = set(OUTPUT_FIELDS) - {
        "split",
        "question_type",
        "difficulty",
        "binary_label",
        "one_minus_mean_top2_margin",
        "one_minus_min_top2_margin",
        "negative_mean_spilled_energy_delta",
    }
    for derived_field in [
        "mean_top2_margin",
        "min_top2_margin",
        "mean_spilled_energy_delta",
    ]:
        required_alignment_fields.add(derived_field)

    score_rows: list[dict[str, Any]] = []
    seen_annotation_ids: set[str] = set()
    for record in alignment_rows:
        annotation_id = str(record.get("annotation_id", ""))
        if not annotation_id:
            failures.append({"reason": "missing annotation_id", "record": record})
            continue
        if annotation_id in seen_annotation_ids:
            failures.append({"annotation_id": annotation_id, "reason": "duplicate annotation_id"})
            continue
        seen_annotation_ids.add(annotation_id)

        missing_fields = sorted(field for field in required_alignment_fields if field not in record)
        if missing_fields:
            failures.append({"annotation_id": annotation_id, "reason": "missing alignment fields", "fields": missing_fields})
            continue

        question_id = str(record["question_id"])
        question = questions_by_id.get(question_id)
        if not question:
            failures.append({"annotation_id": annotation_id, "question_id": question_id, "reason": "missing question metadata"})
            continue

        try:
            mean_top2_margin = as_float(record, "mean_top2_margin")
            min_top2_margin = as_float(record, "min_top2_margin")
            mean_spilled_energy_delta = as_float(record, "mean_spilled_energy_delta")
            row = {
                "annotation_id": annotation_id,
                "question_id": question_id,
                "prompt_id": record["prompt_id"],
                "split": question["split"],
                "question_type": question["question_type"],
                "difficulty": question.get("difficulty", ""),
                "fact_type": record["fact_type"],
                "label": record["label"],
                "binary_label": binary_label(str(record["label"])),
                "span_text": record["span_text"],
                "token_count": int(record["token_count"]),
                "token_start_position": int(record["token_start_position"]),
                "token_end_position": int(record["token_end_position"]),
                "mean_token_nll": format_number(record["mean_token_nll"]),
                "mean_token_entropy": format_number(record["mean_token_entropy"]),
                "max_token_entropy": format_number(record["max_token_entropy"]),
                "mean_top2_margin": format_number(mean_top2_margin),
                "min_top2_margin": format_number(min_top2_margin),
                "one_minus_mean_top2_margin": format_number(1.0 - mean_top2_margin),
                "one_minus_min_top2_margin": format_number(1.0 - min_top2_margin),
                "mean_spilled_energy_delta": format_number(mean_spilled_energy_delta),
                "negative_mean_spilled_energy_delta": format_number(-mean_spilled_energy_delta),
                "mean_spilled_energy_abs_delta": format_number(record["mean_spilled_energy_abs_delta"]),
                "max_spilled_energy_abs_delta": format_number(record["max_spilled_energy_abs_delta"]),
                "mean_selected_step_energy_gap": format_number(record["mean_selected_step_energy_gap"]),
                "max_selected_step_energy_gap": format_number(record["max_selected_step_energy_gap"]),
                "mean_spilled_probability_mass_after_top1": format_number(record["mean_spilled_probability_mass_after_top1"]),
                "mean_spilled_probability_mass_after_top2": format_number(record["mean_spilled_probability_mass_after_top2"]),
                "mean_token_logprob": format_number(record["mean_token_logprob"]),
                "mean_token_energy": format_number(record["mean_token_energy"]),
                "mean_marginal_energy": format_number(record["mean_marginal_energy"]),
            }
        except (KeyError, TypeError, ValueError) as exc:
            failures.append({"annotation_id": annotation_id, "reason": "could not build score row", "detail": str(exc)})
            continue
        score_rows.append(row)

    for field in score_fields:
        if field not in OUTPUT_FIELDS:
            failures.append({"reason": "configured score field is missing from output schema", "score_field": field})

    if failures:
        ready_for_score_validation = False
    else:
        write_csv(scores_path, OUTPUT_FIELDS, score_rows)
        by_split_rows: list[dict[str, Any]] = []
        for split in sorted({row["split"] for row in score_rows}):
            split_rows = [row for row in score_rows if row["split"] == split]
            binary_counts = Counter(str(row["binary_label"]) for row in split_rows)
            by_split_rows.append(
                {
                    "split": split,
                    "question_count": len({row["question_id"] for row in split_rows}),
                    "span_count": len(split_rows),
                    "positive_count": binary_counts.get("1", 0),
                    "negative_count": binary_counts.get("0", 0),
                    "label_counts": json.dumps(dict(sorted(Counter(row["label"] for row in split_rows).items())), ensure_ascii=True),
                    "fact_type_counts": json.dumps(dict(sorted(Counter(row["fact_type"] for row in split_rows).items())), ensure_ascii=True),
                }
            )
        write_csv(
            by_split_path,
            ["split", "question_count", "span_count", "positive_count", "negative_count", "label_counts", "fact_type_counts"],
            by_split_rows,
        )
        ready_for_score_validation = True

    report = {
        "alignment_path": str(alignment_path),
        "alignment_validation_path": str(alignment_validation_path),
        "audit_note_review_validation_path": str(audit_note_review_validation_path),
        "questions_path": str(questions_path),
        "baseline_config_path": str(baseline_config_path),
        "scores_path": str(scores_path),
        "by_split_path": str(by_split_path),
        "row_count": len(score_rows),
        "question_count": len({row["question_id"] for row in score_rows}),
        "split_counts": dict(sorted(Counter(row["split"] for row in score_rows).items())),
        "span_counts_by_split": {split: sum(counter.values()) for split, counter in sorted(count_by_split(score_rows).items())},
        "label_counts": dict(sorted(Counter(row["label"] for row in score_rows).items())),
        "binary_counts": dict(sorted(Counter(str(row["binary_label"]) for row in score_rows).items())),
        "binary_counts_by_split": {
            split: dict(sorted(Counter(str(row["binary_label"]) for row in score_rows if row["split"] == split).items()))
            for split in sorted({row["split"] for row in score_rows})
        },
        "baseline_families": BASELINE_FAMILIES,
        "baseline_score_fields": score_fields,
        "baseline_score_field_count": len(score_fields),
        "score_field_summary": summarize_score_fields(score_rows, score_fields) if score_rows else {},
        "ready_for_score_validation": ready_for_score_validation,
        "allowed_next_step": "validate full100 draft detector score files; do not run split-safe metrics yet",
        "metrics_reported": False,
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
