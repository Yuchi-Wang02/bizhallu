from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from build_prompts import QUESTIONS_PATH, markdown_table, system_prompt
from build_top3_structured_prompts import format_currency, load_questions, structured_user_prompt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
CONFIG_DIR = PROJECT_ROOT / "configs"

VARIANT_ID = "top3_sorted_control_v0.1"
PROMPTS_JSONL = OUTPUT_DIR / "qwen_top3_sorted_control_prompts.jsonl"
PROMPTS_SAMPLE_CSV = OUTPUT_DIR / "qwen_top3_sorted_control_prompts_sample.csv"
PROMPTS_REPORT = OUTPUT_DIR / "qwen_top3_sorted_control_prompts_report.json"
PILOT3_CONFIG = CONFIG_DIR / "top3_sorted_control_pilot3_questions.json"

PILOT3_QUESTION_IDS = ["q_0060", "q_0065", "q_0072"]


def sorted_control_rows(record: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(record["evidence"]["rows"], key=lambda row: float(row["net_revenue"]), reverse=True)


def sorted_control_user_prompt(record: dict[str, Any], evidence_table: str) -> str:
    prompt = structured_user_prompt(record, evidence_table)
    return prompt.replace(
        "Structured response requirements:\n",
        (
            "Diagnostic control note:\n"
            "- For this control run only, the evidence table is already sorted by net_revenue_gbp in descending order.\n"
            "- This condition is used to test copying and rank binding, not final benchmark fairness.\n\n"
            "Structured response requirements:\n"
        ),
    )


def build_prompt_record(record: dict[str, Any]) -> dict[str, Any]:
    rows = sorted_control_rows(record)
    table = markdown_table(rows)
    sys_prompt = system_prompt()
    usr_prompt = sorted_control_user_prompt(record, table)
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": usr_prompt},
    ]
    top_products = record["gold_answer"]["top_products"]
    expected_output_rows = [
        {
            "rank": item["rank"],
            "stock_code": item["stock_code"],
            "product_name": item["description"],
            "net_revenue_gbp": format_currency(item["merchandise_net_revenue"]),
        }
        for item in top_products
    ]

    return {
        "prompt_id": f"p_{record['question_id'][2:]}_top3_sorted_control",
        "question_id": record["question_id"],
        "question_type": record["question_type"],
        "difficulty": record["difficulty"],
        "split": record["split"],
        "variant_id": VARIANT_ID,
        "base_template_version": "bizhallu_prompt_v0.1",
        "row_order_policy": "sorted_by_net_revenue_desc_control",
        "variant_purpose": (
            "Diagnostic control to isolate whether top3 failures come from sorting shuffled evidence "
            "or from copying/rank binding after the evidence is already sorted."
        ),
        "benchmark_fairness_note": "Do not use this condition as the final benchmark prompt because row order reveals the top3 answer.",
        "messages": messages,
        "full_prompt": f"System:\n{sys_prompt}\n\nUser:\n{usr_prompt}",
        "evidence_table_markdown": table,
        "prompt_evidence_rows": rows,
        "structured_response_contract": {
            "format": "markdown_table",
            "columns": ["rank", "stock_code", "product_name", "net_revenue_gbp"],
            "row_count": 3,
            "rank_metric": "net_revenue_gbp",
            "sort_order": "descending",
        },
        "expected_output_rows_for_validation_only": expected_output_rows,
        "gold_answer": record["gold_answer"],
        "gold_facts": record["gold_facts"],
        "gold_short_answer": record["gold_short_answer"],
        "source_question_record": {
            "question": record["question"],
            "evidence_source": record["evidence"]["source_file"],
            "evidence_filters": record["evidence"]["filters"],
            "evidence_metadata": record["evidence"].get("metadata", {}),
        },
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")


def write_sample(path: Path, records: list[dict[str, Any]]) -> None:
    fieldnames = [
        "prompt_id",
        "question_id",
        "split",
        "difficulty",
        "row_order_policy",
        "question",
        "expected_top3",
        "prompt_preview",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "prompt_id": record["prompt_id"],
                    "question_id": record["question_id"],
                    "split": record["split"],
                    "difficulty": record["difficulty"],
                    "row_order_policy": record["row_order_policy"],
                    "question": record["source_question_record"]["question"],
                    "expected_top3": json.dumps(record["expected_output_rows_for_validation_only"], ensure_ascii=False),
                    "prompt_preview": " ".join(record["full_prompt"][:760].split()),
                }
            )


