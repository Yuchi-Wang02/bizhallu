# BizHallu Agent Instructions

## Project Positioning

BizHallu is a portfolio-scale AI reliability project for business analytics. It audits whether LLM-generated retail analysis is grounded in transaction evidence at the level of individual business-fact spans.

Use this public positioning:

> BizHallu audits whether LLM-generated business analysis is grounded in transaction evidence, at the level of individual business-fact spans.

## Non-Negotiable Claim Guardrails

- Do not claim this is a production-ready hallucination detector.
- Do not claim this is a large independent human-labeled benchmark.
- Do not claim whole-answer correctness; metrics are span-level.
- Describe the annotation package precisely:
  - `205 AI-assisted provisional business-fact span labels` cover 35 dev/test answers.
  - `15 selected presentation spans received an additional assistant review`.
  - No independent human annotation or inter-annotator agreement has been completed.
- Preserve `lock_basis=assistant_full_review` only for the 15 selected presentation spans
  unless the label package is explicitly reworked.
- Preserve published metric values exactly unless they are recomputed from source artifacts:
  - exploratory maximum test AUPRC across candidate signals: `0.835073`
  - exploratory maximum test F1 across candidate signals: `0.779412`
  - aligned business-fact spans: `205`
  - test spans scored: `103`
- The AUPRC and F1 maxima come from different signals. Thresholds were selected on
  dev, but the headline signal for each metric was selected after comparing test
  results. Do not describe these maxima as preregistered, confirmatory, or an
  unbiased held-out model-selection estimate.
- The 205-span score package covers 35 of 36 dev/test questions. Those 35 were
  selected through a high-priority queue conditioned on generated-answer
  auto-status. Describe current metrics as conditional on an outcome-informed,
  error-enriched subset rather than representative of all generated answers.
- The current question split is periodic within question type, not grouped by
  month or evidence context. Dev and test share business periods, and exact gold
  evidence-row payloads cross splits. Do not claim context-independent or
  unseen-period generalization.
- State that the current evaluation scores pre-identified business-fact spans.
  Automatic claim extraction from unseen responses is outside the current scope.

## Public Artifact Rules

- `docs/` is the GitHub Pages source of truth.
- `reports/` contains experiment-native HTML and summary artifacts.
- `results/` contains lightweight detector reports and metrics.
- Do not commit raw data, model weights, Hugging Face cache, full Qwen generations, token traces, or external baseline repositories.
- Public JSON and manifest artifacts must use repo-relative paths. Do not publish `C:\Users\...` or `Downloads\p1\bizhallu` paths.
- Local setup docs may mention local Windows paths only when they are explicitly documenting the local runtime setup.

## Validation Checklist

GitHub Actions runs the public artifact checks from `.github/workflows/validate.yml`.

Run these checks after modifying public pages, reports, summaries, or README:

```powershell
python src\sanitize_public_json_paths.py
python src\validate_public_path_hygiene.py
python src\validate_github_pages_bundle.py
python src\validate_portfolio_demo_v2.py
python src\validate_portfolio_demo.py
python src\validate_full100_detector_interpretation.py
python src\validate_career_package.py
python src\validate_portfolio_narrative.py
python src\validate_interview_deck.py
python src\validate_business_risk_lens.py
python src\validate_research_one_pager.py
python src\validate_evidence_verifier_pilot.py
python src\validate_methodology_hardening.py
python src\validate_confirmation_dataset_acquisition.py
python src\validate_confirmation_dataset_quality.py
python src\validate_confirmation_dataset_overlap.py
python src\validate_confirmation_context_feasibility.py
python src\validate_confirmation_precision_review.py
python src\validate_confirmation_context_manifest.py
python src\validate_confirmation_question_design.py
python src\validate_confirmation_dataset_source_audit.py
python src\validate_confirmation_set_v1_design.py
```

When local full100 artifacts are available, also run:

```powershell
python src\build_full100_preflight_report.py
```

## Preferred Next Technical Direction

