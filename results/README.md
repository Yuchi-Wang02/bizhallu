# Results

This directory is reserved for final or report-ready evaluation artifacts:

- baseline score tables
- threshold decisions
- metrics summaries
- confusion matrices
- final figures

Do not place raw model generations or token traces here. Those belong in
`outputs/`.

Current pilot files:

- `pilot20_simple_baseline_scores.csv`
- `pilot20_simple_baseline_metrics.csv`
- `pilot20_simple_baseline_report.json`
- `pilot20_simple_baseline_validation.json`
- `pilot20_baseline_error_review.csv`
- `pilot20_baseline_error_summary.json`
- `pilot20_baseline_error_review_validation.json`
- `pilot20_error_analysis_by_family.csv`
- `pilot20_error_analysis_examples.csv`
- `pilot20_error_analysis_summary.json`
- `pilot20_error_analysis_validation.json`
- `top3_structured_pilot3_evaluation.csv`
- `top3_structured_pilot3_report.json`
- `top3_structured_pilot3_validation.json`
- `top3_sorted_control_pilot3_evaluation.csv`
- `top3_sorted_control_pilot3_report.json`
- `top3_sorted_control_pilot3_validation.json`
- `top3_prompt_condition_comparison.csv`
- `top3_prompt_condition_comparison.json`
- `top3_prompt_condition_comparison_validation.json`
- `top3_sorted_control_token_signal_spans.csv`
- `top3_sorted_control_token_signal_summary.json`
- `top3_sorted_control_token_signal_validation.json`
- `top3_stock_code_score_distribution.csv`
- `top3_stock_code_score_distribution_summary.json`
- `top3_stock_code_score_distribution_validation.json`
- `energy_trace_readiness_report.json`
- `energy_trace_readiness_validation.json`
- `pilot20_energy_baseline_scores.csv`
- `pilot20_energy_baseline_metrics.csv`
- `pilot20_energy_baseline_report.json`
- `pilot20_energy_baseline_validation.json`
- `pilot20_detector_readiness_summary.json`
- `pilot20_detector_readiness_validation.json`
- `split_eval_smoke_metrics.csv`
- `split_eval_smoke_report.json`
- `split_eval_smoke_validation.json`
- `pilot20_train_only_split_guard_report.json`
- `full100_preflight_report.json`
- `full100_preflight_validation.json`
- `full100_draft_detector_scores.csv`
- `full100_draft_detector_scores_by_split.csv`
- `full100_draft_detector_scores_report.json`
- `full100_draft_detector_scores_validation.json`
- `full100_draft_simple_split_metrics.csv`
- `full100_draft_simple_split_report.json`
- `full100_draft_simple_split_validation.json`
- `full100_draft_energy_split_metrics.csv`
- `full100_draft_energy_split_report.json`
- `full100_draft_energy_split_validation.json`
- `full100_draft_detector_family_comparison.csv`
- `full100_draft_detector_family_summary.csv`
- `full100_draft_detector_family_comparison_report.json`
- `full100_draft_detector_family_comparison_validation.json`
- `full100_draft_detector_error_review.csv`
- `full100_draft_detector_error_review_by_baseline.csv`
- `full100_draft_detector_error_review_by_fact_type.csv`
- `full100_draft_detector_error_review_by_question_type.csv`
- `full100_draft_detector_error_review_examples.csv`
- `full100_draft_detector_error_review_report.json`
- `full100_draft_detector_error_review_validation.json`
- `confusion_matrices/pilot20_energy_baselines_confusion_matrices.csv`
- `confusion_matrices/pilot20_simple_baselines_confusion_matrices.csv`

Split-safe evaluation files choose detector thresholds on dev spans and report
test metrics with those fixed thresholds. The pilot20 train-only guard is an
expected rejection, not a failed experiment.

The full100 preflight files aggregate readiness checks and now record whether
`qwen_full100` has been run, whether full100 review and annotation-queue
artifacts are ready, whether full100 detector score files are ready, and what
remains before held-out detector metrics.

The `full100_draft_detector_scores*` files are detector-input artifacts for the
205 aligned held-out draft spans. They contain score rows and validation
summaries only; they do not contain threshold choices, metrics, or confusion
matrices.

The `full100_draft_simple_split*` files are the first held-out split-safe metric
outputs for the simple detector family. Thresholds are selected on dev spans
and reused unchanged on test spans.

The `full100_draft_energy_split*` files apply the same policy to the energy
detector family. The `full100_draft_detector_family_*` files compare simple and
energy families and flag all-positive-like thresholds before interpretation.

The `full100_draft_detector_error_review*` files inspect held-out test
false positives and false negatives for the selected simple best-AUPRC baseline
and energy best-F1 baseline, grouped by fact type and question type.
