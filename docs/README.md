# Documentation and public pages

Start at the [project homepage](https://yuchi-wang02.github.io/bizhallu/).
The current reader-facing route is **Cases → Methods → Research**.

| Read or present | Link |
| --- | --- |
| Inspect original answers and transaction evidence | [Interactive cases](https://yuchi-wang02.github.io/bizhallu/portfolio_demo_v2.html) |
| Understand the exploratory evaluation | [Methods and results](https://yuchi-wang02.github.io/bizhallu/detector_interpretation.html) |
| Discuss a small annotation pilot | [Research brief](https://yuchi-wang02.github.io/bizhallu/research_one_pager.html) |
| Present the evidence and its limits | [English interview deck v2](https://yuchi-wang02.github.io/bizhallu/assets/bizhallu_interview_v2.pptx) |
| Connect evidence checks to business decisions | [Business risk lens](https://yuchi-wang02.github.io/bizhallu/business_risk_lens.html) |
| Prepare a spoken explanation | [Career package](https://yuchi-wang02.github.io/bizhallu/career_package.html) |

## Reproduction and design

- [Reproducibility guide](reproducibility.md): public checks, local replay,
  dependencies and what stays excluded from Git.
- [Current-state audit](current_state_audit.md): detailed records, publication
  receipts and scoped acceptance checks.
- [Data definitions and cleaning](data_source_and_cleaning.md) and
  [experiment design](experiment_design.md): historical experiment provenance.
- [Evidence-aware verifier design](evidence_aware_verifier_design.md): comparison
  proposal; the current label-derived schema is not an independent detector.
- [Confirmation study design](https://yuchi-wang02.github.io/bizhallu/confirmation_set_v1_design.html):
  a prospective, estimation-focused plan, not an executed experiment.

Earlier case readouts, the original presentation deck, annotation reports and
confirmation preparation records remain linked from the homepage's historical
materials section. Their original labels and metrics are preserved. Current
Cases, Methods and Research pages explain the interpretation to use now.

## Maintaining the pages

`docs/` is the GitHub Pages source of truth. Generated pages are copied from
report artifacts; edit their builders in `src/`, then rebuild and validate the
bundle. Do not hand-edit a generated page or overwrite historical evaluation
artifacts to change presentation wording.

The [reproducibility guide](reproducibility.md) separates rendering public pages
from data preparation, model execution and frozen study design. The
[upload checklist](github_upload_checklist.md) records public-file boundaries.
