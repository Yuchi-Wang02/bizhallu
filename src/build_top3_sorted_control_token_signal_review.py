from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from build_span_token_alignment import build_token_char_spans, overlapping_tokens, summarize_scores
from evaluate_top3_structured_pilot import amount_matches, normalize_name, normalize_stock_code, parse_amount


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RESULTS_DIR = PROJECT_ROOT / "results"

PROMPTS_PATH = OUTPUT_DIR / "qwen_top3_sorted_control_prompts.jsonl"
GENERATIONS_PATH = OUTPUT_DIR / "qwen_top3_sorted_control_pilot3_generations.jsonl"
TRACES_PATH = OUTPUT_DIR / "qwen_top3_sorted_control_pilot3_token_traces.jsonl"
EVALUATION_PATH = RESULTS_DIR / "top3_sorted_control_pilot3_evaluation.csv"
PILOT_BASELINE_REPORT_PATH = RESULTS_DIR / "pilot20_simple_baseline_report.json"

SIGNAL_SPANS_CSV = RESULTS_DIR / "top3_sorted_control_token_signal_spans.csv"
SIGNAL_SUMMARY_JSON = RESULTS_DIR / "top3_sorted_control_token_signal_summary.json"
VALIDATION_JSON = RESULTS_DIR / "top3_sorted_control_token_signal_validation.json"

EXPECTED_QUESTION_IDS = ["q_0060", "q_0065", "q_0072"]
EXPECTED_HEADERS = ["rank", "stock_code", "product_name", "net_revenue_gbp"]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


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


def line_offsets(text: str) -> list[tuple[int, str]]:
    offsets: list[tuple[int, str]] = []
    cursor = 0
    for line in text.splitlines(keepends=True):
        offsets.append((cursor, line.rstrip("\r\n")))
        cursor += len(line)
    return offsets


def trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return start, end


