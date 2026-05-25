# Qwen Local Setup

Version: 0.1

## Local Environment Used

Use the existing conda environment:

```powershell
C:\Users\yuchi\anaconda3\envs\torch\python.exe
```

Verified package state:

- Python 3.10.18
- PyTorch 2.8.0+cu128
- Transformers 4.55.4
- Accelerate 1.10.1
- Hugging Face Hub 0.34.4
- Safetensors 0.6.2
- SentencePiece 0.2.1
- CUDA available: yes
- GPU: NVIDIA GeForce RTX 5070 Ti

Qwen3 requires a recent `transformers` version. The Qwen model card warns that older versions can fail to load Qwen3 model types.

## Cache Location

Use a project-level Hugging Face cache:

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
```

The downloaded model is stored under:

```text
C:\Users\yuchi\Downloads\p1\hf_cache\hub\models--Qwen--Qwen3-0.6B
```

The current snapshot contains `model.safetensors`, tokenizer files, and config files.

## Dry Run

From the project root:

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_dry_run.py --question-id q_0001 --max-new-tokens 120 --seed 42
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\validate_qwen_dry_run.py
```

Outputs:

- `outputs/qwen_dry_run_generation.jsonl`
- `outputs/qwen_dry_run_token_trace.jsonl`

## Batch Smoke Test

Run five diverse prompt types after the single-record dry run passes:

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_batch.py --question-ids q_0001,q_0017,q_0030,q_0050,q_0073 --output-prefix qwen_batch5 --max-new-tokens 160 --seed 42
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\validate_qwen_batch.py --prefix qwen_batch5 --expected-count 5
```

Outputs:

- `outputs/qwen_batch5_generations.jsonl`
- `outputs/qwen_batch5_token_traces.jsonl`
- `outputs/qwen_batch5_report.json`
- `outputs/qwen_batch5_validation.json`

## Pilot20 Generation

After `configs/pilot20_questions.json` passes validation, run:

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_batch.py --question-config configs\pilot20_questions.json --output-prefix qwen_pilot20 --max-new-tokens 160 --seed 42
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\validate_qwen_batch.py --prefix qwen_pilot20 --expected-count 20
```

Expected outputs:

- `outputs/qwen_pilot20_generations.jsonl`
- `outputs/qwen_pilot20_token_traces.jsonl`
- `outputs/qwen_pilot20_report.json`
- `outputs/qwen_pilot20_validation.json`

## Top3 Structured Pilot

After `outputs/qwen_top3_structured_prompts.jsonl` and
`configs/top3_structured_pilot3_questions.json` pass validation, run:

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_batch.py --prompts-path outputs\qwen_top3_structured_prompts.jsonl --question-config configs\top3_structured_pilot3_questions.json --output-prefix qwen_top3_structured_pilot3 --greedy --max-new-tokens 140
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\validate_qwen_batch.py --prefix qwen_top3_structured_pilot3 --expected-count 3
python src\evaluate_top3_structured_pilot.py
```

Expected outputs:

- `outputs/qwen_top3_structured_pilot3_generations.jsonl`
- `outputs/qwen_top3_structured_pilot3_token_traces.jsonl`
- `outputs/qwen_top3_structured_pilot3_report.json`
- `outputs/qwen_top3_structured_pilot3_validation.json`
- `results/top3_structured_pilot3_evaluation.csv`
- `results/top3_structured_pilot3_report.json`
- `results/top3_structured_pilot3_validation.json`

## Top3 Sorted-Evidence Control

This is a diagnostic control, not a final benchmark prompt. It sorts evidence
rows by `net_revenue_gbp` descending before generation.

```powershell
python src\build_top3_sorted_control_prompts.py
python src\validate_top3_sorted_control_prompts.py
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_batch.py --prompts-path outputs\qwen_top3_sorted_control_prompts.jsonl --question-config configs\top3_sorted_control_pilot3_questions.json --output-prefix qwen_top3_sorted_control_pilot3 --greedy --max-new-tokens 140
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\validate_qwen_batch.py --prefix qwen_top3_sorted_control_pilot3 --expected-count 3
python src\evaluate_top3_structured_pilot.py --prompts-path outputs\qwen_top3_sorted_control_prompts.jsonl --generation-prefix qwen_top3_sorted_control_pilot3 --pilot-config configs\top3_sorted_control_pilot3_questions.json --output-prefix top3_sorted_control_pilot3 --condition-name "sorted-evidence top3 control"
python src\build_top3_condition_comparison.py
```

Expected outputs:

- `outputs/qwen_top3_sorted_control_prompts.jsonl`
- `outputs/qwen_top3_sorted_control_prompts_report.json`
- `outputs/qwen_top3_sorted_control_prompts_validation.json`
- `configs/top3_sorted_control_pilot3_questions.json`
- `outputs/qwen_top3_sorted_control_pilot3_generations.jsonl`
- `outputs/qwen_top3_sorted_control_pilot3_token_traces.jsonl`
- `outputs/qwen_top3_sorted_control_pilot3_report.json`
- `outputs/qwen_top3_sorted_control_pilot3_validation.json`
- `results/top3_sorted_control_pilot3_evaluation.csv`
- `results/top3_sorted_control_pilot3_report.json`
- `results/top3_sorted_control_pilot3_validation.json`
- `results/top3_prompt_condition_comparison.json`

## Top3 Sorted-Control Token Signal Review

After the sorted-control pilot and comparison are generated, inspect token-level
signals on the remaining failure:

```powershell
python src\build_top3_sorted_control_token_signal_review.py
```

Expected outputs:

- `results/top3_sorted_control_token_signal_spans.csv`
- `results/top3_sorted_control_token_signal_summary.json`
- `results/top3_sorted_control_token_signal_validation.json`

## Energy Trace Readiness Check

Before running a full100 generation, verify that new traces include the fields
needed by both simple logit baselines and a Spilled Energy adapter:

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_batch.py --prompts-path outputs\qwen_top3_sorted_control_prompts.jsonl --question-config configs\top3_sorted_control_pilot3_questions.json --output-prefix qwen_top3_sorted_control_pilot3_energy --greedy --max-new-tokens 140
python src\validate_qwen_batch.py --prefix qwen_top3_sorted_control_pilot3_energy --expected-count 3 --require-energy-fields
python src\build_energy_trace_readiness_report.py
```