The September 5 semester plan is employment-first with a research option, not an
instruction to execute every research stage immediately. The owner subsequently
deferred personal review and requested English presentation work to continue.
Do not make the B01 trial a prerequisite for assistant-led content improvements,
and do not count those improvements as completed owner review.
Use the milestones and owner procedure in `app/README.md`. Keep actual reviews,
learning notes and identities private; do not fill in the owner's judgments.
Preserve the packet commitment and existing response schema. Localized display
labels do not change saved enum values. `--case-id B01 --require-complete` requires
only the selected case to be submitted, never turns other drafts into labels, and
does not verify semantic accuracy or independent review. No new Qwen run,
confirmation execution, baseline expansion or plugin is needed for this batch.

The English primary presentation uses `src/presentation_evidence.py` to check
six explicitly curated ranked statements in q_0064/q_0069. This is not an
independent verifier or six new evaluation labels. Their own product-amount
pairs match evidence; their ranking relationships can still be wrong. Do not
infer completed-relationship confidence from an earlier list-marker token.
Preserve original evidence order, answers, 205 labels and 15 selected judgments.
The primary pages, career package and narrative share the source-backed B1
comparison. English interview deck v2 is separate from the preserved historical
deck. Its script, notes and evidence come from `src/presentation_story.py`.
Do not replace the versioned deck with an old template or change chart scales
to exaggerate small differences. Public content and
script tests do not establish visual quality, human review or owner mastery.
The historical seven-span case readout now uses the same curated relationship
checks and B1 comparison. Its original labels, outcomes and thresholds remain
unchanged. Compare public thresholds to the original split reports, not only to
another regenerated summary. The business risk lens uses Stage A's historical
ledger and metric contract; category subtotals must reconcile and physical
return value remains unidentifiable. Public validation is not raw-data replay
or evidence of business savings.
`python src/audit_calibration_sources.py` independently replays quantity-price
arithmetic for q_0048/q_0053/q_0092 against the local eligible-line table. It writes
only `outputs/relation_calibration_admin_v2/source_checks.json`, outside the
reviewer packet. This is a curated assistant calculation note, not automatic
claim extraction, reviewed v1 atoms, relation labels or an owner submission.
Do not treat q_0048 whole-pound rounding as a new error, q_0053's missing
increase keyword as proof of reversed direction, or q_0092's unrequested
percentage omission as an answer error. The B2 supplement is still separate.
Test generated demo logic with `node --test tests/test_public_demo_ui.cjs`.
Deck source checks use only standard-library OOXML parsing; authoring requires
the bundled Artifact Tool runtime and never runs in CI. Rendered-slide review
does not establish behavior in desktop PowerPoint or owner presentation mastery.
The published English deck v2 and speaking script include the B2 caveat;
keep the original B1 chart/interval distinct from sensitivity results. Four
historical Pages reports receive archive notices during copying, without editing
their source records. Preserve those notices and their tests. A reviewed public
candidate was tested via a temporary local commit and clean clone with a
standard-library-only environment before the real release. The ignored
`outputs/release_stage1/` receipts describe that Windows dry-run, not deployment.
The candidate was subsequently published as `24c7f5a`; GitHub Linux CI and Pages
passed for that exact commit, and ten live HTML/deck responses matched local
content. See the current-state audit for run links. Browser/mobile/print and
owner acceptance remain unverified. Do not add the unrelated Claude files or
private review/confirmation artifacts to a release.

The next research extension should keep two tracks open. The current public
`Claim-Evidence Review Schema v0` organizes the 15 Demo v2 spans for comparison,
but its statuses are derived from existing presentation labels. It is not an
independent evidence-aware detector. Internal-state and literature-grounded
hallucination baselines remain comparison candidates rather than rejected paths.

Preferred framing:

> Internal uncertainty signals can rank some risky spans. Their relationship to full evidence-binding correctness remains an open comparison question. BizHallu will compare internal-state signals with evidence-aware verification while accounting for information timing and annotation units.

Research comparison tracks:

- Internal uncertainty: entropy, top-2 margin, and energy-style probability-mass signals already used in the project.
- Literature-grounded baselines: Semantic Entropy, TOHA, and entity-level hallucination detection as future comparison candidates.
- Evidence-aware verification: claim-evidence consistency checks against structured evidence rows and deterministic gold answers.

