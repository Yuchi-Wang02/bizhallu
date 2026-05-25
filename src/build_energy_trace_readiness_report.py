from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RESULTS_DIR = PROJECT_ROOT / "results"

ENERGY_FIELDS = [
    "token_logit",
    "step_logsumexp_logits",
    "negative_step_logsumexp_energy",
    "selected_step_energy_gap",
    "top1_logit",
    "top2_logit",
    "spilled_probability_mass_after_top1",
    "spilled_probability_mass_after_top2",
    "next_state_logsumexp_logits",
    "token_energy",
    "marginal_energy",
    "spilled_energy_delta",
    "spilled_energy_abs_delta",
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def finite(value: Any) -> bool:
    return isinstance(value, int | float) and math.isfinite(float(value))


def score_range(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "mean": None, "max": None}
    return {
        "min": min(values),
        "mean": sum(values) / len(values),
        "max": max(values),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generation-prefix", default="qwen_top3_sorted_control_pilot3_energy")
    parser.add_argument("--output-prefix", default="energy_trace_readiness")
    args = parser.parse_args()

    generation_path = OUTPUT_DIR / f"{args.generation_prefix}_generations.jsonl"
    trace_path = OUTPUT_DIR / f"{args.generation_prefix}_token_traces.jsonl"
    report_path = RESULTS_DIR / f"{args.output_prefix}_report.json"
    validation_path = RESULTS_DIR / f"{args.output_prefix}_validation.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    failures: list[dict[str, str]] = []
    if not generation_path.exists():
        failures.append({"question_id": "GLOBAL", "reason": f"missing {generation_path}"})
    if not trace_path.exists():
        failures.append({"question_id": "GLOBAL", "reason": f"missing {trace_path}"})
    if failures:
        validation_path.write_text(json.dumps({"num_failures": len(failures), "failures": failures}, indent=2), encoding="utf-8")
        raise SystemExit(1)

    generations = load_jsonl(generation_path)
    traces = load_jsonl(trace_path)
    traces_by_qid = {record["question_id"]: record for record in traces}

    total_tokens = 0
    tokens_with_all_energy_fields = 0
    selected_gap_diffs: list[float] = []
    step_energy_diffs: list[float] = []
    token_energy_diffs: list[float] = []
    marginal_energy_diffs: list[float] = []
    spilled_delta_diffs: list[float] = []
    spilled_abs_diffs: list[float] = []
    spilled_abs_values: list[float] = []
    selected_gap_values: list[float] = []
    entropy_values: list[float] = []

    for generation in generations:
        qid = generation.get("question_id", "UNKNOWN")
        trace = traces_by_qid.get(qid)
        if trace is None:
            failures.append({"question_id": qid, "reason": "missing trace record"})
            continue
        token_traces = trace.get("token_traces", [])
        total_tokens += len(token_traces)
        if generation.get("generated_token_count") != len(token_traces):
            failures.append({"question_id": qid, "reason": "generated_token_count does not match token trace length"})

        for index, item in enumerate(token_traces):
            missing = [field for field in ENERGY_FIELDS if field not in item]
            if missing:
                failures.append({"question_id": qid, "reason": f"token {index} missing energy fields: {missing}"})
                continue
            if not all(finite(item[field]) for field in ENERGY_FIELDS):
                failures.append({"question_id": qid, "reason": f"token {index} has non-finite energy field"})
                continue

            tokens_with_all_energy_fields += 1
            selected_gap_diffs.append(abs(float(item["selected_step_energy_gap"]) + float(item["token_logprob"])))
            step_energy_diffs.append(abs(float(item["negative_step_logsumexp_energy"]) + float(item["step_logsumexp_logits"])))
            token_energy_diffs.append(abs(float(item["token_energy"]) + float(item["token_logit"])))
            marginal_energy_diffs.append(abs(float(item["marginal_energy"]) + float(item["next_state_logsumexp_logits"])))
            expected_delta = float(item["next_state_logsumexp_logits"]) - float(item["token_logit"])
            spilled_delta_diffs.append(abs(float(item["spilled_energy_delta"]) - expected_delta))
            spilled_abs_diffs.append(abs(float(item["spilled_energy_abs_delta"]) - abs(float(item["spilled_energy_delta"]))))
            spilled_abs_values.append(float(item["spilled_energy_abs_delta"]))
            selected_gap_values.append(float(item["selected_step_energy_gap"]))
            entropy_values.append(float(item["token_entropy"]))

    max_formula_diffs = {
        "selected_step_energy_gap_vs_negative_logprob": max(selected_gap_diffs, default=None),
        "negative_step_logsumexp_energy_vs_step_logsumexp": max(step_energy_diffs, default=None),
        "token_energy_vs_token_logit": max(token_energy_diffs, default=None),
        "marginal_energy_vs_next_state_logsumexp": max(marginal_energy_diffs, default=None),
        "spilled_energy_delta_formula": max(spilled_delta_diffs, default=None),
        "spilled_energy_abs_delta_formula": max(spilled_abs_diffs, default=None),
    }
    readiness_passed = (
        not failures
        and total_tokens > 0
        and tokens_with_all_energy_fields == total_tokens
        and all(value is not None and value <= 1e-4 for value in max_formula_diffs.values())
    )

    report = {
        "generation_prefix": args.generation_prefix,
        "generation_path": str(generation_path),
        "trace_path": str(trace_path),
        "record_count": len(generations),
        "trace_count": len(traces),
        "question_ids": [record.get("question_id") for record in generations],
        "total_generated_tokens": total_tokens,
        "tokens_with_all_energy_fields": tokens_with_all_energy_fields,
        "energy_fields": ENERGY_FIELDS,
        "max_formula_diffs": max_formula_diffs,
        "score_ranges": {
            "spilled_energy_abs_delta": score_range(spilled_abs_values),
            "selected_step_energy_gap": score_range(selected_gap_values),
            "token_entropy": score_range(entropy_values),
        },
        "readiness_passed": readiness_passed,
        "full100_preparation_note": (
            "Qwen traces now save raw-logit fields needed for entropy/NLL/top-2 baselines "
            "and adjacent-step fields needed for a Spilled Energy adapter."
        ),
    }
    validation = {
        "num_failures": len(failures),
        "failures": failures,
        "readiness_passed": readiness_passed,
        "tokens_with_all_energy_fields": tokens_with_all_energy_fields,
        "total_generated_tokens": total_tokens,
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    validation_path.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if not readiness_passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
