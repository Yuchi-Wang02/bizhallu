from __future__ import annotations

import json
from pathlib import Path

from validate_qwen_batch import validate_energy_fields


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATION_PATH = PROJECT_ROOT / "outputs" / "qwen_dry_run_generation.jsonl"
TRACE_PATH = PROJECT_ROOT / "outputs" / "qwen_dry_run_token_trace.jsonl"


def load_one(path: Path) -> dict:
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(records) != 1:
        raise ValueError(f"Expected 1 record in {path}, found {len(records)}")
    return records[0]


def main() -> None:
    failures: list[str] = []
    if not GENERATION_PATH.exists():
        failures.append(f"missing {GENERATION_PATH}")
    if not TRACE_PATH.exists():
        failures.append(f"missing {TRACE_PATH}")
    if failures:
        print(json.dumps({"num_failures": len(failures), "failures": failures}, indent=2))
        raise SystemExit(1)

    generation = load_one(GENERATION_PATH)
    trace = load_one(TRACE_PATH)
    token_traces = trace.get("token_traces", [])

    if not generation.get("generated_text", "").strip():
        failures.append("generated_text is empty")
    if generation.get("generated_token_count") != len(generation.get("generated_token_ids", [])):
        failures.append("generated_token_count does not match generated_token_ids length")
    if generation.get("generated_token_count") != len(token_traces):
        failures.append("generated_token_count does not match token trace length")
    if generation.get("question_id") != trace.get("question_id"):
        failures.append("question_id mismatch between generation and trace")
    if not generation.get("cuda_available"):
        failures.append("CUDA was not available during generation")

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
            failures.append(f"token trace {index} missing fields: {missing}")
            break
        if item.get("score_source") != "raw_forward_logits_after_generation":
            failures.append(f"token trace {index} uses unexpected score source: {item.get('score_source')}")
            break
        energy_failures: list[dict[str, str]] = []
        if not validate_energy_fields(energy_failures, trace.get("question_id", "UNKNOWN"), item, index, False):
            failures.append(energy_failures[-1]["reason"])
            break

    if token_traces and all(abs(item.get("token_entropy", 0.0)) < 1e-8 for item in token_traces):
        failures.append("all token entropies are zero; raw logits scoring likely failed")

    report = {
        "num_failures": len(failures),
        "failures": failures,
        "question_id": generation.get("question_id"),
        "generated_token_count": generation.get("generated_token_count"),
        "input_token_count": generation.get("input_token_count"),
        "elapsed_seconds": generation.get("elapsed_seconds"),
        "generated_text_preview": generation.get("generated_text", "")[:500],
    }
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
