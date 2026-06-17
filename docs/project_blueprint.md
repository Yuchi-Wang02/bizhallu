# BizHallu Project Blueprint

Version: 0.1

## Purpose

BizHallu is a business-analysis hallucination detection project. The final
artifact should show that an LLM can write fluent retail analytics conclusions
that contain incorrect or unsupported business facts, and that those facts can
be labeled and evaluated with transparent detector baselines.

The project should stay focused on this message:

```text
business evidence table -> LLM answer -> key fact spans -> detector scores -> metrics/demo
```

It should not become a generic sales dashboard or a loose reproduction of
hallucination papers.

## Workspace Boundaries

The current workspace is split into four roles:

```text
C:\Users\yuchi\Downloads\p1\bizhallu   # active project code, data products, reports
C:\Users\yuchi\Downloads\p1\papers     # paper PDFs and reference material
C:\Users\yuchi\Downloads\p1\baselines  # external baseline repositories, kept unmodified when possible
C:\Users\yuchi\Downloads\p1\hf_cache   # Hugging Face model cache and weights
```

Keep the BizHallu project reproducible without committing large model files or
vendored baseline code. Baseline adapters should live in BizHallu; upstream
baseline repositories should remain in the sibling `baselines` folder.

## Canonical Project Layout

```text
bizhallu/
  README.md
  requirements.txt
  app/
    README.md
  configs/
    README.md
  data/
    raw/
    processed/
    annotations/
      README.md
  docs/
    index.html
    portfolio_demo.html
    portfolio_demo_v2.html
    portfolio_narrative.html
    career_package.html
    business_risk_lens.html
    detector_interpretation.html
    label_lock_report.html
    github_upload_checklist.md
    data_source_and_cleaning.md
    experiment_design.md
    prompt_design.md
    project_blueprint.md
    qwen_setup.md
  models/
    README.md
  notebooks/
  outputs/
    README.md
  reports/
    README.md
  results/
    README.md
  site/
    index.html
    assets/
      style.css
  src/
```

### Directory Policy

| Directory | Purpose | Current status |
| --- | --- | --- |
| `data/raw/` | Immutable source files. | Contains UCI Online Retail XLSX and ZIP. |
| `data/processed/` | Deterministic cleaned tables, gold questions, validation reports. | Complete for Step 1 and Step 2. |
| `data/annotations/` | Span-label artifacts and annotation guidelines. | Contains pilot labels, full100 working annotations, and guidance. Public wording should say assistant-reviewed / presentation-locked labels, not large human-labeled benchmark. |
| `outputs/` | Intermediate model inputs, generations, traces, review files. | Contains prompt files, Qwen runs, pilot20 and full100 review artifacts, structured/control pilot runs, and validations. |
| `results/` | Final detector scores, metrics, confusion matrices, tables for report/demo. | Contains pilot20 simple and energy baseline diagnostics, top3 prompt-condition evaluations, split-safe evaluation checks, full100 preflight, full100 draft detector score files, split-safe metrics, family comparison, and detector error review. |
| `models/` | Metadata about model choices and external cache locations. | Should not store Qwen weights. |
| `configs/` | Reusable run configs for generation, annotation, baselines, and evaluation. | Contains pilot20, top3 structured/control pilot, full100 generation, and detector baseline-suite configs. |
| `src/` | Project-owned scripts and adapters. | Contains data, prompt, Qwen, and validation scripts. |
| `app/` | Optional local demo. | Static GitHub Pages demo v2 is the public priority; Streamlit can be added later for local deep inspection. |
| `docs/` | Public GitHub Pages bundle and design docs. | Public source of truth for the Pages site: index, demo v2, career package, business risk lens, narrative, detector interpretation, and label lock pages. |
| `reports/` | Source HTML reports, summaries, figures, and portfolio assets. | Contains generated source pages and summaries before they are copied into `docs/`. |
| `site/` | Earlier local static overview. | Kept as a local overview; `docs/` is the current public Pages bundle. |

