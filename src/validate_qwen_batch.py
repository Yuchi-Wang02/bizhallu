from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def add_failure(failures: list[dict[str, Any]], question_id: str, reason: str) -> None:
    failures.append({"question_id": question_id, "reason": reason})


def is_finite_number(value: Any) -> bool:
    return isinstance(value, int | float) and math.isfinite(float(value))


def validate_energy_fields(
    failures: list[dict[str, Any]],
    question_id: str,
    item: dict[str, Any],
    index: int,
    require_energy_fields: bool,
) -> bool:
    energy_required = {
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
    }
    missing = sorted(energy_required - set(item))
    if missing:
        if require_energy_fields:
            add_failure(failures, question_id, f"token trace {index} missing energy fields: {missing}")
            return False
        return True

    for field in energy_required:
        if not is_finite_number(item.get(field)):
            add_failure(failures, question_id, f"token trace {index} has non-finite {field}")
            return False

    probability_fields = [
        "spilled_probability_mass_after_top1",
        "spilled_probability_mass_after_top2",
    ]
    for field in probability_fields:
        value = float(item[field])
        if value < -1e-6 or value > 1.000001:
            add_failure(failures, question_id, f"token trace {index} has out-of-range {field}: {value}")
            return False

    if float(item["selected_step_energy_gap"]) < -1e-5:
        add_failure(failures, question_id, f"token trace {index} has negative selected_step_energy_gap")
        return False
    if float(item["spilled_energy_abs_delta"]) < -1e-8:
        add_failure(failures, question_id, f"token trace {index} has negative spilled_energy_abs_delta")
        return False

    if abs(float(item["negative_step_logsumexp_energy"]) + float(item["step_logsumexp_logits"])) > 1e-4:
        add_failure(failures, question_id, f"token trace {index} has inconsistent step energy")
        return False
    if abs(float(item["token_energy"]) + float(item["token_logit"])) > 1e-4:
        add_failure(failures, question_id, f"token trace {index} has inconsistent token energy")
        return False
    if abs(float(item["marginal_energy"]) + float(item["next_state_logsumexp_logits"])) > 1e-4:
        add_failure(failures, question_id, f"token trace {index} has inconsistent marginal energy")
        return False
    if abs(float(item["selected_step_energy_gap"]) + float(item["token_logprob"])) > 1e-4:
        add_failure(failures, question_id, f"token trace {index} has inconsistent selected_step_energy_gap")
        return False

    expected_delta = float(item["next_state_logsumexp_logits"]) - float(item["token_logit"])
    if abs(float(item["spilled_energy_delta"]) - expected_delta) > 1e-4:
        add_failure(failures, question_id, f"token trace {index} has inconsistent spilled_energy_delta")
        return False
    if abs(float(item["spilled_energy_abs_delta"]) - abs(float(item["spilled_energy_delta"]))) > 1e-4:
        add_failure(failures, question_id, f"token trace {index} has inconsistent spilled_energy_abs_delta")
        return False

    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefix", default="qwen_batch5")
    parser.add_argument("--expected-count", type=int, default=5)
    parser.add_argument("--require-energy-fields", action="store_true")
    args = parser.parse_args()

    generation_path = OUTPUT_DIR / f"{args.prefix}_generations.jsonl"
    trace_path = OUTPUT_DIR / f"{args.prefix}_token_traces.jsonl"
    validation_path = OUTPUT_DIR / f"{args.prefix}_validation.json"

    failures: list[dict[str, Any]] = []
    if not generation_path.exists():
        add_failure(failures, "GLOBAL", f"missing {generation_path}")
    if not trace_path.exists():
        add_failure(failures, "GLOBAL", f"missing {trace_path}")
    if failures:
        report = {"num_failures": len(failures), "failures": failures}
        validation_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        raise SystemExit(1)

    generations = load_jsonl(generation_path)
    traces = load_jsonl(trace_path)
    traces_by_qid = {record["question_id"]: record for record in traces}

    if len(generations) != args.expected_count:
        add_failure(failures, "GLOBAL", f"expected {args.expected_count} generations, found {len(generations)}")
    if len(traces) != len(generations):
        add_failure(failures, "GLOBAL", f"trace count {len(traces)} != generation count {len(generations)}")
    if len({record["question_id"] for record in generations}) != len(generations):
        add_failure(failures, "GLOBAL", "duplicate generation question_id")
    if len({record["question_id"] for record in traces}) != len(traces):
        add_failure(failures, "GLOBAL", "duplicate trace question_id")

    for generation in generations:
        qid = generation.get("question_id", "UNKNOWN")
        trace = traces_by_qid.get(qid)
        if trace is None:
            add_failure(failures, qid, "missing token trace record")
            continue
        token_traces = trace.get("token_traces", [])
        generated_ids = generation.get("generated_token_ids", [])

        if not generation.get("generated_text", "").strip():
            add_failure(failures, qid, "generated_text is empty")
        if generation.get("generated_token_count") != len(generated_ids):
            add_failure(failures, qid, "generated_token_count does not match generated_token_ids")
        if generation.get("generated_token_count") != len(token_traces):
            add_failure(failures, qid, "generated_token_count does not match token_traces")
        if not generation.get("cuda_available"):
            add_failure(failures, qid, "CUDA was not available during generation")
        if not generation.get("gold_short_answer"):
            add_failure(failures, qid, "missing gold_short_answer")
        if generation.get("input_token_count", 0) <= 0:
            add_failure(failures, qid, "invalid input_token_count")

        if token_traces:
            entropies = [item.get("token_entropy", 0.0) for item in token_traces]
            if all(abs(value) < 1e-8 for value in entropies):
                add_failure(failures, qid, "all token entropies are zero")
            for index, item in enumerate(token_traces):
                required = {
                    "position",
                    "token_id",
                    "token_text",
                    "score_source",
                    "token_logprob",
                    "token_probability",
                    "token_entropy",
                    "top2_margin",
                }
                missing = sorted(required - set(item))
                if missing:
                    add_failure(failures, qid, f"token trace {index} missing fields: {missing}")
                    break
                if item.get("score_source") != "raw_forward_logits_after_generation":
                    add_failure(failures, qid, f"unexpected score source: {item.get('score_source')}")
                    break
                if not validate_energy_fields(
                    failures,
                    qid,
                    item,
                    index,
                    args.require_energy_fields,
                ):
                    break

    report = {
        "generation_path": str(generation_path),
        "trace_path": str(trace_path),
        "record_count": len(generations),
        "trace_count": len(traces),
        "num_failures": len(failures),
        "failures": failures,
        "question_ids": [record.get("question_id") for record in generations],
        "question_type_counts": {
            question_type: sum(1 for record in generations if record.get("question_type") == question_type)
            for question_type in sorted({record.get("question_type") for record in generations})
        },
        "generated_token_counts": {
            record.get("question_id"): record.get("generated_token_count") for record in generations
        },
    }
    validation_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
