# BizHallu Annotation Guidelines

Version: 0.1

Status: pilot-tested draft for `qwen_pilot20`; ready for `qwen_full100` span
annotation with review-table support.

## Purpose

These guidelines define how to label key business fact spans in Qwen-generated
retail analysis answers. The labels will support span-level hallucination
detection experiments.

The goal is not to grade the whole answer as right or wrong. The goal is to
mark the generated spans that a business user could rely on:

- entities
- products
- months and date ranges
- currency amounts
- percentages
- rankings
- comparison directions
- business conclusions

## Source Files

Use these files for the pilot annotation pass:

- `outputs/qwen_pilot20_generations.jsonl`
- `outputs/pilot20_review.csv`
- `data/processed/business_questions_gold.jsonl`

Use these files for the full100 annotation pass:

- `outputs/qwen_full100_generations.jsonl`
- `outputs/full100_review.csv`
- `outputs/full100_review.jsonl`
- `outputs/full100_annotation_queue.csv`
- `outputs/full100_heldout_high_annotation_batch.csv`
- `data/annotations/span_annotations_full100_seed.jsonl`
- `data/annotations/span_annotations_full100_draft.jsonl`
- `data/processed/business_questions_gold.jsonl`

Do not annotate prompt text, gold answers, or evidence tables. Annotate spans in
the `generated_text` field only.

## Span Unit

Annotate the smallest text span that expresses a business fact.

Use 0-based character offsets:

- `span_start_char` is inclusive.
- `span_end_char` is exclusive.
- `span_text` must exactly equal `generated_text[span_start_char:span_end_char]`.

Do not include Markdown markers unless the marker itself is part of the fact.
For example, in `**Spain**`, annotate `Spain`, not `**Spain**`.

Do not label every word. Filler text such as "the", "therefore", "with", and
"based on" should normally be ignored.

## Labels

Use exactly these labels:

| Label | Meaning | Primary metrics |
| --- | --- | --- |
| `correct_key_fact` | The span is supported by the gold answer or the provided evidence. | Negative class |
| `hallucinated_key_fact` | The span contradicts the gold answer or provided evidence. | Positive class |
| `unsupported_claim` | The span is business-relevant but not supported by the prompt evidence. | Positive class |
| `ambiguous_or_unverifiable` | The span cannot be judged reliably under the current evidence and question. | Excluded |
| `ignore` | The span is not a key business fact. Usually do not create rows for this. | Excluded |

Prefer not to write `ignore` rows. Use `ignore` only if a future annotation tool
requires explicit ignored spans.

## Fact Types

Use exactly these fact types unless the guidelines are revised:

- `month`
- `date_range`
- `country`
- `product_stock_code`
- `product_name`
- `currency_amount`
- `percentage`
- `ranking`
- `comparison_direction`
- `business_definition`
- `unsupported_business_claim`
- `malformed_number`

## Correctness Rules

### Context-Bound Correctness

Judge each span in the context of the business claim it supports, not as an
isolated string.

A value can appear in the evidence table and still be labeled
`hallucinated_key_fact` if the generated answer uses it to support the wrong
answer entity, rank, comparison, or conclusion.

Example:

- If Spain's net revenue is present in the evidence table, but the question asks
  for the highest non-UK country and the gold answer is Netherlands, label
  `Spain` and its answer amount as `hallucinated_key_fact` in that answer
  context.

For multi-fact sentences, annotate the smallest separable spans. A sentence can
contain both correct and hallucinated facts. For example, a comparison sentence
can state the wrong higher country while still quoting the correct revenue for
one compared country.

### Time Ranges and Partial Months

Use `date_range` when the generated span identifies a partial month, cutoff
date, or explicit through-date range.

Example:

- `December 2011 through December 9` should be labeled as `date_range` when the
  question and gold answer are scoped to the partial December 2011 period.

Use `month` for ordinary full-month labels such as `January 2011`.

### Numbers

Currency amounts are correct if they are within:

```text
max(1.00 GBP, 0.5 percent of absolute gold value)
```