def is_separator_line(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if not cells:
        return False
    for cell in cells:
        compact = cell.replace(" ", "")
        if not compact or any(char not in "-:" for char in compact):
            return False
    return True


def parse_table_cells_with_offsets(generated_text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    failures: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    data_row_index = 0

    for line_start, line in line_offsets(generated_text):
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        if [cell.strip().lower() for cell in stripped.strip("|").split("|")] == EXPECTED_HEADERS:
            continue
        if is_separator_line(stripped):
            continue

        pipe_positions = [index for index, char in enumerate(line) if char == "|"]
        if len(pipe_positions) != len(EXPECTED_HEADERS) + 1:
            failures.append({"reason": "unexpected markdown pipe count", "line": line})
            continue

        data_row_index += 1
        row_start, row_end = trim_span(generated_text, line_start + pipe_positions[0] + 1, line_start + pipe_positions[-1])
        cells: dict[str, dict[str, Any]] = {}
        for index, header in enumerate(EXPECTED_HEADERS):
            cell_start = line_start + pipe_positions[index] + 1
            cell_end = line_start + pipe_positions[index + 1]
            cell_start, cell_end = trim_span(generated_text, cell_start, cell_end)
            cells[header] = {
                "text": generated_text[cell_start:cell_end],
                "start": cell_start,
                "end": cell_end,
            }

        try:
            rank = int(cells["rank"]["text"])
        except ValueError:
            rank = data_row_index
            failures.append({"reason": "rank cell is not an integer", "text": cells["rank"]["text"]})

        rows.append(
            {
                "table_row_index": data_row_index,
                "rank": rank,
                "row_text": generated_text[row_start:row_end],
                "row_start": row_start,
                "row_end": row_end,
                "cells": cells,
                "stock_code": normalize_stock_code(cells["stock_code"]["text"]),
                "product_name": normalize_name(cells["product_name"]["text"]),
                "net_revenue_gbp": parse_amount(cells["net_revenue_gbp"]["text"]),
            }
        )

    return rows, failures


def baseline_thresholds() -> dict[str, float]:
    report = json.loads(PILOT_BASELINE_REPORT_PATH.read_text(encoding="utf-8"))
    return {
        "max_token_entropy": float(report["best_by_auprc"]["threshold"]),
        "one_minus_min_top2_margin": float(report["best_by_f1"]["threshold"]),
    }


def score_span(
    token_spans: list[dict[str, Any]],
    span_start: int,
    span_end: int,
    thresholds: dict[str, float],
) -> dict[str, Any]:
    tokens = overlapping_tokens(token_spans, span_start, span_end)
    scores = summarize_scores(tokens)
    min_top2_margin = scores["min_top2_margin"]
    one_minus_min_top2_margin = None if min_top2_margin is None else round(1.0 - float(min_top2_margin), 6)
    max_token_entropy = scores["max_token_entropy"]
    predicted_by_entropy = max_token_entropy is not None and float(max_token_entropy) >= thresholds["max_token_entropy"]
    predicted_by_margin = (
        one_minus_min_top2_margin is not None
        and one_minus_min_top2_margin >= thresholds["one_minus_min_top2_margin"]
    )
    return {
        "token_count": len(tokens),
        **scores,
        "one_minus_min_top2_margin": one_minus_min_top2_margin,
        "predict_positive_max_token_entropy": predicted_by_entropy,
        "predict_positive_one_minus_min_top2_margin": predicted_by_margin,
        "predict_positive_any_selected_baseline": predicted_by_entropy or predicted_by_margin,
        "token_positions": " ".join(str(token["position"]) for token in tokens),
        "token_texts": " ".join(str(token["token_text"]).replace("\n", "\\n") for token in tokens),
    }


def row_reason(row: dict[str, Any], gold_row: dict[str, Any], evidence_position: int | None) -> str:
    generated_code = row["stock_code"]
    expected_code = normalize_stock_code(gold_row["stock_code"])
    if generated_code == expected_code:
        return "rank-bound row matches gold"
    position_text = "unknown" if evidence_position is None else str(evidence_position)
    return f"rank {row['rank']} should be {expected_code}, generated {generated_code} from evidence position {position_text}"


def build_signal_rows() -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    failures: list[dict[str, Any]] = []
    prompts = load_jsonl(PROMPTS_PATH)
    generations = load_jsonl(GENERATIONS_PATH)
    trace_records = load_jsonl(TRACES_PATH)
    evaluation_rows = read_csv(EVALUATION_PATH)
    thresholds = baseline_thresholds()

    prompts_by_qid = {record["question_id"]: record for record in prompts}
    traces_by_qid = {record["question_id"]: record for record in trace_records}
    evaluation_by_qid = {record["question_id"]: record for record in evaluation_rows}

    generation_ids = [record["question_id"] for record in generations]
    if generation_ids != EXPECTED_QUESTION_IDS:
        add_failure(failures, "unexpected sorted-control generation question ids", generation_ids)

    signal_rows: list[dict[str, Any]] = []
    omitted_gold_rows: list[dict[str, Any]] = []

    for generation in generations:
        qid = generation["question_id"]
        prompt = prompts_by_qid.get(qid)
        trace_record = traces_by_qid.get(qid)
        evaluation = evaluation_by_qid.get(qid)
        if prompt is None or trace_record is None or evaluation is None:
            add_failure(failures, "missing prompt, trace, or evaluation record", qid)
            continue

        generated_text = generation["generated_text"]
        token_spans, token_failures = build_token_char_spans(qid, generated_text, trace_record["token_traces"])
        failures.extend(token_failures)
        table_rows, table_failures = parse_table_cells_with_offsets(generated_text)
        failures.extend({"question_id": qid, **failure} for failure in table_failures)

        if len(table_rows) != 3:
            add_failure(failures, "expected 3 generated table rows", {"question_id": qid, "rows": len(table_rows)})

        gold_rows = generation["gold_answer"]["top_products"]
        evidence_rows = prompt["prompt_evidence_rows"]
        evidence_position_by_code = {
            normalize_stock_code(row["stock_code"]): index for index, row in enumerate(evidence_rows, start=1)
        }
        generated_codes = {row["stock_code"] for row in table_rows}
        for gold_row in gold_rows:
            gold_code = normalize_stock_code(gold_row["stock_code"])
            if gold_code not in generated_codes:
                omitted_gold_rows.append(
                    {
                        "question_id": qid,
                        "expected_rank": gold_row["rank"],
                        "stock_code": gold_code,
                        "product_name": gold_row["description"],
                        "net_revenue_gbp": gold_row["merchandise_net_revenue"],
                        "reason": "gold top3 row was omitted from generated text; token-level detectors cannot flag an absent span directly",
                    }
                )

        for row in table_rows:
            rank = int(row["rank"])
            gold_row = gold_rows[rank - 1] if 1 <= rank <= len(gold_rows) else None
            evidence_position = evidence_position_by_code.get(row["stock_code"])
            row_exact_correct = False
            if gold_row is not None:
                row_exact_correct = (
                    row["stock_code"] == normalize_stock_code(gold_row["stock_code"])
                    and row["product_name"] == normalize_name(gold_row["description"])
                    and amount_matches(row["net_revenue_gbp"], float(gold_row["merchandise_net_revenue"]))
                )
            label = "correct" if row_exact_correct else "incorrect_rank_binding"
            binary_label = 0 if row_exact_correct else 1
            reason = "rank outside gold top3" if gold_row is None else row_reason(row, gold_row, evidence_position)

            span_specs = [
                ("row_full", "ranking_row", row["row_text"], row["row_start"], row["row_end"]),
                ("stock_code", "product_stock_code", row["cells"]["stock_code"]["text"], row["cells"]["stock_code"]["start"], row["cells"]["stock_code"]["end"]),
                ("product_name", "product_name", row["cells"]["product_name"]["text"], row["cells"]["product_name"]["start"], row["cells"]["product_name"]["end"]),
                ("net_revenue_gbp", "currency_amount", row["cells"]["net_revenue_gbp"]["text"], row["cells"]["net_revenue_gbp"]["start"], row["cells"]["net_revenue_gbp"]["end"]),
            ]
            for span_scope, fact_type, span_text, span_start, span_end in span_specs:
                scores = score_span(token_spans, span_start, span_end, thresholds)
                signal_rows.append(
                    {
                        "question_id": qid,
                        "prompt_id": generation["prompt_id"],
                        "condition_id": "sorted_control",
                        "is_focus_failure": qid == "q_0065",
                        "question_exact_order_match": evaluation["exact_order_match"],
                        "rank": rank,
                        "span_scope": span_scope,
                        "fact_type": fact_type,
                        "label": label,
                        "binary_label": binary_label,
                        "span_text": span_text,
                        "span_start_char": span_start,
                        "span_end_char": span_end,
                        "generated_stock_code": row["stock_code"],
                        "expected_stock_code_at_rank": "" if gold_row is None else normalize_stock_code(gold_row["stock_code"]),
                        "generated_evidence_position": "" if evidence_position is None else evidence_position,
                        "reason": reason,
                        **scores,
                    }
                )

    report = summarize_signal_rows(signal_rows, omitted_gold_rows, thresholds)
    return signal_rows, report, failures


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    flagged_entropy = sum(1 for row in rows if row["predict_positive_max_token_entropy"])
    flagged_margin = sum(1 for row in rows if row["predict_positive_one_minus_min_top2_margin"])
    flagged_any = sum(1 for row in rows if row["predict_positive_any_selected_baseline"])
    return {
        "span_count": len(rows),
        "flagged_by_max_token_entropy": flagged_entropy,
        "flagged_by_one_minus_min_top2_margin": flagged_margin,
        "flagged_by_any_selected_baseline": flagged_any,
        "any_selected_baseline_flag_rate": rate(flagged_any, len(rows)),
    }


def summarize_signal_rows(
    rows: list[dict[str, Any]],
    omitted_gold_rows: list[dict[str, Any]],
    thresholds: dict[str, float],
) -> dict[str, Any]:
    focus_rows = [row for row in rows if row["question_id"] == "q_0065"]
    correct_rows = [row for row in rows if row["label"] == "correct"]
    incorrect_rows = [row for row in rows if row["label"] != "correct"]
    by_scope: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_scope[row["span_scope"]].append(row)

    flag_counts_by_label = {
        label: summarize_group([row for row in rows if row["label"] == label])
        for label in sorted({row["label"] for row in rows})
    }
    focus_by_scope = {scope: summarize_group([row for row in focus_rows if row["span_scope"] == scope]) for scope in sorted(by_scope)}
    by_scope_and_label = {
        f"{scope}__{label}": summarize_group(
            [row for row in rows if row["span_scope"] == scope and row["label"] == label]
        )
        for scope in sorted({row["span_scope"] for row in rows})
        for label in sorted({row["label"] for row in rows})
    }
    selected_flagged_focus = [
        {
            "rank": row["rank"],
            "span_scope": row["span_scope"],
            "span_text": row["span_text"],
            "max_token_entropy": row["max_token_entropy"],
            "one_minus_min_top2_margin": row["one_minus_min_top2_margin"],
            "flagged_any": row["predict_positive_any_selected_baseline"],
            "reason": row["reason"],
        }
        for row in focus_rows
        if row["predict_positive_any_selected_baseline"]
    ]
    label_counts = Counter(row["label"] for row in rows)

    return {
        "signal_spans_csv_path": str(SIGNAL_SPANS_CSV),
        "source_generation_path": str(GENERATIONS_PATH),
        "source_trace_path": str(TRACES_PATH),
        "question_ids": EXPECTED_QUESTION_IDS,
        "focus_question_id": "q_0065",
        "thresholds_from_pilot20": thresholds,
        "span_count": len(rows),
        "label_counts": dict(sorted(label_counts.items())),
        "focus_q0065_summary": summarize_group(focus_rows),
        "correct_reference_summary": summarize_group(correct_rows),
        "incorrect_rank_binding_summary": summarize_group(incorrect_rows),
        "focus_q0065_by_scope": focus_by_scope,
        "by_scope_and_label": by_scope_and_label,
        "omitted_gold_rows": omitted_gold_rows,
        "selected_flagged_focus_spans": selected_flagged_focus,
        "main_findings": [
            "The remaining sorted-control failure is represented by generated spans only; the omitted top product has no generated tokens for token-level detectors to score.",
            "The review compares q_0065 incorrect rank-bound spans against the correct q_0060 and q_0072 sorted-control spans using the same token metrics.",
            "Stock-code and row-level spans carry the strongest uncertainty signal, but the same signal also flags correct stock-code and row-level spans in this small control.",
            "Selected pilot20 thresholds are reused only as a diagnostic reference, not as held-out performance claims.",
        ],
    }


def validate_outputs(rows: list[dict[str, Any]], report: dict[str, Any], failures: list[dict[str, Any]]) -> None:
    if len(rows) != 36:
        add_failure(failures, "expected 36 generated span rows", {"actual": len(rows)})
    qids = sorted({row["question_id"] for row in rows})
    if qids != EXPECTED_QUESTION_IDS:
        add_failure(failures, "unexpected question ids in signal rows", qids)
    focus_rows = [row for row in rows if row["question_id"] == "q_0065"]
    if len(focus_rows) != 12:
        add_failure(failures, "expected 12 q_0065 focus spans", {"actual": len(focus_rows)})
    if any(row["label"] == "correct" for row in focus_rows):
        add_failure(failures, "q_0065 should have no rank-exact correct generated rows")
    if int(report.get("span_count", -1)) != len(rows):
        add_failure(failures, "report span_count mismatch", report.get("span_count"))
    omitted = report.get("omitted_gold_rows", [])
    if not any(row.get("question_id") == "q_0065" and row.get("stock_code") == "47566" for row in omitted):
        add_failure(failures, "q_0065 omitted top product not recorded")

    with SIGNAL_SPANS_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.DictReader(f))
    if len(csv_rows) != len(rows):
        add_failure(failures, "signal csv row count mismatch", {"csv": len(csv_rows), "memory": len(rows)})


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path in [PROMPTS_PATH, GENERATIONS_PATH, TRACES_PATH, EVALUATION_PATH, PILOT_BASELINE_REPORT_PATH]:
        if not path.exists():
            add_failure(failures, "missing input file", str(path))

    if failures:
        validation = {"num_failures": len(failures), "failures": failures}
        VALIDATION_JSON.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(validation, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    rows, report, failures = build_signal_rows()
    fieldnames = [
        "question_id",
        "prompt_id",
        "condition_id",
        "is_focus_failure",
        "question_exact_order_match",
        "rank",
        "span_scope",
        "fact_type",
        "label",
        "binary_label",
        "span_text",
        "span_start_char",
        "span_end_char",
        "generated_stock_code",
        "expected_stock_code_at_rank",
        "generated_evidence_position",
        "reason",
        "token_count",
        "mean_token_logprob",
        "mean_token_nll",
        "mean_token_entropy",
        "max_token_entropy",
        "mean_top2_margin",
        "min_top2_margin",
        "one_minus_min_top2_margin",
        "predict_positive_max_token_entropy",
        "predict_positive_one_minus_min_top2_margin",
        "predict_positive_any_selected_baseline",
        "token_positions",
        "token_texts",
    ]
    write_csv(SIGNAL_SPANS_CSV, fieldnames, rows)
    SIGNAL_SUMMARY_JSON.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    validate_outputs(rows, report, failures)

    validation = {
        "signal_spans_csv_path": str(SIGNAL_SPANS_CSV),
        "signal_summary_path": str(SIGNAL_SUMMARY_JSON),
        "span_count": len(rows),
        "focus_question_id": "q_0065",
        "focus_span_count": sum(1 for row in rows if row["question_id"] == "q_0065"),
        "num_failures": len(failures),
        "failures": failures,
    }
    VALIDATION_JSON.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
