# Outputs

This directory stores intermediate artifacts that are produced while running the
pipeline:

- model input prompts
- Qwen generations
- token traces
- smoke-test reports
- pilot review tables
- annotation guideline validation reports
- span annotation validation reports
- pilot span coverage reviews
- span-token alignment files
- structured prompt variants

These files are not final evaluation results. Detector scores, metrics, and
confusion matrices belong in `results/`.

Current smoke-test files use flat filename prefixes such as `qwen_batch5_*`.
Future larger runs should use explicit prefixes such as `qwen_pilot20_*` and
`qwen_full100_*`.

Current prompt variant files:

- `qwen_top3_structured_prompts.jsonl`
- `qwen_top3_structured_prompts_sample.csv`
- `qwen_top3_structured_prompts_report.json`
- `qwen_top3_structured_prompts_validation.json`
- `qwen_top3_sorted_control_prompts.jsonl`
- `qwen_top3_sorted_control_prompts_sample.csv`
- `qwen_top3_sorted_control_prompts_report.json`
- `qwen_top3_sorted_control_prompts_validation.json`

Current structured pilot generation files:

- `qwen_top3_structured_pilot3_generations.jsonl`
- `qwen_top3_structured_pilot3_token_traces.jsonl`
- `qwen_top3_structured_pilot3_report.json`
- `qwen_top3_structured_pilot3_validation.json`
- `qwen_top3_sorted_control_pilot3_generations.jsonl`
- `qwen_top3_sorted_control_pilot3_token_traces.jsonl`
- `qwen_top3_sorted_control_pilot3_report.json`
- `qwen_top3_sorted_control_pilot3_validation.json`
- `qwen_top3_sorted_control_pilot3_energy_generations.jsonl`
- `qwen_top3_sorted_control_pilot3_energy_token_traces.jsonl`
- `qwen_top3_sorted_control_pilot3_energy_report.json`
- `qwen_top3_sorted_control_pilot3_energy_validation.json`
- `full100_config_validation.json`
- `qwen_pilot20_energy_generations.jsonl`
- `qwen_pilot20_energy_token_traces.jsonl`
- `qwen_pilot20_energy_report.json`
- `qwen_pilot20_energy_validation.json`
- `qwen_full100_generations.jsonl`
- `qwen_full100_token_traces.jsonl`
- `qwen_full100_report.json`
- `qwen_full100_validation.json`
- `qwen_full100_stdout.log`
- `qwen_full100_stderr.log`
- `full100_review.csv`
- `full100_review.jsonl`
- `full100_review_sample.csv`
- `full100_review_report.json`
- `full100_review_validation.json`
- `full100_annotation_queue.csv`
- `full100_annotation_queue.jsonl`
- `full100_heldout_high_annotation_batch.csv`
- `full100_heldout_high_annotation_batch.jsonl`
- `full100_annotation_queue_report.json`
- `full100_annotation_queue_validation.json`
- `full100_annotation_seed_preview.csv`
- `full100_annotation_seed_report.json`
- `full100_annotation_seed_policy_review.json`
- `full100_annotation_seed_validation.json`
- `full100_annotation_draft_preview.csv`
- `full100_annotation_draft_report.json`
- `full100_annotation_draft_round1_review.json`
- `full100_annotation_draft_round2_review.json`
- `full100_annotation_draft_round3_review.json`
- `full100_annotation_draft_round4_review.json`
- `full100_annotation_draft_validation.json`
- `full100_annotation_consistency_audit_report.json`
- `full100_annotation_consistency_audit_by_question.csv`
- `full100_annotation_consistency_audit_by_split.csv`
- `full100_annotation_consistency_audit_policy_flags.csv`
- `full100_draft_span_token_alignment.jsonl`
- `full100_draft_span_token_alignment.csv`
- `full100_draft_span_token_alignment_report.json`
- `full100_draft_span_token_alignment_validation.json`
- `full100_draft_span_token_alignment_by_split.csv`
- `full100_draft_span_token_alignment_by_question.csv`
- `full100_audit_note_review.csv`
- `full100_audit_note_review_report.json`
- `full100_audit_note_review_validation.json`
- `pilot20_energy_span_token_alignment.jsonl`
- `pilot20_energy_span_token_alignment.csv`
- `pilot20_energy_span_token_alignment_report.json`
- `split_eval_smoke_scores.csv`
- `split_eval_smoke_scores_report.json`

The `*_energy_*` run is a trace-readiness rerun of the sorted-control pilot.
It should match the earlier generated answers but include additional raw-logit
and adjacent-step fields for Spilled Energy scoring.

The `qwen_pilot20_energy_*` run is a retrace of the existing pilot20 answers.
It does not regenerate answers; it rebuilds token traces with energy-ready
fields from a raw forward pass.

The `qwen_full100_*` files are the completed 100-question generation run. The
validation file currently reports 100 generations, 100 traces, and 0 failures
with required energy fields.

The `full100_review.*` files combine generated answers with gold answers, gold
facts, prompt evidence rows, and evidence tables for manual review and span
annotation preparation.

The `full100_annotation_queue.*` files order review rows for manual span
labeling. The `full100_heldout_high_annotation_batch.*` files are the first
recommended annotation batch.

The `full100_annotation_seed_*` files describe, review, and validate the first
5-question policy-reviewed annotation seed. The actual seed labels live in
`data/annotations/span_annotations_full100_seed.jsonl`.

The `full100_annotation_draft_*` files describe and validate the current
35-question full100 held-out high-priority draft annotation pass. The actual draft labels live in
`data/annotations/span_annotations_full100_draft.jsonl`.

The `full100_annotation_consistency_audit_*` files check that the 35-question
draft exactly matches the held-out high-priority batch, has the expected 17 dev
/ 18 test split, keeps source batches consistent, and preserves review notes
before span-token alignment.

The `full100_draft_span_token_alignment*` files align the 205 draft annotation
spans to the saved full100 token traces and validate token coverage. They are
score-preparation artifacts, not final detector metrics.

The `full100_audit_note_review*` files record the resolution of the audit-note
review: `q_0049` was changed to `hallucinated_key_fact`, while `q_0021`,
`q_0058`, and `q_0097` were confirmed without further label changes.

The `split_eval_smoke_scores.*` files are synthetic intermediate fixtures for
testing dev-threshold/test-metric detector logic. They are not model outputs.
