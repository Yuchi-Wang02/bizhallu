# Annotation Artifacts

This directory stores span-level annotation artifacts for BizHallu. The
205-span full100 working file is AI-assisted and provisional. Fifteen selected
presentation spans received an additional assistant review and are recorded in
the label-lock package. No independent human annotation or inter-annotator
agreement has been completed.

## Relation Calibration v2

`configs/relation_annotation_v2.json` defines the next calibration protocol.
The five-case reviewer packet is local under `outputs/relation_calibration_v2/`;
the ID/split mapping is separate under `outputs/relation_calibration_admin_v2/`.
No completed reviews or new evaluation labels exist at packet creation time.
It separates neutral atom type, syntax, row fidelity and full-relation verdict,
records character information endpoints, and links repeated assertions into
claim groups. Source-row support can coexist with a wrong ranking relation.

The old guideline file and 205 annotations below remain historical v1 provenance.
Do not overwrite them, expose them in the first-pass review UI, or automatically
map new relation judgments to old atomic labels. q_0048's historical-v1 dev
sensitivity now has a separate assistant-provisional supplement. This follows
the owner's decision to defer personal calibration; it is not an owner submission.
Its nine atoms were saved before this batch read their token scores, with prior
project familiarity disclosed. Whole-pound rounding is accepted explicitly.
The supplement is only used in B2, not merged into the original 205 labels or
relation calibration. Independent review remains pending.

Do not store generated model answers here. Generated text belongs in `outputs/`;
annotations should reference records by `question_id`, `prompt_id`, and
character offsets.

Current files:

- `annotation_guidelines.md`
- `span_annotations_q0048_b2_assistant_v1.jsonl` (nine correct-key-fact atoms for
  the omitted dev answer; provenance and fixed recipe are in
  `configs/q0048_dev_sensitivity_v1.json`; augmented sensitivity only)
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
