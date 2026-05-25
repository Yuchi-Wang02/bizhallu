from __future__ import annotations

import argparse
import json
import math
import os
import random
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_PATH = PROJECT_ROOT / "outputs" / "qwen_input_prompts.jsonl"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_MODEL_ID = "Qwen/Qwen3-0.6B"


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def load_prompt(question_id: str | None) -> dict[str, Any]:
    with PROMPTS_PATH.open("r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    if question_id is None:
        return records[0]
    for record in records:
        if record["question_id"] == question_id:
            return record
    raise ValueError(f"Question id not found: {question_id}")


def build_model_input(tokenizer: AutoTokenizer, messages: list[dict[str, str]]) -> str:
    try:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
    except TypeError:
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )


def tensor_to_float(value: torch.Tensor) -> float:
    return float(value.detach().cpu().item())


def score_generated_tokens(
    tokenizer: AutoTokenizer,
    generated_token_ids: list[int],
    raw_logits: torch.Tensor,
    input_length: int,
) -> list[dict[str, Any]]:
    traces: list[dict[str, Any]] = []
    for position, token_id in enumerate(generated_token_ids):
        logits_index = input_length - 1 + position
        step_scores = raw_logits[0, logits_index].detach().float().cpu()
        next_state_index = input_length + position
        if next_state_index < raw_logits.shape[1]:
            next_state_scores = raw_logits[0, next_state_index].detach().float().cpu()
            next_state_logsumexp = torch.logsumexp(next_state_scores, dim=-1)
        else:
            next_state_logsumexp = None
        step_logsumexp = torch.logsumexp(step_scores, dim=-1)
        log_probs = torch.log_softmax(step_scores, dim=-1)
        probs = torch.softmax(step_scores, dim=-1)
        top_values, top_indices = torch.topk(probs, k=2)
        top_logit_values = step_scores[top_indices]
        entropy = -torch.sum(probs * torch.log(probs.clamp_min(1e-12)))
        token_text = tokenizer.decode([token_id], skip_special_tokens=False)
        token_logit = step_scores[token_id]
        selected_step_energy_gap = step_logsumexp - token_logit
        energy_fields: dict[str, Any] = {
            "token_logit": tensor_to_float(token_logit),
            "step_logsumexp_logits": tensor_to_float(step_logsumexp),
            "negative_step_logsumexp_energy": tensor_to_float(-step_logsumexp),
            "selected_step_energy_gap": tensor_to_float(selected_step_energy_gap),
            "top1_logit": tensor_to_float(top_logit_values[0]),
            "top2_logit": tensor_to_float(top_logit_values[1]),
            "spilled_probability_mass_after_top1": tensor_to_float(1.0 - top_values[0]),
            "spilled_probability_mass_after_top2": tensor_to_float(1.0 - top_values[0] - top_values[1]),
        }
        if next_state_logsumexp is not None:
            spilled_energy_delta = next_state_logsumexp - token_logit
            energy_fields.update(
                {
                    "next_state_logsumexp_logits": tensor_to_float(next_state_logsumexp),
                    "token_energy": tensor_to_float(-token_logit),
                    "marginal_energy": tensor_to_float(-next_state_logsumexp),
                    "spilled_energy_delta": tensor_to_float(spilled_energy_delta),
                    "spilled_energy_abs_delta": tensor_to_float(torch.abs(spilled_energy_delta)),
                }
            )
        traces.append(
            {
                "position": position,
                "token_id": int(token_id),
                "token_text": token_text,
                "score_source": "raw_forward_logits_after_generation",
                "token_logprob": tensor_to_float(log_probs[token_id]),
                "token_probability": tensor_to_float(probs[token_id]),
                "token_entropy": tensor_to_float(entropy),
                "top1_token_id": int(top_indices[0].item()),
                "top1_token_text": tokenizer.decode(
                    [int(top_indices[0].item())],
                    skip_special_tokens=False,
                ),
                "top1_probability": tensor_to_float(top_values[0]),
                "top2_token_id": int(top_indices[1].item()),
                "top2_token_text": tokenizer.decode(
                    [int(top_indices[1].item())],
                    skip_special_tokens=False,
                ),
                "top2_probability": tensor_to_float(top_values[1]),
                "top2_margin": tensor_to_float(top_values[0] - top_values[1]),
                **energy_fields,
            }
        )
    return traces


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--question-id", default=None)
    parser.add_argument("--max-new-tokens", type=int, default=160)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--top-p", type=float, default=0.8)
    parser.add_argument("--top-k", type=int, default=20)
    parser.add_argument("--greedy", action="store_true")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    set_seed(args.seed)

    prompt_record = load_prompt(args.question_id)
    started = time.time()

    tokenizer = AutoTokenizer.from_pretrained(args.model_id, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        args.model_id,
        torch_dtype="auto",
        device_map="auto",
        trust_remote_code=True,
    )
    model.eval()

    input_text = build_model_input(tokenizer, prompt_record["messages"])
    inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

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
        "seed": args.seed,
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

    generation_path = OUTPUT_DIR / "qwen_dry_run_generation.jsonl"
    trace_path = OUTPUT_DIR / "qwen_dry_run_token_trace.jsonl"
    write_jsonl(generation_path, [generation_record])
    write_jsonl(trace_path, [trace_record])

    summary = {
        "generation_path": str(generation_path),
        "trace_path": str(trace_path),
        "question_id": prompt_record["question_id"],
        "input_token_count": input_length,
        "generated_token_count": len(generated_token_ids),
        "elapsed_seconds": round(elapsed, 3),
        "generated_text": generated_text,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
