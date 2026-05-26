# GitHub Upload Checklist

Use this checklist before making BizHallu public.

## 1. Public Positioning

Recommended repository description:

```text
Span-level hallucination detection for LLM-generated business analysis on Online Retail transaction data.
```

Recommended topics:

```text
llm-evaluation, hallucination-detection, business-analytics, ai-reliability, qwen, retail-analytics
```

Core claim:

```text
BizHallu evaluates whether generated business facts are grounded in transaction-level evidence.
```

Avoid claiming:

- a large human-labeled benchmark
- whole-answer correctness
- production-ready hallucination detection
- that Spilled Energy beat all simple baselines in this run

## 2. Files To Include

Include:

- `README.md`
- `requirements.txt`
- `.gitignore`
- `.gitattributes`
- `src/`
- `configs/`
- `docs/`
- `reports/`
- `results/`
- `site/`
- `data/annotations/README.md`
- `data/annotations/annotation_guidelines.md`
- `data/annotations/span_annotations_full100_draft.jsonl`
- `data/processed/business_questions_gold.jsonl`
- `docs/assets/bizhallu_ai_reliability_deck.pptx`
- `docs/assets/bizhallu_ai_reliability_deck_contact_sheet.png`
- `models/README.md`
- `outputs/README.md`

Include only if intentionally public:

- lightweight gold-question metadata in `data/processed/`
- small report-ready CSV files in `results/`

## 3. Files To Keep Local

Do not upload:

- `data/raw/`
- `C:\Users\yuchi\Downloads\p1\hf_cache`
- `C:\Users\yuchi\Downloads\p1\baselines`
- model weights
- full token traces such as `outputs/qwen_full100_token_traces.jsonl`
- generation JSONL files under `outputs/`
- local run logs under `outputs/`
- Python cache folders

The current `.gitignore` is set up to exclude the main large local artifacts.

## 4. Refresh Before Upload

Run:

```powershell
python src\build_github_pages_bundle.py
python src\validate_github_pages_bundle.py
python src\build_full100_preflight_report.py
```

Expected results:

- `docs/github_pages_validation.json`: `ready_for_github_pages=true`
- `results/full100_preflight_validation.json`: `current_stage=github_pages_ready`
- both validation files have `num_failures=0`

## 5. GitHub Pages Settings

After pushing to GitHub:

1. Open the repository settings.
2. Go to Pages.
3. Set source to deploy from branch.
4. Select the main branch.
5. Select `/docs` as the publishing folder.
6. Open the published URL and check:
   - landing page loads
   - `portfolio_demo.html` opens
   - `portfolio_narrative.html` opens
   - links to detector interpretation and label lock report work
   - the interview deck downloads from `assets/bizhallu_ai_reliability_deck.pptx`

## 6. README Front Page Check

The root README should quickly answer:

- what problem this solves
- why it matters for business analytics
- what data and model were used
- what the main metrics are
- how to open the public demo
- what claims are intentionally limited

## 7. Interview Talking Point

One-minute version:

```text
I built BizHallu to test whether LLM-generated retail analysis is grounded in the actual transaction evidence. The project creates deterministic business questions from Online Retail data, runs Qwen3-0.6B locally, labels hallucinated and correct business fact spans, aligns those spans to token-level traces, and evaluates simple and energy-style detector baselines. The strongest public result is a span-level AI reliability workflow for business analytics, not just a sales dashboard.
```
