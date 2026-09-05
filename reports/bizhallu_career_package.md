# BizHallu Career Package

## Project Brief

Business analytics with evidence checks for AI-generated analysis

## 90-Second Pitch

BizHallu is my business analytics project on checking AI-generated analysis against transaction evidence. My accounting and supply-management background makes me interested in the difference between a number that reconciles and a business conclusion that is actually supported.

One retail example makes that distinction concrete. Qwen lists WOODEN UNION JACK BUNTING third at 4,173.18 pounds. That product and amount match a source row, but the product is seventh among the eight rows shown to the model. The copying is correct; the ranking is wrong.

I directed the project with AI-assisted implementation and review. The pipeline contains 100 deterministic questions, local Qwen3-0.6B answers, and 205 provisional fact spans aligned to saved token traces. It checks whether uncertainty signals identify the labeled errors.

The original entropy F1 was 0.779, versus 0.744 for flagging every span. Adding one omitted dev answer changes entropy F1 to 0.752 on the same old test. That sensitivity and provisional labels rule out a stable superiority claim.

The business lesson is that source-row accuracy and relationship accuracy need separate checks. My next technical step is a small independent verifier, while keeping statistical evaluation and alternative uncertainty methods open for comparison.

## 5-Minute Interview Flow

### 1. BizHallu (20 seconds planned)

BizHallu studies a practical reporting problem: when an AI writes business analysis, can we trace its claims back to the evidence? I directed the project with AI-assisted implementation and review. My focus is on the accounting and operational decisions behind the numbers, alongside the model evaluation.

### 2. April product ranking (35 seconds planned)

Here is April 2011. The answer places WOODEN UNION JACK BUNTING third with revenue of 4,173.18 pounds. We can locate that exact product and amount in the source table. But six shown products have larger values. The correct third product is PAPER CHAIN KIT EMPIRE at 6,619.51 pounds. A check that only asks whether the amount appears in the table would miss the ranking error.

### 3. September: all three ranks differ (30 seconds planned)

The September answer repeats the pattern across all three listed products. Their stated ranks are one, two and three, while their ranks in the eight shown evidence rows are three, eight and two. Every product still matches its own amount. I use these cases to distinguish row fidelity from relationship correctness. They are selected historical examples, not evidence of a general error rate or an automatic verifier.

### 4. Business metric scope (30 seconds planned)

Metric definitions matter before we judge an answer. Negative transaction value is not the same as confirmed physical returns, because fee and adjustment records can contribute. Merchandise scope also depends on a documented stock-code rule. I preserve the historical calculation and provide a versioned definition amendment instead of silently rewriting old gold answers. Without cost, inventory or delivery data, I cannot claim profit analysis or inventory optimization.

### 5. The historical evaluation pipeline (35 seconds planned)

The pipeline turns retail transactions into deterministic questions and evidence tables, then captures local Qwen answers and token traces. B1 retains the original 205 provisional spans across 35 development and test answers. A separate B2 sensitivity adds nine assistant-provisional atoms for the omitted dev answer, without changing the 103 old test spans. Fifteen selected original spans received additional assistant review. None of this is independent human annotation or end-to-end claim extraction.

### 6. Historical B1 references and B2 sensitivity (45 seconds planned)

The chart preserves B1's original test results. Entropy F1 0.779; flag-every-span F1 0.744. Paired F1 difference +0.0355; exploratory 95% interval [-0.0356, 0.1047]. That interval is conditional on fixed thresholds and is not a B2 interval. B2 adds one previously omitted dev answer with nine provisional correct facts. Refitting on dev lowers entropy F1 to 0.752 on the same old test, with five fewer false alarms and six more missed errors. Margin is unchanged in this check. We report sensitivity, not a new winner or fresh confirmation.

### 7. Token timing and completed relationships (30 seconds planned)

One methodological correction is especially important. A list marker is generated before the product and amount that follow it. Low uncertainty on that marker cannot establish that the completed relationship was confidently wrong. The saved raw teacher-forced logits also differ from generation probabilities after sampling transformations. Some nominally different features are mathematical aliases: same-step energy gap is token negative log probability. These distinctions prevent an unfair comparison with a checker that sees the whole answer.

### 8. Scope of the evidence (25 seconds planned)

The results describe a limited retrospective study. The annotation queue depended on generated-answer status, development and test share contexts, and independent human agreement has not been measured. The six curated relationships clarify particular cases; they do not replace the 205 labels. No result here establishes performance on larger models, unseen periods, automatically extracted claims or production business reports.

