# App

This directory contains the offline relation-review workbench template and
JavaScript, separate from the public portfolio demo.

## Local Calibration Workbench

`python src/relation_review.py build` creates a five-case historical calibration
packet under the Git-ignored `outputs/relation_calibration_v2/` directory.
Open its `review.html` directly; no server or external assets are required.
Reviewer exports stay local and must never be automatically promoted to labels.
`python src/relation_review.py check-response --responses <export.json>` checks
structure, character ranges and reference integrity. `--require-complete` rejects
partial drafts; even a complete submission is not an adjudicated evaluation set.

Inputs exclude gold answers, old annotation boundaries/labels, split and detector
scores. Already-seen examples are not truly blind; prior exposure is self-reported.
The admin mapping is outside the reviewer packet. Python checks are authoritative;
Node tests cover client data logic, but browser rendering still needs owner QA.
Do not use the public demo, existing annotated reports or admin mapping while
performing the first-pass review. The packet preserves original prompt evidence
order and original business wording, with a separate metric-definition caveat.

## First Owner Session

This procedure is retained for later. The owner has deferred personal review;
the current workstream is English evidence-backed presentation and assistant
source checking. Zero completed owner reviews remains the honest status. Do not
prefill an export, simulate a reviewer, or delay all content work on this session.

Start with B01 only. The other four cases remain drafts, and none of the existing
historical labels or scores is replaced by this exercise.

1. Open the local `outputs/relation_calibration_v2/review.html`. Record reviewer
   identity and previous exposure honestly; no answer or identity is prefilled.
2. Read the original question, evidence and answer. Select factual text and record
   the corresponding business relationship with source-row references. If the
   interface or a rule is unclear, export a partial draft instead of guessing.
3. Use the case notes for your own explanation: the business decision, metric
   scope/sign/unit, evidence for your judgment, and remaining limitations. Do not
   consult the public annotated examples or detector scores for this first pass.
4. Check the case draft. Only mark full coverage after reviewing the entire
   answer; changing annotations or notes clears that attestation. Submit this
   case for review only when ready, then request a JSON export.
5. Verify that the downloaded JSON exists, then import it back to compare the
   text, selected spans, references and notes. A requested browser download is
   not proof of a saved file; the leave-page warning remains after export.

Share the actual export location with the assistant for a read-only check:

```powershell
python src/relation_review.py check-response --responses <export.json> --case-id B01
python src/relation_review.py check-response --responses <export.json> --case-id B01 --require-complete
```

The first command accepts a partial draft; the second requires B01 to be
submitted. Both validate the whole imported file, including other draft cases.
Without `--case-id`, `--require-complete` still requires all five cases.
`ready_for_case_adjudication` means ready for someone to inspect that case, not
verified accuracy, independent human agreement, or readiness for metrics.

The owner trial also includes a 90-second explanation in the owner's own words:
what decision is being checked, what the evidence does or does not establish,
and what should not be claimed. Recording this text is not proof of mastery;
follow-up questions and a fresh calculation are the learning check. Browser
layout and real selection/download/import acceptance remain pending an actual
owner trial. No private review or learning notes belong in the public repository.

## Adopted Semester Milestones

The September 5 plan prioritizes employment with a research option, using about
7-10 hours of owner participation per week. Milestones are deliverable gates,
not calendar guarantees; keep at most two active workstreams.

| Stage | Target window | Deliverable and acceptance | Current state |
| --- | --- | --- | --- |
| Credible portfolio and ownership | Weeks 1-2 | First-case trial, five-case calibration, separately versioned q_0048 sensitivity, three main public entry points, 90-second and five-minute explanations | English B1/B2 materials and separate supplement published; public HTTPS desktop/narrow-viewport workflows tested with mobile fixes at 51caaa1; CI/Pages pass; private workbench trial, owner calibration and mastery remain open |
| External feedback | Weeks 2-4 | 15 current employer-posted roles, skill-gap table, 3-5 faculty candidates, three tailored outreach drafts and two practice presentations | Not started; owner confirms any sending |
| Core analyst skills | Weeks 3-6 | Six SQL queries, at most two Power BI pages, one business note; reconcile numbers and explain query changes | Not started |
| Independent verifier | Weeks 6-9 | top3 relation extraction and evidence checking; no evaluation-only inputs; coverage/abstention/error analysis | Not started; public schema is not a detector |
| Research decision | Weeks 9-12 | Formula/resource/information-budget comparison and explicit continue-or-hold decision | Not started; confirmation outcomes remain sealed |

Default owner time: three hours on hands-on analysis, two on business review,
one or two on communication, and one to three on the current technical stage.
During busy coursework, reduce research expansion first. Portfolio sharing with
honest limitations does not require completing an independently double-reviewed
benchmark. Current A/B1/C1 preparation does not count as completed owner review.
JHU course projects and career feedback should inform these milestones, not be
replaced by additional report-generation infrastructure.

Assistant calculation notes for the other three calibration examples live only
in `outputs/relation_calibration_admin_v2/source_checks.json`. They replay seven
scope aggregates from quantity and unit price and preserve exact answer quotes.
Those notes do not assign owner labels, alter the reviewer packet or attest to
whole-answer coverage. A subsequent B2 batch prepared a separately versioned
nine-atom q_0048 supplement and dev-threshold sensitivity; this does not complete
the C1 form. Any later reviewer who reads the notes or B2 supplement must disclose
that exposure rather than claim a blind first pass.

No new model run, baseline family, plugin installation or confirmation execution
is part of this first owner-session batch. Existing Python and Node are enough.

The existing public-demo priority remains:


- Use the static GitHub Pages bundle first.
- The public interactive path is `docs/portfolio_demo_v2.html`.
- The public data bundle is `docs/assets/bizhallu_demo_v2_data.json`.

Why static first:

- It runs directly from GitHub Pages without local setup.
- It is better for recruiters, interviewers, and portfolio visitors.
- It keeps raw data, model outputs, token traces, and model weights outside the
  public app surface.

Optional future entry point:

- `streamlit_demo.py`

The optional local app can add heavier inspection views, but it should reuse the
same public-safe case data shape: business question, evidence summary, Qwen
answer, span labels, detector scores, and detector outcome.