### Public Terminology

- `full100_draft_*` remains in filenames for artifact lineage. It refers to the
  working annotation/evaluation files used during development.
- Public pages should refer to selected demo labels as
  assistant-reviewed / presentation-locked span labels.
- Do not describe the project as a large human-labeled benchmark, a
  production-ready detector, or a whole-answer correctness benchmark.

## Artifact Lifecycle

### 1. Source and Cleaning

Inputs:

- `data/raw/Online Retail.xlsx`

Project-owned scripts:

- `src/clean_online_retail.py`
- `src/validate_processed_data.py`

Outputs:

- cleaned line-level files
- summary tables
- `data/processed/data_quality_report.json`

Acceptance check:

- processed data validation has 0 failures

### 2. Gold Business Questions

Project-owned scripts:

- `src/generate_questions.py`
- `src/validate_questions.py`

Outputs:

- `data/processed/business_questions_gold.jsonl`
- sample CSV and validation/report JSON files

Acceptance check:

- 100 deterministic question records
- all question ids unique
- question type, difficulty, and split distributions recorded
- validation has 0 failures

### 3. Prompt Inputs

Project-owned scripts:

- `src/build_prompts.py`
- `src/validate_prompts.py`

Outputs:

- `outputs/qwen_input_prompts.jsonl`
- sample CSV and validation/report JSON files

Acceptance check:

- one prompt per question
- gold answers are stored outside the prompt text
- row order does not leak ranking answers
- validation has 0 failures

### 4. Qwen Generations and Token Traces

Project-owned scripts:

- `src/run_qwen_dry_run.py`
- `src/validate_qwen_dry_run.py`
- `src/run_qwen_batch.py`
- `src/validate_qwen_batch.py`

Outputs:

- generation JSONL
- token trace JSONL
- run report JSON
- validation JSON

Acceptance check:

- generated text is non-empty
- generated token ids match token trace length
- token logprob, entropy, top-2 margin, and energy-ready fields are computed from raw forward logits
- optional energy validation passes with `--require-energy-fields` before full100
- CUDA is available during generation

### 5. Pilot Review and Span Annotation

Planned outputs:

- `configs/pilot20_questions.json`
- `outputs/pilot20_selection_preview.csv`
- `outputs/pilot20_selection_validation.json`
- `outputs/pilot20_review.csv`
- `outputs/pilot20_review_report.json`
- `outputs/pilot20_review_validation.json`
- `data/annotations/annotation_guidelines.md`
- `outputs/annotation_guidelines_validation.json`
- `data/annotations/span_annotations_pilot.jsonl`
- `outputs/span_annotations_pilot_validation.json`
- `outputs/pilot20_span_coverage_report.json`
- `outputs/pilot20_span_coverage_by_question.csv`
- `outputs/pilot20_span_coverage_by_fact_type.csv`

Acceptance check:

- each selected answer has enough labelable business fact spans
- both supported and hallucinated spans appear in the pilot
- ambiguous label rules are revised before scaling to 100 answers

### 6. Baseline Scores

External baseline code lives outside the project at:

```text
C:\Users\yuchi\Downloads\p1\baselines
```

Project-owned adapters should live under `src/` and write outputs into
`results/`.

Span-token alignment outputs:

- `outputs/pilot20_span_token_alignment.jsonl`
- `outputs/pilot20_span_token_alignment.csv`
- `outputs/pilot20_span_token_alignment_report.json`

Pilot simple baseline outputs:

- `results/pilot20_simple_baseline_scores.csv`
- `results/pilot20_simple_baseline_metrics.csv`
- `results/pilot20_simple_baseline_report.json`
- `results/pilot20_simple_baseline_validation.json`
- `results/confusion_matrices/pilot20_simple_baselines_confusion_matrices.csv`