Percentages are correct if they are within:

```text
0.5 percentage points
```

For monthly-change answers, if the percentage span omits the sign but a nearby
direction span correctly states `increase` or `decrease`, judge the percentage
magnitude against the gold percent and explain the sign handling in `notes`.
If the answer gives no correct direction cue, signs must match inside the
percentage span.

If a generated number has the right magnitude but malformed formatting, label it
as `hallucinated_key_fact` with `fact_type = malformed_number`.

Example:

- `GBP 145,6145.80` should be labeled as a malformed number when the gold value
  is `GBP 1,456,145.80`.

### Signs and Directions

Signs matter when the statement is about change, reduction, increase, decrease,
or cancellation revenue.

Annotate comparison direction as a span when the answer states which entity,
month, or product is higher or lower.

For monthly-change answers, use `comparison_direction` for change direction
spans such as `increased`, `decreased`, `rose`, or `fell`.

Example:

- If gold says France generated more than Germany but the answer says
  `Germany generated more net revenue`, annotate that phrase as
  `hallucinated_key_fact` with `fact_type = comparison_direction`.
- If gold says revenue decreased from January to February and the answer says
  `decreased`, annotate `decreased` as `correct_key_fact` with
  `fact_type = comparison_direction`.

### Entities

Countries, product names, and stock codes must match after basic normalization:

- case-insensitive comparison
- repeated whitespace collapsed
- product stock code or product name can identify the product when unique

If a product name is correct but capitalization is odd, treat it as correct.

### Rankings

Ranking facts require the ordered list to match the gold answer.

For natural-language ranking claims, annotate the smallest ranking assertion
span, not a bare rank value. A ranking assertion usually includes a local
predicate such as `ranked`, `ranking is`, `rank`, or the ranked-list line that
ties the rank to an entity.

Preferred examples:

- `ranked 1st`
- `ranking is 1`
- `ranking is **2nd**`

Do not annotate an isolated digit such as `1` as a ranking span in prose. It
does not carry a business fact without the ranking predicate.

For ranked lists or tables, a standalone rank marker such as `1.`, `1)`, or `1`
is allowed only when it is visually or structurally tied to the list item. Add
`list_rank_marker` in `notes` when using this exception.

For ranking answers, annotate the concrete spans that carry the wrong ranking
claim:

- ranking assertion, such as `ranked 1st` or `ranking is 1`
- product stock code
- product name
- revenue amount

If a listed product is correct but in the wrong rank position, label the rank
assertion or product-at-rank span as `hallucinated_key_fact`.

### Product Revenue Share

For product revenue share answers, annotate the numerator, denominator, and
share percentage as separate spans.

- The numerator is the merchandise net revenue for the requested top product or
  top-N product group.
- The denominator is the total merchandise net revenue for the requested month.
- The share percentage is the numerator divided by the denominator.

If the denominator is correct but the numerator is wrong, label the denominator
as `correct_key_fact` and the numerator and share percentage as
`hallucinated_key_fact`.

For top-N share answers, generated component amounts for the top-N products can
be annotated separately when they are explicitly listed. Use the relevant
`top_products[i].merchandise_net_revenue` gold field in `gold_reference`.

### Extra Business Claims

Generated answers may add facts not required by the question.

Label extra claims when they are business-relevant, such as:

- unsupported percentages
- unsupported causal explanations
- unsupported recommendations
- unsupported claims about gross revenue, cancellation revenue, or rank

Use `hallucinated_key_fact` when the claim is contradicted by the gold answer,
the evidence table, or a deterministic calculation from the provided evidence.

Use `unsupported_claim` when the claim is business-relevant but the prompt does
not provide enough evidence to verify it and it is not directly contradicted.

Examples:

- A cancellation return revenue of `GBP 0.00` is `hallucinated_key_fact` when
  the evidence row shows `GBP -126,980.43`.
- A causal explanation such as "because demand increased" is
  `unsupported_claim` unless the evidence explicitly supports demand as a cause.