Expected outputs:

- `outputs/qwen_top3_sorted_control_pilot3_energy_generations.jsonl`
- `outputs/qwen_top3_sorted_control_pilot3_energy_token_traces.jsonl`
- `outputs/qwen_top3_sorted_control_pilot3_energy_report.json`
- `outputs/qwen_top3_sorted_control_pilot3_energy_validation.json`
- `results/energy_trace_readiness_report.json`
- `results/energy_trace_readiness_validation.json`

## Trace Policy

The dry-run script generates text first, then runs a second forward pass over the full prompt plus generated output. Token logprob, token entropy, and top-2 margin are computed from raw forward logits, not from post-sampling scores.

This matters because `generate(output_scores=True)` can return scores after top-k/top-p processing. Those processed scores are useful for some generation diagnostics, but they are not the raw model distribution we want for uncertainty baselines.

Current token traces also include energy-ready fields from the same raw forward
pass:

- same-step fields: `token_logit`, `step_logsumexp_logits`,
  `selected_step_energy_gap`, `top1_logit`, and `top2_logit`
- probability-mass fields: `spilled_probability_mass_after_top1` and
  `spilled_probability_mass_after_top2`
- adjacent-step fields: `next_state_logsumexp_logits`, `token_energy`,
  `marginal_energy`, `spilled_energy_delta`, and `spilled_energy_abs_delta`

`selected_step_energy_gap` should equal negative token logprob. The adjacent
`spilled_energy_delta` follows the local adapter formula:

```text
spilled_energy_delta = next_state_logsumexp_logits - token_logit
```

## Full100 Generation Prep

Before running the full 100-question generation, validate the explicit run
config:

```powershell
python src\validate_full100_config.py
```

This writes:

- `outputs/full100_config_validation.json`

When the later preflight section reports `ready_to_run_full100_generation=true`,
use the explicit config and require energy fields:

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_batch.py --question-config configs\full100_questions.json --output-prefix qwen_full100 --max-new-tokens 160 --seed 42
python src\validate_qwen_batch.py --prefix qwen_full100 --expected-count 100 --require-energy-fields
```

Do not omit `--question-config`; the batch runner's default question list is
the 5-question smoke test.

## Pilot20 Energy Retrace

To test energy-style detectors before full100, rebuild token traces for the
existing pilot20 answers without generating new text:

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\retrace_qwen_outputs.py --source-prefix qwen_pilot20 --output-prefix qwen_pilot20_energy --expected-count 20
python src\validate_qwen_batch.py --prefix qwen_pilot20_energy --expected-count 20 --require-energy-fields
```

Then align and score spans:

```powershell
python src\build_span_token_alignment.py --generations-path outputs\qwen_pilot20_energy_generations.jsonl --traces-path outputs\qwen_pilot20_energy_token_traces.jsonl --output-prefix pilot20_energy_span_token_alignment
python src\evaluate_pilot_energy_baselines.py
python src\validate_pilot_energy_baselines.py
python src\build_detector_readiness_summary.py
```

## Split-Safe Detector Evaluation Prep

The final detector evaluation must not choose a threshold on the same spans
used for the reported test metrics. The split evaluator joins detector score
rows to the question metadata, selects each detector threshold on dev spans,
and reports held-out test metrics with the fixed dev threshold.

```powershell
python src\build_split_eval_smoke_fixture.py
python src\evaluate_detector_split_metrics.py --scores-path outputs\split_eval_smoke_scores.csv --baseline-family smoke --output-prefix split_eval_smoke
python src\validate_detector_split_metrics.py --output-prefix split_eval_smoke --expected-baseline-count 2
```

The smoke fixture is intentionally tiny. It verifies the mechanics before
full100: dev and test rows are both present, both splits contain positive and
negative spans, and the test threshold is copied from dev.

The pilot20 score files remain train-only, so they should fail split-safe
evaluation. That rejection is expected and is recorded in:

- `results/pilot20_train_only_split_guard_report.json`

## Full100 Preflight

After the config, energy retrace, detector baselines, and split evaluator are
ready, run the consolidated preflight:

```powershell
python src\build_full100_preflight_report.py
```

Current preflight outputs:

- `results/full100_preflight_report.json`
- `results/full100_preflight_validation.json`

The current preflight result is `ready_to_run_full100_generation=true` with
0 failures. The `qwen_full100` generation has now been run and validated.

Current full100 outputs:

- `outputs/qwen_full100_generations.jsonl`
- `outputs/qwen_full100_token_traces.jsonl`
- `outputs/qwen_full100_report.json`
- `outputs/qwen_full100_validation.json`
- `outputs/qwen_full100_stdout.log`
- `outputs/qwen_full100_stderr.log`

Current full100 run summary:

- 100 generation records
- 100 token-trace records
- 7,575 generated tokens
- 218.258 total elapsed seconds
- 0 validation failures with `--require-energy-fields`
- empty stderr log