MVP order:

1. Simple logit baselines: token NLL, entropy, top-2 margin, span averages.
2. Spilled Energy adapter using generated token logits/traces.
3. Lightweight hidden-state probe if hidden states are saved for annotated spans.
4. Semantic entropy as an answer-level or claim-level comparison if time allows.

Deferred:

- TOHA, unless a reliable runnable implementation is identified.

### 7. Evaluation and Demo

Planned outputs:

- `results/pilot20_simple_baseline_scores.csv` (current pilot sanity check)
- `results/pilot20_simple_baseline_metrics.csv` (current pilot sanity check)
- `results/pilot20_simple_baseline_report.json` (current pilot sanity check)
- `results/pilot20_baseline_error_review.csv` (current pilot diagnostics)
- `results/pilot20_baseline_error_summary.json` (current pilot diagnostics)
- `results/pilot20_error_analysis_by_family.csv` (current pilot diagnostics)
- `results/pilot20_error_analysis_examples.csv` (current pilot diagnostics)
- `outputs/qwen_top3_structured_prompts.jsonl` (current prompt variant)
- `outputs/qwen_top3_structured_pilot3_generations.jsonl` (current prompt variant pilot)
- `outputs/qwen_top3_structured_pilot3_token_traces.jsonl` (current prompt variant pilot)
- `results/top3_structured_pilot3_evaluation.csv` (current prompt variant evaluation)
- `results/top3_structured_pilot3_report.json` (current prompt variant evaluation)
- `outputs/qwen_top3_sorted_control_prompts.jsonl` (current diagnostic control)
- `outputs/qwen_top3_sorted_control_pilot3_generations.jsonl` (current diagnostic control)
- `outputs/qwen_top3_sorted_control_pilot3_token_traces.jsonl` (current diagnostic control)
- `results/top3_sorted_control_pilot3_evaluation.csv` (current diagnostic control)
- `results/top3_prompt_condition_comparison.json` (current prompt-condition comparison)
- `results/top3_sorted_control_token_signal_summary.json` (current detector diagnostic)
- `results/top3_stock_code_score_distribution_summary.json` (current detector diagnostic)
- `outputs/qwen_top3_sorted_control_pilot3_energy_token_traces.jsonl` (current energy trace readiness)
- `results/energy_trace_readiness_report.json` (current energy trace readiness)
- `configs/full100_questions.json` (current full100 preparation)
- `outputs/full100_config_validation.json` (current full100 preparation)
- `outputs/qwen_pilot20_energy_token_traces.jsonl` (current energy retrace)
- `outputs/pilot20_energy_span_token_alignment.jsonl` (current energy retrace)
- `results/pilot20_energy_baseline_metrics.csv` (current energy baseline evaluation)
- `results/pilot20_detector_readiness_summary.json` (current detector readiness summary)
- `configs/detector_baseline_suite.json` (current split-safe evaluation prep)
- `results/split_eval_smoke_metrics.csv` (current split-safe evaluation prep)
- `results/split_eval_smoke_report.json` (current split-safe evaluation prep)
- `results/split_eval_smoke_validation.json` (current split-safe evaluation prep)
- `results/pilot20_train_only_split_guard_report.json` (current split-safe evaluation prep)
- `results/full100_preflight_report.json` (current full100 preflight)
- `results/full100_preflight_validation.json` (current full100 preflight)
- `results/full100_draft_detector_scores.csv` (current full100 score-file prep)
- `results/full100_draft_detector_scores_validation.json` (current full100 score-file prep)
- `results/full100_draft_simple_split_metrics.csv` (current full100 simple split-safe evaluation)
- `results/full100_draft_simple_split_validation.json` (current full100 simple split-safe evaluation)
- `results/full100_draft_energy_split_metrics.csv` (current full100 energy split-safe evaluation)
- `results/full100_draft_energy_split_validation.json` (current full100 energy split-safe evaluation)
- `results/full100_draft_detector_family_comparison.csv` (current detector-family comparison)
- `results/full100_draft_detector_family_comparison_validation.json` (current detector-family comparison)
- `results/full100_draft_detector_error_review.csv` (current detector error review)
- `results/full100_draft_detector_error_review_examples.csv` (current detector error review)
- `results/full100_draft_detector_error_review_validation.json` (current detector error review)
- `reports/full100_detector_interpretation.html` (current detector interpretation)
- `reports/full100_detector_interpretation_summary.json` (current detector interpretation)
- `reports/full100_detector_interpretation_validation.json` (current detector interpretation)
- `reports/full100_label_confirmation_packet.html` (current label confirmation)
- `reports/full100_label_confirmation_packet_summary.json` (current label confirmation)
- `reports/full100_label_confirmation_packet_validation.json` (current label confirmation)
- `reports/full100_label_lock_report.html` (current label lock)
- `reports/full100_label_lock_summary.json` (current label lock)
- `reports/full100_label_lock_validation.json` (current label lock)
- `reports/bizhallu_portfolio_demo.html` (current portfolio demo)
- `reports/bizhallu_portfolio_demo_summary.json` (current portfolio demo)
- `reports/bizhallu_portfolio_demo_validation.json` (current portfolio demo)
- `reports/bizhallu_portfolio_narrative.html` (current portfolio narrative)
- `reports/bizhallu_portfolio_narrative_summary.json` (current portfolio narrative)
- `reports/bizhallu_portfolio_narrative_validation.json` (current portfolio narrative)
- `docs/index.html` (current GitHub Pages bundle)
- `docs/portfolio_demo.html` (current GitHub Pages bundle)
- `docs/portfolio_narrative.html` (current GitHub Pages bundle)
- `docs/detector_interpretation.html` (current GitHub Pages bundle)
- `docs/label_lock_report.html` (current GitHub Pages bundle)
- `docs/github_pages_manifest.json` (current GitHub Pages bundle)
- `docs/github_pages_validation.json` (current GitHub Pages bundle)
- `outputs/qwen_full100_generations.jsonl` (current full100 generation)
- `outputs/qwen_full100_token_traces.jsonl` (current full100 generation)
- `outputs/qwen_full100_validation.json` (current full100 generation)
- `outputs/full100_review.csv` (current full100 review)
- `outputs/full100_review.jsonl` (current full100 review)
- `outputs/full100_review_validation.json` (current full100 review)
- `outputs/full100_annotation_queue.csv` (current annotation prep)
- `outputs/full100_heldout_high_annotation_batch.csv` (current annotation prep)
- `outputs/full100_annotation_queue_validation.json` (current annotation prep)
- `results/simple_baselines.csv` (future full/dev-test run)
- `results/spilled_energy_scores.csv`
- `results/metrics_summary.csv`
- `results/confusion_matrices/`
- `app/streamlit_demo.py`
- `site/index.html`
- `reports/bizhallu_experiment_report.pdf`

