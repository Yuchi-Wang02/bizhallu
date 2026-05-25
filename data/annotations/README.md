# Annotation Artifacts

This directory stores human span-level labels.

Planned files:

- `annotation_guidelines.md`
- `span_annotations_pilot.jsonl`
- `span_annotations_full100.jsonl`

Do not store generated model answers here. Generated text belongs in `outputs/`;
annotations should reference records by `question_id`, `prompt_id`, and
character offsets.

Current files:

- `annotation_guidelines.md`
- `span_annotations_pilot.jsonl` (20-answer pilot annotations for `q_0001`, `q_0012`, `q_0016`, `q_0017`, `q_0022`, `q_0029`, `q_0030`, `q_0041`, `q_0047`, `q_0050`, `q_0052`, `q_0057`, `q_0060`, `q_0065`, `q_0072`, `q_0073`, `q_0084`, `q_0088`, `q_0089`, and `q_0100`)
- `span_annotations_full100_seed.jsonl` (policy-reviewed draft 5-question
  full100 seed for offset/schema validation before expanding to the full
  held-out batch)
- `span_annotations_full100_draft.jsonl` (current 35-question held-out
  high-priority draft annotation pass; consistency audit is in
  `outputs/full100_annotation_consistency_audit_report.json`; audit-note
  review is in `outputs/full100_audit_note_review_report.json`; review before
  using for public final scoring)
