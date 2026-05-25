from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

try:
    from run_qwen_dry_run import (
        DEFAULT_MODEL_ID,
        PROMPTS_PATH,
        build_model_input,
        score_generated_tokens,
        set_seed,
    )
except ModuleNotFoundError as exc:
    if exc.name != "run_qwen_dry_run":
        raise
    from src.run_qwen_dry_run import (
        DEFAULT_MODEL_ID,
        PROMPTS_PATH,
        build_model_input,
        score_generated_tokens,
        set_seed,
    )


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_QUESTION_IDS = ["q_0001", "q_0017", "q_0030", "q_0050", "q_0073"]


def load_prompts(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def select_prompts(
    prompts: list[dict[str, Any]],
    question_ids: list[str] | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    if question_ids:
        by_id = {record["question_id"]: record for record in prompts}
        missing = [question_id for question_id in question_ids if question_id not in by_id]
        if missing:
            raise ValueError(f"Question ids not found: {missing}")
        selected = [by_id[question_id] for question_id in question_ids]
    else:
        selected = prompts

    if limit is not None:
        selected = selected[:limit]
    return selected


def load_question_ids_from_config(path: Path) -> list[str]:
    config = json.loads(path.read_text(encoding="utf-8"))
    question_ids = config.get("question_ids", [])
    if not isinstance(question_ids, list) or not all(isinstance(item, str) for item in question_ids):
        raise ValueError(f"{path} must contain a string list at question_ids")
    if not question_ids:
        raise ValueError(f"{path} contains no question_ids")
    return question_ids


def generation_config_from_args(args: argparse.Namespace, tokenizer: AutoTokenizer) -> dict[str, Any]:
    generation_config: dict[str, Any] = {
        "max_new_tokens": args.max_new_tokens,
        "return_dict_in_generate": True,
        "pad_token_id": tokenizer.eos_token_id,
    }
    if args.greedy:
        generation_config.update({"do_sample": False})
    else:
        generation_config.update(
            {
                "do_sample": True,
                "temperature": args.temperature,
                "top_p": args.top_p,
                "top_k": args.top_k,
            }
        )
    return generation_config


def generate_one(
    prompt_record: dict[str, Any],
    tokenizer: AutoTokenizer,
    model: AutoModelForCausalLM,
    args: argparse.Namespace,
    seed: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    set_seed(seed)
    started = time.time()
    input_text = build_model_input(tokenizer, prompt_record["messages"])
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
    generation_config = generation_config_from_args(args, tokenizer)

    with torch.no_grad():
        output = model.generate(**inputs, **generation_config)

    input_length = int(inputs["input_ids"].shape[1])
    output_ids = output.sequences[0].detach().cpu().tolist()
    generated_token_ids = output_ids[input_length:]
    generated_text = tokenizer.decode(generated_token_ids, skip_special_tokens=True)

    with torch.no_grad():
        forward_output = model(output.sequences)

    token_traces = score_generated_tokens(
        tokenizer,
        generated_token_ids,
        forward_output.logits,
        input_length,
    )

    elapsed = time.time() - started
    generation_record = {
        "prompt_id": prompt_record["prompt_id"],
        "question_id": prompt_record["question_id"],
        "question_type": prompt_record["question_type"],
        "difficulty": prompt_record["difficulty"],
        "split": prompt_record["split"],
        "model_id": args.model_id,
        "device": str(model.device),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "seed": seed,
        "generation_config": {
            key: value
            for key, value in generation_config.items()
            if key not in {"return_dict_in_generate"}
        },
        "input_token_count": input_length,
        "generated_token_count": len(generated_token_ids),
        "elapsed_seconds": round(elapsed, 3),
        "prompt": input_text,
        "generated_text": generated_text,
        "generated_token_ids": generated_token_ids,
        "gold_answer": prompt_record["gold_answer"],
        "gold_short_answer": prompt_record["gold_short_answer"],
    }

    trace_record = {
        "prompt_id": prompt_record["prompt_id"],
        "question_id": prompt_record["question_id"],
        "model_id": args.model_id,
        "token_traces": token_traces,
    }
    return generation_record, trace_record


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--prompts-path", default=str(PROMPTS_PATH))
    parser.add_argument("--question-config", default=None)
    parser.add_argument("--question-ids", default=",".join(DEFAULT_QUESTION_IDS))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=160)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-p", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--greedy", action="store_true")
    parser.add_argument("--output-prefix", default="qwen_batch5")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.question_config:
        config_path = Path(args.question_config)
        if not config_path.is_absolute():
            config_path = PROJECT_ROOT / config_path
        question_ids = load_question_ids_from_config(config_path)
    else:
        question_ids = [item.strip() for item in args.question_ids.split(",") if item.strip()]
    prompts_path = Path(args.prompts_path)
    if not prompts_path.is_absolute():
        prompts_path = PROJECT_ROOT / prompts_path
    prompts = select_prompts(load_prompts(prompts_path), question_ids, args.limit)

    batch_started = time.time()
    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        torch_dtype="auto",
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()

    generation_records: list[dict[str, Any]] = []
    trace_records: list[dict[str, Any]] = []
    for index, prompt_record in enumerate(prompts):
        record_seed = args.seed + index
        generation_record, trace_record = generate_one(
            prompt_record,
            tokenizer,
            model,
            args,
            record_seed,
        )
        generation_records.append(generation_record)
        trace_records.append(trace_record)
        print(
            json.dumps(
                {
                    "status": "generated",
                    "question_id": generation_record["question_id"],
                    "question_type": generation_record["question_type"],
                    "generated_token_count": generation_record["generated_token_count"],
                    "elapsed_seconds": generation_record["elapsed_seconds"],
                    "generated_text_preview": generation_record["generated_text"][:220],
                },
                ensure_ascii=True,
            ),
            flush=True,
        )

    generation_path = OUTPUT_DIR / f"{args.output_prefix}_generations.jsonl"
    trace_path = OUTPUT_DIR / f"{args.output_prefix}_token_traces.jsonl"
    report_path = OUTPUT_DIR / f"{args.output_prefix}_report.json"
    write_jsonl(generation_path, generation_records)
    write_jsonl(trace_path, trace_records)

    total_elapsed = time.time() - batch_started
    report = {
        "prompts_path": str(prompts_path),
        "generation_path": str(generation_path),
        "trace_path": str(trace_path),
        "record_count": len(generation_records),
        "model_id": args.model_id,
        "device": str(model.device),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "cuda_version": torch.version.cuda,
        "base_seed": args.seed,
        "question_ids": [record["question_id"] for record in generation_records],
        "question_type_counts": {
            question_type: sum(1 for record in generation_records if record["question_type"] == question_type)
            for question_type in sorted({record["question_type"] for record in generation_records})
        },
        "total_elapsed_seconds": round(total_elapsed, 3),
        "avg_elapsed_seconds_per_record": round(
            sum(record["elapsed_seconds"] for record in generation_records) / len(generation_records),
            3,
        ),
        "total_generated_tokens": sum(record["generated_token_count"] for record in generation_records),
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
