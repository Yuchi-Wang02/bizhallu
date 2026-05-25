# Prompt Design

Version: 0.1

## Goal

The Qwen prompt set should create a fair business-analysis task:

- The model receives enough evidence to answer the question.
- The prompt does not include the gold answer text.
- Ranking answers are not leaked by table row order.
- The model is instructed to avoid unsupported causes, recommendations, or external knowledge.

## Prompt Record

Each prompt record is stored in `outputs/qwen_input_prompts.jsonl` with:

- `prompt_id`
- `question_id`
- `question_type`
- `difficulty`
- `split`
- `messages`
- `full_prompt`
- `evidence_table_markdown`
- `prompt_evidence_rows`
- `row_order_policy`
- `gold_answer`
- `gold_facts`

The `full_prompt` and `messages` are the only fields intended for model input. Gold fields are stored outside the prompt for downstream evaluation.

## Row Ordering Policy

The question generator stores evidence rows in useful source order. The prompt builder changes row order before presenting the table:

- country evidence: alphabetic by country
- product evidence: deterministic hash order based on `question_id` and `stock_code`
- monthly-change evidence: chronological by `year_month`
- return-impact evidence: single row

This reduces accidental leakage where the first row is always the correct top-ranked answer.

## Prompt Constraints

The system instruction tells the model:

- act as a cautious business analyst
- use only provided evidence
- treat GBP amounts as British pounds
- avoid causes, recommendations, or external explanations unless supported
- answer concisely

The user prompt includes:

- the question
- metric definitions
- scope notes
- evidence table
- response requirements

## Fairness Checks

`src/validate_prompts.py` checks:

- each question has one prompt
- prompt ids are unique
- prompt text does not contain the exact gold short answer
- evidence rows are present
- share questions include total merchandise net revenue metadata
- partial December 2011 prompts explicitly mention December 9
- prompt JSONL can be parsed

