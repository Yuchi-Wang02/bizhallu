from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
OUTPUT_PATH = PROJECT_ROOT / "outputs" / "split_eval_smoke_scores.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "split_eval_smoke_scores_report.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def first_question_ids_by_split() -> dict[str, list[str]]:
    ids: dict[str, list[str]] = {"dev": [], "test": []}
    for record in load_jsonl(QUESTIONS_PATH):
        split = str(record["split"])
        if split in ids:
            ids[split].append(str(record["question_id"]))
    if len(ids["dev"]) < 2 or len(ids["test"]) < 2:
        raise ValueError("Need at least two dev and two test questions for split smoke fixture")
    return ids


def main() -> None:
    ids = first_question_ids_by_split()
    dev_a, dev_b = ids["dev"][0], ids["dev"][1]
    test_a, test_b = ids["test"][0], ids["test"][1]
    rows = [
        {
            "annotation_id": "smoke_dev_pos_1",
            "question_id": dev_a,
            "prompt_id": "smoke",
            "fact_type": "smoke",
            "label": "hallucinated_key_fact",
            "binary_label": "1",
            "span_text": "dev positive high score",
            "token_count": "1",
            "score_good": "0.90",
            "score_bad": "0.20",
        },
        {
            "annotation_id": "smoke_dev_pos_2",
            "question_id": dev_b,
            "prompt_id": "smoke",
            "fact_type": "smoke",
            "label": "hallucinated_key_fact",
            "binary_label": "1",
            "span_text": "dev positive medium score",
            "token_count": "1",
            "score_good": "0.80",
            "score_bad": "0.40",
        },
        {
            "annotation_id": "smoke_dev_neg_1",
            "question_id": dev_a,
            "prompt_id": "smoke",
            "fact_type": "smoke",
            "label": "correct_key_fact",
            "binary_label": "0",
            "span_text": "dev negative low score",
            "token_count": "1",
            "score_good": "0.10",
            "score_bad": "0.60",
        },
        {
            "annotation_id": "smoke_dev_neg_2",
            "question_id": dev_b,
            "prompt_id": "smoke",
            "fact_type": "smoke",
            "label": "correct_key_fact",
            "binary_label": "0",
            "span_text": "dev negative lower score",
            "token_count": "1",
            "score_good": "0.20",
            "score_bad": "0.80",
        },
        {
            "annotation_id": "smoke_test_pos_1",
            "question_id": test_a,
            "prompt_id": "smoke",
            "fact_type": "smoke",
            "label": "hallucinated_key_fact",
            "binary_label": "1",
            "span_text": "test positive high score",
            "token_count": "1",
            "score_good": "0.85",
            "score_bad": "0.30",
        },
        {
            "annotation_id": "smoke_test_pos_2",
            "question_id": test_b,
            "prompt_id": "smoke",
            "fact_type": "smoke",
            "label": "hallucinated_key_fact",
            "binary_label": "1",
            "span_text": "test positive medium score",
            "token_count": "1",
            "score_good": "0.70",
            "score_bad": "0.50",
        },
        {
            "annotation_id": "smoke_test_neg_1",
            "question_id": test_a,
            "prompt_id": "smoke",
            "fact_type": "smoke",
            "label": "correct_key_fact",
            "binary_label": "0",
            "span_text": "test negative low score",
            "token_count": "1",
            "score_good": "0.30",
            "score_bad": "0.70",
        },
        {
            "annotation_id": "smoke_test_neg_2",
            "question_id": test_b,
            "prompt_id": "smoke",
            "fact_type": "smoke",
            "label": "correct_key_fact",
            "binary_label": "0",
            "span_text": "test negative lower score",
            "token_count": "1",
            "score_good": "0.15",
            "score_bad": "0.90",
        },
    ]
    fieldnames = [
        "annotation_id",
        "question_id",
        "prompt_id",
        "fact_type",
        "label",
        "binary_label",
        "span_text",
        "token_count",
        "score_good",
        "score_bad",
    ]
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "scores_path": str(OUTPUT_PATH),
        "row_count": len(rows),
        "dev_question_ids": [dev_a, dev_b],
        "test_question_ids": [test_a, test_b],
        "expected_score_good_threshold": 0.8,
        "purpose": "Synthetic fixture for validating dev-threshold/test-evaluation detector logic.",
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
