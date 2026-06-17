# Evidence-Aware Verifier Design

## Purpose

This document defines the next research extension for BizHallu without changing
the locked full100 results.

The goal is to compare two detector families:

- **Internal-state signals**: uncertainty or energy-style signals computed from
  model logits and token traces.
- **Evidence-aware verification**: explicit checks that a generated business
  claim is supported by structured evidence rows or deterministic gold answers.

The verifier is not a replacement for the current uncertainty baselines. It is a
new comparison family for the same business-fact grounding problem.

## Research Question

Internal uncertainty signals can rank some risky spans, but confident wrong
evidence bindings remain difficult. Can an evidence-aware verifier catch
business-fact errors that internal-state detectors miss?

## Initial Scope

Start small and do not rerun full100.

- Primary scope: the 9 presentation-locked Demo v2 cases.
- Optional next scope: the 35 held-out high-priority dev/test questions.
- Do not relabel spans or change existing detector metrics during the design
  phase.
- Do not claim production readiness or a new benchmark result until a fixed
  protocol is implemented and validated.

## Inputs

Use existing committed and local artifacts:

- deterministic question metadata and gold answers
- evidence summaries shown in the public demo
- Qwen-generated answer text
- existing span labels and offsets
- existing detector score rows for comparison

The verifier should operate at the same unit as the current evaluation:
individual business-fact spans.

## Output Schema

Each verifier row should contain:

| Field | Meaning |
| --- | --- |
| `question_id` | Existing BizHallu question id |
| `span_id` | Existing span id or stable generated id |
| `span_text` | Exact generated text span |
| `fact_type` | Existing fact type when available |
| `claim_text` | Minimal claim containing the span |
| `evidence_keys` | Evidence rows or gold fields used for verification |
| `verifier_label` | `supported`, `contradicted`, `unmatched`, or `needs_review` |
| `verifier_reason` | Short explanation grounded in evidence |
| `comparison_target` | Current span label or detector outcome being compared |

Label meanings:

- `supported`: the claim is directly supported by evidence or gold answer.
- `contradicted`: the claim conflicts with evidence, rank, entity binding, or
  gold answer.
- `unmatched`: the verifier cannot map the claim to a clear evidence field.
- `needs_review`: the claim is too compound or ambiguous for deterministic
  verification.

## Baseline Backlog

Keep academic comparison paths open:

- **Semantic Entropy**: compare semantic consistency across multiple sampled
  generations. Requires extra generation runs and clustering/paraphrase logic.
- **TOHA**: compare topology divergence over attention graphs. Requires reliable
  attention extraction and a runnable implementation path.
- **Entity hallucination detection**: detect unsupported or contradicted
  product, country, month, and stock-code entities in long-form generated
  answers.
- **Spilled Energy**: already partially represented by current energy-family
  fields; future work should separate pure adjacent-step energy from
  probability-mass controls.

## Evaluation Plan

For the first implementation, report only diagnostic comparisons:

- verifier label distribution by fact type
- overlap between verifier `contradicted` and current hallucinated spans
- internal detector false negatives that the verifier marks `contradicted`
- verifier `unmatched` rate, because high unmatched rate signals poor parsing
- qualitative examples where real evidence values are bound to wrong products,
  ranks, or conclusions

Do not report a new headline AUPRC or F1 until the verifier protocol is fixed
before scoring and applied to a held-out set.

## Success Criteria

The design is ready to implement when:

- the input artifacts are fixed
- claim extraction rules are written
- verifier labels are defined exactly as above
- comparison reporting is limited to existing locked spans
- the public narrative still says the current published metrics are unchanged:
  0.835073 AUPRC, 0.779412 F1, 205 aligned spans, and 103 held-out test spans
