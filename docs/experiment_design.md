# BizHallu Experiment Design

Version: 0.1

## 1. Project Goal

BizHallu evaluates whether hallucination-detection methods can identify incorrect or unsupported facts in AI-generated business analysis reports.

The project is not a generic sales dashboard and not only a paper-reproduction exercise. The intended message is:

> When an LLM is used as a business analyst, it can produce confident but incorrect numbers, rankings, entities, time windows, and business conclusions. BizHallu builds an auditable retail analytics setting where those errors can be generated, labeled, detected, and evaluated.

The first version focuses on a retail sales-analysis workflow using the UCI Online Retail dataset and Qwen3-0.6B.

## 2. Intended Final Presentation

The final portfolio artifact should have three layers.

### 2.1 Streamlit Demo

The demo should let a user select a business question, inspect the Qwen-generated answer, and see fact spans highlighted:

- Green: correct key business fact
- Red: hallucinated or incorrect key business fact
- Yellow: unsupported business claim
- Gray: non-key text

The right panel should show:

- gold answer
- source evidence table
- detector scores
- predicted vs true labels
- confusion matrix
- error type breakdown

### 2.2 GitHub Repository

The repository should communicate a complete pipeline:

```text
raw data -> cleaned summaries -> business questions -> Qwen generations
-> span labels -> baselines -> metrics -> demo
```

### 2.3 Experiment Report

The report should answer:

- What types of business facts does the LLM get wrong?
- Do simple uncertainty signals catch those mistakes?
- Does a training-free white-box method improve detection?
- Does a lightweight trained probe improve detection with limited labels?
- Where do the methods fail in realistic business analysis?

## 3. Business Scenario

Scenario:

> A retailer wants to use an AI business analyst to generate short sales-performance summaries from transaction-derived tables. Before trusting these summaries, the company needs a control layer that flags unsupported or incorrect business facts.

The LLM receives a question and a compact evidence table. It must write a concise business analysis answer. The detector then scores generated spans that contain business facts.

## 4. Dataset and Evidence Sources

Primary dataset:

- UCI Machine Learning Repository, Online Retail
- Citation: Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5BW33
- Local raw file: `data/raw/Online Retail.xlsx`

Processed evidence files:

- `monthly_net_revenue_summary.csv`
- `country_month_net_revenue_summary.csv`
- `product_month_net_revenue_summary.csv`
- `country_net_revenue_summary.csv`
- `product_net_revenue_summary.csv`
- `monthly_coverage_summary.csv`

Default revenue metric:

- Use net revenue unless a question explicitly says gross positive sales.
- Net revenue includes cancellations and returns as negative revenue.

Product questions:

- Use merchandise net revenue tables.
- Product tables exclude non-product charge codes such as postage, discounts, bank charges, manual adjustments, samples, and no-digit stock codes.

Trend questions:

- Use 2011-01 through 2011-11 for month-over-month or full-month trend questions.
- 2011-12 is a partial month because the source data ends on 2011-12-09.
- 2011-12 can be used only if the prompt explicitly states "through 2011-12-09" or "partial December 2011."

## 5. What Counts as a Hallucinated Business Fact

The unit of annotation is a key business fact span, not the full answer.

A key business fact span is any generated text that asserts a business-relevant fact:

- number
- currency amount
- percentage
- country
- product name or stock code
- month or date range
- ranking
- comparison
- direction of change
- business conclusion

### 5.1 Labels

Use these labels in the MVP:

| Label | Meaning |
| --- | --- |
| `correct_key_fact` | The span is supported by the gold answer or evidence table. |
| `hallucinated_key_fact` | The span is contradicted by the gold answer or evidence table. |
| `unsupported_claim` | The span may be plausible, but the given evidence does not support it. |
| `ambiguous_or_unverifiable` | The span cannot be judged reliably under the current question/evidence setup. |
| `ignore` | The text is not a key business fact. |

For binary detection metrics, map:

- Positive class: `hallucinated_key_fact` and `unsupported_claim`
- Negative class: `correct_key_fact`
- Exclude from primary metrics: `ambiguous_or_unverifiable` and `ignore`

### 5.2 Numeric Correctness Rules

Currency and revenue values are correct if they are within:

```text
max(1.00, 0.5 percent of absolute gold value)
```

Percentages are correct if they are within:

```text
0.5 percentage points
```

