from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "full100_questions.json"
QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
PROMPTS_PATH = PROJECT_ROOT / "outputs" / "qwen_input_prompts.jsonl"
VALIDATION_PATH = PROJECT_ROOT / "outputs" / "full100_config_validation.json"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None) -> None:
    failures.append({"reason": reason, "detail": detail})


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    questions = load_jsonl(QUESTIONS_PATH)
    prompts = load_jsonl(PROMPTS_PATH)
    question_ids = config.get("question_ids", [])
    generation_args = config.get("generation_command", {}).get("arguments", [])

    questions_by_id = {record["question_id"]: record for record in questions}
    prompts_by_qid = {record["question_id"]: record for record in prompts}
    expected_question_ids = [record["question_id"] for record in questions]

    failures: list[dict[str, Any]] = []
    if len(question_ids) != 100:
        add_failure(failures, "full100 question count is not 100", len(question_ids))
    if len(set(question_ids)) != len(question_ids):
        duplicates = [qid for qid, count in Counter(question_ids).items() if count > 1]
        add_failure(failures, "duplicate question ids", duplicates)
    if question_ids != expected_question_ids:
        add_failure(
            failures,
            "question_ids must exactly match gold question order",
            {
                "missing": sorted(set(expected_question_ids) - set(question_ids)),
                "extra": sorted(set(question_ids) - set(expected_question_ids)),
            },
        )

    missing_prompts = [qid for qid in question_ids if qid not in prompts_by_qid]
    if missing_prompts:
        add_failure(failures, "question ids missing from prompt set", missing_prompts)

    selected = [questions_by_id[qid] for qid in question_ids if qid in questions_by_id]
    split_counts = Counter(record["split"] for record in selected)
    type_counts = Counter(record["question_type"] for record in selected)
    difficulty_counts = Counter(record["difficulty"] for record in selected)

    if dict(split_counts) != config.get("expected_split_counts", {}):
        add_failure(failures, "split counts do not match config", dict(split_counts))
    if dict(type_counts) != config.get("expected_question_type_counts", {}):
        add_failure(failures, "question type counts do not match config", dict(type_counts))
    if dict(difficulty_counts) != config.get("expected_difficulty_counts", {}):
        add_failure(failures, "difficulty counts do not match config", dict(difficulty_counts))

    if "--question-config" not in generation_args or "configs\\full100_questions.json" not in generation_args:
        add_failure(failures, "generation command must use explicit full100 question config", generation_args)
    if "--output-prefix" not in generation_args or "qwen_full100" not in generation_args:
        add_failure(failures, "generation command must use qwen_full100 output prefix", generation_args)
    if "--question-ids" in generation_args or "--limit" in generation_args:
        add_failure(failures, "generation command must not use question-ids or limit for full100", generation_args)

    prompt_mismatches: list[dict[str, Any]] = []
    for qid in question_ids:
        question = questions_by_id.get(qid)
        prompt = prompts_by_qid.get(qid)
        if not question or not prompt:
            continue
        for field in ["question_type", "difficulty", "split", "gold_short_answer"]:
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
        add_failure(failures, "prompt metadata mismatches full100 questions", prompt_mismatches)

    report = {
        "config_path": str(CONFIG_PATH),
        "question_count": len(question_ids),
        "num_failures": len(failures),
        "failures": failures,
        "split_counts": dict(split_counts),
        "question_type_counts": dict(type_counts),
        "difficulty_counts": dict(difficulty_counts),
        "first_question_id": question_ids[0] if question_ids else None,
        "last_question_id": question_ids[-1] if question_ids else None,
        "planned_outputs": config.get("planned_outputs", {}),
        "generation_arguments": generation_args,
    }
    VALIDATION_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
