# BizHallu Agent Instructions

## Project Positioning

BizHallu is a portfolio-scale AI reliability project for business analytics. It audits whether LLM-generated retail analysis is grounded in transaction evidence at the level of individual business-fact spans.

Use this public positioning:

> BizHallu audits whether LLM-generated business analysis is grounded in transaction evidence, at the level of individual business-fact spans.

## Non-Negotiable Claim Guardrails

- Do not claim this is a production-ready hallucination detector.
- Do not claim this is a large independent human-labeled benchmark.
- Do not claim whole-answer correctness; metrics are span-level.
- Use `assistant-reviewed presentation labels` or `presentation-locked labels`.
- Preserve `lock_basis=assistant_full_review` unless the label package is explicitly reworked.
- Preserve published metrics exactly unless they are recomputed from source artifacts:
  - best held-out test AUPRC: `0.835073`
  - best held-out test F1: `0.779412`
  - aligned business-fact spans: `205`
  - held-out test spans: `103`

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
```

When local full100 artifacts are available, also run:

```powershell
python src\build_full100_preflight_report.py
```

## Preferred Next Technical Direction

The next research extension should keep two tracks open. A small evidence-aware verifier pilot now exists over Demo v2 locked spans because it is closest to business analytics use cases, but internal-state and literature-grounded hallucination baselines remain comparison candidates rather than rejected paths.

Preferred framing:

> Internal uncertainty signals can rank some risky spans, but confident wrong evidence bindings remain difficult. BizHallu's next research step is to compare internal-state signals with evidence-aware verification for business-fact grounding.

Research comparison tracks:

- Internal uncertainty: entropy, top-2 margin, and energy-style probability-mass signals already used in the project.
- Literature-grounded baselines: Semantic Entropy, TOHA, and entity-level hallucination detection as future comparison candidates.
- Evidence-aware verification: claim-evidence consistency checks against structured evidence rows and deterministic gold answers.

Do not expand the verifier beyond Demo v2 or report new verifier metrics until the comparison protocol is fixed and validated.
