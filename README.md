# BizHallu

[Interactive cases](https://yuchi-wang02.github.io/bizhallu/portfolio_demo_v2.html) |
[Methods and results](https://yuchi-wang02.github.io/bizhallu/detector_interpretation.html) |
[Research one-pager](https://yuchi-wang02.github.io/bizhallu/research_one_pager.html)

## TL;DR

BizHallu is an AI reliability project for business analytics. It turns retail
transaction evidence into 100 deterministic questions, asks
`Qwen/Qwen3-0.6B` to generate analysis, builds an AI-assisted provisional span
annotation set, aligns pre-identified business-fact spans to token-level traces,
and compares internal-state detector signals.

Across 103 test spans, the highest observed test AUPRC among the candidate
signals was 0.835 and the highest observed test F1 was 0.779. These values come
from different signals. Thresholds were selected on dev spans, but the headline
signal for each metric was selected after comparing test results, so these are
exploratory test-set maxima rather than a preregistered confirmatory estimate.

**September 4 statistical audit:** the [B1 retrospective appendix](reports/bizhallu_statistics_v2_review.html)
adds corrected tied-score AP and stronger references without overwriting history.
A dev-fitted fact-type prior yields F1 0.836 versus entropy's 0.779 on this
pre-annotated subset; margin retains higher AP than that prior. Entropy's F1
advantage over all-positive predictions has a paired question-bootstrap interval
crossing zero. These are exploratory diagnostics, not detector-superiority claims.
The fact-type prior is an annotation-composition control, not an information-matched
detector: supplied type names can themselves contain correctness hints.

**September 5 omission sensitivity:** the separate [B2 appendix](docs/detector_interpretation.html#b2-dev-sensitivity)
adds nine assistant-provisional q_0048 dev atoms. Refitting on dev changes entropy's
old-test F1 from 0.7794 to 0.7520; margin is unchanged. This is sensitivity of the
same old test, not a new headline or independent validation. Original 205-span results remain intact.

BizHallu is a span-level hallucination detection project for LLM-generated
business analysis. It asks whether generated retail analytics claims are
grounded in the underlying transaction evidence.

The project uses UCI Online Retail data, local `Qwen/Qwen3-0.6B` generations,
business-fact span labels, token alignment, and split-safe detector baselines.
It is designed as a business analytics and AI reliability portfolio artifact.

**Current presentation revision:** the cases, methods page, research brief,
career package and narrative separate correct product-amount copying from
incorrect ranking. [English interview deck v2](docs/assets/bizhallu_interview_v2.pptx)
contains ten editable slides and matching speaker notes. Its B1 chart is preserved;
a visible B2 note identifies the separate omission sensitivity on the same old test.
The [career package](docs/career_package.html) includes a 191-word short pitch and
a ten-part, 669-word walkthrough. Speaking times are planning budgets, not
measured owner performance. The earlier PPTX remains historical provenance.
The [business risk lens](docs/business_risk_lens.html) now reconciles positive,
negative and net transaction values by category, without treating negative value
as verified physical returns. The [historical case readout](docs/portfolio_demo.html)
preserves its seven selected span outcomes but uses the corrected relationship
interpretation and statistical references.

## My Role

I directed the project with AI-assisted implementation and review: data cleaning, deterministic
question generation, prompt construction, local Qwen generation, the
AI-assisted provisional annotation workflow, token alignment, detector
evaluation, public GitHub Pages packaging, and interview/research-facing
documentation. Fifteen selected demo spans received an additional assistant
review for presentation use; the project does not claim independent human
annotation. Owner calibration and independent review remain pending.

## How to Review This Project in 5 Minutes

1. Open [Demo v2](https://yuchi-wang02.github.io/bizhallu/portfolio_demo_v2.html)
   and inspect `q_0064` or `q_0069`.
2. Compare a complete ranked statement with its evidence row. In April, GBP
   4,173.18 matches the named product, but that product is seventh among the
   eight shown rows, not third. These are curated checks, not automatic extraction.
3. Expand the historical detector readouts. A low score on an early list marker
   is not confidence in the later completed product-rank-amount relationship.
4. Read [Methods and results](https://yuchi-wang02.github.io/bizhallu/detector_interpretation.html)
   for tied-score AP, simple references, paired uncertainty and provisional-label limits.
5. Read the [research brief](https://yuchi-wang02.github.io/bizhallu/research_one_pager.html)
   for three open methodological questions and a specific collaboration request.

<details>
<summary>Supporting materials and study history</summary>

- [Project homepage](https://yuchi-wang02.github.io/bizhallu/)
- [Earlier deck retained as historical provenance](https://yuchi-wang02.github.io/bizhallu/assets/bizhallu_ai_reliability_deck.pptx)
- [Confirmation capacity proof](https://yuchi-wang02.github.io/bizhallu/confirmation_context_feasibility.html)
- [Confirmation precision review](https://yuchi-wang02.github.io/bizhallu/confirmation_precision_review.html)
- [Confirmation manifest freeze](https://yuchi-wang02.github.io/bizhallu/confirmation_context_manifest.html)
- [Confirmation study design](https://yuchi-wang02.github.io/bizhallu/confirmation_set_v1_design.html)

</details>

## Reproducibility Levels

The public candidate has also passed an isolated local Git clone dry-run without
raw data, model traces or third-party Python packages: 25 validators, 109 tests
plus two optional skipped scikit-learn checks, and 23 Node tests. All 111 Python
tests pass in the original environment. This was Windows/Python 3.13, not a new
GitHub Ubuntu/Python 3.11 deployment or private-data reproduction.

**Publication verified, September 5:** commit `24c7f5a` subsequently passed
[GitHub Ubuntu/Python 3.11 CI](https://github.com/Yuchi-Wang02/bizhallu/actions/runs/33992015667)
and [Pages deployment](https://github.com/Yuchi-Wang02/bizhallu/actions/runs/33992015366).
Eight primary/supporting HTML pages and both deck assets returned HTTP 200 and
matched the committed content. This verifies publication, not browser rendering,
private-data reproduction, independent annotation or owner presentation mastery.

**Business-definition amendment (September 4, 2026).** Stage A preserves the
historical gold and detector metrics. Its [metric contract](configs/business_metric_contract_v1_1.json)
separates sign-based transaction value, merchandise scope and cancellation flags.
The [100-question sensitivity table](reports/bizhallu_historical_metric_sensitivity.csv)
describes changes to business answers, not new model performance. The
[v1.1 amendment](reports/bizhallu_metric_amendment_v1_1_report.json) revalidates
96 questions on the same 48 contexts without new generations. Original v1
manifests remain provenance; `active_business_definition` in the study protocol
identifies the active v1.1 inputs. Physical returns are not separately identifiable.

Stage A public checks: `python -m unittest discover -s tests -v` and
`python src/validate_metric_amendment.py`. Local source replay additionally uses
`python src/validate_metric_amendment.py --require-local --output reports/bizhallu_metric_amendment_v1_1_local_validation.json`.
That local check requires excluded source tables and both private manifests;
it is not performed by public CI.

Stage B1 calculations can be replayed from committed lightweight scores with
`python src/validate_retrospective_statistics.py` (standard library, including
15,000 paired cluster draws). Saved-trace verification additionally uses
`python src/validate_retrospective_statistics.py --require-local --output reports/bizhallu_statistics_v2_local_validation.json`.
The [analysis recipe](configs/retrospective_statistics_v2.json) and
[metric table](results/full100_statistics_v2_metrics.csv) retain full available
precision and do not change the provisional labels. The raw-logit traces are
teacher-forced scores after generation, not sampling-distribution probabilities.
B2 uses a [separate nine-atom supplement](data/annotations/span_annotations_q0048_b2_assistant_v1.jsonl)
and [120-row sensitivity table](results/q0048_b2_sensitivity_metrics.csv), preserving B1.
Run `python src/q0048_dev_sensitivity.py validate` for public calculation replay;
add `--require-local` to verify q_0048 alignment and scores against excluded traces.
The augmented 214-span package is retrospective and assistant-provisional, not a
replacement for the original 205-span package or completed owner calibration.

**Relation calibration, not completed annotation:** a five-case local review
packet now separates neutral fact spans, formatting, source-row fidelity and
full business relations. It hides old labels, scores, gold and split metadata;
prior exposure remains a limitation. See the [protocol](configs/relation_annotation_v2.json)
and [workbench notes](app/README.md). The packet is Git-ignored, starts with zero
reviews, and does not change historical metrics. Public CI validates the protocol
and form logic, not private reviews or independent human agreement.
Owner review is currently deferred at the owner's request, not completed or
replaced with assistant judgments. English evidence-backed explanations can be
prepared meanwhile; independent review and owner mastery remain unverified.
Single-case checks leave the remaining drafts incomplete. The adopted semester
milestones and optional owner-session procedure are in the workbench notes.

- Public review: GitHub Pages, README, reports, summaries, and committed
  lightweight validation artifacts.
- Clean-clone validation: committed public pages and summaries can be checked
  with the standard-library validators used by GitHub Actions.
- Local artifact rebuild: public pages can be regenerated when the excluded
  Qwen outputs, token traces, and experiment reports are available locally.
- Full rerun: Qwen generation requires the raw UCI Online Retail file, local
  model cache, and non-committed token traces.

## Best Use Cases

| Reader | Start with |
| --- | --- |
| Recruiter | [Demo v2](https://yuchi-wang02.github.io/bizhallu/portfolio_demo_v2.html) |
| Professor or research advisor | [Research one-pager](https://yuchi-wang02.github.io/bizhallu/research_one_pager.html) and [methodology audit](https://yuchi-wang02.github.io/bizhallu/methodology_hardening.html) |
| Technical interviewer | [Detector interpretation](https://yuchi-wang02.github.io/bizhallu/detector_interpretation.html) and [methodology audit](https://yuchi-wang02.github.io/bizhallu/methodology_hardening.html) |
| Business interviewer | [Business risk lens](https://yuchi-wang02.github.io/bizhallu/business_risk_lens.html) |

## Why It Matters

Business users do not only need fluent analysis. They need to know whether a
generated claim is supported by the data. BizHallu turns that into an auditable
workflow:

```text
transaction evidence -> deterministic question -> LLM answer -> fact spans -> detector scores -> public demo
```

The evaluation unit is a business fact span, not a whole response. A span can be
a product, country, month, rank, amount, percentage, comparison direction, or
business conclusion.

## Public Artifacts

| Artifact | Link |
| --- | --- |
| GitHub Pages entry | <https://yuchi-wang02.github.io/bizhallu/> |
| Interactive demo v2 | <https://yuchi-wang02.github.io/bizhallu/portfolio_demo_v2.html> |
| Interactive case demo | <https://yuchi-wang02.github.io/bizhallu/portfolio_demo.html> |
| Career package | <https://yuchi-wang02.github.io/bizhallu/career_package.html> |
| Business risk lens | <https://yuchi-wang02.github.io/bizhallu/business_risk_lens.html> |
| Research one-pager | <https://yuchi-wang02.github.io/bizhallu/research_one_pager.html> |
| Methodology Hardening v1 | <https://yuchi-wang02.github.io/bizhallu/methodology_hardening.html> |
| Confirmation precision review | <https://yuchi-wang02.github.io/bizhallu/confirmation_precision_review.html> |
| Confirmation context manifest | <https://yuchi-wang02.github.io/bizhallu/confirmation_context_manifest.html> |
| Confirmation Set v1 design | <https://yuchi-wang02.github.io/bizhallu/confirmation_set_v1_design.html> |
| Claim-evidence review schema v0 | <https://yuchi-wang02.github.io/bizhallu/evidence_verifier_pilot.html> |
| Portfolio narrative | <https://yuchi-wang02.github.io/bizhallu/portfolio_narrative.html> |
| Detector interpretation | <https://yuchi-wang02.github.io/bizhallu/detector_interpretation.html> |
| English interview deck v2 | [Ten-slide walkthrough](docs/assets/bizhallu_interview_v2.pptx) |

The main demo cases are `q_0064` and `q_0069`. They show Qwen3-0.6B producing
plausible retail analysis while binding real transaction values to the wrong
rank or product.

## Key Results

| Item | Value |
| --- | ---: |
| Deterministic business questions | 100 |
| Question types | 7 |
| Local Qwen3-0.6B generations | 100 |
| High-priority dev/test answers in provisional annotation set | 35 of 36 |
| AI-assisted provisional business-fact span labels | 205 |
| Selected spans with additional assistant presentation review | 15 |
| Test spans scored | 103 |
| Exploratory maximum test AUPRC across candidate signals | 0.835 |
| Exploratory maximum test F1 across candidate signals | 0.779 |
| GitHub Pages validation | `num_failures=0` |

The AUPRC maximum comes from `one_minus_min_top2_margin`; the F1 maximum comes
from `mean_token_entropy`. The strongest observed energy-family F1 is 0.773
from `mean_spilled_probability_mass_after_top2`. Because these winners were
identified by comparing test results, the numbers summarize this experiment
and should not be treated as a fresh confirmation-set estimate.

The 35 evaluated answers were selected through a high-priority queue that used
generated-answer auto-status. The split was assigned periodically within each
question type rather than grouped by month or evidence payload. Methodology
Hardening v1 therefore classifies these results as exploratory and conditional
on an error-enriched subset; it also specifies a fresh, context-separated
confirmation protocol.

## What This Shows

- Business analytics framing: the questions and gold answers come from
  transaction evidence, not synthetic facts.
- AI evaluation discipline: generated answers are represented with exact span
  offsets, token alignment, and dev-selected thresholds; public wording keeps
  the provisional label and exploratory model-selection limits visible.
- Practical limitation: token signals can miss provisional wrong-relation labels.
  An early list marker does not measure confidence in the later full relationship.
- Research extension: Claim-Evidence Review Schema v0 organizes 15 Demo v2
  spans as claim-evidence rows. Its statuses are inherited from the selected
  presentation labels, so it is a protocol scaffold rather than an independent
  verifier result.
- Portfolio relevance: the final pages and deck explain the work as AI
  reliability for business analysis, not as a generic sales dashboard.
- Career relevance: the career package and business risk lens connect the work
  to business, data and operations analyst interviews across accounting, supply-management,
  and evidence-grounded decision-support use cases.

## Repository Map

| Path | Purpose | GitHub status |
| --- | --- | --- |
| `docs/` | GitHub Pages bundle, public pages, public assets; current public source of truth | upload |
| `reports/` | Experiment-native HTML reports, summaries, deck | upload |
| `results/` | Detector scores, split metrics, error reviews | upload lightweight files |
| `src/` | Data, generation, annotation, validation, packaging scripts | upload |
| `configs/` | Question and detector run configurations | upload |
| `data/annotations/` | Guidelines and span labels | upload |
| `data/processed/` | Gold-question metadata and small summaries | upload selected lightweight files |
| `outputs/` | README only; large model outputs stay local | do not upload generated outputs |
| `models/` | README only; model weights stay outside git | do not upload weights |

## Detailed Docs

| Document | Purpose |
| --- | --- |
| [`docs/project_blueprint.md`](docs/project_blueprint.md) | Project architecture and workflow overview |
| [`docs/current_state_audit.md`](docs/current_state_audit.md) | Detailed state audit of completed work |
| [`docs/evidence_aware_verifier_design.md`](docs/evidence_aware_verifier_design.md) | Next-stage verifier design and research comparison plan |
| [`configs/methodology_protocol_v1.json`](configs/methodology_protocol_v1.json) | Machine-readable boundary between the current exploratory study and a future confirmation study |
| [`configs/confirmation_set_v1_protocol.json`](configs/confirmation_set_v1_protocol.json) | Prospective, context-separated confirmation design with outcome-blind sampling and seven execution gates |
| [`configs/confirmation_context_feasibility_v1.json`](configs/confirmation_context_feasibility_v1.json) | Frozen complete-week grain, family eligibility rules, revised 48-context capacity target, and public privacy boundary |
| [`configs/confirmation_context_manifest_v1.json`](configs/confirmation_context_manifest_v1.json) | Frozen outcome-blind assignment algorithm, 6/15/27 split policy, reserve rule, and public/private manifest boundary |
| [`configs/confirmation_question_design_v1.json`](configs/confirmation_question_design_v1.json) | Frozen six-template question design, gold calculation rules, entity-selection policy, evidence ordering, and privacy boundary |
| [`configs/confirmation_precision_review_v1.json`](configs/confirmation_precision_review_v1.json) | Frozen synthetic cluster-precision scenarios and strong-comparison decision rules |
| [`configs/confirmation_precision_scope_amendment_v1.json`](configs/confirmation_precision_scope_amendment_v1.json) | Estimation-focused claim amendment after no candidate passed every frozen strong-comparison rule |
| [`reports/bizhallu_confirmation_dataset_source_audit.html`](reports/bizhallu_confirmation_dataset_source_audit.html) | Candidate-source decision, verified acquisition/structure evidence, and remaining source gates |
| [`reports/bizhallu_confirmation_dataset_quality.html`](reports/bizhallu_confirmation_dataset_quality.html) | Strict-window completeness, grain, cancellation, revenue reconciliation, monthly coverage, and controls |
| [`reports/bizhallu_confirmation_dataset_overlap.html`](reports/bizhallu_confirmation_dataset_overlap.html) | Aggregate-only canonical, date-blind, lineage-calibration, business-pattern, and entity-overlap proof |
| [`reports/bizhallu_confirmation_context_feasibility.html`](reports/bizhallu_confirmation_context_feasibility.html) | Aggregate-only proof that 48 unique complete-week context slots are feasible without selecting contexts or viewing model outcomes |
| [`reports/bizhallu_confirmation_precision_review.html`](reports/bizhallu_confirmation_precision_review.html) | Outcome-blind simulation review, failed strong-comparison gate, and frozen estimation-only scope |
| [`reports/bizhallu_confirmation_context_manifest.html`](reports/bizhallu_confirmation_context_manifest.html) | Aggregate public commitment to the frozen private 48-context inventory and seeded 6/15/27 split |
| [`reports/bizhallu_confirmation_question_design_report.json`](reports/bizhallu_confirmation_question_design_report.json) | Aggregate public commitment to 96 private deterministic questions, gold answers, and unique evidence payload fingerprints |
| [`reports/bizhallu_confirmation_set_v1_design.html`](reports/bizhallu_confirmation_set_v1_design.html) | Human-readable Confirmation Set v1 design; no new experiment result |
| [`docs/github_upload_checklist.md`](docs/github_upload_checklist.md) | Public upload checklist and claim guardrails |
| [`docs/github_upload_dry_run.md`](docs/github_upload_dry_run.md) | Current GitHub safety and file-inclusion review |

## What Stays Local

The repository intentionally excludes:

- raw Online Retail files under `data/raw/`
- large cleaned line-level transaction tables
- the detailed Confirmation Set v1 context manifest containing selected periods,
  scope entities, context IDs, and context evidence-pool hashes
- the detailed Confirmation Set v1 question manifest containing question IDs,
  question text, gold answers, selected entities, and evidence rows
- full Qwen generation JSONL files and token traces under `outputs/`
- Hugging Face cache and model weights
- external baseline repositories downloaded for local reference
- local logs and temporary presentation workspaces

This keeps the public repo small while preserving enough code, configuration,
validated reports, and sample artifacts to understand and reproduce the project.

## Validate Committed Public Artifacts

```powershell
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
python src\validate_confirmation_dataset_overlap.py
python src\validate_confirmation_context_feasibility.py
python src\validate_confirmation_precision_review.py
python src\validate_confirmation_context_manifest.py
python src\validate_confirmation_question_design.py
python src\validate_confirmation_dataset_source_audit.py
python src\validate_confirmation_set_v1_design.py
```

Expected state:

- `docs/github_pages_validation.json`: `ready_for_github_pages=true`
- `reports/public_path_hygiene_validation.json`: `num_failures=0`
- `reports/bizhallu_evidence_verifier_pilot_validation.json`: `num_failures=0`
- `reports/bizhallu_methodology_hardening_validation.json`: `num_failures=0`
- `reports/bizhallu_confirmation_dataset_quality_validation.json`: `num_failures=0`
- `reports/bizhallu_confirmation_dataset_overlap_validation.json`: `num_failures=0`
- `reports/bizhallu_confirmation_context_feasibility_validation.json`: `num_failures=0`
- `reports/bizhallu_confirmation_precision_review_validation.json`: `num_failures=0`
- `reports/bizhallu_confirmation_context_manifest_validation.json`: `num_failures=0`
- `reports/bizhallu_confirmation_question_design_validation.json`: `num_failures=0`
- `reports/bizhallu_confirmation_dataset_source_audit_validation.json`: `num_failures=0`
- `reports/bizhallu_confirmation_set_v1_design_validation.json`: `num_failures=0`
- all validation files report `num_failures=0`

The GitHub Actions workflow at `.github/workflows/validate.yml` runs only
lightweight public-artifact checks with the Python standard library. The
`requirements.txt` file remains focused on the full local experiment pipeline,
including Qwen and model-trace dependencies.

## Rebuild From Local Experiment Artifacts

The following commands require excluded local artifacts such as full Qwen
generations, token traces, and intermediate validation reports. They are not a
clean-clone reproduction path.

```powershell
python src\build_evidence_verifier_pilot.py
python src\build_methodology_hardening_report.py
python src\profile_confirmation_dataset_quality.py
python src\build_confirmation_dataset_quality_report.py
python src\profile_confirmation_dataset_overlap.py
python src\build_confirmation_dataset_overlap_report.py
python src\profile_confirmation_context_feasibility.py
python src\build_confirmation_context_feasibility_report.py
python src\build_confirmation_precision_review_report.py
python src\freeze_confirmation_context_manifest.py
python src\build_confirmation_context_manifest_report.py
python src\freeze_confirmation_question_design.py
python src\build_confirmation_dataset_source_audit.py
python src\build_confirmation_set_v1_design.py
python src\build_research_one_pager.py
python src\build_github_pages_bundle.py
python src\sanitize_public_json_paths.py
python src\build_full100_preflight_report.py
```

## Scope

- The 205-span annotation set is AI-assisted and provisional. Fifteen selected
  presentation spans received an additional assistant review with
  `lock_basis=assistant_full_review`. No independent human annotation or
  inter-annotator agreement has been completed.
- Metrics should be interpreted at span level, not as whole-answer correctness.
- The current evaluation scores pre-identified business-fact spans; automatic
  claim extraction from new responses is outside the current scope.
- Thresholds are selected on dev spans, but the reported AUPRC/F1 headline
  signals were chosen after test comparison. Treat them as exploratory maxima,
  not confirmatory held-out model-selection estimates.
- The detector baselines are diagnostics, not production hallucination
  detection systems.
- Claim-Evidence Review Schema v0 derives statuses from existing presentation
  labels. It is not an independent verifier, production checker, or new
  benchmark result.
- Confirmation Set v1 is a prospective design, not a completed experiment. Its
  frozen post-review plan contains a 12-question protocol pilot, 30-question
  development split, and 54-question sealed confirmation split, for 96 total
  generations. The 502,938-row
  strict-window quality profile is complete with documented controls. Canonical
  eight-field and date-blind seven-field comparisons both found zero repeated
  current-source records. The frozen outcome-blind precision review found that
  none of the 15/21/24/27 confirmation-context candidates passed every strong-
  comparison rule; thresholds were not relaxed. The study scope is therefore
  estimation-focused and does not authorize detector-superiority claims. Fifty
  observed complete weeks support 48/48 period-to-family slots with minimum
  Hall slack 2. A Git-ignored private manifest now fixes 48 unique periods and
  the 6/15/27 split, with two periods retained as source reserve; the public
  report exposes only aggregate counts and a canonical SHA-256 commitment. A
  second Git-ignored manifest now freezes 96 deterministic questions and gold
  answers across six templates. All 96 full payload fingerprints and all 96
  normalized evidence-table content fingerprints are unique, with zero exact
  cross-split overlap. None of the normalized contents matches the 66 unique
  historical full100 evidence-table contents under the wrapper-independent
  comparison.
  Three of seven execution gates are complete. The next gate is limited to
  freezing model, tokenizer, prompt, decoding, detector-family, and metric
  configurations before protocol-pilot generation. No prompt, Qwen output,
  annotation, detector score, verifier score, or new confirmation metric has
  been created. This is same-retailer, same-lineage temporal separation, not
  external independence.

## License and Data

Project code is released under the MIT License. The raw dataset is not
committed. Online Retail is provided by the UCI Machine Learning Repository
under CC BY 4.0: Chen, D. (2015), DOI
<https://doi.org/10.24432/C5BW33>. The Qwen model and other external components
remain governed by their own licenses and model cards.