- A percentage with no stated denominator, such as `100% gross positive
  revenue`, is usually `unsupported_claim` unless the context makes it directly
  contradicted by the evidence.

When unsure whether an extra claim is contradicted or merely unsupported, prefer
`ambiguous_or_unverifiable` and add a note. Do not use the model's fluency as
evidence.

### Contradictions Within One Answer

Label later claims independently even if they contradict earlier generated
claims. The gold answer and evidence table are the source of truth, not the
model's earlier sentence.

Example:

- If an answer first says Netherlands generated more than EIRE, then later says
  Netherlands was less than EIRE, label the first comparison direction as
  `hallucinated_key_fact` and the later direction as `correct_key_fact` if the
  later direction matches the gold answer.

## Examples From Pilot20

### q_0001

Gold: Netherlands, GBP 26,611.16.

Generated:

```text
The country ... is **Spain** with a net revenue of **GBP 7178.54**.
```

Suggested labels:

| Span | Fact type | Label | Reason |
| --- | --- | --- | --- |
| `January 2011` | `month` | `correct_key_fact` | Correct month. |
| `Spain` | `country` | `hallucinated_key_fact` | Gold country is Netherlands. |
| `GBP 7178.54` | `currency_amount` | `hallucinated_key_fact` | Spain's value appears in evidence, but it is used as the answer amount for the wrong top-country claim. |
| `ranking is **2nd**` | `ranking` | `hallucinated_key_fact` | The generated answer asserts the wrong rank for the selected country. |

### q_0012

Gold: United Kingdom, GBP 432,995.40.

Generated:

```text
The United Kingdom ranked 1st with a 100% gross positive revenue and a cancellation return revenue of GBP 0.00.
```

Suggested labels:

| Span | Fact type | Label | Reason |
| --- | --- | --- | --- |
| `United Kingdom` | `country` | `correct_key_fact` | Correct answer country. |
| `ranked 1st` | `ranking` | `correct_key_fact` | Supported by the evidence table. |
| `100% gross positive revenue` | `percentage` | `unsupported_claim` | No denominator or percentage basis is provided. |
| `GBP 0.00` | `currency_amount` | `hallucinated_key_fact` | Evidence shows cancellation return revenue is GBP -126,980.43. |

### q_0017

Gold: 22423, REGENCY CAKESTAND 3 TIER, GBP 26,722.16.

Generated:

```text
The ranking is 1. The stock code is **79321**, and the product name is **CHILLI LIGHTS**.
```

Suggested labels:

| Span | Fact type | Label | Reason |
| --- | --- | --- | --- |
| `ranking is 1` | `ranking` | `hallucinated_key_fact` | The rank-1 claim is attached to the wrong product. |
| `79321` | `product_stock_code` | `hallucinated_key_fact` | Gold stock code is 22423. |
| `CHILLI LIGHTS` | `product_name` | `hallucinated_key_fact` | Gold product name is REGENCY CAKESTAND 3 TIER. |

### q_0060

Gold: the December 2010 top 3 products are REGENCY CAKESTAND 3 TIER, RED
WOOLLY HOTTIE WHITE HEART., and PAPER CHAIN KIT 50'S CHRISTMAS.

Generated:

```text
1. **WHITE SKULL HOT WATER BOTTLE** ... GBP 8,224.98.
2. **CHILLI LIGHTS** ... GBP 7,506.44.
3. **PAPER CHAIN KIT 50'S CHRISTMAS** ... GBP 9,187.45.
```

Suggested labels:

| Span | Fact type | Label | Reason |
| --- | --- | --- | --- |
| `1.` | `ranking` | `hallucinated_key_fact` | List rank marker is tied to the wrong rank-1 product; add `list_rank_marker` in notes. |
| `WHITE SKULL HOT WATER BOTTLE` | `product_name` | `hallucinated_key_fact` | Wrong rank-1 product. |
| `3.` | `ranking` | `correct_key_fact` | List rank marker is tied to the correct rank-3 product; add `list_rank_marker` in notes. |
| `PAPER CHAIN KIT 50'S CHRISTMAS` | `product_name` | `correct_key_fact` | Correct rank-3 product. |

