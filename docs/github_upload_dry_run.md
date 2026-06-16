# GitHub Upload Dry Run

Date checked: 2026-05-25

Workspace:

```text
C:\Users\yuchi\Downloads\p1\bizhallu
```

Remote:

```text
https://github.com/Yuchi-Wang02/bizhallu.git
```

## Result

The repository is safe for public GitHub upload and is already pushed to
`main`. GitHub Pages is configured around the `/docs` bundle.

Current public stage:

```text
github_pages_ready
```

Validation status:

- `docs/github_pages_validation.json`: `ready_for_github_pages=true`, `num_failures=0`
- `results/full100_preflight_validation.json`: `ready_for_current_stage=true`, `num_failures=0`

## Include In GitHub

Keep these tracked:

- `README.md`, `LICENSE`, `.gitignore`, `.gitattributes`
- `src/`
- `configs/`
- `docs/`
- `reports/`
- `results/`
- `site/`
- `data/annotations/`
- selected lightweight files under `data/processed/`
- `models/README.md`
- `outputs/README.md`

Current public assets include:

- `docs/assets/bizhallu_ai_reliability_deck.pptx`
- `docs/assets/bizhallu_ai_reliability_deck_contact_sheet.png`
- `docs/assets/full100_draft_detector_error_review_examples.csv`
- `docs/assets/bizhallu_demo_v2_data.json`

## Keep Local

Do not upload:

- `data/raw/`
- full line-level cleaned transaction tables under `data/processed/`
- `outputs/*.jsonl`, `outputs/*.csv`, `outputs/*.json`, `outputs/*.log`
- full Qwen token traces
- Hugging Face cache under `C:\Users\yuchi\Downloads\p1\hf_cache`
- downloaded external baseline repositories
- model weights
- temporary presentation workspaces under `outputs/*/`

The current `.gitignore` protects these categories.

## Current Size Check

The repository has no oversized tracked artifacts. The largest tracked files are
the slide contact sheet, the gold-question JSONL, annotation JSONL, and small
report-ready CSV files. Raw data and token traces remain ignored.

Run this before future pushes:

```powershell
git status --short --branch
git ls-files --others --exclude-standard
git ls-tree -r -l HEAD | Sort-Object {[int64]($_ -split '\s+')[3]} -Descending | Select-Object -First 25
```

Expected:

- no untracked raw data
- no files from `outputs/` except `outputs/README.md`
- no model weights or Hugging Face cache files

## Publish Check

After pushing:

```powershell
python src\build_github_pages_bundle.py
python src\validate_github_pages_bundle.py
python src\build_full100_preflight_report.py
```

Then check:

- <https://yuchi-wang02.github.io/bizhallu/>
- <https://yuchi-wang02.github.io/bizhallu/portfolio_demo_v2.html>
- <https://yuchi-wang02.github.io/bizhallu/portfolio_demo.html>
- <https://yuchi-wang02.github.io/bizhallu/career_package.html>
- <https://yuchi-wang02.github.io/bizhallu/business_risk_lens.html>
- <https://yuchi-wang02.github.io/bizhallu/assets/bizhallu_ai_reliability_deck.pptx>

## Public Claim Guardrails

Say:

- span-level business fact evaluation
- UCI Online Retail + local Qwen3-0.6B
- assistant-reviewed presentation labels
- internal uncertainty is useful but incomplete

Do not claim:

- large human-labeled benchmark
- whole-answer correctness
- production-ready hallucination detection
- that energy-family methods beat all simple baselines in this run
