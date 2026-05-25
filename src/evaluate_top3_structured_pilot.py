from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from statistics import mean
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_PROMPTS_PATH = PROJECT_ROOT / "outputs" / "qwen_top3_structured_prompts.jsonl"
DEFAULT_GENERATION_PREFIX = "qwen_top3_structured_pilot3"
DEFAULT_PILOT_CONFIG_PATH = PROJECT_ROOT / "configs" / "top3_structured_pilot3_questions.json"
DEFAULT_OUTPUT_PREFIX = "top3_structured_pilot3"

EXPECTED_HEADERS = ["rank", "stock_code", "product_name", "net_revenue_gbp"]
AMOUNT_TOLERANCE = 0.01


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a top3 structured-style pilot generation run.")
    parser.add_argument("--prompts-path", default=str(DEFAULT_PROMPTS_PATH), help="Prompt JSONL used for the generation run.")
    parser.add_argument("--generation-prefix", default=DEFAULT_GENERATION_PREFIX, help="Prefix under outputs/ for generation, trace, report, and validation files.")
    parser.add_argument("--pilot-config", default=str(DEFAULT_PILOT_CONFIG_PATH), help="Pilot question config JSON.")
    parser.add_argument("--output-prefix", default=DEFAULT_OUTPUT_PREFIX, help="Prefix under results/ for evaluation outputs.")
    parser.add_argument("--condition-name", default="structured top3", help="Human-readable prompt condition name for report text.")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None) -> None:
    failure: dict[str, Any] = {"reason": reason}
    if detail is not None:
        failure["detail"] = detail
    failures.append(failure)


def normalize_stock_code(value: Any) -> str:
    return str(value).strip().upper()


def normalize_name(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().upper())


def parse_amount(value: str) -> float | None:
    text = value.replace(",", "").replace("GBP", "").replace("gbp", "").replace("\u00a3", "").replace("\u00c2\u00a3", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0))


