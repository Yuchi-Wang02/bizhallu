# Reproducibility and evidence provenance

[Project overview](../README.md) ·
[Methods and results](https://yuchi-wang02.github.io/bizhallu/detector_interpretation.html) ·
[Detailed audit](current_state_audit.md)

Public artifact checks, saved-score replay and a complete model rerun establish
different things. None establishes independent human annotation or business
impact. Run commands below from the repository root.

## Choose the appropriate level

| Level | Available inputs | What it checks |
| --- | --- | --- |
| Public review | Committed pages, reports, labels and lightweight scores | Inspect claims, examples and provenance |
| Public calculation replay | A clone of this repository; Python standard library | Recompute selected statistics and validate public contracts |
| Local source replay | Excluded source tables, saved Qwen outputs and token traces | Compare public calculations with local evidence and saved traces |
| Full generation rerun | Raw UCI file, model/tokenizer cache and experiment dependencies | Recreate model outputs under the documented configuration |

The public validation workflow uses Python 3.11 on GitHub Actions. It does not
download raw data, run Qwen or evaluate the sealed confirmation set. Optional
scikit-learn cross-checks may be skipped when that package is absent. Node is
used for public interface logic tests. For the full experiment environment, see
[`requirements.txt`](../requirements.txt) and [Qwen setup](qwen_setup.md).

## Check committed artifacts

```powershell
python -m unittest discover -s tests -v
node --test tests/test_public_demo_ui.cjs
node --test tests/test_relation_review_ui.cjs
python src/validate_public_path_hygiene.py
python src/validate_github_pages_bundle.py
python src/validate_research_one_pager.py
python src/validate_retrospective_statistics.py
python src/q0048_dev_sensitivity.py validate
python src/validate_metric_amendment.py
```

The complete current check list is maintained in
[`.github/workflows/validate.yml`](../.github/workflows/validate.yml) and
[`AGENTS.md`](../AGENTS.md). Validators write reports; their expected result is
zero failures. That is a consistency check, not an independent replication of
the research. Interface tests do not replace visual/browser inspection.

The statistical replay uses committed scores, tied-score-aware average precision
and 15,000 paired cluster draws. B1 is retrospective. B2 adds a separate nine-atom
q_0048 dev supplement and refits dev policies; it keeps the original 205 labels
and 103 test spans unchanged. B2's 214-span augmented package is sensitivity
analysis on the same old test, not fresh confirmation.

## Replay against local sources

These commands need excluded local inputs. Each writes to a separate validation
artifact; do not run legacy evaluation commands over the original output prefixes.

```powershell
python src/validate_retrospective_statistics.py --require-local --output reports/bizhallu_statistics_v2_local_validation.json
python src/q0048_dev_sensitivity.py validate --require-local
python src/validate_metric_amendment.py --require-local --output reports/bizhallu_metric_amendment_v1_1_local_validation.json
python src/relation_review.py validate --require-local
python src/build_full100_preflight_report.py
```

Saved token traces are teacher-forced raw-logit scores after generation; they are
not the sampling distribution after decoding transformations. Same-step selected
energy gap is an NLL alias. Probability outside the top two choices is a
concentration control, not an independent replication of adjacent-step Spilled
Energy. The latter, TOHA and entity probes remain comparison candidates subject
to formula, compatibility and resource checks.

## Rebuild presentation artifacts

The source builders consume existing experiment and presentation reports. The
following is a focused research-page refresh when those inputs are available;
it does not prepare new data or run a model.

```powershell
python src/build_research_one_pager.py
python src/build_github_pages_bundle.py
python src/sanitize_public_json_paths.py
python src/validate_research_one_pager.py
python src/validate_github_pages_bundle.py
python src/validate_public_path_hygiene.py
```

For other pages, use their corresponding builders and the full workflow checks.
Do not run context/question freeze scripts as a routine presentation rebuild.
Frozen private manifests have versioned provenance and must not be silently
reselected or replaced. Slide authoring also requires the bundled authoring
runtime; it is separate from the standard-library slide source checks in CI.

The printable research brief uses `src/build_research_pdf.mjs`. After rebuilding
the research HTML, run it with `--runtime-root` pointing to the bundled dependency
runtime (which supplies Node and Playwright); it uses local Microsoft Edge in
headless mode. Rebuild the Pages bundle afterward. Check that the PDF remains one
A4 page, inspect its rendering and verify its links before publishing. This
optional authoring step does not run in public CI.

## Scientific scope preserved by the public package

- **Annotation:** 205 AI-assisted provisional spans from 35 of 36 dev/test answers;
  15 selected presentation spans have an additional assistant review with
  `lock_basis=assistant_full_review`. No independent human annotation or
  inter-annotator agreement has been completed. The five-case relation review
  packet is preparation, not completed annotation.
- **Selection:** the annotated answers were selected through an outcome-informed,
  error-enriched queue. The evaluation concerns pre-identified spans, not automatic
  claim extraction or whole-answer accuracy.
- **Dependence:** question splits are periodic within type. Dev/test share
  periods and exact evidence-row payloads. Only two overlapping-period components
  remain, too few for reliable cluster inference.
- **Model selection:** thresholds were selected on dev; headline signals were
  selected after test comparison. Historical maximum test AUPRC `0.835073` and
  F1 `0.779412` come from different signals. They are exploratory maxima.
- **References:** the fact-type prior is a composition control with possible
  correctness hints in supplied types, not an information-matched detector.
  The current review schema derives statuses from existing labels and is not
  an independently evaluated evidence-aware verifier.
- **Business scope:** the active
  [v1.1 metric contract](../configs/business_metric_contract_v1_1.json) separates
  transaction signs, merchandise-code scope and cancellation flags. Negative
  transaction value may include fees and adjustments; physical returns,
  audited financial-statement revenue, savings, profit and inventory optimization
  are not established.

## Prospective study: designed, not executed

The estimation-focused plan has 48 period-disjoint contexts and 96 questions,
split 6/15/27 contexts into protocol pilot, development and confirmation. Source,
context-manifest and question-design gates are complete; four execution gates
remain pending. This is not execution-ready. Confirmation remains sealed.

The strict prior-period Online Retail II window contains 502,938 rows. Canonical
eight-field and date-blind seven-field comparisons found zero repeated records
against the historical source. The new question evidence contents are distinct
across splits and from the 66 unique historical evidence-table contents. These
checks establish the documented separation, not external independence: both
sources share retailer lineage and business entities.

The frozen precision review found that none of the 15/21/24/27-context candidates
passed every strong-comparison rule. The amended scope is therefore estimation,
not detector superiority. The v1.1 business-definition amendment preserves the
48 contexts, splits and all 96 numeric/entity gold answers while versioning their
wording and metadata. Follow the active definition in the
[study protocol](../configs/confirmation_set_v1_protocol.json).

[Study design](https://yuchi-wang02.github.io/bizhallu/confirmation_set_v1_design.html) ·
[Methodology audit](https://yuchi-wang02.github.io/bizhallu/methodology_hardening.html) ·
[Evidence-verifier design](evidence_aware_verifier_design.md)

## Repository and data boundaries

`src/` holds builders and validators; `configs/` holds method contracts;
`data/annotations/` holds provisional labels; `results/` holds lightweight
scores; `reports/` holds experiment-native reports; `docs/` holds the Pages bundle.

Raw files, full line-level transaction tables, model weights/caches, full Qwen
outputs and traces, external baseline repositories, and private review/context/
question manifests stay excluded from Git. Public manifests expose only permitted
aggregate information and commitments. Never publish private periods, selected
entities, reviewer identities, evidence hashes or private question payloads.

Publication and browser acceptance receipts are in the
[current-state audit](current_state_audit.md). They apply to the named commits,
platforms and viewports; they do not establish physical-device, cross-browser,
native PowerPoint or independent-human acceptance.

Code is [MIT licensed](../LICENSE). [UCI Online Retail](https://doi.org/10.24432/C5BW33)
is CC BY 4.0; model and external component licenses remain separate.