Rounded values are acceptable if the answer signals approximation with words such as "about", "approximately", or "roughly" and stays within the tolerance above.

### 5.3 Entity and Ranking Correctness Rules

Countries, products, and months must match the gold answer exactly after basic normalization:

- case-insensitive comparison
- collapse repeated whitespace
- allow stock-code plus description when either uniquely identifies the product

Rankings are correct only if the ordered list matches the gold answer for the requested `top-k`.

Comparisons are correct only if both the compared entities and the direction of the comparison are correct.

### 5.4 Unsupported Business Conclusions

Business conclusions are unsupported when the output states a cause, implication, risk, or recommendation that is not directly supported by the provided evidence table.

Examples:

- Supported: "The United Kingdom had the highest net revenue in November 2011."
- Unsupported: "This was driven by a successful marketing campaign."
- Unsupported: "The company should increase inventory for this product next quarter."

Unsupported claims matter because business users may act on them even when the numeric fact is correct.

## 6. MVP Question Types

The first question set should contain around 100 deterministic questions.

| Question type | Evidence source | Intended errors |
| --- | --- | --- |
| `top_country_month` | `country_month_net_revenue_summary.csv` | wrong country, wrong revenue, wrong month |
| `top_product_month` | `product_month_net_revenue_summary.csv` | wrong product, wrong revenue, non-product confusion |
| `country_comparison_month` | `country_month_net_revenue_summary.csv` | wrong comparison direction, wrong values |
| `monthly_revenue_change` | `monthly_net_revenue_summary.csv` | wrong month-over-month arithmetic, partial-month confusion |
| `top3_products_month` | `product_month_net_revenue_summary.csv` | wrong ranking order, omitted product |
| `product_revenue_share_month` | `product_month_net_revenue_summary.csv` | wrong percentage, wrong denominator |
| `return_impact_month` | `monthly_net_revenue_summary.csv` | gross vs net confusion, cancellation interpretation |

MVP constraints:

- Prefer months from 2011-01 through 2011-11.
- Avoid tiny country-month groups in the first 100 questions unless the question is explicitly about returns or negative net revenue.
- Include enough distractor rows in prompts so the task is nontrivial, but keep tables small enough for Qwen3-0.6B.

## 7. Prompt Conditions

Use three prompt difficulty levels.

### 7.1 Easy

Provide only the directly relevant rows. The model mostly needs to read the table.

Purpose:

- establish baseline accuracy
- verify prompt and gold-answer pipeline

### 7.2 Medium

Provide relevant rows plus plausible distractors, such as neighboring months or nearby-ranked countries/products.

Purpose:

- induce ranking, comparison, and numeric mistakes

### 7.3 Hard

Provide distractors that test business definitions:

- gross vs net revenue
- cancellation revenue
- product vs non-product charges
- partial December 2011

Purpose:

- test whether detectors catch confident business-specific mistakes

## 8. Generation Protocol

Model:

- Qwen3-0.6B

Implementation:

- Use Hugging Face `transformers`
- Use a setup that returns generated token ids, logits or scores, token probabilities, entropy, and hidden states

Store each generation as JSONL with:

- `question_id`
- `prompt_id`
- `difficulty`
- `prompt`
- `model_name`
- `generation_config`
- `generated_text`
- `generated_tokens`
- `generated_token_ids`
- `token_logprobs`
- `token_entropy`
- `top2_margin`
- `hidden_state_file` or compressed hidden-state reference
- `gold_answer`

Current implementation note:

- The current Qwen scripts store generated token ids and raw-logit token traces
  for logprob, entropy, and top-2 margin baselines.
- Hidden states are not saved yet. A hidden-state probe will require a later
  script update or a separate extraction pass.

The first generation pass should prioritize reproducibility over scale.

## 9. Annotation Protocol

Start with 20 generated answers as a pilot annotation set.

Annotate only key business fact spans. Do not label every word.

Each span record should include:

```json
{
  "question_id": "q_001",
  "span_text": "Germany",
  "span_start_char": 0,
  "span_end_char": 7,
  "fact_type": "country",
  "label": "hallucinated_key_fact",
  "reason": "Gold country is United Kingdom.",
  "gold_reference": {
    "field": "country",
    "value": "United Kingdom"
  }
}
```

After the 20-answer pilot:

