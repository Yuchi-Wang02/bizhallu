from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
PROMPTS_PATH = PROJECT_ROOT / "outputs" / "qwen_top3_sorted_control_prompts.jsonl"
REPORT_PATH = PROJECT_ROOT / "outputs" / "qwen_top3_sorted_control_prompts_report.json"
VALIDATION_PATH = PROJECT_ROOT / "outputs" / "qwen_top3_sorted_control_prompts_validation.json"
PILOT3_CONFIG_PATH = PROJECT_ROOT / "configs" / "top3_sorted_control_pilot3_questions.json"

EXPECTED_VARIANT_ID = "top3_sorted_control_v0.1"
EXPECTED_COLUMNS = ["rank", "stock_code", "product_name", "net_revenue_gbp"]
EXPECTED_PILOT3_IDS = ["q_0060", "q_0065", "q_0072"]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def add_failure(failures: list[dict[str, Any]], prompt_id: str, reason: str, detail: Any = None) -> None:
    failure: dict[str, Any] = {"prompt_id": prompt_id, "reason": reason}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def stock_codes(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row.get("stock_code", "")) for row in rows]


def net_revenues(rows: list[dict[str, Any]]) -> list[float]:
    return [float(row["net_revenue"]) for row in rows]


def expected_top3_from_evidence(rows: list[dict[str, Any]]) -> list[str]:
    sorted_rows = sorted(rows, key=lambda row: float(row["net_revenue"]), reverse=True)
    return [str(row["stock_code"]) for row in sorted_rows[:3]]


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path, description in [
        (PROMPTS_PATH, "missing sorted-control prompt jsonl"),
        (REPORT_PATH, "missing sorted-control prompt report"),
        (PILOT3_CONFIG_PATH, "missing sorted-control pilot3 config"),
    ]:
        if not path.exists():
            add_failure(failures, "GLOBAL", description, str(path))

    if failures:
        validation = {"num_failures": len(failures), "failures": failures}
        VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    questions = load_jsonl(QUESTIONS_PATH)
    top3_questions = [record for record in questions if record["question_type"] == "top3_products_month"]
    questions_by_id = {record["question_id"]: record for record in top3_questions}
    prompts = load_jsonl(PROMPTS_PATH)
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    pilot3_config = json.loads(PILOT3_CONFIG_PATH.read_text(encoding="utf-8"))

    if len(prompts) != len(top3_questions):
        add_failure(failures, "GLOBAL", "prompt count does not match top3 question count", {"prompts": len(prompts), "questions": len(top3_questions)})
    if int(report.get("prompt_count", -1)) != len(prompts):
        add_failure(failures, "GLOBAL", "report prompt count mismatch", {"report": report.get("prompt_count"), "prompts": len(prompts)})
    if report.get("variant_id") != EXPECTED_VARIANT_ID:
        add_failure(failures, "GLOBAL", "report variant_id mismatch", report.get("variant_id"))

    prompt_ids = [record.get("prompt_id") for record in prompts]
    if len(prompt_ids) != len(set(prompt_ids)):
        add_failure(failures, "GLOBAL", "duplicate prompt_id values")

    prompt_question_ids = {record.get("question_id") for record in prompts}
    if prompt_question_ids != set(questions_by_id):
        add_failure(
            failures,
            "GLOBAL",
            "question_id set mismatch",
            {"missing": sorted(set(questions_by_id) - prompt_question_ids), "extra": sorted(prompt_question_ids - set(questions_by_id))},
        )

    pilot3_question_ids = pilot3_config.get("question_ids", [])
    if pilot3_question_ids != EXPECTED_PILOT3_IDS:
        add_failure(failures, "GLOBAL", "pilot3 question ids changed unexpectedly", pilot3_question_ids)
    if pilot3_config.get("source_prompt_file") != "outputs/qwen_top3_sorted_control_prompts.jsonl":
        add_failure(failures, "GLOBAL", "pilot3 config source prompt file mismatch", pilot3_config.get("source_prompt_file"))
    planned_command = str(pilot3_config.get("planned_command", ""))
    if "--prompts-path outputs/qwen_top3_sorted_control_prompts.jsonl" not in planned_command:
        add_failure(failures, "GLOBAL", "pilot3 planned command missing sorted-control prompts path")

    required_fields = {
        "prompt_id",
        "question_id",
        "question_type",
        "difficulty",
        "split",
        "variant_id",
        "base_template_version",
        "row_order_policy",
        "variant_purpose",
        "benchmark_fairness_note",
        "messages",
        "full_prompt",
        "evidence_table_markdown",
        "prompt_evidence_rows",
        "structured_response_contract",
        "expected_output_rows_for_validation_only",
        "gold_answer",
        "gold_facts",
        "gold_short_answer",
        "source_question_record",
    }

    for record in prompts:
        prompt_id = str(record.get("prompt_id", "UNKNOWN"))
        missing = sorted(required_fields - set(record))
        if missing:
            add_failure(failures, prompt_id, "missing required fields", missing)
            continue

        question = questions_by_id.get(record["question_id"])
        if question is None:
            add_failure(failures, prompt_id, "unknown top3 question_id")
            continue

        if record["question_type"] != "top3_products_month":
            add_failure(failures, prompt_id, "non-top3 question included")
        if record["variant_id"] != EXPECTED_VARIANT_ID:
            add_failure(failures, prompt_id, "variant_id mismatch")
        if not prompt_id.endswith("_top3_sorted_control"):
            add_failure(failures, prompt_id, "prompt_id missing sorted-control suffix")
        if record["difficulty"] != question["difficulty"] or record["split"] != question["split"]:
            add_failure(failures, prompt_id, "difficulty or split mismatch with question")
        if record["gold_short_answer"] != question["gold_short_answer"]:
            add_failure(failures, prompt_id, "gold_short_answer mismatch with question")
        if record["row_order_policy"] != "sorted_by_net_revenue_desc_control":
            add_failure(failures, prompt_id, "row order policy mismatch")

        contract = record["structured_response_contract"]
        if contract.get("columns") != EXPECTED_COLUMNS:
            add_failure(failures, prompt_id, "structured columns mismatch", contract.get("columns"))
        if contract.get("row_count") != 3:
            add_failure(failures, prompt_id, "structured row count should be 3")
        if contract.get("rank_metric") != "net_revenue_gbp" or contract.get("sort_order") != "descending":
            add_failure(failures, prompt_id, "rank contract mismatch", contract)

        full_prompt = record["full_prompt"]
        required_phrases = [
            "For this control run only, the evidence table is already sorted by net_revenue_gbp in descending order.",
            "This condition is used to test copying and rank binding, not final benchmark fairness.",
            "Return exactly one markdown table and no extra prose.",
            "| rank | stock_code | product_name | net_revenue_gbp |",
            "First determine the top 3 rows by net_revenue_gbp in descending order.",
        ]
        for phrase in required_phrases:
            if phrase not in full_prompt:
                add_failure(failures, prompt_id, "missing sorted-control instruction", phrase)
        if question["question"] not in full_prompt:
            add_failure(failures, prompt_id, "question text missing from prompt")
        if question["gold_short_answer"] in full_prompt:
            add_failure(failures, prompt_id, "exact gold short answer leaked into prompt")
        if "gold_answer" in full_prompt.lower() or "gold short answer" in full_prompt.lower():
            add_failure(failures, prompt_id, "prompt mentions gold answer")

        messages = record["messages"]
        if len(messages) != 2 or messages[0].get("role") != "system" or messages[1].get("role") != "user":
            add_failure(failures, prompt_id, "messages should be system then user")

        evidence_rows = record["prompt_evidence_rows"]
        if set(stock_codes(evidence_rows)) != set(stock_codes(question["evidence"]["rows"])):
            add_failure(failures, prompt_id, "evidence stock code set mismatch")
        revenues = net_revenues(evidence_rows)
        if revenues != sorted(revenues, reverse=True):
            add_failure(failures, prompt_id, "evidence rows are not sorted by answer metric", revenues)

        expected_output = record["expected_output_rows_for_validation_only"]
        expected_codes = expected_top3_from_evidence(question["evidence"]["rows"])
        if [str(row["stock_code"]) for row in expected_output] != expected_codes:
            add_failure(failures, prompt_id, "expected output rows do not match evidence top3")
        if stock_codes(evidence_rows[:3]) != expected_codes:
            add_failure(failures, prompt_id, "first three sorted evidence rows do not match gold top3")
        if [row["rank"] for row in expected_output] != [1, 2, 3]:
            add_failure(failures, prompt_id, "expected output ranks are not 1,2,3")

    split_counts: dict[str, int] = {}
    difficulty_counts: dict[str, int] = {}
    for record in prompts:
        split_counts[str(record.get("split"))] = split_counts.get(str(record.get("split")), 0) + 1
        difficulty_counts[str(record.get("difficulty"))] = difficulty_counts.get(str(record.get("difficulty")), 0) + 1

    validation = {
        "prompts_path": str(PROMPTS_PATH),
        "report_path": str(REPORT_PATH),
        "prompt_count": len(prompts),
        "variant_id": EXPECTED_VARIANT_ID,
        "question_ids": [record.get("question_id") for record in prompts],
        "pilot3_question_ids": pilot3_question_ids,
        "split_counts": dict(sorted(split_counts.items())),
        "difficulty_counts": dict(sorted(difficulty_counts.items())),
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
