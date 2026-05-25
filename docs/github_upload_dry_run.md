# GitHub Upload Dry Run

Date checked: 2026-05-25

Workspace:

```text
C:\Users\yuchi\Downloads\p1\bizhallu
```

## Result

The local repository is ready for a first GitHub upload dry-run.

No files were staged, committed, or pushed during this check.

Current git state:

- local git repository initialized on branch `main`
- no remote configured
- staged file count: 0
- dry-run candidate file count: 202
- dry-run candidate total size: 2.659 MB
- largest dry-run candidate file: 284,933 bytes

## Important Fix Applied

The first dry-run found several `outputs/*.json` intermediate review files that
would have been included. These are not final public artifacts.

Fix:

```text
outputs/*.json
```

was added to `.gitignore`.

After the fix, `outputs/` contributes only:

```text
outputs/README.md
```

## Files That Would Be Included

Top-level dry-run candidate counts:

| Path | Count |
| --- | ---: |
| `.gitignore` | 1 |
| `README.md` | 1 |
| `app/` | 1 |
| `configs/` | 6 |
| `data/` | 10 |
| `docs/` | 18 |
| `models/` | 1 |
| `outputs/` | 1 |
| `reports/` | 25 |
| `requirements.txt` | 1 |
| `results/` | 64 |
| `site/` | 3 |
| `src/` | 70 |

Largest included candidates:

| File | Size |
| --- | ---: |
| `data/processed/business_questions_gold.jsonl` | 284,933 bytes |
| `data/annotations/span_annotations_full100_draft.jsonl` | 144,831 bytes |
| `results/full100_draft_detector_error_review.csv` | 103,069 bytes |
| `src/build_full100_annotation_draft.py` | 91,461 bytes |
| `results/pilot20_baseline_error_review.csv` | 78,719 bytes |

These are small enough for normal GitHub upload.

## Large Files Confirmed Ignored

The largest ignored files are the intended local-only artifacts:

| File | Size |
| --- | ---: |
| `data/processed/retail_lines_normalized.csv` | 84,540,169 bytes |
| `data/processed/retail_net_revenue_lines.csv` | 83,398,846 bytes |
| `data/processed/retail_merchandise_net_revenue_lines.csv` | 83,017,508 bytes |
| `data/processed/retail_sales_lines.csv` | 81,957,009 bytes |
| `data/processed/retail_merchandise_sales_lines.csv` | 81,652,732 bytes |
| `data/raw/online_retail_uci.zip` | 23,715,478 bytes |
| `data/raw/Online Retail.xlsx` | 23,715,344 bytes |
| `outputs/qwen_full100_token_traces.jsonl` | 7,394,830 bytes |

This confirms the current `.gitignore` protects the main upload risks:

- raw source dataset
- large cleaned line-level tables
- model generation JSONL files
- token traces
- local logs
- generated intermediate output tables

## Validation Status

Public bundle validation:

```text
docs/github_pages_validation.json
ready_for_github_pages=true
num_failures=0
```

Full preflight validation:

```text
results/full100_preflight_validation.json
current_stage=github_pages_ready
ready_for_current_stage=true
num_failures=0
```

## Next Commands When Ready

Review the dry-run output:

```powershell
git add -n .
```

If it still looks safe, stage and commit:

```powershell
git add .
git commit -m "Initial BizHallu portfolio release"
```

After you create an empty GitHub repository, add the remote:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/bizhallu.git
git push -u origin main
```

Then enable GitHub Pages from the `/docs` folder.