Acceptance check:

- thresholds chosen only on dev split
- final metrics reported on held-out test split
- results are shown by fact type, question type, and difficulty
- demo connects generated answer, gold evidence, labels, detector scores, and confusion matrix

## Data Balance Policy

The final test set does not need to force a 50/50 split between correct and
incorrect full answers. The more important unit is the labeled business fact
span.

Use two views:

- balanced diagnostic view: enough supported and hallucinated spans to compare
  detectors clearly
- realistic evaluation view: preserve the natural distribution produced by
  Qwen on the business-analysis prompts

Report class counts for every metric table.

## Current Feasibility Status

The project is feasible on the current machine:

- Qwen3-0.6B is downloaded under the external Hugging Face cache.
- The `torch` conda environment can load the model with CUDA.
- Dry run, 5-record batch smoke test, and 20-record pilot generation already
  produced valid token traces.
- Current traces include raw-logit token logprob, entropy, top-2 margin,
  same-step logit/logsumexp fields, and adjacent-step fields for Spilled
  Energy scoring.
- The split-safe evaluator is implemented and smoke-tested: thresholds are
  selected on dev spans and reused on test spans.
- The consolidated full100 preflight currently reports 0 failures and
  `current_stage=github_pages_ready`.
- The full100 generation and review table are complete and validated.
- The full100 annotation queue is complete and validated, with a 35-row
  held-out high-priority initial batch.
