# Annotation Artifacts

This directory stores span-level annotation artifacts for BizHallu. The
205-span full100 working file is AI-assisted and provisional. Fifteen selected
presentation spans received an additional assistant review and are recorded in
the label-lock package. No independent human annotation or inter-annotator
agreement has been completed.

Do not store generated model answers here. Generated text belongs in `outputs/`;
annotations should reference records by `question_id`, `prompt_id`, and
character offsets.

Current files:

- `annotation_guidelines.md`
- `span_annotations_pilot.jsonl` (20-answer pilot annotations for `q_0001`, `q_0012`, `q_0016`, `q_0017`, `q_0022`, `q_0029`, `q_0030`, `q_0041`, `q_0047`, `q_0050`, `q_0052`, `q_0057`, `q_0060`, `q_0065`, `q_0072`, `q_0073`, `q_0084`, `q_0088`, `q_0089`, and `q_0100`)
- `span_annotations_full100_seed.jsonl` (policy-reviewed draft 5-question
  full100 seed for offset/schema validation before expanding to the full
  held-out batch)
- `span_annotations_full100_draft.jsonl` (35-question held-out high-priority
  working annotation file with 205 spans; the `draft` name is retained for
  artifact lineage, while selected public examples are presentation-locked in
  `reports/full100_label_lock_decisions.jsonl`)

Public wording:

- Say: 205 AI-assisted provisional business-fact span labels.
- Say: 15 selected presentation spans received additional assistant review.
- Say: span-level business-fact evaluation.
- Do not say: large human-labeled benchmark.
- Do not say: whole-answer correctness benchmark.
