# BizHallu

[Live demo](https://yuchi-wang02.github.io/bizhallu/) |
[Case demo](https://yuchi-wang02.github.io/bizhallu/portfolio_demo.html) |
[Portfolio narrative](https://yuchi-wang02.github.io/bizhallu/portfolio_narrative.html)

BizHallu is a span-level hallucination detection project for LLM-generated
business analysis. It evaluates whether generated business facts are grounded in
transaction-level evidence, using UCI Online Retail data, local Qwen3-0.6B
generations, locked business-fact span labels, and split-safe detector
baselines.

The project is designed as a business analytics and AI reliability portfolio
piece: it shows how fluent retail analysis can contain wrong products, ranks,
amounts, months, and conclusions, and how those failures can be converted into
auditable evaluation artifacts.

## Why This Project Matters

Business users often do not need a model to write more fluent analysis. They
need to know whether a generated business claim is grounded in the underlying
transaction evidence. BizHallu turns that problem into an auditable workflow:

```text
transaction evidence -> LLM answer -> business-fact spans -> detector scores -> public demo
```

The unit of evaluation is a fact span, not the whole answer. A span can be a
number, month, product, country, ranking, comparison, percentage, or business
conclusion that a user might rely on.

## Public Demo

Start here:

- Live GitHub Pages entry: <https://yuchi-wang02.github.io/bizhallu/>
- Interactive case demo: <https://yuchi-wang02.github.io/bizhallu/portfolio_demo.html>
- Long-form portfolio narrative: <https://yuchi-wang02.github.io/bizhallu/portfolio_narrative.html>
- Detector interpretation: <https://yuchi-wang02.github.io/bizhallu/detector_interpretation.html>

The demo focuses on `q_0064` and `q_0069`, two cases where Qwen3-0.6B writes
fluent retail analysis while binding evidence values to the wrong rank or
product. These are the strongest examples for explaining the project in an
interview or portfolio review.

## Key Results

| Item | Value |
| --- | ---: |
| Deterministic business questions | 100 |
| Question types | 7 |
| Local Qwen3-0.6B generations | 100 |
| Held-out high-priority annotated questions | 35 |
| Aligned business-fact spans | 205 |
| Best held-out test AUPRC | 0.835 |
| Best held-out test F1 | 0.779 |
| GitHub Pages bundle status | `github_pages_ready` |

Best held-out test AUPRC comes from `one_minus_min_top2_margin`. Best held-out
test F1 comes from `mean_token_entropy`. In this run, the strongest
energy-family F1 is close but slightly lower at 0.773 from
`mean_spilled_probability_mass_after_top2`.

## What This Shows

- Business analytics framing: deterministic retail questions and gold answers
  are derived from transaction evidence, not synthetic facts.
- AI evaluation discipline: generated answers are reviewed at span level, with
  labels, offsets, token alignment, and split-safe metrics.
- Portfolio relevance: the final pages explain the work as an AI reliability
  project for business analysis rather than a generic sales dashboard.

## Scope and Limitations

- The labels are locked for presentation with `lock_basis=assistant_full_review`;
  this is not a large independently human-labeled benchmark.
- Results should be interpreted at span level, not as whole-answer correctness.
- Raw Online Retail data, large cleaned tables, model traces, and model weights
  are intentionally excluded from the repository.
- The detector baselines are useful diagnostics, not production-ready
  hallucination detection systems.

## Repository Map

| Path | Purpose |
| --- | --- |
| `docs/` | GitHub Pages bundle and project documentation |
| `reports/` | Experiment-native HTML reports and validation summaries |
| `results/` | Detector scores, split metrics, error reviews, and report-ready tables |
| `src/` | Data, generation, annotation, validation, and packaging scripts |
| `configs/` | Question and detector run configurations |
| `data/annotations/` | Annotation guidelines and span-label files |
| `data/processed/` | Lightweight gold-question metadata kept for reproducibility |
| `outputs/` | README only in git; large model outputs are ignored |

## Reproduce the Public Pages

```powershell
python src\build_github_pages_bundle.py
python src\validate_github_pages_bundle.py
python src\build_full100_preflight_report.py
```

Expected state:

- `docs/github_pages_validation.json`: `ready_for_github_pages=true`
- `results/full100_preflight_validation.json`: `current_stage=github_pages_ready`
- both validation files report `num_failures=0`

## License and Data Note

Project code is released under the MIT License. The raw Online Retail dataset
is not committed; the project documents how to rebuild derived artifacts from a
local copy of the source data.

## Workspace Layout

The active project lives under:

```text
C:\Users\yuchi\Downloads\p1\bizhallu
```

Sibling directories are used for large or external assets:

```text
C:\Users\yuchi\Downloads\p1\papers      # downloaded papers and reference PDFs
C:\Users\yuchi\Downloads\p1\baselines   # unmodified external baseline repositories
C:\Users\yuchi\Downloads\p1\hf_cache    # Hugging Face model cache
```

Do not copy model weights or external baseline repositories into the BizHallu
project unless a later packaging step explicitly requires it.

## Current Project Structure

```text
app/
configs/
data/
  raw/
  processed/
  annotations/
docs/
models/
notebooks/
outputs/
reports/
results/
site/
src/
```

The experiment roadmap and artifact policy are documented in
`docs/project_blueprint.md`.

A visual project overview is available at `site/index.html`.

## GitHub Portfolio Bundle

The project now has a GitHub Pages-ready public bundle under `docs/`.

Recommended public entry point:

- `docs/index.html`

Public-facing pages generated from validated report artifacts:

- `docs/portfolio_demo.html`
- `docs/portfolio_narrative.html`
- `docs/detector_interpretation.html`
- `docs/label_lock_report.html`
- `docs/label_confirmation_packet.html`

Upload checklist:

- `docs/github_upload_checklist.md`
- `docs/github_upload_dry_run.md`

To refresh the public bundle after updating report pages:

```powershell
python src\build_github_pages_bundle.py
python src\validate_github_pages_bundle.py
python src\build_full100_preflight_report.py
```

Current result: `docs/github_pages_validation.json` reports
`ready_for_github_pages=true` with 0 failures. The full preflight stage is now
`github_pages_ready`.

For GitHub upload, keep raw data, model weights, Hugging Face cache files,
external baseline repositories, and large model traces out of the commit. The
public pages are intended to explain the project without requiring local Qwen
reruns.

## Step 1: Clean Online Retail Data

```powershell
python src/clean_online_retail.py
```

Processed files are written to `data/processed/`.

For question generation, prefer the net revenue summary files:

- `monthly_net_revenue_summary.csv`
- `country_month_net_revenue_summary.csv`
- `product_month_net_revenue_summary.csv`
- `country_net_revenue_summary.csv`
- `product_net_revenue_summary.csv`

For month-over-month or trend questions, use `monthly_coverage_summary.csv` and prefer 2011-01 through 2011-11. The source data ends on 2011-12-09, so December 2011 is a partial month.

## Validate Processed Data

```powershell
python src/validate_processed_data.py
```

## Experiment Design

The MVP scope, labeling policy, question types, baselines, and evaluation plan are documented in `docs/experiment_design.md`.

## Step 2: Generate Business Questions and Gold Answers

```powershell
python src/generate_questions.py
python src/validate_questions.py
```

Generated files:

- `data/processed/business_questions_gold.jsonl`
- `data/processed/business_questions_gold_sample.csv`
- `data/processed/business_questions_gold_report.json`
- `data/processed/business_questions_gold_validation.json`

## Step 3: Build Qwen Prompt Inputs

Prompt policy is documented in `docs/prompt_design.md`.

```powershell
python src/build_prompts.py
python src/validate_prompts.py
```

Generated files:

- `outputs/qwen_input_prompts.jsonl`
- `outputs/qwen_input_prompts_sample.csv`
- `outputs/qwen_input_prompts_report.json`
- `outputs/qwen_input_prompts_validation.json`

## Step 4 Dry Run: Qwen Generation

Local setup notes are documented in `docs/qwen_setup.md`.

Use the existing conda environment:

```powershell
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_dry_run.py --question-id q_0001
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\validate_qwen_dry_run.py
```

Dry-run outputs:

- `outputs/qwen_dry_run_generation.jsonl`
- `outputs/qwen_dry_run_token_trace.jsonl`

Batch smoke test:

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_batch.py --question-ids q_0001,q_0017,q_0030,q_0050,q_0073 --output-prefix qwen_batch5
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\validate_qwen_batch.py --prefix qwen_batch5 --expected-count 5
```

Batch outputs:

- `outputs/qwen_batch5_generations.jsonl`
- `outputs/qwen_batch5_token_traces.jsonl`
- `outputs/qwen_batch5_report.json`
- `outputs/qwen_batch5_validation.json`

## Step 5a: Select Pilot20 Questions

The pilot selection is stored in `configs/pilot20_questions.json`.

```powershell
python src/validate_pilot_selection.py
```

Validation output:

- `outputs/pilot20_selection_preview.csv`
- `outputs/pilot20_selection_validation.json`

To reproduce pilot20 generation, use the validated config directly:

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_batch.py --question-config configs\pilot20_questions.json --output-prefix qwen_pilot20 --max-new-tokens 160 --seed 42
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\validate_qwen_batch.py --prefix qwen_pilot20 --expected-count 20
```

Generated pilot files:

- `outputs/qwen_pilot20_generations.jsonl`
- `outputs/qwen_pilot20_token_traces.jsonl`
- `outputs/qwen_pilot20_report.json`
- `outputs/qwen_pilot20_validation.json`

## Step 5b: Build Pilot20 Review Table

```powershell
python src/build_pilot_review.py
python src/validate_pilot_review.py
```

Review outputs:

- `outputs/pilot20_review.csv`
- `outputs/pilot20_review_report.json`
- `outputs/pilot20_review_validation.json`

## Step 5c: Draft Annotation Guidelines

```powershell
python src/validate_annotation_guidelines.py
```

Guideline files:

- `data/annotations/annotation_guidelines.md`
- `outputs/annotation_guidelines_validation.json`

## Step 5d: Pilot Span Annotation

```powershell
python src/validate_span_annotations.py --expected-question-count 20 --expected-min-span-count 135
```

Pilot annotation files:

- `data/annotations/span_annotations_pilot.jsonl`
- `outputs/span_annotations_pilot_validation.json`

## Step 5e: Pilot Coverage Review

```powershell
python src/build_pilot_coverage_review.py
```

Coverage review outputs:

- `outputs/pilot20_span_coverage_report.json`
- `outputs/pilot20_span_coverage_by_question.csv`
- `outputs/pilot20_span_coverage_by_fact_type.csv`

## Step 6a: Build Span-Token Alignment

```powershell
python src/build_span_token_alignment.py
```

Alignment outputs:

- `outputs/pilot20_span_token_alignment.jsonl`
- `outputs/pilot20_span_token_alignment.csv`
- `outputs/pilot20_span_token_alignment_report.json`

## Step 6b: Pilot Simple Baselines

```powershell
python src/evaluate_pilot_simple_baselines.py
python src/validate_pilot_simple_baselines.py
```

Pilot baseline outputs:

- `results/pilot20_simple_baseline_scores.csv`
- `results/pilot20_simple_baseline_metrics.csv`
- `results/pilot20_simple_baseline_report.json`
- `results/pilot20_simple_baseline_validation.json`
- `results/confusion_matrices/pilot20_simple_baselines_confusion_matrices.csv`

## Step 6c: Pilot Baseline Error Review

```powershell
python src/build_pilot_baseline_error_review.py
python src/validate_pilot_baseline_error_review.py
```

Pilot error review outputs:

- `results/pilot20_baseline_error_review.csv`
- `results/pilot20_baseline_error_summary.json`
- `results/pilot20_baseline_error_review_validation.json`

## Step 6d: Pilot Error Analysis

```powershell
python src/build_pilot_error_analysis.py
python src/validate_pilot_error_analysis.py
```

Pilot error analysis outputs:

- `results/pilot20_error_analysis_by_family.csv`
- `results/pilot20_error_analysis_examples.csv`
- `results/pilot20_error_analysis_summary.json`
- `results/pilot20_error_analysis_validation.json`

## Step 7a: Top3 Structured Prompt Variant

```powershell
python src/build_top3_structured_prompts.py
python src/validate_top3_structured_prompts.py
```

Structured top3 prompt outputs:

- `outputs/qwen_top3_structured_prompts.jsonl`
- `outputs/qwen_top3_structured_prompts_sample.csv`
- `outputs/qwen_top3_structured_prompts_report.json`
- `outputs/qwen_top3_structured_prompts_validation.json`
- `configs/top3_structured_pilot3_questions.json`

## Step 7b: Run and Evaluate Top3 Structured Pilot

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_batch.py --prompts-path outputs\qwen_top3_structured_prompts.jsonl --question-config configs\top3_structured_pilot3_questions.json --output-prefix qwen_top3_structured_pilot3 --greedy --max-new-tokens 140
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\validate_qwen_batch.py --prefix qwen_top3_structured_pilot3 --expected-count 3
python src/evaluate_top3_structured_pilot.py
```

Structured pilot outputs:

- `outputs/qwen_top3_structured_pilot3_generations.jsonl`
- `outputs/qwen_top3_structured_pilot3_token_traces.jsonl`
- `outputs/qwen_top3_structured_pilot3_report.json`
- `outputs/qwen_top3_structured_pilot3_validation.json`
- `results/top3_structured_pilot3_evaluation.csv`
- `results/top3_structured_pilot3_report.json`
- `results/top3_structured_pilot3_validation.json`

## Step 7c: Sorted-Evidence Top3 Control

This is a diagnostic control, not a final benchmark prompt. The evidence rows
are sorted by `net_revenue_gbp` descending to test whether Qwen can copy and
bind ranks when the answer order is visible.

```powershell
python src/build_top3_sorted_control_prompts.py
python src/validate_top3_sorted_control_prompts.py
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_batch.py --prompts-path outputs\qwen_top3_sorted_control_prompts.jsonl --question-config configs\top3_sorted_control_pilot3_questions.json --output-prefix qwen_top3_sorted_control_pilot3 --greedy --max-new-tokens 140
python src/evaluate_top3_structured_pilot.py --prompts-path outputs\qwen_top3_sorted_control_prompts.jsonl --generation-prefix qwen_top3_sorted_control_pilot3 --pilot-config configs\top3_sorted_control_pilot3_questions.json --output-prefix top3_sorted_control_pilot3 --condition-name "sorted-evidence top3 control"
python src/build_top3_condition_comparison.py
```

Sorted-control outputs:

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
- `results/top3_prompt_condition_comparison.csv`
- `results/top3_prompt_condition_comparison.json`
- `results/top3_prompt_condition_comparison_validation.json`

## Step 7d: Token Signal Review for Sorted-Control Failure

```powershell
python src/build_top3_sorted_control_token_signal_review.py
```

Token-signal review outputs:

- `results/top3_sorted_control_token_signal_spans.csv`
- `results/top3_sorted_control_token_signal_summary.json`
- `results/top3_sorted_control_token_signal_validation.json`

## Step 7e: Stock-Code Score Distribution

```powershell
python src/build_top3_stock_code_score_distribution.py
```

Stock-code distribution outputs:

- `results/top3_stock_code_score_distribution.csv`
- `results/top3_stock_code_score_distribution_summary.json`
- `results/top3_stock_code_score_distribution_validation.json`

## Step 7f: Energy Trace Readiness

The Qwen trace writer now saves raw-logit fields for simple uncertainty
baselines and adjacent-step fields for a Spilled Energy adapter.

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_batch.py --prompts-path outputs\qwen_top3_sorted_control_prompts.jsonl --question-config configs\top3_sorted_control_pilot3_questions.json --output-prefix qwen_top3_sorted_control_pilot3_energy --greedy --max-new-tokens 140
python src\validate_qwen_batch.py --prefix qwen_top3_sorted_control_pilot3_energy --expected-count 3 --require-energy-fields
python src\build_energy_trace_readiness_report.py
```

Energy-readiness outputs:

- `outputs/qwen_top3_sorted_control_pilot3_energy_generations.jsonl`
- `outputs/qwen_top3_sorted_control_pilot3_energy_token_traces.jsonl`
- `outputs/qwen_top3_sorted_control_pilot3_energy_report.json`
- `outputs/qwen_top3_sorted_control_pilot3_energy_validation.json`
- `results/energy_trace_readiness_report.json`
- `results/energy_trace_readiness_validation.json`

## Step 8: Full100 Run Config Readiness

The full run should use an explicit config so `run_qwen_batch.py` cannot fall
back to its 5-question smoke-test default.

```powershell
python src\validate_full100_config.py
```

Validated prep files:

- `configs/full100_questions.json`
- `outputs/full100_config_validation.json`

The full generation command should be run only after the split-safe evaluation
and preflight checks in Step 10 pass:

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_batch.py --question-config configs\full100_questions.json --output-prefix qwen_full100 --max-new-tokens 160 --seed 42
python src\validate_qwen_batch.py --prefix qwen_full100 --expected-count 100 --require-energy-fields
```

## Step 9: Pilot20 Energy Retrace and Baselines

Before full100, test the detector adapter on the existing pilot20 answers
without regenerating those answers:

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\retrace_qwen_outputs.py --source-prefix qwen_pilot20 --output-prefix qwen_pilot20_energy --expected-count 20
python src\validate_qwen_batch.py --prefix qwen_pilot20_energy --expected-count 20 --require-energy-fields
python src\build_span_token_alignment.py --generations-path outputs\qwen_pilot20_energy_generations.jsonl --traces-path outputs\qwen_pilot20_energy_token_traces.jsonl --output-prefix pilot20_energy_span_token_alignment
python src\evaluate_pilot_energy_baselines.py
python src\validate_pilot_energy_baselines.py
python src\build_detector_readiness_summary.py
```

Energy detector outputs:

- `outputs/qwen_pilot20_energy_generations.jsonl`
- `outputs/qwen_pilot20_energy_token_traces.jsonl`
- `outputs/qwen_pilot20_energy_report.json`
- `outputs/qwen_pilot20_energy_validation.json`
- `outputs/pilot20_energy_span_token_alignment.jsonl`
- `outputs/pilot20_energy_span_token_alignment.csv`
- `outputs/pilot20_energy_span_token_alignment_report.json`
- `results/pilot20_energy_baseline_scores.csv`
- `results/pilot20_energy_baseline_metrics.csv`
- `results/pilot20_energy_baseline_report.json`
- `results/pilot20_energy_baseline_validation.json`
- `results/confusion_matrices/pilot20_energy_baselines_confusion_matrices.csv`
- `results/pilot20_detector_readiness_summary.json`
- `results/pilot20_detector_readiness_validation.json`

## Step 10: Split-Safe Evaluation and Full100 Preflight

Before full100, detector thresholds must be selected on dev spans and then
reused unchanged on held-out test spans. The split evaluator is tested on a
small synthetic fixture with real dev/test question ids, and a guard verifies
that train-only pilot20 scores are rejected rather than scored as held-out
results.

```powershell
python src\build_split_eval_smoke_fixture.py
python src\evaluate_detector_split_metrics.py --scores-path outputs\split_eval_smoke_scores.csv --baseline-family smoke --output-prefix split_eval_smoke
python src\validate_detector_split_metrics.py --output-prefix split_eval_smoke --expected-baseline-count 2
python src\build_full100_preflight_report.py
```

Preflight outputs:

- `configs/detector_baseline_suite.json`
- `outputs/split_eval_smoke_scores.csv`
- `outputs/split_eval_smoke_scores_report.json`
- `results/split_eval_smoke_metrics.csv`
- `results/split_eval_smoke_report.json`
- `results/split_eval_smoke_validation.json`
- `results/pilot20_train_only_split_guard_report.json`
- `results/full100_preflight_report.json`
- `results/full100_preflight_validation.json`

Current result: `ready_for_current_stage` is true, with 0 preflight
failures. The current stage is `github_pages_ready`;
the older `ready_to_run_full100_generation` field is retained only for
backward compatibility with earlier reports.

## Step 11: Full100 Generation Run

The validated full100 command produced 100 generations and 100 energy-ready
token traces:

```powershell
$env:HF_HOME='C:\Users\yuchi\Downloads\p1\hf_cache'
$env:HUGGINGFACE_HUB_CACHE='C:\Users\yuchi\Downloads\p1\hf_cache\hub'
& C:\Users\yuchi\anaconda3\envs\torch\python.exe src\run_qwen_batch.py --question-config configs\full100_questions.json --output-prefix qwen_full100 --max-new-tokens 160 --seed 42
python src\validate_qwen_batch.py --prefix qwen_full100 --expected-count 100 --require-energy-fields
python src\build_detector_readiness_summary.py
python src\build_full100_preflight_report.py
```

Full100 outputs:

- `outputs/qwen_full100_generations.jsonl`
- `outputs/qwen_full100_token_traces.jsonl`
- `outputs/qwen_full100_report.json`
- `outputs/qwen_full100_validation.json`
- `outputs/qwen_full100_stdout.log`
- `outputs/qwen_full100_stderr.log`

Current run summary: 100 records, 100 traces, 7,575 generated tokens, 218.258
seconds total, 0 validation failures, and stderr is empty.

## Step 12: Full100 Review Table

The full100 review artifacts combine each generated answer with the gold
answer, gold facts, prompt evidence rows, and evidence table. These files are
for manual answer inspection and span annotation preparation, not final
detector metrics.

```powershell
python src\build_full100_review.py
python src\validate_full100_review.py
```

Full100 review outputs:

- `outputs/full100_review.csv`
- `outputs/full100_review.jsonl`
- `outputs/full100_review_sample.csv`
- `outputs/full100_review_report.json`
- `outputs/full100_review_validation.json`

Current review summary: 100 rows, 64 train / 18 dev / 18 test, 0 validation
failures. Auto triage marks 9 rows as `likely_correct` and 91 rows as
`partially_correct`; this is only a review aid, not a ground-truth label.

## Step 13: Full100 Annotation Queue

The annotation queue orders the validated full100 review rows for manual span
labeling. It puts high-priority held-out rows first, then remaining held-out
rows, then training rows. This is an annotation logistics queue only; detector
thresholds still must be selected on dev and reported on held-out test.

```powershell
python src\build_full100_annotation_queue.py
python src\validate_full100_annotation_queue.py
```

Annotation queue outputs:

- `outputs/full100_annotation_queue.csv`
- `outputs/full100_annotation_queue.jsonl`
- `outputs/full100_heldout_high_annotation_batch.csv`
- `outputs/full100_heldout_high_annotation_batch.jsonl`
- `outputs/full100_annotation_queue_report.json`
- `outputs/full100_annotation_queue_validation.json`

Current queue summary: 100 rows, 0 validation failures. The initial held-out
high-priority batch contains 35 rows: 17 dev and 18 test.

## Step 14: Full100 Annotation Seed

Before labeling the whole 35-row held-out batch, create a small draft seed and
validate the offset/schema mechanics:

```powershell
python src\build_full100_annotation_seed.py
python src\validate_span_annotations.py --annotation-path data\annotations\span_annotations_full100_seed.jsonl --validation-path outputs\full100_annotation_seed_validation.json --generation-file outputs\qwen_full100_generations.jsonl --expected-question-count 5 --expected-min-span-count 18
```

Seed annotation outputs:

- `data/annotations/span_annotations_full100_seed.jsonl`
- `outputs/full100_annotation_seed_preview.csv`
- `outputs/full100_annotation_seed_report.json`
- `outputs/full100_annotation_seed_policy_review.json`
- `outputs/full100_annotation_seed_validation.json`

Current seed summary: 5 held-out high-priority top-country rows, 18 span
labels, 0 validation failures. The reviewed seed now fixes repeated-entity,
malformed-number, and explicit-ranking-claim policy before scaling. This is not
the final full100 evaluation label file.

## Step 15: Full100 Draft Annotation Rounds 1-4 and Consistency Audit

Extend the reviewed seed with balanced multi-type draft batches:

```powershell
python src\build_full100_annotation_draft.py
python src\validate_span_annotations.py --annotation-path data\annotations\span_annotations_full100_draft.jsonl --validation-path outputs\full100_annotation_draft_validation.json --generation-file outputs\qwen_full100_generations.jsonl --expected-question-count 35 --expected-min-span-count 205
python src\audit_full100_annotation_consistency.py
python src\build_full100_preflight_report.py
```

Draft annotation outputs:

- `data/annotations/span_annotations_full100_draft.jsonl`
- `outputs/full100_annotation_draft_preview.csv`
- `outputs/full100_annotation_draft_report.json`
- `outputs/full100_annotation_draft_round1_review.json`
- `outputs/full100_annotation_draft_round2_review.json`
- `outputs/full100_annotation_draft_round3_review.json`
- `outputs/full100_annotation_draft_round4_review.json`
- `outputs/full100_annotation_draft_validation.json`
- `outputs/full100_annotation_consistency_audit_report.json`
- `outputs/full100_annotation_consistency_audit_by_question.csv`
- `outputs/full100_annotation_consistency_audit_by_split.csv`
- `outputs/full100_annotation_consistency_audit_policy_flags.csv`

Current draft summary: all 35 held-out high-priority rows, 205 span labels,
17 dev / 18 test questions, and 0 validation failures. The round-1 through
round-4 expansions add 30 rows and cover top product, country comparison,
monthly change, top 3 products, product-share, and return-impact question
types. The consistency audit reports 0 hard failures and marks the draft ready
for span-token alignment. The follow-up review resolved all four original
notes, including one label change for `q_0049`.

## Step 16: Full100 Draft Span-Token Alignment

Align only the 205 draft spans to the saved full100 token traces. This step
produces span-level score fields but does not report detector metrics.

```powershell
python src\build_span_token_alignment.py --annotations-path data\annotations\span_annotations_full100_draft.jsonl --generations-path outputs\qwen_full100_generations.jsonl --traces-path outputs\qwen_full100_token_traces.jsonl --output-prefix full100_draft_span_token_alignment
python src\validate_full100_span_token_alignment.py
python src\build_full100_preflight_report.py
```

Alignment outputs:

- `outputs/full100_draft_span_token_alignment.jsonl`
- `outputs/full100_draft_span_token_alignment.csv`
- `outputs/full100_draft_span_token_alignment_report.json`
- `outputs/full100_draft_span_token_alignment_validation.json`
- `outputs/full100_draft_span_token_alignment_by_split.csv`
- `outputs/full100_draft_span_token_alignment_by_question.csv`

Current alignment summary: 205/205 spans aligned across 35 held-out rows, 17
dev / 18 test questions, 0 validation failures, simple and energy score fields
present, and `metrics_reported=false`.

## Step 17: Full100 Audit-Note Review

Review the consistency-audit notes before building detector score files:

```powershell
python src\review_full100_audit_notes.py
python src\build_full100_preflight_report.py
```

Review outputs:

- `outputs/full100_audit_note_review.csv`
- `outputs/full100_audit_note_review_report.json`
- `outputs/full100_audit_note_review_validation.json`

Current review summary: 4 questions reviewed, 1 label change applied
(`q_0049`), 0 validation failures, and `metrics_reported=false`.

## Step 18: Full100 Detector Score Files

Build and validate score rows from the 205 aligned draft spans. This produces
detector inputs only; it does not select thresholds or report final metrics.

```powershell
python src\build_full100_detector_score_files.py
python src\validate_full100_detector_score_files.py
python src\build_full100_preflight_report.py
```

Detector score-file outputs:

- `results/full100_draft_detector_scores.csv`
- `results/full100_draft_detector_scores_by_split.csv`
- `results/full100_draft_detector_scores_report.json`
- `results/full100_draft_detector_scores_validation.json`

Current score-file summary: 205 score rows across 35 held-out rows, 102 dev
span rows and 103 test span rows, 12 configured detector score fields, 0
validation failures, and `metrics_reported=false`.

## Step 19: Full100 Simple Split-Safe Metrics

Run only the simple detector family first. Thresholds are selected on dev spans
and then reused unchanged on held-out test spans.

```powershell
python src\evaluate_detector_split_metrics.py --scores-path results\full100_draft_detector_scores.csv --baseline-family simple --output-prefix full100_draft_simple_split
python src\validate_detector_split_metrics.py --output-prefix full100_draft_simple_split --expected-baseline-count 5
python src\build_full100_preflight_report.py
```

Simple split-safe metric outputs:

- `results/full100_draft_simple_split_metrics.csv`
- `results/full100_draft_simple_split_report.json`
- `results/full100_draft_simple_split_validation.json`

Current simple split summary: 5 baselines, 10 dev/test metric rows, 0
validation failures. On held-out test spans, best AUPRC is 0.835 from
`one_minus_min_top2_margin`; best F1 is 0.779 from `mean_token_entropy`.

## Step 20: Full100 Energy Split-Safe Metrics

Run the energy detector family with the same dev-threshold/test-reporting
policy:

```powershell
python src\evaluate_detector_split_metrics.py --scores-path results\full100_draft_detector_scores.csv --baseline-family energy --output-prefix full100_draft_energy_split
python src\validate_detector_split_metrics.py --output-prefix full100_draft_energy_split --expected-baseline-count 7
python src\build_full100_preflight_report.py
```

Energy split-safe metric outputs:

- `results/full100_draft_energy_split_metrics.csv`
- `results/full100_draft_energy_split_report.json`
- `results/full100_draft_energy_split_validation.json`

Current energy split summary: 7 baselines, 14 dev/test metric rows, 0
validation failures. On held-out test spans, best energy-family AUPRC is 0.830
from `max_selected_step_energy_gap`; best energy-family F1 is 0.773 from
`mean_spilled_probability_mass_after_top2`.

## Step 21: Detector Family Comparison

Compare simple and energy families after both split-safe metric passes:

```powershell
python src\build_full100_detector_family_comparison.py
python src\validate_full100_detector_family_comparison.py
python src\build_full100_preflight_report.py
```

Family comparison outputs:

- `results/full100_draft_detector_family_comparison.csv`
- `results/full100_draft_detector_family_summary.csv`
- `results/full100_draft_detector_family_comparison_report.json`
- `results/full100_draft_detector_family_comparison_validation.json`

Current comparison summary: 12 baselines compared, 0 validation failures. Best
overall held-out test AUPRC is 0.835 from the simple `one_minus_min_top2_margin`
baseline. Best overall held-out test F1 is 0.779 from the simple
`mean_token_entropy` baseline. The best energy-family F1 is 0.773 from
`mean_spilled_probability_mass_after_top2`. Four pure adjacent-step energy rows
are flagged as all-positive-like, so they should not be oversold as useful
specific detectors.

## Step 22: Full100 Detector Error Review

Review false positives and false negatives for the selected held-out baselines:
best-AUPRC simple baseline and best-F1 energy-family baseline.

```powershell
python src\build_full100_detector_error_review.py
python src\validate_full100_detector_error_review.py
python src\build_full100_preflight_report.py
```

Detector error-review outputs:

- `results/full100_draft_detector_error_review.csv`
- `results/full100_draft_detector_error_review_by_baseline.csv`
- `results/full100_draft_detector_error_review_by_fact_type.csv`
- `results/full100_draft_detector_error_review_by_question_type.csv`
- `results/full100_draft_detector_error_review_examples.csv`
- `results/full100_draft_detector_error_review_report.json`
- `results/full100_draft_detector_error_review_validation.json`

Current error-review summary: 57 held-out test error rows, 0 validation
failures. The simple best-AUPRC baseline has 7 false positives and 20 false
negatives. The energy best-F1 baseline has 20 false positives and 10 false
negatives. The largest miss patterns are currency amounts and top-3 product
rows; the largest false-positive patterns are correct currency/month facts and
country-comparison spans.

## Step 23: Full100 Detector Interpretation

Build a report-ready HTML interpretation that connects the split-safe metrics
to the detector error-review patterns:

```powershell
python src\build_full100_detector_interpretation.py
python src\validate_full100_detector_interpretation.py
python src\build_full100_preflight_report.py
```

Detector interpretation outputs:

- `reports/full100_detector_interpretation.html`
- `reports/full100_detector_interpretation_summary.json`
- `reports/full100_detector_interpretation_validation.json`

Current interpretation summary: report-ready draft generated, 0 validation
failures. The page states the conservative conclusion: simple uncertainty gives
the strongest current held-out signal, the best energy-family row is a
probability-mass control rather than pure adjacent-step Spilled Energy, and
business context is still needed for top-3 and currency-binding errors.

## Step 24: Full100 Label Confirmation Packet

Build a focused confirmation packet for the examples most likely to appear in
the final report/demo:

```powershell
python src\build_full100_label_confirmation_packet.py
python src\validate_full100_label_confirmation_packet.py
python src\build_full100_preflight_report.py
```

Label confirmation outputs:

- `reports/full100_label_confirmation_packet.html`
- `reports/full100_label_confirmation_packet.csv`
- `reports/full100_label_confirmation_packet.jsonl`
- `reports/full100_label_confirmation_packet_summary.json`
- `reports/full100_label_confirmation_packet_validation.json`

Current confirmation-packet summary: 15 selected spans across 9 questions, 0
validation failures. The packet covers all 20 detector error-example rows after
deduplicating repeated annotation ids, plus the 3 rank-marker offset regression
checks. This packet remains the pre-lock review queue; the final lock decision
is recorded in Step 26.

## Step 25: Full100 Label Review Notes

Build assistant review notes for the 15 confirmation-packet items without
locking labels:

```powershell
python src\build_full100_label_confirmation_review_notes.py
python src\validate_full100_label_confirmation_review_notes.py
python src\build_full100_preflight_report.py
```

Label review-note outputs:

- `reports/full100_label_confirmation_review_notes.html`
- `reports/full100_label_confirmation_review_notes.csv`
- `reports/full100_label_confirmation_review_notes.jsonl`
- `reports/full100_label_confirmation_review_notes_summary.json`
- `reports/full100_label_confirmation_review_notes_validation.json`

Current review-note summary: all 15 selected labels are supported by this
assistant review pass and no source annotation edits are recommended. The main
presentation constraint is that 6 items are `span_level_caveat`: the selected
span is supported, but the surrounding generated answer contains other errors.
These notes feed the locked label package in Step 26.

## Step 26: Full100 Label Lock Package

Lock the 15 presentation-selected labels after assistant full review:

```powershell
python src\build_full100_label_lock_package.py
python src\validate_full100_label_lock_package.py
python src\build_full100_preflight_report.py
```

Label lock outputs:

- `reports/full100_label_lock_report.html`
- `reports/full100_label_lock_decisions.csv`
- `reports/full100_label_lock_decisions.jsonl`
- `reports/full100_label_lock_summary.json`
- `reports/full100_label_lock_validation.json`

Current lock summary: 15/15 selected labels are locked with
`lock_basis=assistant_full_review`, 0 source fixes are required, and the package
is ready for portfolio/demo packaging. The primary demo questions are `q_0064`
and `q_0069`.

## Step 27: Portfolio Demo Page

Package the locked primary examples into a static portfolio/demo page:

```powershell
python src\build_portfolio_demo.py
python src\validate_portfolio_demo.py
python src\build_full100_preflight_report.py
```

Portfolio demo outputs:

- `reports/bizhallu_portfolio_demo.html`
- `reports/bizhallu_portfolio_demo_summary.json`
- `reports/bizhallu_portfolio_demo_validation.json`

Current demo summary: the page uses the locked `q_0064` and `q_0069` primary
examples, covers 7 locked primary spans, and validates against the label-lock
package, review rows, detector score rows, and span offsets. The demo makes the
project's central point visible: Qwen can copy real business values while
binding them to the wrong rank or product, and internal uncertainty signals can
miss those confident wrong bindings.

## Step 28: Portfolio Narrative Page

Build the long-form portfolio narrative that turns the experiment into a
presentation and career-branding artifact:

```powershell
python src\build_portfolio_narrative.py
python src\validate_portfolio_narrative.py
python src\build_full100_preflight_report.py
```

Portfolio narrative outputs:

- `reports/bizhallu_portfolio_narrative.html`
- `reports/bizhallu_portfolio_narrative_summary.json`
- `reports/bizhallu_portfolio_narrative_validation.json`

Current narrative summary: the page is generated from the demo, detector
interpretation, label lock, Qwen run, annotation draft, alignment, and error
review summaries. It includes the project story, method, split-safe results,
primary cases, one-minute pitch, LinkedIn/portfolio blurb, resume bullets,
slide outline, presentation guardrails, and next build steps. It is now the
source of truth for how to explain BizHallu in a portfolio or interview.

## Step 29: GitHub Pages Bundle

Build the public GitHub Pages version from the validated report artifacts:

```powershell
python src\build_github_pages_bundle.py
python src\validate_github_pages_bundle.py
python src\build_full100_preflight_report.py
```

GitHub Pages outputs:

- `docs/index.html`
- `docs/portfolio_demo.html`
- `docs/portfolio_narrative.html`
- `docs/detector_interpretation.html`
- `docs/label_lock_report.html`
- `docs/label_confirmation_packet.html`
- `docs/assets/full100_draft_detector_error_review_examples.csv`
- `docs/github_pages_manifest.json`
- `docs/github_pages_validation.json`

Current public-bundle summary: 7 required public files are present, 6 HTML
files parse successfully, local links resolve, stale report-relative links are
rewritten, and validation reports 0 failures. The root preflight now reports
`current_stage=github_pages_ready`.

## Current Review Point

The pilot20 simple baseline sanity check is complete. The best pilot AUPRC is
0.703 for max token entropy, and the best pilot F1 is 0.691 for one-minus
minimum top-2 margin. These are pilot-only optimistic numbers because thresholds
are selected and evaluated on the same 20 answers.

The baseline error review is also generated. It contains 101 false-positive and
false-negative rows across the best-AUPRC and best-F1 simple baselines. The
pilot error analysis groups those rows into 7 error families and 52 unique
annotated span errors.

The top3 structured prompt variant is generated and validated for all 13
`top3_products_month` questions, and the 3-question structured pilot has been
run and evaluated. The result is a useful negative finding: Qwen produced valid
3-row markdown tables for 3/3 questions, but exact top3 accuracy was 0/3 and
rank-position stock-code accuracy was 0/9. All 9 generated rows came from the
evidence table and copied the selected evidence amount correctly, so the failure
is mainly selecting and sorting rows, not table formatting or product invention.

The sorted-evidence control has also been run on the same three questions. It
improved exact top3 accuracy from 0/3 to 2/3 and rank-position stock-code
accuracy from 0/9 to 6/9, but `q_0065` still failed by skipping the highest
revenue evidence row. This suggests the shuffled structured failure is largely
a row-selection/sorting problem, while Qwen3-0.6B can still miss a salient row
even in an answer-visible control.

The token-signal review for the remaining `q_0065` failure is complete. The
simple selected pilot thresholds flag all three wrong stock-code spans and all
three wrong row-level spans, but they also flag all correct stock-code spans and
all correct row-level spans in the two correct sorted-control answers. Product
names and amounts are mostly not flagged. Interpretation: simple token
uncertainty sees stock-code choice points, but does not cleanly distinguish
wrong rank binding from correct rank binding.

The stock-code score distribution comparison is also complete. On the 9
stock-code spans from the sorted-control run, max token entropy has the best
local ranking signal with pairwise AUC 0.889, followed by mean token NLL at
0.833 and one-minus minimum top-2 margin at 0.778. However, none of the three
scores perfectly separates correct and incorrect rank binding because their
score ranges overlap. This suggests threshold tuning alone is not enough.

The energy trace readiness check is complete on the same three sorted-control
questions. It produced 359 token traces with all required energy fields and 0
validation failures. The regenerated answers match the earlier sorted-control
answers exactly, so the change affects trace richness rather than prompt
behavior.

The full100 run config is also ready and validated. It contains all 100 question
ids, preserves the 64 train / 18 dev / 18 test split, and records the intended
`qwen_full100` command. The full100 generation has now been completed and
validated with energy fields.

The pilot20 energy retrace and baseline pass is now complete. It rebuilt raw
forward-logit traces for the existing pilot20 answers without changing any
generated text or generated token ids. The energy alignment covers all 135
annotated spans with 0 failures. The detector adapter is operational, but pure
adjacent-step Spilled Energy is weaker than the best simple baseline on this
pilot: best simple AUPRC is 0.703, best energy-suite AUPRC is 0.674, and best
pure Spilled Energy AUPRC is 0.560.

The split-safe evaluation path is now implemented and checked. It selects
thresholds on dev spans, reuses those thresholds on test spans, and correctly
rejects train-only pilot20 scores as not eligible for held-out metrics.

The full100 preflight report now aggregates the gold-question, prompt,
full100-config, energy-trace, pilot20-energy, detector-readiness, split
evaluator, and full100 generation checks. It reports 0 failures and records
`full100_generation_run=true`.

The full100 review table is now generated and validated. It includes generated
answers, gold answers, gold facts, evidence rows, evidence tables, auto triage,
and annotation priority. It is the source table for the completed held-out
high-priority draft annotations.

The full100 annotation queue is now generated and validated. It turns that
review table into an ordered annotation workflow and writes a dedicated initial
batch for the 35 high-priority held-out rows.

The first full100 annotation seed is also generated and validated. It labels 18
business-fact spans across 5 held-out high-priority rows, covering correct month
spans, wrong answer entities, wrong answer amounts, and malformed answer
amounts, plus explicit extra ranking claims. It should be reviewed before
being treated as final labels, and it now serves as the template for the full
35-row held-out high-priority draft.

The full100 draft annotation expansion is now generated and validated through
round 4. It combines the 5-question seed with the remaining 30 held-out
high-priority rows, bringing the draft to 35 questions and 205 spans. It is
still a reviewable draft, not final evaluation labels.

The 35-question draft consistency audit is now complete. It checks the draft
against the held-out high-priority batch, split distribution, source batches,
question-level label mix, and dev/test label/fact-type distributions. It has 0
hard failures. The audit-note review resolved the four original notes:
`q_0049` was changed from `unsupported_claim` to `hallucinated_key_fact`;
`q_0021` remains `unsupported_claim`; `q_0058` and `q_0097` remain
correct-only because the missing facts are omissions, not generated spans.

The full100 draft span-token alignment is now complete. It aligns all 205 draft
spans to `qwen_full100_token_traces.jsonl`, validates split distributions
against the consistency audit, and confirms energy-ready score fields. It has
not produced final metrics.

The full100 detector score files, split-safe simple/energy metrics,
detector-family comparison, detector error review, and report-ready detector
interpretation are now complete and validated. A focused label confirmation
packet, assistant review-note layer, and label lock package are also ready.
During error-review
inspection, three rank-3 marker spans
(`q_0063`, `q_0068`, `q_0064`) were found to point at `3.` inside currency
amounts instead of the list marker; the annotation builder was fixed and the
alignment, score files, metrics, family comparison, error review, and preflight
were rerun cleanly. The review notes found 0 source-fix requirements and 7
high-priority demo items, with `q_0064` and `q_0069` the strongest portfolio
examples. The selected presentation labels are now locked, the static portfolio
demo page has been built and validated, the long-form portfolio narrative has
been generated, and the GitHub Pages bundle has been packaged under `docs/`.
The next technical branch is upload hygiene plus deciding whether to add a
short slide deck in the first public release or as a follow-up.
