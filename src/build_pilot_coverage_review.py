from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "pilot20_questions.json"
QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
ANNOTATIONS_PATH = PROJECT_ROOT / "data" / "annotations" / "span_annotations_pilot.jsonl"
PILOT_REVIEW_PATH = PROJECT_ROOT / "outputs" / "pilot20_review.csv"

REPORT_PATH = PROJECT_ROOT / "outputs" / "pilot20_span_coverage_report.json"
BY_QUESTION_PATH = PROJECT_ROOT / "outputs" / "pilot20_span_coverage_by_question.csv"
BY_FACT_TYPE_PATH = PROJECT_ROOT / "outputs" / "pilot20_span_coverage_by_fact_type.csv"

POSITIVE_LABELS = {"hallucinated_key_fact", "unsupported_claim"}
NEGATIVE_LABELS = {"correct_key_fact"}
EXCLUDED_LABELS = {"ambiguous_or_unverifiable", "ignore"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_csv_by_id(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return {row[key]: row for row in csv.DictReader(f)}


def label_group(label: str) -> str:
    if label in POSITIVE_LABELS:
        return "positive"
    if label in NEGATIVE_LABELS:
        return "negative"
    if label in EXCLUDED_LABELS:
        return "excluded"
    return "unknown"


def sorted_counter(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items()))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_question_rows(
    pilot_ids: list[str],
    annotations: list[dict[str, Any]],
    questions_by_id: dict[str, dict[str, Any]],
    review_by_id: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    annotations_by_qid: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for annotation in annotations:
        annotations_by_qid[str(annotation["question_id"])].append(annotation)

    rows: list[dict[str, Any]] = []
    for qid in pilot_ids:
        question = questions_by_id[qid]
        review = review_by_id.get(qid, {})
        question_annotations = annotations_by_qid.get(qid, [])
        label_counts = Counter(str(row["label"]) for row in question_annotations)
        group_counts = Counter(label_group(str(row["label"])) for row in question_annotations)
        fact_types = sorted({str(row["fact_type"]) for row in question_annotations})

        rows.append(
            {
                "question_id": qid,
                "question_type": question["question_type"],
                "difficulty": question["difficulty"],
                "split": question["split"],
                "auto_status": review.get("auto_status", ""),
                "span_count": len(question_annotations),
                "negative_span_count": group_counts["negative"],
                "positive_span_count": group_counts["positive"],
                "excluded_span_count": group_counts["excluded"],
                "correct_key_fact": label_counts["correct_key_fact"],
                "hallucinated_key_fact": label_counts["hallucinated_key_fact"],
                "unsupported_claim": label_counts["unsupported_claim"],
                "ambiguous_or_unverifiable": label_counts["ambiguous_or_unverifiable"],
                "ignore": label_counts["ignore"],
                "fact_types": "|".join(fact_types),
            }
        )
    return rows


def build_fact_type_rows(annotations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for annotation in annotations:
        grouped[str(annotation["fact_type"])].append(annotation)

    rows: list[dict[str, Any]] = []
    for fact_type in sorted(grouped):
        fact_annotations = grouped[fact_type]
        label_counts = Counter(str(row["label"]) for row in fact_annotations)
        group_counts = Counter(label_group(str(row["label"])) for row in fact_annotations)
        rows.append(
            {
                "fact_type": fact_type,
                "span_count": len(fact_annotations),
                "negative_span_count": group_counts["negative"],
                "positive_span_count": group_counts["positive"],
                "excluded_span_count": group_counts["excluded"],
                "correct_key_fact": label_counts["correct_key_fact"],
                "hallucinated_key_fact": label_counts["hallucinated_key_fact"],
                "unsupported_claim": label_counts["unsupported_claim"],
                "question_count": len({str(row["question_id"]) for row in fact_annotations}),
            }
        )
    return rows


def count_by_question_type(question_rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    output: dict[str, dict[str, int]] = {}
    for row in question_rows:
        question_type = str(row["question_type"])
        bucket = output.setdefault(
            question_type,
            {
                "question_count": 0,
                "span_count": 0,
                "negative_span_count": 0,
                "positive_span_count": 0,
                "excluded_span_count": 0,
            },
        )
        bucket["question_count"] += 1
        for field in ["span_count", "negative_span_count", "positive_span_count", "excluded_span_count"]:
            bucket[field] += int(row[field])
    return dict(sorted(output.items()))


def build_readiness(
    pilot_ids: list[str],
    annotations: list[dict[str, Any]],
    question_rows: list[dict[str, Any]],
    fact_type_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    annotated_ids = sorted({str(row["question_id"]) for row in annotations})
    missing_ids = [qid for qid in pilot_ids if qid not in annotated_ids]
    extra_ids = [qid for qid in annotated_ids if qid not in set(pilot_ids)]

    label_counts = Counter(str(row["label"]) for row in annotations)
    group_counts = Counter(label_group(str(row["label"])) for row in annotations)
    question_type_counts = Counter(str(row["question_type"]) for row in question_rows)

    failures: list[str] = []
    warnings: list[str] = []

    if missing_ids:
        failures.append(f"Missing annotations for pilot questions: {missing_ids}")
    if extra_ids:
        failures.append(f"Annotations include non-pilot questions: {extra_ids}")
    if len(annotated_ids) != len(pilot_ids):
        failures.append(f"Expected {len(pilot_ids)} annotated questions, found {len(annotated_ids)}")
    if len(annotations) < 100:
        failures.append(f"Expected at least 100 pilot spans, found {len(annotations)}")
    if group_counts["positive"] == 0 or group_counts["negative"] == 0:
        failures.append("Pilot labels must include both positive and negative spans")
    if any(int(row["span_count"]) < 3 for row in question_rows):
        failures.append("Every pilot answer should have at least 3 labeled spans")

    positive = group_counts["positive"]
    negative = group_counts["negative"]
    balance_ratio = min(positive, negative) / max(positive, negative) if max(positive, negative) else 0.0
    if balance_ratio < 0.5:
        warnings.append(f"Positive/negative span balance is weak: ratio={balance_ratio:.2f}")
    if label_counts["unsupported_claim"] < 5:
        warnings.append("Unsupported claims are rare; do not report unsupported_claim as a separate robust class yet")

    low_fact_types = [row["fact_type"] for row in fact_type_rows if int(row["span_count"]) < 5]
    if low_fact_types:
        warnings.append(f"Fact types with fewer than 5 spans should be treated as qualitative only: {low_fact_types}")

    low_question_types = [question_type for question_type, count in question_type_counts.items() if count < 2]
    if low_question_types:
        warnings.append(f"Question types with fewer than 2 pilot answers: {low_question_types}")

    split_counts = Counter(str(row["split"]) for row in question_rows)
    if len(split_counts) == 1:
        warnings.append(
            f"Pilot annotations are all in split {next(iter(split_counts))}; final metrics still need dev/test separation"
        )

    return {
        "ready_for_pilot_simple_baselines": not failures,
        "failures": failures,
        "warnings": warnings,
        "positive_negative_balance_ratio": round(balance_ratio, 4),
    }


def main() -> None:
    pilot_ids = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["question_ids"]
    questions_by_id = {row["question_id"]: row for row in load_jsonl(QUESTIONS_PATH)}
    annotations = load_jsonl(ANNOTATIONS_PATH)
    review_by_id = load_csv_by_id(PILOT_REVIEW_PATH, "question_id")

    question_rows = build_question_rows(pilot_ids, annotations, questions_by_id, review_by_id)
    fact_type_rows = build_fact_type_rows(annotations)

    write_csv(
        BY_QUESTION_PATH,
        [
            "question_id",
            "question_type",
            "difficulty",
            "split",
            "auto_status",
            "span_count",
            "negative_span_count",
            "positive_span_count",
            "excluded_span_count",
            "correct_key_fact",
            "hallucinated_key_fact",
            "unsupported_claim",
            "ambiguous_or_unverifiable",
            "ignore",
            "fact_types",
        ],
        question_rows,
    )
    write_csv(
        BY_FACT_TYPE_PATH,
        [
            "fact_type",
            "span_count",
            "negative_span_count",
            "positive_span_count",
            "excluded_span_count",
            "correct_key_fact",
            "hallucinated_key_fact",
            "unsupported_claim",
            "question_count",
        ],
        fact_type_rows,
    )

    label_counts = Counter(str(row["label"]) for row in annotations)
    group_counts = Counter(label_group(str(row["label"])) for row in annotations)
    fact_type_counts = Counter(str(row["fact_type"]) for row in annotations)
    split_counts = Counter(str(row["split"]) for row in question_rows)
    difficulty_counts = Counter(str(row["difficulty"]) for row in question_rows)

    report = {
        "annotation_path": str(ANNOTATIONS_PATH),
        "by_question_path": str(BY_QUESTION_PATH),
        "by_fact_type_path": str(BY_FACT_TYPE_PATH),
        "pilot_question_count": len(pilot_ids),
        "annotated_question_count": len({str(row["question_id"]) for row in annotations}),
        "span_count": len(annotations),
        "label_counts": sorted_counter(label_counts),
        "label_group_counts": sorted_counter(group_counts),
        "fact_type_counts": sorted_counter(fact_type_counts),
        "question_type_coverage": count_by_question_type(question_rows),
        "split_counts": sorted_counter(split_counts),
        "difficulty_counts": sorted_counter(difficulty_counts),
        "spans_by_question": {row["question_id"]: int(row["span_count"]) for row in question_rows},
        "readiness": build_readiness(pilot_ids, annotations, question_rows, fact_type_rows),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))

    if report["readiness"]["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
