# BizHallu Career Package

## Positioning

I build business analytics systems that do not just generate answers, but audit whether the answer is grounded in the underlying transaction evidence.

## Project Brief

- Problem: business users increasingly ask LLMs to summarize revenue, rankings, returns, and product performance, but fluent answers can still bind transaction evidence incorrectly.
- Approach: BizHallu turns UCI Online Retail records into deterministic business questions, runs local Qwen3-0.6B generations, builds AI-assisted provisional business-fact span labels, aligns pre-identified spans to token traces, and evaluates internal-state detector signals.
- Result: across 103 test spans, the exploratory maximum AUPRC was 0.835 and the exploratory maximum F1 was 0.779; the maxima come from different signals selected after test comparison.
- Business value: the project demonstrates an auditable workflow for checking whether generated analytics claims are grounded in evidence before a stakeholder relies on them.
- Limitation: the 205 labels are AI-assisted and provisional, only 15 selected presentation spans received additional assistant review, claim extraction is not automated, and the detector results are not production estimates.

## Resume Bullets

- Built BizHallu, an AI reliability project for business analytics that evaluates whether LLM-generated retail claims are grounded in transaction evidence.
- Generated 100 deterministic Online Retail questions across 7 business-analysis types and ran local Qwen3-0.6B inference with saved token-level traces.
- Built an AI-assisted provisional annotation workflow for 205 business-fact spans across 35 dev/test answers and aligned every pre-identified span to uncertainty and energy-style detector scores.
- Selected detector thresholds on dev spans and compared candidate signals on 103 test spans; exploratory maxima reached 0.835 AUPRC and 0.779 F1 from different signals.
- Published a GitHub Pages demo, methods page, and interview deck that connect AI evaluation with revenue reconciliation, returns, and product-concentration risk.

## LinkedIn / GitHub Blurb

I built BizHallu to study hallucinations in business analytics as concrete evidence-grounding failures: wrong products, ranks, amounts, countries, and conclusions. The project uses Online Retail transactions, local Qwen3-0.6B generations, AI-assisted provisional span labels, token alignment, and internal-state detector signals to show why business AI systems need auditable validation, not just fluent answers.

Short profile line: Business analytics + AI reliability. I build evidence-grounded evaluation workflows for LLM-generated analysis, with a focus on finance, supply management, and decision-support use cases.

## 60-Second Pitch

- BizHallu is my business analytics AI reliability project.
- I used UCI Online Retail transactions to create deterministic questions with known gold answers, then asked Qwen3-0.6B to write concise business analysis.
- Instead of judging whole answers, I built an AI-assisted provisional label set for exact spans such as product names, ranks, countries, months, amounts, and percentages.
- The strongest result is that internal uncertainty has useful signal, but it still misses confident evidence-binding errors, especially top-3 product rank and amount mistakes.
- That makes the project relevant to BA, DS, and AI analyst roles because it connects data cleaning, experiment design, metrics, and business-risk interpretation.

## 5-Minute Interview Flow

- Start with the business problem: a stakeholder may ask an LLM which product, country, or month performed best, and a fluent answer can still be wrong.
- Explain the data pipeline: Online Retail records are cleaned into deterministic evidence tables and gold answers, so each question can be audited.
- Explain the model run: Qwen3-0.6B is small enough to run locally, which makes the project reproducible and transparent.
- Explain the label unit: the evaluation unit is a pre-identified business fact span, not a whole answer; automatic claim extraction is not part of the current pipeline.
- Explain the metrics honestly: thresholds are selected on dev spans, but the headline AUPRC/F1 signals were chosen after test comparison, so the values are exploratory maxima rather than confirmatory held-out estimates.
- Show q_0064 or q_0069: the model uses plausible values but binds them to the wrong rank or product, which is exactly the business-risk failure mode.
- Close with the next step: add evidence-aware claim verification to complement internal uncertainty signals.

## Interview FAQ

- Why is this relevant to business analytics instead of only NLP research? The errors are business facts: wrong revenue, country, product, month, rank, percentage, or conclusion. Those are exactly the claims a business user might put into a decision memo.
- Why span-level labels? Whole-answer labels hide mixed cases. A generated answer can correctly state rank 1 and rank 2 while hallucinating rank 3, so the useful unit is the exact fact span.
- Why Qwen3-0.6B? It is small enough to run locally on available hardware while still producing realistic fluent errors. That makes the experiment reproducible and portfolio-friendly.
- Why not claim production-ready hallucination detection? The current detector baselines are diagnostic. They show signal and limitations, but the dataset and label scope are not large enough for a production claim.
- Why did simple uncertainty beat the energy-family result? In this run, the strongest energy-family F1 came from a probability-mass control, while simple entropy and top-2 margin were slightly stronger overall. That is a result, not a problem.
- What is the strongest technical decision? Thresholds are selected on dev spans and reused on test spans. However, the headline signal for each metric was chosen after comparing test results, so I present 0.835 and 0.779 as exploratory maxima and would use a fresh confirmation set for a confirmatory claim.
- What is the strongest business insight? LLMs can copy real-looking values from a table while assigning them to the wrong product or rank. Business AI needs evidence checks, not only answer fluency checks.
- How does your accounting and supply-management background show up? The project focuses on net revenue, returns, product performance, country exposure, and rank-based reporting. These connect to accounting reconciliation and supply-management thinking about product concentration, while avoiding inventory, cost, or vendor claims that the dataset cannot support.
- What would you build next? First, define an independent claim-extraction and claim-evidence decision protocol. Then compare that evidence-aware verifier with entropy, top-2 margin, energy-style signals, and selected literature baselines on a fresh evaluation design.
- How should the label scope be described? Describe 205 AI-assisted provisional span labels and 15 selected presentation spans with additional assistant review. There is no independent human annotation or inter-annotator agreement.

## Public Claim Guardrails

- Say span-level business fact evaluation, not whole-answer correctness.
- Say 205 AI-assisted provisional labels and 15 additionally assistant-reviewed presentation spans, not a human-labeled benchmark.
- Say diagnostic detector baselines, not production-ready detection.
- Say simple uncertainty is strongest in this run; do not imply energy baselines won overall.
- Say the 0.835 AUPRC and 0.779 F1 values are exploratory test maxima from different signals.

## Public Links

- [Live demo](https://yuchi-wang02.github.io/bizhallu/)
- [Interactive case demo](https://yuchi-wang02.github.io/bizhallu/portfolio_demo.html)
- [Detector interpretation](https://yuchi-wang02.github.io/bizhallu/detector_interpretation.html)
- [Interview deck](https://yuchi-wang02.github.io/bizhallu/assets/bizhallu_ai_reliability_deck.pptx)
- [JHU Carey BAAI](https://carey.jhu.edu/programs/master-science/business-analytics-artificial-intelligence/full-time)
- [BLS Data Scientists](https://www.bls.gov/ooh/math/data-scientists.htm)
- [O*NET Data Scientists](https://www.onetonline.org/link/summary/15-2051.00)
- [O*NET Business Intelligence Analysts](https://www.onetonline.org/link/summary/15-2051.01)