- revise ambiguous label rules
- check whether numeric tolerance is too strict or too loose
- review coverage across labels, fact types, and question types
- expand to 100 annotated answers

## 10. Baselines

### 10.1 Simple Baselines

These are required before paper baselines:

- token negative log probability
- token entropy
- top-2 probability margin
- span average log probability
- span max entropy

These baselines answer whether ordinary model uncertainty can detect business hallucinations.

### 10.2 Spilled Energy

Training-free white-box baseline using output logits or energy-derived signals.

Use it as the main paper-style training-free method in MVP.

### 10.3 Hidden-State Probe

Train a lightweight classifier on Qwen3-0.6B hidden states:

- logistic regression first
- small MLP only if logistic regression is too weak

Use the annotated spans as training data. Split by question id to avoid leakage.

### 10.4 Semantic Entropy

Use as answer-level or claim-level baseline, not forced token-level.

Run multiple samples per question and measure semantic disagreement across answers.

### 10.5 Deferred

TOHA is deferred to a later version because the code source is currently not reliable enough for MVP integration.

## 11. Evaluation

Primary evaluation:

- span-level binary classification
- positive: hallucinated or unsupported key fact
- negative: correct key fact

Metrics:

- confusion matrix
- precision
- recall
- F1
- AUROC
- AUPRC

Secondary analysis:

- metrics by fact type
- metrics by prompt difficulty
- metrics by question type
- error examples where the model is confident but wrong

Threshold policy:

- pilot sanity checks may tune thresholds on pilot20 only for debugging, but
  must be labeled as optimistic
- choose thresholds on a dev split
- report final metrics on a held-out test split
- do not tune thresholds on the test split

## 12. Planned Output Files

Question generation:

- `data/processed/business_questions_gold.jsonl`
- `data/processed/business_questions_gold_sample.csv`

Model generation:

- `outputs/qwen_input_prompts.jsonl`
- `outputs/qwen_pilot20_generations.jsonl`
- `outputs/qwen_pilot20_token_traces.jsonl`
- `outputs/pilot20_span_token_alignment.jsonl`
- `outputs/qwen_full100_generations.jsonl`
- `outputs/qwen_full100_token_traces.jsonl`

Annotation:

- `data/annotations/annotation_guidelines.md`
- `data/annotations/span_annotations_pilot.jsonl`
- `data/annotations/span_annotations_full100_seed.jsonl`
- `data/annotations/span_annotations_full100_draft.jsonl`
- `data/annotations/span_annotations_full100.jsonl`

Baselines and evaluation:

- `results/pilot20_simple_baseline_scores.csv`
- `results/pilot20_simple_baseline_metrics.csv`
- `results/pilot20_simple_baseline_report.json`
- `results/spilled_energy_scores.csv`
- `results/probe_scores.csv`
- `results/metrics_summary.csv`
- `results/confusion_matrices/`

Demo:

- `app/streamlit_demo.py`

Report:

- `site/index.html`
- `reports/bizhallu_experiment_report.pdf`

## 13. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Gold answers are wrong due to unclear business definitions. | Use deterministic summary tables and default to net revenue. |
| Partial December 2011 creates misleading trend answers. | Exclude 2011-12 from full-month trend questions. |
| Qwen3-0.6B is too accurate or too inaccurate. | Use prompt difficulty levels and distractor rows to tune task difficulty. |
| Token-level labels are too expensive. | Label only key business spans, not all tokens. |
| Simple uncertainty baselines perform poorly. | Treat this as a finding: business hallucinations can be confident errors. |
| Paper baseline code is hard to adapt. | Keep MVP grounded in simple baselines, Spilled Energy, and a lightweight probe. |

## 14. Step Acceptance Criteria

The question-generation step is ready to start when:

- this document exists and matches the cleaned data policy
- processed data validation passes
- default revenue metric is net revenue
- trend questions avoid 2011-12 unless explicitly partial
- product questions use merchandise net revenue
- MVP question types are fixed

The generation step is ready to start when:

- at least 100 question-gold records exist
- each record names its evidence source
- each record can be recomputed from processed CSV files
- each record has a prompt difficulty label

## 15. Portfolio Positioning

Recommended one-line project description:

> Built BizHallu, an AI reliability benchmark for detecting unsupported facts in LLM-generated retail business analysis reports, using UCI transaction data, Qwen3-0.6B, span-level labels, and white-box hallucination-detection baselines.