- A 5-question full100 annotation seed is complete and validated with 18 spans
  and exact character offsets.
- A 35-question held-out high-priority full100 draft annotation pass is
  complete and validated with 205 spans across seven question types.
- Full100 detector score files are complete and validated with 205 score rows,
  12 configured simple/energy fields, and `metrics_reported=false`.
- Full100 simple split-safe metrics are complete and validated with 5 baselines,
  dev-selected thresholds, and held-out test reporting.
- Full100 energy split-safe metrics are complete and validated with 7 baselines,
  dev-selected thresholds, and held-out test reporting.
- Full100 detector-family comparison is complete and validated with 12 baseline
  rows, 2 family summary rows, and 4 all-positive-like energy flags.
- Full100 detector error review is complete and validated with 57 held-out test
  FP/FN rows across the selected simple best-AUPRC and energy best-F1 baselines.
- Full100 detector interpretation is complete and validated as a report-ready
  draft generated from source result files.
- Full100 label confirmation packet is complete and validated with 15 selected
  spans across 9 questions.
- Full100 label confirmation review notes are complete and validated. They mark
  15/15 selected labels as supported in this assistant pass, recommend 0 source
  annotation edits, and flag 6 items as span-level caveats.
- Full100 label lock package is complete and validated. It locks 15/15 selected
  spans with `lock_basis=assistant_full_review`, marks 7 rows as primary demo
  examples, 6 as caveat rows, and 2 as QA regression rows.
- The portfolio demo page is complete and validated around `q_0064` and
  `q_0069`, covering 7 locked primary spans with source-backed detector
  readouts.
- The portfolio narrative page is complete and validated. It packages the
  project story, method, results, cases, pitch, resume bullets, slide outline,
  and presentation guardrails.
- The GitHub Pages bundle is complete and validated under `docs/`. It rewrites
  report-relative links into public `docs/` links and records
  `github_pages_ready` in the root preflight.

Main risk:

- Qwen3-0.6B is weak enough on business evidence tables to create many
  labelable errors, and pilot20 now has enough correct and incorrect spans for
  pilot sanity checks. The remaining risk is whether this signal generalizes
  once dev/test splits and larger generation runs are used.

## Immediate Next Decision

The pilot20 simple baseline sanity check is complete. Max token entropy has the
best pilot AUPRC at 0.703, while one-minus minimum top-2 margin has the best
pilot F1 at 0.691. These numbers are optimistic because thresholds are selected
and evaluated on the same pilot set.

The pilot baseline error review is generated with 101 false-positive and
false-negative rows across the best-AUPRC and best-F1 simple baselines. The
pilot error analysis groups those rows into 7 error families and 52 unique
annotated span errors. The largest patterns are correct numeric facts flagged
as uncertain, correct context facts flagged as uncertain, and confident wrong
top-3 product ranking spans.

The top3 structured prompt variant is generated for all 13 top3 product
questions, and the 3-question pilot targeting `q_0060`, `q_0065`, and `q_0072`
has been run and evaluated. It produced valid 3-row markdown tables for 3/3
questions, but exact top3 accuracy was 0/3 and rank-position stock-code accuracy
was 0/9.

The sorted-evidence diagnostic control has also been run on the same three
questions. It improved exact top3 accuracy from 0/3 to 2/3 and rank-position
stock-code accuracy from 0/9 to 6/9. The remaining failure is `q_0065`, where
the model skipped the first evidence row even though it was the highest-revenue
product.

