# BizHallu

[Live demo](https://yuchi-wang02.github.io/bizhallu/) |
[Demo v2](https://yuchi-wang02.github.io/bizhallu/portfolio_demo_v2.html) |
[Case demo](https://yuchi-wang02.github.io/bizhallu/portfolio_demo.html) |
[Career package](https://yuchi-wang02.github.io/bizhallu/career_package.html) |
[Research one-pager](https://yuchi-wang02.github.io/bizhallu/research_one_pager.html) |
[Evidence verifier pilot](https://yuchi-wang02.github.io/bizhallu/evidence_verifier_pilot.html) |
[Portfolio narrative](https://yuchi-wang02.github.io/bizhallu/portfolio_narrative.html) |
[Presentation deck](https://yuchi-wang02.github.io/bizhallu/assets/bizhallu_ai_reliability_deck.pptx)

## TL;DR

BizHallu is an AI reliability project for business analytics. It turns retail
transaction evidence into deterministic business questions, asks
`Qwen/Qwen3-0.6B` to generate analysis, labels supported versus hallucinated
business-fact spans, aligns those spans to token-level uncertainty traces, and
evaluates split-safe detector baselines.

Best held-out result: 0.835 AUPRC and 0.779 F1 across 103 held-out test spans.

BizHallu is a span-level hallucination detection project for LLM-generated
business analysis. It asks whether generated retail analytics claims are
grounded in the underlying transaction evidence.

The project uses UCI Online Retail data, local `Qwen/Qwen3-0.6B` generations,
business-fact span labels, token alignment, and split-safe detector baselines.
It is designed as a business analytics and AI reliability portfolio artifact.

![BizHallu deck preview](docs/assets/bizhallu_ai_reliability_deck_contact_sheet.png)

## My Role

I designed and implemented the full pipeline: data cleaning, deterministic
question generation, prompt construction, local Qwen generation, span review,
token alignment, detector evaluation, public GitHub Pages packaging, and
interview/research-facing documentation.

## How to Review This Project in 5 Minutes

1. Open [Demo v2](https://yuchi-wang02.github.io/bizhallu/portfolio_demo_v2.html)
   and inspect `q_0064` or `q_0069`.
2. Read the highlighted span labels: supported facts can sit next to
   hallucinated rank, product, or amount bindings.
3. Check the detector outcome column to see which internal uncertainty signals
   missed confident wrong business facts.
4. Open the [Career package](https://yuchi-wang02.github.io/bizhallu/career_package.html)
   for interview language.
5. Open the [Research one-pager](https://yuchi-wang02.github.io/bizhallu/research_one_pager.html)
   for professor or research-advisor framing.

## Reproducibility Levels

- Public review: GitHub Pages, README, reports, summaries, and committed
  lightweight validation artifacts.
- Local rebuild: public pages and validations can be rebuilt from committed
  reports plus local generated artifacts.
- Full rerun: Qwen generation requires the raw UCI Online Retail file, local
  model cache, and non-committed token traces.

## Best Use Cases

| Reader | Start with |
| --- | --- |
| Recruiter | [Demo v2](https://yuchi-wang02.github.io/bizhallu/portfolio_demo_v2.html) and [Career package](https://yuchi-wang02.github.io/bizhallu/career_package.html) |
| Professor or research advisor | [Research one-pager](https://yuchi-wang02.github.io/bizhallu/research_one_pager.html) and [evidence verifier pilot](https://yuchi-wang02.github.io/bizhallu/evidence_verifier_pilot.html) |
| Technical interviewer | [Detector interpretation](https://yuchi-wang02.github.io/bizhallu/detector_interpretation.html) and `AGENTS.md` guardrails |
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
| Evidence-aware verifier pilot | <https://yuchi-wang02.github.io/bizhallu/evidence_verifier_pilot.html> |
| Portfolio narrative | <https://yuchi-wang02.github.io/bizhallu/portfolio_narrative.html> |
| Detector interpretation | <https://yuchi-wang02.github.io/bizhallu/detector_interpretation.html> |
| Interview deck | <https://yuchi-wang02.github.io/bizhallu/assets/bizhallu_ai_reliability_deck.pptx> |

The main demo cases are `q_0064` and `q_0069`. They show Qwen3-0.6B producing
plausible retail analysis while binding real transaction values to the wrong
rank or product.

## Key Results

| Item | Value |
| --- | ---: |
| Deterministic business questions | 100 |
| Question types | 7 |
| Local Qwen3-0.6B generations | 100 |
| Held-out high-priority annotated questions | 35 |
| Aligned business-fact spans | 205 |
| Held-out test spans scored | 103 |
| Best held-out test AUPRC | 0.835 |
| Best held-out test F1 | 0.779 |
| GitHub Pages validation | `num_failures=0` |

Best held-out test AUPRC comes from `one_minus_min_top2_margin`. Best held-out
test F1 comes from `mean_token_entropy`. The strongest energy-family F1 is
0.773 from `mean_spilled_probability_mass_after_top2`.

## What This Shows

- Business analytics framing: the questions and gold answers come from
  transaction evidence, not synthetic facts.
- AI evaluation discipline: generated answers are reviewed at span level, with
  labels, offsets, token alignment, and split-safe metrics.
- Practical limitation: internal uncertainty is useful, but confident wrong
  business bindings can still be missed.
- Research extension: the evidence-aware verifier pilot reframes 15 Demo v2
  spans as claim-evidence rows, without changing the locked detector metrics.
- Portfolio relevance: the final pages and deck explain the work as AI
  reliability for business analysis, not as a generic sales dashboard.
- Career relevance: the career package and business risk lens connect the work
  to BA, DS, and AI Analyst interviews across accounting, supply-management,
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
| [`docs/github_upload_checklist.md`](docs/github_upload_checklist.md) | Public upload checklist and claim guardrails |
| [`docs/github_upload_dry_run.md`](docs/github_upload_dry_run.md) | Current GitHub safety and file-inclusion review |

## What Stays Local

The repository intentionally excludes:

- raw Online Retail files under `data/raw/`
- large cleaned line-level transaction tables
- full Qwen generation JSONL files and token traces under `outputs/`
- Hugging Face cache and model weights
- external baseline repositories downloaded for local reference
- local logs and temporary presentation workspaces

This keeps the public repo small while preserving enough code, configuration,
validated reports, and sample artifacts to understand and reproduce the project.

## Reproduce Public Pages

```powershell
python src\build_evidence_verifier_pilot.py
python src\build_research_one_pager.py
python src\build_github_pages_bundle.py
python src\sanitize_public_json_paths.py
python src\validate_public_path_hygiene.py
python src\validate_github_pages_bundle.py
python src\validate_portfolio_demo_v2.py
python src\validate_career_package.py
python src\validate_business_risk_lens.py
python src\validate_research_one_pager.py
python src\validate_evidence_verifier_pilot.py
python src\build_full100_preflight_report.py
```

Expected state:

- `docs/github_pages_validation.json`: `ready_for_github_pages=true`
- `reports/public_path_hygiene_validation.json`: `num_failures=0`
- `reports/bizhallu_evidence_verifier_pilot_validation.json`: `num_failures=0`
- `results/full100_preflight_validation.json`: `current_stage=github_pages_ready`
- all validation files report `num_failures=0`

The GitHub Actions workflow at `.github/workflows/validate.yml` runs only
lightweight public-artifact checks with the Python standard library. The
`requirements.txt` file remains focused on the full local experiment pipeline,
including Qwen and model-trace dependencies.

## Scope

- Labels are locked for presentation with `lock_basis=assistant_full_review`;
  this is not a large independently human-labeled benchmark.
- Metrics should be interpreted at span level, not as whole-answer correctness.
- The detector baselines are diagnostics, not production hallucination
  detection systems.
- The evidence-aware verifier pilot is a small research prototype over Demo v2
  locked spans, not a production checker or new benchmark result.

## License and Data

Project code is released under the MIT License. The raw UCI Online Retail
dataset is not committed; the project keeps derived lightweight artifacts and
documents how to rebuild the public pages from local validated outputs.