def amount_matches(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return False
    return abs(left - right) <= AMOUNT_TOLERANCE


def split_markdown_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return False
    for cell in cells:
        compact = cell.replace(" ", "")
        if not compact or any(char not in "-:" for char in compact):
            return False
    return True


def parse_generated_table(text: str) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    issues: list[str] = []
    table_rows = [split_markdown_row(line) for line in text.splitlines()]
    table_rows = [row for row in table_rows if row is not None]
    if not table_rows:
        return [], [], ["no markdown table rows found"]

    headers = [cell.strip().lower() for cell in table_rows[0]]
    data_rows = [row for row in table_rows[1:] if not is_separator_row(row)]
    parsed_rows: list[dict[str, Any]] = []

    for row_index, cells in enumerate(data_rows, start=1):
        if len(cells) != len(EXPECTED_HEADERS):
            issues.append(f"row {row_index} has {len(cells)} columns")
            continue
        rank_text, stock_code, product_name, amount_text = cells
        try:
            rank = int(rank_text)
        except ValueError:
            rank = None
            issues.append(f"row {row_index} rank is not an integer")

        amount = parse_amount(amount_text)
        if amount is None:
            issues.append(f"row {row_index} amount is not parseable")

        parsed_rows.append(
            {
                "rank": rank,
                "stock_code": normalize_stock_code(stock_code),
                "product_name": normalize_name(product_name),
                "net_revenue_gbp": amount,
                "raw_net_revenue_gbp": amount_text.strip(),
            }
        )

    return headers, parsed_rows, issues


def compact_codes(rows: list[dict[str, Any]]) -> str:
    return " > ".join(str(row["stock_code"]) for row in rows)


def compact_gold_rows(rows: list[dict[str, Any]]) -> str:
    return " > ".join(
        f'{row["rank"]}:{normalize_stock_code(row["stock_code"])} GBP {float(row["merchandise_net_revenue"]):.2f}'
        for row in rows
    )


def compact_generated_rows(rows: list[dict[str, Any]]) -> str:
    values = []
    for row in rows:
        amount = row["net_revenue_gbp"]
        amount_text = "NA" if amount is None else f"GBP {amount:.2f}"
        values.append(f'{row["rank"]}:{row["stock_code"]} {amount_text}')
    return " > ".join(values)


def build_evaluation_rows(prompts: list[dict[str, Any]], generations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prompts_by_question_id = {record["question_id"]: record for record in prompts}
    rows: list[dict[str, Any]] = []

    for generation in generations:
        question_id = generation["question_id"]
        prompt_record = prompts_by_question_id[question_id]
        headers, parsed_rows, parse_issues = parse_generated_table(generation["generated_text"])

        gold_rows = generation["gold_answer"]["top_products"]
        evidence_rows = prompt_record["prompt_evidence_rows"]
        evidence_by_code = {normalize_stock_code(row["stock_code"]): row for row in evidence_rows}
        evidence_position_by_code = {
            normalize_stock_code(row["stock_code"]): index for index, row in enumerate(evidence_rows, start=1)
        }

        generated_codes = [row["stock_code"] for row in parsed_rows]
        gold_codes = [normalize_stock_code(row["stock_code"]) for row in gold_rows]
        evidence_codes = [normalize_stock_code(row["stock_code"]) for row in evidence_rows]

        header_valid = headers == EXPECTED_HEADERS
        row_count_valid = len(parsed_rows) == 3
        rank_sequence_valid = [row["rank"] for row in parsed_rows] == [1, 2, 3]
        format_valid = header_valid and row_count_valid and rank_sequence_valid and not parse_issues

        correct_rank_count = sum(1 for generated, gold in zip(generated_codes, gold_codes) if generated == gold)
        gold_presence_count = sum(1 for generated in generated_codes if generated in set(gold_codes))
        evidence_membership_count = sum(1 for generated in generated_codes if generated in evidence_by_code)

        copied_evidence_amount_count = 0
        correct_rank_amount_count = 0
        generated_amounts: list[float] = []
        evidence_positions: list[int] = []

        for index, generated_row in enumerate(parsed_rows):
            generated_code = generated_row["stock_code"]
            generated_amount = generated_row["net_revenue_gbp"]
            if generated_amount is not None:
                generated_amounts.append(float(generated_amount))
            if generated_code in evidence_position_by_code:
                evidence_positions.append(evidence_position_by_code[generated_code])
            evidence_row = evidence_by_code.get(generated_code)
            if evidence_row and amount_matches(generated_amount, float(evidence_row["net_revenue"])):
                copied_evidence_amount_count += 1
            if index < len(gold_rows):
                gold_row = gold_rows[index]
                if generated_code == normalize_stock_code(gold_row["stock_code"]) and amount_matches(
                    generated_amount,
                    float(gold_row["merchandise_net_revenue"]),
                ):
                    correct_rank_amount_count += 1

        is_sorted_by_generated_amount_desc = False
        if len(generated_amounts) == len(parsed_rows) and len(generated_amounts) >= 2:
            is_sorted_by_generated_amount_desc = all(
                generated_amounts[index] >= generated_amounts[index + 1] - AMOUNT_TOLERANCE
                for index in range(len(generated_amounts) - 1)
            )

        evidence_prefix_match_count = 0
        for generated, evidence in zip(generated_codes, evidence_codes):
            if generated != evidence:
                break
            evidence_prefix_match_count += 1

        rows.append(
            {
                "question_id": question_id,
                "prompt_id": generation["prompt_id"],
                "month_label": generation["gold_answer"].get("month_label", ""),
                "format_valid": format_valid,
                "header_valid": header_valid,
                "row_count": len(parsed_rows),
                "rank_sequence_valid": rank_sequence_valid,
                "exact_order_match": generated_codes == gold_codes,
                "set_match": set(generated_codes) == set(gold_codes) and len(generated_codes) == len(gold_codes),
                "correct_rank_count": correct_rank_count,
                "gold_presence_count": gold_presence_count,
                "evidence_membership_count": evidence_membership_count,
                "all_generated_from_evidence": evidence_membership_count == len(parsed_rows) and bool(parsed_rows),
                "copied_evidence_amount_count": copied_evidence_amount_count,
                "correct_rank_amount_count": correct_rank_amount_count,
                "is_sorted_by_generated_amount_desc": is_sorted_by_generated_amount_desc,
                "evidence_prefix_match_count": evidence_prefix_match_count,
                "mean_generated_evidence_position": round(mean(evidence_positions), 3) if evidence_positions else "",
                "generated_stock_codes": " > ".join(generated_codes),
                "gold_stock_codes": " > ".join(gold_codes),
                "evidence_order_stock_codes": " > ".join(evidence_codes),
                "generated_table_compact": compact_generated_rows(parsed_rows),
                "gold_table_compact": compact_gold_rows(gold_rows),
                "parse_issues": "; ".join(parse_issues),
            }
        )

    return rows


def summarize(
    rows: list[dict[str, Any]],
    prompts_path: Path,
    generations_path: Path,
    evaluation_csv_path: Path,
    condition_name: str,
) -> dict[str, Any]:
    total_rank_rows = sum(int(row["row_count"]) for row in rows)
    total_gold_rank_rows = len(rows) * 3
    exact_order_match_count = sum(1 for row in rows if row["exact_order_match"])
    set_match_count = sum(1 for row in rows if row["set_match"])
    format_valid_count = sum(1 for row in rows if row["format_valid"])
    all_generated_from_evidence_count = sum(1 for row in rows if row["all_generated_from_evidence"])
    sorted_output_count = sum(1 for row in rows if row["is_sorted_by_generated_amount_desc"])

    correct_rank_rows = sum(int(row["correct_rank_count"]) for row in rows)
    gold_presence_rows = sum(int(row["gold_presence_count"]) for row in rows)
    evidence_membership_rows = sum(int(row["evidence_membership_count"]) for row in rows)
    copied_evidence_amount_rows = sum(int(row["copied_evidence_amount_count"]) for row in rows)
    correct_rank_amount_rows = sum(int(row["correct_rank_amount_count"]) for row in rows)
    evidence_prefix_rows = sum(int(row["evidence_prefix_match_count"]) for row in rows)

    if exact_order_match_count == len(rows) and rows:
        recommended_next_step = (
            "Compare this control against the shuffled structured condition. If sorted evidence succeeds while shuffled "
            "evidence fails, the next detector work should treat top3 ranking errors as row-selection/sorting failures."
        )
    else:
        recommended_next_step = (
            "This condition still failed despite the structured table contract. Next inspect generated examples before "
            "scaling, then decide whether to continue prompt controls or return to detector work."
        )

    return {
        "generation_path": str(generations_path),
        "prompt_path": str(prompts_path),
        "evaluation_csv_path": str(evaluation_csv_path),
        "condition_name": condition_name,
        "record_count": len(rows),
        "total_gold_rank_rows": total_gold_rank_rows,
        "total_generated_rows_parsed": total_rank_rows,
        "format_valid_count": format_valid_count,
        "exact_order_match_count": exact_order_match_count,
        "set_match_count": set_match_count,
        "correct_rank_rows": correct_rank_rows,
        "gold_presence_rows": gold_presence_rows,
        "evidence_membership_rows": evidence_membership_rows,
        "all_generated_from_evidence_count": all_generated_from_evidence_count,
        "copied_evidence_amount_rows": copied_evidence_amount_rows,
        "correct_rank_amount_rows": correct_rank_amount_rows,
        "sorted_output_count": sorted_output_count,
        "evidence_prefix_rows": evidence_prefix_rows,
        "main_findings": [
            f"The {condition_name} condition produced parseable 3-row tables for {format_valid_count}/{len(rows)} pilot questions.",
            f"It achieved {exact_order_match_count}/{len(rows)} exact top-3 lists and {correct_rank_rows}/{total_gold_rank_rows} rank-position stock codes.",
            f"The model copied evidence rows rather than inventing products: {evidence_membership_rows}/{total_rank_rows} generated rows are from the evidence table.",
            f"It also copied amounts for selected products: {copied_evidence_amount_rows}/{total_rank_rows} generated amounts match the selected evidence row.",
            "Compare evidence-prefix rows with exact accuracy to separate copying behavior from sorting behavior.",
        ],
        "recommended_next_step": recommended_next_step,
    }


def validate_inputs(
    failures: list[dict[str, Any]],
    prompts_path: Path,
    generations_path: Path,
    run_report_path: Path,
    run_validation_path: Path,
    pilot_config_path: Path,
) -> None:
    for path in [prompts_path, generations_path, run_report_path, run_validation_path, pilot_config_path]:
        if not path.exists():
            add_failure(failures, "missing input file", str(path))


def validate_outputs(
    prompts: list[dict[str, Any]],
    generations: list[dict[str, Any]],
    evaluation_rows: list[dict[str, Any]],
    report: dict[str, Any],
    run_report_path: Path,
    run_validation_path: Path,
    pilot_config_path: Path,
    evaluation_csv_path: Path,
    failures: list[dict[str, Any]],
) -> None:
    prompt_ids = {record["question_id"] for record in prompts}
    generation_ids = [record["question_id"] for record in generations]
    if len(generation_ids) != len(set(generation_ids)):
        add_failure(failures, "duplicate generated question_id values", generation_ids)
    missing_prompt_ids = sorted(set(generation_ids) - prompt_ids)
    if missing_prompt_ids:
        add_failure(failures, "generation ids missing from structured prompts", missing_prompt_ids)

    run_report = json.loads(run_report_path.read_text(encoding="utf-8"))
    run_validation = json.loads(run_validation_path.read_text(encoding="utf-8"))
    pilot_config = json.loads(pilot_config_path.read_text(encoding="utf-8"))

    expected_ids = pilot_config.get("question_ids", [])
    if generation_ids != expected_ids:
        add_failure(failures, "generation question order does not match pilot config", {"generation_ids": generation_ids, "expected_ids": expected_ids})
    if int(run_report.get("record_count", -1)) != len(generations):
        add_failure(failures, "run report record_count mismatch", run_report.get("record_count"))
    if int(run_validation.get("num_failures", -1)) != 0:
        add_failure(failures, "generation validation has failures", run_validation.get("failures"))

    if len(evaluation_rows) != len(generations):
        add_failure(failures, "evaluation row count mismatch", {"evaluation": len(evaluation_rows), "generations": len(generations)})
    if int(report.get("record_count", -1)) != len(evaluation_rows):
        add_failure(failures, "report record_count mismatch", report.get("record_count"))
    if int(report.get("total_gold_rank_rows", -1)) != len(evaluation_rows) * 3:
        add_failure(failures, "report total_gold_rank_rows mismatch", report.get("total_gold_rank_rows"))

    csv_rows: list[dict[str, str]]
    with evaluation_csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    if len(csv_rows) != len(evaluation_rows):
        add_failure(failures, "evaluation csv row count mismatch", {"csv": len(csv_rows), "memory": len(evaluation_rows)})


def main() -> None:
    args = parse_args()
    prompts_path = resolve_project_path(args.prompts_path)
    generations_path = PROJECT_ROOT / "outputs" / f"{args.generation_prefix}_generations.jsonl"
    run_report_path = PROJECT_ROOT / "outputs" / f"{args.generation_prefix}_report.json"
    run_validation_path = PROJECT_ROOT / "outputs" / f"{args.generation_prefix}_validation.json"
    pilot_config_path = resolve_project_path(args.pilot_config)
    evaluation_csv_path = PROJECT_ROOT / "results" / f"{args.output_prefix}_evaluation.csv"
    report_path = PROJECT_ROOT / "results" / f"{args.output_prefix}_report.json"
    validation_path = PROJECT_ROOT / "results" / f"{args.output_prefix}_validation.json"

    failures: list[dict[str, Any]] = []
    validate_inputs(failures, prompts_path, generations_path, run_report_path, run_validation_path, pilot_config_path)
    if failures:
        validation = {"num_failures": len(failures), "failures": failures}
        validation_path.parent.mkdir(parents=True, exist_ok=True)
        validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    prompts = load_jsonl(prompts_path)
    generations = load_jsonl(generations_path)
    evaluation_rows = build_evaluation_rows(prompts, generations)
    report = summarize(evaluation_rows, prompts_path, generations_path, evaluation_csv_path, args.condition_name)

    fieldnames = [
        "question_id",
        "prompt_id",
        "month_label",
        "format_valid",
        "header_valid",
        "row_count",
        "rank_sequence_valid",
        "exact_order_match",
        "set_match",
        "correct_rank_count",
        "gold_presence_count",
        "evidence_membership_count",
        "all_generated_from_evidence",
        "copied_evidence_amount_count",
        "correct_rank_amount_count",
        "is_sorted_by_generated_amount_desc",
        "evidence_prefix_match_count",
        "mean_generated_evidence_position",
        "generated_stock_codes",
        "gold_stock_codes",
        "evidence_order_stock_codes",
        "generated_table_compact",
        "gold_table_compact",
        "parse_issues",
    ]
    write_csv(evaluation_csv_path, fieldnames, evaluation_rows)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")

    validate_outputs(
        prompts,
        generations,
        evaluation_rows,
        report,
        run_report_path,
        run_validation_path,
        pilot_config_path,
        evaluation_csv_path,
        failures,
    )
    validation = {
        "evaluation_csv_path": str(evaluation_csv_path),
        "report_path": str(report_path),
        "record_count": len(evaluation_rows),
        "format_valid_count": report["format_valid_count"],
        "exact_order_match_count": report["exact_order_match_count"],
        "correct_rank_rows": report["correct_rank_rows"],
        "total_gold_rank_rows": report["total_gold_rank_rows"],
        "num_failures": len(failures),
        "failures": failures,
    }
    validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