def write_pilot_config() -> None:
    config = {
        "name": "top3_sorted_control_pilot3",
        "version": "0.1",
        "purpose": (
            "Diagnostic control for the same three top3 ranking failures. Evidence rows are sorted by net_revenue_gbp "
            "descending to test copying and rank binding without requiring the model to sort shuffled rows."
        ),
        "source_prompt_file": "outputs/qwen_top3_sorted_control_prompts.jsonl",
        "selection_policy": {
            "record_count": 3,
            "split": "train_only",
            "requirements": [
                "use the same question ids as top3_structured_pilot3",
                "keep this as a diagnostic control rather than a final benchmark prompt",
                "compare exact top3 accuracy against the shuffled structured condition",
            ],
        },
        "question_ids": PILOT3_QUESTION_IDS,
        "planned_command": (
            "& C:\\Users\\yuchi\\anaconda3\\envs\\torch\\python.exe src/run_qwen_batch.py "
            "--prompts-path outputs/qwen_top3_sorted_control_prompts.jsonl "
            "--question-config configs/top3_sorted_control_pilot3_questions.json "
            "--output-prefix qwen_top3_sorted_control_pilot3 --greedy --max-new-tokens 140"
        ),
        "planned_outputs": {
            "generations": "outputs/qwen_top3_sorted_control_pilot3_generations.jsonl",
            "token_traces": "outputs/qwen_top3_sorted_control_pilot3_token_traces.jsonl",
            "run_report": "outputs/qwen_top3_sorted_control_pilot3_report.json",
            "validation": "outputs/qwen_top3_sorted_control_pilot3_validation.json",
        },
    }
    PILOT3_CONFIG.write_text(json.dumps(config, indent=2, ensure_ascii=True), encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    questions = [record for record in load_questions() if record["question_type"] == "top3_products_month"]
    prompts = [build_prompt_record(record) for record in questions]
    write_jsonl(PROMPTS_JSONL, prompts)
    write_sample(PROMPTS_SAMPLE_CSV, prompts)
    write_pilot_config()

    report = {
        "variant_id": VARIANT_ID,
        "prompt_count": len(prompts),
        "question_ids": [record["question_id"] for record in prompts],
        "split_counts": dict(sorted({split: sum(1 for record in prompts if record["split"] == split) for split in {record["split"] for record in prompts}}.items())),
        "difficulty_counts": dict(
            sorted({difficulty: sum(1 for record in prompts if record["difficulty"] == difficulty) for difficulty in {record["difficulty"] for record in prompts}}.items())
        ),
        "row_order_policy_counts": dict(
            sorted({policy: sum(1 for record in prompts if record["row_order_policy"] == policy) for policy in {record["row_order_policy"] for record in prompts}}.items())
        ),
        "pilot3_question_ids": PILOT3_QUESTION_IDS,
        "design_note": (
            "This is a diagnostic control. The evidence table is sorted by net_revenue_gbp descending, "
            "so the condition should not be used for final fairness claims."
        ),
        "outputs": {
            "jsonl": str(PROMPTS_JSONL),
            "sample_csv": str(PROMPTS_SAMPLE_CSV),
            "pilot3_config": str(PILOT3_CONFIG),
        },
        "source_questions_path": str(QUESTIONS_PATH),
    }
    PROMPTS_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