Interpretation: the shuffled structured failure is largely a row-selection and
sorting problem, but Qwen3-0.6B can still miss a salient evidence row even when
the answer order is visible. The sorted-control condition should not be used for
final fairness claims because row order reveals the answer.

The token-signal review on the remaining `q_0065` sorted-control failure shows
that simple uncertainty signals do fire on stock-code choice points: all three
wrong stock-code spans are flagged by the selected pilot20 thresholds. However,
all six correct stock-code spans from the two correct sorted-control answers are
also flagged. Product names and amounts mostly remain unflagged. This means the
simple signals have useful local sensitivity but poor specificity for rank
binding.

The stock-code score distribution comparison adds more detail. On the 9
stock-code spans, max token entropy has pairwise AUC 0.889, mean token NLL has
AUC 0.833, and one-minus minimum top-2 margin has AUC 0.778. The score ranges
still overlap, so no simple metric cleanly separates correct and incorrect
stock-code rank binding in this tiny control.

The energy trace readiness check is complete. A 3-question rerun of the
sorted-control pilot generated 359 token traces with all required energy fields,
0 validation failures, and the same generated answers as the earlier
sorted-control pilot. The trace format is now ready for a Spilled Energy
adapter.

The full100 run config is prepared and validated. It covers all 100 gold
questions, preserves the 64 train / 18 dev / 18 test split, and documents the
intended `qwen_full100` output prefix. The full100 generation has now been run
and validated with energy-ready token traces.

The pilot20 energy retrace is complete. It rebuilt raw-logit traces for the
existing 20 pilot answers, aligned all 135 annotated spans with energy-ready
fields, and evaluated 7 energy-style baselines. The detector adapter is
operational, but pure adjacent-step Spilled Energy does not beat the best simple
uncertainty baseline on pilot20.

The split-safe evaluation code is now implemented. It uses
`configs/detector_baseline_suite.json`, selects thresholds only on dev spans,
reports test metrics with those fixed thresholds, and rejects train-only score
files such as pilot20. The consolidated full100 preflight passes with 0
failures and now records `full100_generation_run=true`.

The full100 review table is also complete. It joins all 100 generated answers
with gold answers, gold facts, prompt evidence rows, and evidence tables. The
review validation passes with 0 failures and preserves the 64 train / 18 dev /
18 test split.

The full100 annotation queue is complete. It orders all 100 review rows and
extracts a 35-row high-priority held-out batch covering 17 dev and 18 test
questions.

The first full100 annotation seed is complete. It labels 18 spans across
`q_0004`, `q_0005`, `q_0009`, `q_0010`, and `q_0014`, with 0 validation
failures. This is a policy-reviewed draft label and offset check, not the final
evaluation label set. The current seed resolves repeated-entity,
malformed-number, and explicit-ranking-claim rules before scaling.

The full100 draft annotation expansion is also complete through round 4. It
combines the seed with the remaining 30 held-out high-priority rows, bringing
the draft to 35 questions and 205 spans with 0 validation failures. It now
covers top country, top product, country comparison, monthly revenue change,
top 3 products, product revenue share, and return impact.

The 35-question draft consistency audit is complete. It reports 0 hard
failures, confirms the 17 dev / 18 test split and source-batch consistency, and
records the review-note path before final metrics. The audit-note review then
resolved all four original notes: `q_0049` was changed to
`hallucinated_key_fact`, `q_0021` remains `unsupported_claim`, and `q_0058` /
`q_0097` remain correct-only because the missing facts are omissions rather
than generated spans.

The full100 draft span-token alignment is complete. It aligns 205/205 draft
spans to `outputs/qwen_full100_token_traces.jsonl`, validates the same 17 dev /
18 test split, confirms all simple and energy score fields are present, and
keeps `metrics_reported=false`.