### q_0047

Gold: EIRE generated more net revenue than Netherlands by GBP 42,663.63.

Generated:

```text
the Netherlands generated more net revenue ... Netherlands' net revenue was 1.00 GBP less than EIRE
```

Suggested labels:

| Span | Fact type | Label | Reason |
| --- | --- | --- | --- |
| `July 2011` | `month` | `correct_key_fact` | Correct month. |
| `the Netherlands generated more net revenue` | `comparison_direction` | `hallucinated_key_fact` | Gold higher country is EIRE. |
| `EIRE` | `country` | `correct_key_fact` | Correct compared entity. |
| `42689.65 GBP` | `currency_amount` | `correct_key_fact` | Correct EIRE revenue. |

The later phrase saying Netherlands was less than EIRE can be separately
labeled as correct direction if its span is useful for analysis.

### q_0100

Gold: net revenue is GBP 1,456,145.80.

Generated:

```text
GBP 145,6145.80
```

Suggested label:

| Span | Fact type | Label | Reason |
| --- | --- | --- | --- |
| `GBP 145,6145.80` | `malformed_number` | `hallucinated_key_fact` | Malformed and does not match the gold value. |

### q_0050

Gold: net revenue decreased by GBP 61,422.15 (-11.00%) from January 2011 to
February 2011.

Generated:

```text
decreased from GBP 558,448.56 in January 2011 to GBP 497,026.41 in February 2011, representing a **GBP 62,422.15 decrease** or a **-12.06%** change.
```

Suggested labels:

| Span | Fact type | Label | Reason |
| --- | --- | --- | --- |
| `decreased` | `comparison_direction` | `correct_key_fact` | Correct change direction. |
| `GBP 558,448.56` | `currency_amount` | `correct_key_fact` | Correct January net revenue. |
| `GBP 497,026.41` | `currency_amount` | `correct_key_fact` | Correct February net revenue. |
| `GBP 62,422.15` | `currency_amount` | `hallucinated_key_fact` | Gold absolute decrease is GBP 61,422.15. |
| `-12.06%` | `percentage` | `hallucinated_key_fact` | Gold percentage change is -11.00%. |

### q_0084

Gold: top 3 product revenue share is GBP 33,787.17 out of GBP 578,914.41, or
5.84%.

Generated:

```text
GBP 5209.79 + GBP 5580.98 + GBP 5133.77 = GBP 15,924.54 ... GBP 578,914.41 ... 27.5%.
```

Suggested labels:

| Span | Fact type | Label | Reason |
| --- | --- | --- | --- |
| `GBP 5209.79` | `currency_amount` | `hallucinated_key_fact` | Wrong top-N component amount. |
| `GBP 15,924.54` | `currency_amount` | `hallucinated_key_fact` | Wrong top-N numerator. |
| `GBP 578,914.41` | `currency_amount` | `correct_key_fact` | Correct denominator. |
| `27.5%` | `percentage` | `hallucinated_key_fact` | Gold share is 5.84%. |

## Annotation Record Schema

Store pilot labels in `data/annotations/span_annotations_pilot.jsonl`.

Store full100 labels in `data/annotations/span_annotations_full100.jsonl`.

Each line should be a JSON object:

```json
{
  "annotation_id": "ann_q_0001_001",
  "question_id": "q_0001",
  "prompt_id": "p_0001",
  "source_generation_file": "outputs/qwen_pilot20_generations.jsonl",
  "annotation_version": "0.1",
  "span_text": "Spain",
  "span_start_char": 93,
  "span_end_char": 98,
  "fact_type": "country",
  "label": "hallucinated_key_fact",
  "gold_reference": {
    "field": "country",
    "value": "Netherlands"
  },
  "reason": "Gold country is Netherlands.",
  "confidence": "high",
  "notes": ""
}
```

Required fields:

- `annotation_id`
- `question_id`
- `prompt_id`
- `source_generation_file`
- `annotation_version`
- `span_text`
- `span_start_char`
- `span_end_char`
- `fact_type`
- `label`
- `gold_reference`
- `reason`
- `confidence`
- `notes`

Allowed confidence values:

- `high`
- `medium`
- `low`

## Pilot Workflow

Use this order:

1. Open `outputs/pilot20_review.csv`.
2. Choose 2-3 records that include both correct and wrong facts.
3. Copy each record's `generated_text` exactly from the JSONL source.
4. Identify only key business fact spans.
5. Create JSONL span records.
6. Validate offsets before expanding annotation.

Recommended first pilot records:

- `q_0001`: simple wrong country and wrong amount.
- `q_0012`: mostly correct answer with extra unsupported numeric claims.
- `q_0047`: contradictory comparison direction.
- `q_0100`: malformed number format.

## Full100 Workflow

Use this order:

1. Open `outputs/full100_heldout_high_annotation_batch.csv` for the first
   held-out annotation batch.
2. Use `outputs/full100_annotation_queue.csv` for the complete annotation
   order.
3. Open `outputs/full100_review.csv` for a spreadsheet-style pass, or
   `outputs/full100_review.jsonl` when nested evidence is easier to inspect.
4. Start with rows where `annotation_priority = high`, especially dev/test
   rows, because final held-out metrics depend on labeled dev/test spans.
5. For each row, copy spans only from `generated_text`.
6. Use `gold_answer_json`, `gold_facts_json`, and `prompt_evidence_rows_json`
   to decide whether each span is correct, contradicted, unsupported, or
   ambiguous.
7. Start with a small draft seed in
   `data/annotations/span_annotations_full100_seed.jsonl`, validate offsets,
   and use the recorded policy review before scaling.
8. Save final full100 labels to
   `data/annotations/span_annotations_full100.jsonl`.
9. Use `data/annotations/span_annotations_full100_draft.jsonl` only as a
   reviewable intermediate file. Do not score final detector metrics from it
   until the held-out annotation pass is complete and reviewed.
10. Validate offsets before scoring detectors.

Do not treat `auto_status`, `preliminary_error_types`, or
`suggested_annotation_focus` as labels. They are triage aids for deciding what
to inspect first.

### Full100 Seed Policy Decisions

The first 5-question seed review fixes these rules before scaling:

- Repeated wrong answer entities should be labeled only when each occurrence is
  part of a distinct business-fact claim. Example: keep both `Spain` spans in
  `q_0005` because the second one binds Spain to the stated revenue amount.
- Malformed answer amounts should use `fact_type = malformed_number` when the
  numeric formatting is invalid or ambiguous. Keep the label positive when the
  amount is malformed or bound to the wrong answer entity, and point
  `gold_reference` to the intended numeric fact.
- Explicit ranking claims should be labeled as `ranking`, even inside
  top-country questions. Examples include `ranking is **second**` and
  `ranking is **1**`. Do not separately label every generic `highest`
  restatement unless it is the smallest concrete ranking assertion.
- Vague explanatory business prose should be recorded as a secondary-claim risk
  rather than forced into the core seed. Add it only when a minimal span can be
  judged consistently from the provided evidence.

## Open Decisions After Pilot Annotation

Resolved during pilot20 annotation:

- Extra business claims should be labeled when they are business-relevant and a
  user might rely on them. Use `hallucinated_key_fact` when contradicted and
  `unsupported_claim` when not verifiable.
- Contradictory statements in the same answer should be labeled independently
  against the gold answer and evidence table.
- Ranking spans in prose should use the smallest ranking assertion, not an
  isolated rank value. Standalone list rank markers require `list_rank_marker`
  in `notes`.
- Partial-month scopes should use `date_range`, not just `month`.

Still open during full 100-answer annotation:

- Whether `ignore` rows are needed at all.
- How broad the final secondary-claim pass should be for vague causal or
  explanatory prose.