Do not call the current schema an implemented verifier, use its label-derived
statuses as predictions, expand it beyond Demo v2, or report verifier metrics until
an independent claim-evidence decision rule and comparison protocol are fixed and
validated.

Use `configs/methodology_protocol_v1.json` and the generated Methodology
Hardening v1 report as the source of truth for the limitations of the current
retrospective study. Use `configs/confirmation_set_v1_protocol.json` and
`reports/bizhallu_confirmation_set_v1_design.html` as the source of truth for
the prospective next study.

Confirmation Set v1 is design-only and is not execution-ready. Its dataset-source,
context-manifest, and question-design gates are complete; the other four gates must remain pending
until each requirement is actually satisfied. The official-source desk audit selects the strict prior-period window from UCI Online
Retail II. The official ZIP and workbook are acquired, hashed, and kept under the
Git-ignored raw-data tree. The two-sheet structure, three required raw-header
aliases, complete InvoiceDate range, and 502,938-row strict prior-period boundary
are verified. Strict-window completeness, duplicate/grain behavior, cancellation
and value rules, and all 12 months have also been profiled with documented
controls. The local 23-column line table remains Git-ignored because it contains
source invoice and customer identifiers. Canonical eight-field and date-blind
seven-field comparisons now prove zero repeated records against the current Online
Retail lineage; expected product, customer, country, and five-field business-pattern
continuity is disclosed separately and is not external independence.

An outcome-blind precision review tested 15, 21, 24, and 27 confirmation
contexts under frozen synthetic scenarios. None passed every frozen
strong-comparison rule, and the thresholds were not relaxed afterward. The
scope amendment therefore changes Confirmation Set v1 from a detector-
superiority study to an estimation-focused study: family-level AUPRC intervals
are primary, paired differences are descriptive, and subgroup results are
descriptive. Do not claim detector superiority from Confirmation Set v1.

The revised plan contains 6 protocol-pilot, 15 development, and 27 confirmation
contexts, for 48 period-disjoint contexts and 96 frozen private questions. A repeated
outcome-blind capacity proof found 50 observed complete calendar weeks, a
48-of-48 period-to-family matching, and minimum Hall-capacity slack 2 across
net-revenue reconciliation, product return comparison, and country-product
exposure. Customer concentration stays blocked because 100,207 Customer IDs
are missing. A deterministic private manifest now fixes the 48 selected periods,
16 contexts per family, the 6/15/27 split, two reserve periods, scope entities,
context IDs, and canonical context evidence-pool hashes. The private manifest is
Git-ignored; public artifacts may expose only aggregate counts and the canonical
SHA-256 commitment `002b484b3b59c52db0a2213b8d896750cdb2bb9157998d48bf015eff27f19e5a`.
Do not publish or manually edit selected periods, context IDs, scope entities, or
private evidence hashes. Do not substitute reserve periods after outcome access.
A second deterministic private manifest now fixes 96 question IDs, six templates,
question text, gold answers, selected scope entities, and question-level evidence
payloads. Public artifacts may expose only rules, aggregate counts, and its canonical
SHA-256 commitment `b72ffaf715afef85867522fb0c7264377350ce146709962e420c16eaa6d9e80c`.
All 96 full-payload fingerprints and all 96 normalized evidence-table content
fingerprints are unique, with zero exact cross-split overlap. None of the normalized
contents matches the 66 unique historical full100 evidence-table contents under the
wrapper-independent comparison.
Do not publish or manually edit private question IDs, text, gold answers, entities,
evidence rows, or payload fingerprints.

The September 4 Stage A amendment is now the active business definition:
`configs/business_metric_contract_v1_1.json` and
`configs/confirmation_metric_amendment_v1_1.json`. The original v1 context and
question manifests remain unchanged historical provenance. v1.1 preserves all 48
contexts, the 6/15/27 split and all 96 numeric/entity gold answers; it changes
business wording, field names, metadata and their commitments. Follow the
`active_business_definition` pointer in the study protocol, not legacy v1 wording.
Negative transaction value includes non-merchandise fees/adjustments and must not
be equated with physical returns. Merchandise is a code-based scope heuristic.
Do not manually change either frozen private manifest; use a versioned generator.

