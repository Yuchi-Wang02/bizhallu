from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GUIDELINES_PATH = PROJECT_ROOT / "data" / "annotations" / "annotation_guidelines.md"
GENERATIONS_PATH = PROJECT_ROOT / "outputs" / "qwen_pilot20_generations.jsonl"
VALIDATION_PATH = PROJECT_ROOT / "outputs" / "annotation_guidelines_validation.json"

REQUIRED_LABELS = {
    "correct_key_fact",
    "hallucinated_key_fact",
    "unsupported_claim",
    "ambiguous_or_unverifiable",
    "ignore",
}

REQUIRED_FACT_TYPES = {
    "month",
    "date_range",
    "country",
    "product_stock_code",
    "product_name",
    "currency_amount",
    "percentage",
    "ranking",
    "comparison_direction",
    "business_definition",
    "unsupported_business_claim",
    "malformed_number",
}

REQUIRED_SCHEMA_FIELDS = {
    "annotation_id",
    "question_id",
    "prompt_id",
    "source_generation_file",
    "annotation_version",
    "span_text",
    "span_start_char",
    "span_end_char",
    "fact_type",
    "label",
    "gold_reference",
    "reason",
    "confidence",
    "notes",
}

REQUIRED_REFERENCES = {
    "outputs/qwen_pilot20_generations.jsonl",
    "outputs/pilot20_review.csv",
    "data/processed/business_questions_gold.jsonl",
    "data/annotations/span_annotations_pilot.jsonl",
}


def add_failure(failures: list[dict[str, Any]], reason: str, detail: Any = None) -> None:
    failures.append({"reason": reason, "detail": detail})


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    failures: list[dict[str, Any]] = []
    if not GUIDELINES_PATH.exists():
        add_failure(failures, "missing annotation guidelines", str(GUIDELINES_PATH))
        text = ""
    else:
        text = GUIDELINES_PATH.read_text(encoding="utf-8")
    plain_text = text.replace("`", "")

    for label in sorted(REQUIRED_LABELS):
        if f"`{label}`" not in text:
            add_failure(failures, "missing required label", label)

    for fact_type in sorted(REQUIRED_FACT_TYPES):
        if f"`{fact_type}`" not in text:
            add_failure(failures, "missing required fact type", fact_type)

    for field in sorted(REQUIRED_SCHEMA_FIELDS):
        if f"`{field}`" not in text and f'"{field}"' not in text:
            add_failure(failures, "missing required schema field", field)

    for reference in sorted(REQUIRED_REFERENCES):
        if f"`{reference}`" not in text:
            add_failure(failures, "missing required file reference", reference)

    required_phrases = [
        "0-based character offsets",
        "span_start_char is inclusive",
        "span_end_char is exclusive",
        "generated_text field only",
        "Context-Bound Correctness",
        "Judge each span in the context of the business claim it supports",
        "A value can appear in the evidence table and still be labeled",
        "Time Ranges and Partial Months",
        "Use date_range when the generated span identifies a partial month",
        "December 2011 through December 9",
        "deterministic calculation from the provided evidence",
        "no stated denominator",
        "Contradictions Within One Answer",
        "For natural-language ranking claims, annotate the smallest ranking assertion",
        "Do not annotate an isolated digit",
        "list_rank_marker",
        "For monthly-change answers, use comparison_direction",
        "For monthly-change answers, if the percentage span omits the sign",
        "Product Revenue Share",
        "The numerator is the merchandise net revenue",
        "The denominator is the total merchandise net revenue",
        "q_0084",
        "q_0050",
        "Positive class",
        "Negative class",
        "q_0001",
        "q_0012",
        "q_0017",
        "q_0060",
        "q_0047",
        "q_0100",
    ]
    for phrase in required_phrases:
        if phrase not in plain_text:
            add_failure(failures, "missing required guidance phrase", phrase)

    example_match = re.search(r"```json\n(.*?)\n```", text, re.S)
    if example_match:
        try:
            example = json.loads(example_match.group(1))
            generations_by_qid = {record["question_id"]: record for record in load_jsonl(GENERATIONS_PATH)}
            generation = generations_by_qid.get(example.get("question_id"))
            if generation is None:
                add_failure(failures, "schema example question_id not found in pilot generations", example.get("question_id"))
            else:
                if example.get("prompt_id") != generation.get("prompt_id"):
                    add_failure(
                        failures,
                        "schema example prompt_id mismatch",
                        {"example": example.get("prompt_id"), "actual": generation.get("prompt_id")},
                    )
                start = int(example.get("span_start_char"))
                end = int(example.get("span_end_char"))
                actual_span = generation["generated_text"][start:end]
                if actual_span != example.get("span_text"):
                    add_failure(
                        failures,
                        "schema example span offsets do not match generated_text",
                        {"example": example.get("span_text"), "actual": actual_span},
                    )
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            add_failure(failures, "schema example JSON or offsets invalid", str(exc))
    else:
        add_failure(failures, "missing schema JSON example")

    report = {
        "guidelines_path": str(GUIDELINES_PATH),
        "num_failures": len(failures),
        "failures": failures,
        "required_label_count": len(REQUIRED_LABELS),
        "required_fact_type_count": len(REQUIRED_FACT_TYPES),
        "required_schema_field_count": len(REQUIRED_SCHEMA_FIELDS),
    }
    VALIDATION_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
