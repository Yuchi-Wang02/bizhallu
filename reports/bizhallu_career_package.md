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

## From Evidence to Explanation

Optional worked historical examples, not blind annotation or a scored assessment. No responses, identity or progress are collected. Disclose prior exposure in any later review.

### Reconcile the amount and its scope

December 2010 through December 9, 2011; December 2011 is partial. Historical eligible population: 534,129 lines, GBP.

Preserve existing valid-net flags: exclude normalized duplicate copies, missing/blank descriptions and nonpositive unit prices. Missing customer IDs are retained for aggregate analysis, not imputed. No anomaly is automatically removed.

Positive transaction value: 10,642,110.80. Signed negative transaction value: -893,979.73. Merchandise net value: 9,771,708.99.

Question: Calculate all-ledger net value and the net contribution outside merchandise. Does the negative value identify physical returns?

Worked solution:

10,642,110.80 + (-893,979.73) = GBP 9,748,131.07. The negative input is already signed: adding it reduces the total. Subtracting it would double-reverse its sign.

All-ledger net minus merchandise net = 9,748,131.07 - 9,771,708.99 = GBP -23,577.92. Merchandise net is higher because the other categories have a negative net contribution. These are different scopes, not competing estimates of the same population.

Physical returns are not separately identifiable. Negative entries may include fees and adjustments; merchandise is a stock-code heuristic. Net transaction value is not audited financial-statement revenue, profit or cash collected.

Follow-up: What extra records would be needed to link returns to original sales? Why is a partial December unsuitable for an unqualified full-month comparison?

Source: `reports/bizhallu_business_metric_audit_report.json`

### Check the complete ranked statement

April 2011, q_0064. Qwen's exact statement: 3. **WOODEN UNION JACK BUNTING** (rank 3) with a net revenue of GBP 4,173.18.

Use the original eight-row evidence table in the April case. Preserve its product, period, metric and GBP scope.

Question: Find the product and amount. Count shown rows with larger values. Which part is supported, which relationship is wrong, and what belongs at rank three?

Worked solution:

Source row 2 matches WOODEN UNION JACK BUNTING and GBP 4,173.18. Source-row fidelity is supported.

6 shown rows have larger values. With no ties here, rank = 1 + that count = 7, not 3. The third product is PAPER CHAIN KIT EMPIRE at GBP 6,619.51.

This is a curated check within the shown evidence, not automatic extraction or a population error rate. Low uncertainty on a list marker cannot establish confidence in its later completed product-rank-amount relationship.

Follow-up: If a real amount appeared beside a different product, would a number-only lookup be enough? If evidence were incomplete or values tied, what scope or ranking rule would be needed?

Source: `reports/bizhallu_demo_v2_data.json`

### Recompute F1 before interpreting it

Original B1: 103 pre-identified test spans with provisional labels. Positive means a span labeled hallucinated, not a positive sales value.

Entropy: TP=53, FP=22, TN=20, FN=8. Flag every span: TP=61, FP=42, TN=0, FN=0.

F1 = 2TP / (2TP + FP + FN). TP is a flagged labeled error; FP is a flagged labeled-correct span; FN is a missed labeled error.

Question: Compute both F1 values. How many fewer false alarms and how many more misses does entropy have? Does its higher point estimate prove stable superiority?

Worked solution:

Entropy: 106 / (106 + 22 + 8) = 0.7794. Flag every span: 122 / (122 + 42 + 0) = 0.7439.

Entropy makes 20 fewer false alarms, but misses 8 additional labeled errors. F1 does not include true negatives or monetary costs; this is not an estimate of avoided business loss.

The paired question-bootstrap F1 difference is +0.0355, with exploratory 95% interval [-0.0356, 0.1047]. Crossing zero is not proof of equality, and this analysis does not establish stable superiority. It remains conditional on provisional labels and fixed thresholds, without resolving test-based signal selection or shared-period dependence.

Separately, B2 adds nine provisional dev atoms and refits dev thresholds. Entropy F1 becomes 0.752 on the same old test. B1's interval is not a B2 interval; neither analysis is fresh confirmation.

Follow-up: Why can flagging everything have a high F1 here? What false-alarm and missed-error costs would you need before choosing a reporting policy?

Source: `reports/bizhallu_statistics_v2_report.json`

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
