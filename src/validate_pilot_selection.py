from __future__ import annotations

import json
import csv
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "pilot20_questions.json"
QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
PROMPTS_PATH = PROJECT_ROOT / "outputs" / "qwen_input_prompts.jsonl"
VALIDATION_PATH = PROJECT_ROOT / "outputs" / "pilot20_selection_validation.json"
PREVIEW_PATH = PROJECT_ROOT / "outputs" / "pilot20_selection_preview.csv"

REQUIRED_QUESTION_TYPES = {
    "top_country_month",
    "top_product_month",
    "country_comparison_month",
    "monthly_revenue_change",
    "top3_products_month",
    "product_revenue_share_month",
    "return_impact_month",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None) -> None:
    failures.append({"reason": reason, "detail": detail})


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    question_ids = config.get("question_ids", [])
    expected_type_counts = config.get("expected_question_type_counts", {})
    expected_difficulty_counts = config.get("expected_difficulty_counts", {})
    smoke_ids = set(config.get("included_smoke_test_question_ids", []))

    questions = load_jsonl(QUESTIONS_PATH)
    prompts = load_jsonl(PROMPTS_PATH)
    questions_by_id = {record["question_id"]: record for record in questions}
    prompts_by_qid = {record["question_id"]: record for record in prompts}

    failures: list[dict[str, Any]] = []
    if len(question_ids) != 20:
        add_failure(failures, "pilot question count is not 20", len(question_ids))
    if len(set(question_ids)) != len(question_ids):
        duplicates = [qid for qid, count in Counter(question_ids).items() if count > 1]
        add_failure(failures, "duplicate question ids", duplicates)

    missing_questions = [qid for qid in question_ids if qid not in questions_by_id]
    missing_prompts = [qid for qid in question_ids if qid not in prompts_by_qid]
    if missing_questions:
        add_failure(failures, "question ids missing from gold set", missing_questions)
    if missing_prompts:
        add_failure(failures, "question ids missing from prompt set", missing_prompts)

    selected = [questions_by_id[qid] for qid in question_ids if qid in questions_by_id]
    split_counts = Counter(record["split"] for record in selected)
    type_counts = Counter(record["question_type"] for record in selected)
    difficulty_counts = Counter(record["difficulty"] for record in selected)

    if set(split_counts) != {"train"}:
        add_failure(failures, "pilot selection must use only train split", dict(split_counts))
    if set(type_counts) != REQUIRED_QUESTION_TYPES:
        add_failure(
            failures,
            "pilot selection does not cover exactly the required question types",
            sorted(set(type_counts)),
        )
    if dict(type_counts) != expected_type_counts:
        add_failure(failures, "question type counts do not match config", dict(type_counts))
    if dict(difficulty_counts) != expected_difficulty_counts:
        add_failure(failures, "difficulty counts do not match config", dict(difficulty_counts))

    selected_ids = set(question_ids)
    if not smoke_ids.issubset(selected_ids):
        add_failure(failures, "smoke-test anchor ids missing from pilot", sorted(smoke_ids - selected_ids))

    prompt_mismatches: list[dict[str, Any]] = []
    for qid in question_ids:
        question = questions_by_id.get(qid)
        prompt = prompts_by_qid.get(qid)
        if not question or not prompt:
            continue
        for field in ["question_type", "difficulty", "split"]:
            if question[field] != prompt[field]:
                prompt_mismatches.append(
                    {
                        "question_id": qid,
                        "field": field,
                        "question_value": question[field],
                        "prompt_value": prompt[field],
                    }
                )
    if prompt_mismatches:
        add_failure(failures, "prompt metadata mismatches selected questions", prompt_mismatches)

    report = {
        "config_path": str(CONFIG_PATH),
        "question_count": len(question_ids),
        "num_failures": len(failures),
        "failures": failures,
        "question_ids": question_ids,
        "split_counts": dict(split_counts),
        "question_type_counts": dict(type_counts),
        "difficulty_counts": dict(difficulty_counts),
        "included_smoke_test_question_ids": sorted(smoke_ids),
        "planned_outputs": config.get("planned_outputs", {}),
    }
    with PREVIEW_PATH.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "question_id",
            "split",
            "question_type",
            "difficulty",
            "question",
            "gold_short_answer",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in selected:
            writer.writerow({field: record.get(field, "") for field in fieldnames})

    VALIDATION_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
