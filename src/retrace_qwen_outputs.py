from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

try:
    from run_qwen_dry_run import DEFAULT_MODEL_ID, score_generated_tokens
except ModuleNotFoundError as exc:
    if exc.name != "run_qwen_dry_run":
        raise
    from src.run_qwen_dry_run import DEFAULT_MODEL_ID, score_generated_tokens


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--source-prefix", default="qwen_pilot20")
    parser.add_argument("--output-prefix", default="qwen_pilot20_energy")
    parser.add_argument("--source-generations-path", default=None)
    parser.add_argument("--expected-count", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    source_generation_path = (
        resolve_project_path(args.source_generations_path)
        if args.source_generations_path
        else OUTPUT_DIR / f"{args.source_prefix}_generations.jsonl"
    )
    output_generation_path = OUTPUT_DIR / f"{args.output_prefix}_generations.jsonl"
    output_trace_path = OUTPUT_DIR / f"{args.output_prefix}_token_traces.jsonl"
    report_path = OUTPUT_DIR / f"{args.output_prefix}_report.json"

    generation_records = load_jsonl(source_generation_path)
    if args.limit is not None:
        generation_records = generation_records[: args.limit]
    if args.expected_count is not None and len(generation_records) != args.expected_count:
        raise SystemExit(f"Expected {args.expected_count} source generations, found {len(generation_records)}")

    started = time.time()
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        torch_dtype="auto",
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()

    trace_records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for index, generation in enumerate(generation_records):
        qid = str(generation["question_id"])
        prompt = str(generation["prompt"])
        generated_token_ids = [int(token_id) for token_id in generation.get("generated_token_ids", [])]
        prompt_inputs = tokenizer(prompt, return_tensors="pt")
        prompt_input_ids = prompt_inputs["input_ids"][0].detach().cpu().tolist()
        recorded_input_count = int(generation.get("input_token_count", -1))
        if len(prompt_input_ids) != recorded_input_count:
            failures.append(
                {
                    "question_id": qid,
                    "reason": "retokenized prompt length does not match recorded input_token_count",
                    "recorded_input_token_count": recorded_input_count,
                    "retokenized_input_token_count": len(prompt_input_ids),
                }
            )
            continue
        if len(generated_token_ids) != int(generation.get("generated_token_count", -1)):
            failures.append(
                {
                    "question_id": qid,
                    "reason": "generated_token_ids length does not match generated_token_count",
                }
            )
            continue

        full_sequence_ids = prompt_input_ids + generated_token_ids
        input_ids = torch.tensor([full_sequence_ids], dtype=torch.long, device=model.device)
        with torch.no_grad():
            forward_output = model(input_ids=input_ids)
        token_traces = score_generated_tokens(
            tokenizer,
            generated_token_ids,
            forward_output.logits,
            recorded_input_count,
        )

        trace_records.append(
            {
                "prompt_id": generation["prompt_id"],
                "question_id": qid,
                "model_id": args.model_id,
                "trace_source": "raw_forward_logits_retrace_existing_generation",
                "source_generation_path": str(source_generation_path),
                "source_generation_prefix": args.source_prefix,
                "token_traces": token_traces,
            }
        )
        print(
            json.dumps(
                {
                    "status": "retraced",
                    "question_id": qid,
                    "generated_token_count": len(generated_token_ids),
                    "record_index": index,
                },
                ensure_ascii=True,
            ),
            flush=True,
        )

    if failures:
        report = {
            "source_generation_path": str(source_generation_path),
            "output_generation_path": str(output_generation_path),
            "output_trace_path": str(output_trace_path),
            "record_count": len(generation_records),
            "trace_count": len(trace_records),
            "num_failures": len(failures),
            "failures": failures,
        }
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    write_jsonl(output_generation_path, generation_records)
    write_jsonl(output_trace_path, trace_records)

    total_elapsed = time.time() - started
    report = {
        "source_generation_path": str(source_generation_path),
        "output_generation_path": str(output_generation_path),
        "output_trace_path": str(output_trace_path),
        "record_count": len(generation_records),
        "trace_count": len(trace_records),
        "model_id": args.model_id,
        "device": str(model.device),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "question_ids": [record["question_id"] for record in generation_records],
        "total_generated_tokens": sum(int(record["generated_token_count"]) for record in generation_records),
        "total_elapsed_seconds": round(total_elapsed, 3),
        "avg_elapsed_seconds_per_record": round(total_elapsed / len(generation_records), 3)
        if generation_records
        else None,
        "num_failures": 0,
        "failures": [],
        "note": "Existing generated answers were not regenerated; only raw forward-logit token traces were rebuilt.",
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
