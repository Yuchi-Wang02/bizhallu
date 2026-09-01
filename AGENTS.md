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
python src\validate_career_package.py
python src\validate_business_risk_lens.py
python src\validate_research_one_pager.py
python src\validate_evidence_verifier_pilot.py
python src\validate_methodology_hardening.py
python src\validate_confirmation_dataset_acquisition.py
python src\validate_confirmation_dataset_quality.py
python src\validate_confirmation_dataset_source_audit.py
python src\validate_confirmation_set_v1_design.py
```

When local full100 artifacts are available, also run:

```powershell
python src\build_full100_preflight_report.py
```

## Preferred Next Technical Direction

The next research extension should keep two tracks open. The current public
`Claim-Evidence Review Schema v0` organizes the 15 Demo v2 spans for comparison,
but its statuses are derived from existing presentation labels. It is not an
independent evidence-aware detector. Internal-state and literature-grounded
hallucination baselines remain comparison candidates rather than rejected paths.

Preferred framing:

> Internal uncertainty signals can rank some risky spans, but confident wrong evidence bindings remain difficult. BizHallu's next research step is to compare internal-state signals with evidence-aware verification for business-fact grounding.

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

Confirmation Set v1 is design-only and is not execution-ready. Its seven gates
must remain pending until each requirement is actually satisfied. The official-source
desk audit provisionally selects the strict prior-period window from UCI Online
Retail II. The official ZIP and workbook are acquired, hashed, and kept under the
Git-ignored raw-data tree. The two-sheet structure, three required raw-header
aliases, complete InvoiceDate range, and 502,938-row strict prior-period boundary
are verified. Strict-window completeness, duplicate/grain behavior, cancellation
and value rules, and all 12 months have also been profiled with documented
controls. The local 23-column line table remains Git-ignored because it contains
source invoice and customer identifiers. The dataset gate remains pending. The
next authorized research action is only the normalized record-overlap proof against
the current Online Retail lineage; do not generate contexts or prompts yet. If that
proof passes, the following step is the outcome-blind 36-context feasibility check.
Do not run Qwen, annotate new outputs, or report confirmation metrics before those
checks and the subsequent outcome-blind precision review are complete. Any future
result described as confirmatory must use
fresh or context-separated data, select annotation targets before answer-quality
review, freeze primary detector and threshold policies before confirmation-set
access, use two independent human reviewers, and report claim extraction
separately from verification.