The full100 detector score-file step is complete. It converts the 205 aligned
draft spans into a wide score table with 5 simple score fields and 7
energy-suite score fields, validates both dev and test contain positive and
negative spans, and still reports no final metrics.

The full100 simple and energy split-safe evaluations are complete. Best
held-out test AUPRC overall is 0.835 from the simple
`one_minus_min_top2_margin` baseline. Best held-out test F1 overall is 0.779
from the simple `mean_token_entropy` baseline. The best energy-family F1 is
0.773 from `mean_spilled_probability_mass_after_top2`. The comparison flags
four pure adjacent-step energy rows as all-positive-like.

The full100 detector error review is also complete. It inspects the selected
simple best-AUPRC and energy best-F1 baselines on held-out test spans, producing
57 error rows: simple has 7 false positives and 20 false negatives; energy has
20 false positives and 10 false negatives. During this review, three rank-3
marker offsets were found and fixed, then all downstream artifacts were rerun
cleanly.

The detector interpretation page is now generated and validated. It packages the
conservative result for portfolio use: simple uncertainty currently gives the
strongest held-out signal, the best energy-family result is not pure
adjacent-step Spilled Energy, and top-3/currency-binding misses show why
business-context methods are still needed.

The focused label confirmation packet is now generated and validated. It covers
all 20 detector error-example rows after deduplication, adds the 3 rank-marker
offset regression checks, and feeds the final label lock package.

The assistant review-note layer is also generated and validated. It recommends
using `q_0064` and `q_0069` as the strongest portfolio examples.

The label lock package is generated and validated. It records
`presentation_labels_locked`, `lock_basis=assistant_full_review`, 15 locked
selected spans, and 0 source fixes.

The portfolio demo page is also generated and validated. It records
`portfolio_demo_ready`, uses `q_0064` and `q_0069`, and checks all 7 locked
primary spans against the source review rows and detector score table.

The portfolio narrative page is generated and validated. It records
`portfolio_narrative_ready` and packages the project story, method, split-safe
results, demo cases, personal-branding text, and presentation guardrails.

The GitHub Pages bundle is generated and validated. It records
`github_pages_ready`, exposes `docs/index.html` as the public entry point, and
copies the demo, demo v2, career package, business risk lens, narrative,
research one-pager, evidence-aware verifier pilot, detector interpretation,
label-lock report, and confirmation packet into
`docs/` with checked local links.

The public polish layer is now part of the project. README provides a first
screen TL;DR, role statement, 5-minute review path, and reproducibility levels.
`AGENTS.md` records claim guardrails for future agent work. Public JSON path
hygiene is enforced by `src/validate_public_path_hygiene.py`. The GitHub Pages
bundle also includes `docs/research_one_pager.html` for professor and research
advisor outreach and `docs/evidence_verifier_pilot.html` for the first
evidence-aware verifier prototype.

The current research extension should remain dual-track. Evidence-aware
verification is the near-term business-facing design direction, but internal
uncertainty and literature-grounded methods remain comparison candidates rather
than rejected paths. The current verifier pilot is limited to Demo v2 locked
spans and should be treated as protocol scaffolding, not a new benchmark.

Next one-step branch:

- keep `docs/index.html` as the GitHub Pages entry point
- use `docs/portfolio_demo_v2.html` as the primary recruiter/interviewer demo
- use `docs/career_package.html` for resume, LinkedIn, and interview language
- use `docs/business_risk_lens.html` to connect the project to accounting,
  supply management, and BA / DS / AI Analyst positioning
- use `docs/research_one_pager.html` for professor, capstone, and research
  advisor conversations
- use `docs/evidence_verifier_pilot.html` to show the v0 evidence-aware
  verifier family and `docs/evidence_aware_verifier_design.md` to plan any
  expansion beyond Demo v2
- defer new model runs until the public package remains clean after validation