### 9. Analyst contribution and business use (25 seconds planned)

For an analyst role, I would emphasize metric definitions, reproducible calculations and explaining what evidence supports. The potential use is reviewing generated reports before a business decision, not a claim that I have deployed a control or measured savings. AI assistance is part of the provenance. My next learning step is to explain and modify the analysis directly, supported by a small SQL and BI companion project.

### 10. Research questions and next steps (25 seconds planned)

For a professor, my concrete request is feedback on the unit of annotation and comparison design. I would begin with a top-three verifier that uses the question, answer, metric contract and evidence, without evaluation labels or gold answers as inputs. Semantic consistency, attention methods and a faithful adjacent-step energy implementation remain comparison options. The new confirmation study stays sealed until the prediction and evaluation process is ready.

## Resume Bullets

- Directed BizHallu with AI-assisted implementation, connecting retail metric definitions with evidence checks for generated business analysis.
- Developed a documented pipeline for 100 deterministic retail questions and local Qwen3-0.6B answers with saved token-level traces.
- Built an AI-assisted provisional review workflow for 205 pre-identified fact spans and separated source-row fidelity from product-ranking correctness.
- Audited retrospective detector evaluation with tied-score AP, simple reference policies and paired cluster uncertainty; retained historical maxima as exploratory.
- Created inspectable business cases and English methods materials for explaining model errors, metric scope and limitations to business and technical readers.

## Interview FAQ

### What is the main business finding?

A copied amount can match its product while the product has the wrong rank. April and September demonstrate that distinction within the shown evidence; they do not establish a population error rate.

### Why examine spans and also full relationships?

Atomic spans locate an error, but a rank belongs to a product, period and metric. A relationship record preserves those dependencies and avoids interpreting an early list marker as the completed claim.

### Why use Qwen3-0.6B?

It fit the local compute budget and exposed inspectable failures. Small size does not establish external validity. Reproduction also needs frozen model/tokenizer versions, decoding settings, data policies and saved artifacts.

### Did the detector beat simple references?

Entropy F1 0.779; flag-every-span F1 0.744. Paired F1 difference +0.0355; exploratory 95% interval [-0.0356, 0.1047]. B2 sensitivity adds 9 assistant-provisional q_0048 dev atoms. Dev-only refitting changes entropy F1 from 0.779 to 0.752 on the same 103 old test spans; top-2 margin is unchanged. Original B1 results remain intact. This is not fresh held-out evidence or independent review. These checks do not establish stable F1 superiority.

### Why is the fact-type prior not a new winning detector?

It uses supplied annotation categories, some with correctness hints. It diagnoses sample composition rather than providing an information-matched automatic prediction system.

### Is this an independently human-labeled benchmark?

No. There are 205 AI-assisted provisional labels and 15 selected presentation spans with additional assistant review. Independent human annotation and agreement remain uncompleted; owner review is currently deferred.

### What changed about the energy interpretation?

Same-step selected energy gap equals NLL. Probability outside the top two choices is a concentration control. A faithful adjacent-step Spilled Energy comparison still needs a separate formula and time-index audit.

### Does negative transaction value measure returns?

Positive and negative transaction values are sign-based accounting quantities. Negative value is not a verified measure of physical returns; fees and adjustments may be included. Merchandise scope uses a stock-code heuristic, and the historical product grain is stock code plus description. Without separate inventory, cost and delivery records, this project cannot prove inventory optimization, profit improvement or supply-chain optimization.

### What did you do, and where did AI assist?

I directed the project with AI-assisted implementation and review. The repository documents the calculation, annotation and evaluation work. These artifacts are not evidence that every step was coded unaided or that independent human review occurred.

### What is the next comparison?

A small independent top3 verifier versus internal uncertainty, with extraction coverage, abstention and information conditions reported. Semantic Entropy, TOHA and entity probes remain research candidates subject to compatibility and cost checks, not promised results.

## Public Claim Guardrails

- 205 provisional labels; 15 additionally assistant-reviewed spans; no independent human agreement.
- 0.835 AP and 0.779 F1 are exploratory maxima from different signals, not a single confirmatory detector result.
- B2 adds nine assistant-provisional dev atoms separately; the same 103 old test spans are reused, not newly held out.
- Complete relation correctness is different from source-row fidelity and early-token confidence.
- Negative transaction value is not verified physical returns; no inventory or profit optimization claim.
- The public review schema uses existing labels; it is not an independent verifier.
- Sharing a project does not establish owner mastery, a deployed business control or measured financial benefit.