Stage B1 adds `configs/retrospective_statistics_v2.json` and a separate
`reports/bizhallu_statistics_v2_report.json` appendix. It uses tied-score AP,
unrounded aggregation of saved float32 traces, dev-only references, balanced
accuracy, MCC and paired cluster differences. Preserve original full100 results;
do not rerun legacy evaluation commands against their original output prefixes.
The historical maxima remain provenance, not current superiority claims.
The dev-fitted fact-type prior has higher F1 than entropy on this annotated
subset, while margin has higher AP. Do not promote the prior into a new headline.
Type names include correctness hints; the prior is an annotation-composition
diagnostic, not an information-matched independent detector.
Only two overlapping-period components remain; their intervals are diagnostic,
not reliable inferential bounds. Same-step energy gap is an NLL alias.
B2 now has nine assistant-provisional q_0048 atoms in a separate annotation file,
`configs/q0048_dev_sensitivity_v1.json`, and `src/q0048_dev_sensitivity.py`.
Do not alter the prepared packet, annotation/config commitments or original B1
outputs. A changed judgment requires a new version. Recomputing B2 never merges
the nine atoms into the original 205, changes the original 103 test spans, or
completes owner calibration. The 214-span augmented package is sensitivity only.
Entropy's saved-precision old-test F1 changes from 0.7794117647 to 0.752 after
dev-only refitting; margin is unchanged. Fixed-score AP is unchanged; the refitted
fact-type prior can change ranking. Do not select a new winner, compare this
appendix to fresh held-out evidence, or treat repeated precision-arm rows as
independent observations. Methods now includes B2 without replacing B1.
Run `python src/q0048_dev_sensitivity.py validate`; add `--require-local` for
q_0048 token replay and private input preservation checks. Public CI runs only
the committed-data tier. All supplemental labels remain assistant-provisional;
the C1 reviewer packet and zero completed owner reviews are unchanged.
Stage C1 now prepares five score-blind historical calibration cases, not reviewed
labels: `configs/relation_annotation_v2.json` and `src/relation_review.py`.
Reviewer packet/exports and admin mapping stay in separate Git-ignored outputs
folders. Do not embed gold, old atom boundaries, labels, split or scores in the
packet, and do not claim true blinding after prior exposure. Original model input
and evidence order remain intact. Review identity is self-reported; automated
schema checks do not establish independent human agreement or semantic accuracy.
Keep row fidelity separate from relationship correctness, neutral atom types
separate from format errors, and repeated relation counts grouped. A bare list
marker is not a decisive relation; unmatched requires a parseable claim and an
explicit complete search scope. A blank/partial form must never pass as labels.
Validate public protocol with `python src/relation_review.py validate`; add
`--require-local` for the excluded five-case source projection. Test form logic
with `node --test tests/test_relation_review_ui.cjs`. No new package dependency
is required; visual/owner acceptance remains pending before scaling reviews.
Relation annotation and independent verifier development follow. Model/prompt
freeze remains a later gate. Run
`python -m unittest discover -s tests -v` and
`python src/validate_metric_amendment.py` for public checks; with local source
files additionally run `python src/validate_metric_amendment.py --require-local
--output reports/bizhallu_metric_amendment_v1_1_local_validation.json`.
Public-only validation must not be described as a private source replay.
Run `python src/validate_retrospective_statistics.py` to replay public calculations
and all 15,000 paired cluster draws; add `--require-local --output
reports/bizhallu_statistics_v2_local_validation.json` for saved-trace replay.
No model is invoked. Public validation alone cannot attest to private trace values.
Do not run Qwen, invent labels, score an independent verifier, inspect confirmation
outcomes, or present retrospective appendix values as new confirmatory results.
Any future
result described as confirmatory must use
fresh or context-separated data, select annotation targets before answer-quality
review, freeze primary detector and threshold policies before confirmation-set
access, use two independent human reviewers, and report claim extraction
separately from verification.
