from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATION_PATH = PROJECT_ROOT / "outputs" / "qwen_full100_generations.jsonl"
BATCH_PATH = PROJECT_ROOT / "outputs" / "full100_heldout_high_annotation_batch.jsonl"
ANNOTATION_PATH = PROJECT_ROOT / "data" / "annotations" / "span_annotations_full100_seed.jsonl"
PREVIEW_PATH = PROJECT_ROOT / "outputs" / "full100_annotation_seed_preview.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "full100_annotation_seed_report.json"
POLICY_REVIEW_PATH = PROJECT_ROOT / "outputs" / "full100_annotation_seed_policy_review.json"

SOURCE_GENERATION_FILE = "outputs/qwen_full100_generations.jsonl"
ANNOTATION_VERSION = "0.2-full100-seed"
SEED_QUESTION_IDS = ["q_0004", "q_0005", "q_0009", "q_0010", "q_0014"]


POLICY_DECISIONS = [
    {
        "topic": "repeated_wrong_entities",
        "decision": (
            "Label repeated answer entities only when each occurrence participates in a distinct "
            "business-fact claim. Keep the second q_0005 Spain span because it binds the wrong "
            "country to a stated net revenue amount."
        ),
    },
    {
        "topic": "malformed_answer_amounts",
        "decision": (
            "Use fact_type=malformed_number for malformed numeric formatting when the span is "
            "used as an answer amount. Keep the label positive when the amount is malformed or "
            "bound to the wrong answer entity; reference the intended gold numeric fact."
        ),
    },
    {
        "topic": "explicit_ranking_claims",
        "decision": (
            "Annotate explicit ranking assertions such as 'ranking is **second**' or "
            "'ranking is **1**' even in top-country questions. Do not separately annotate every "
            "generic 'highest' restatement unless it is the smallest concrete ranking assertion."
        ),
    },
    {
        "topic": "vague_explanatory_business_prose",
        "decision": (
            "Record as a secondary-claim risk when the prose is vague or causal, such as q_0004's "
            "decline explanation. Do not add it to the core seed unless a minimal adjudicable "
            "span can be judged consistently from the provided evidence."
        ),
    },
]


SEED_SPECS: dict[str, list[dict[str, Any]]] = {
    "q_0004": [
        {
            "span_text": "April 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month for the deterministic question.",
            "notes": "seed_batch_draft; prompt_copied_key_context; human_review_required",
        },
        {
            "span_text": "Japan",
            "fact_type": "country",
            "label": "hallucinated_key_fact",
            "gold_field": "country",
            "reason_template": "Generated top country is Japan, but the gold top country is {gold_display}.",
            "notes": "seed_batch_draft; wrong_answer_entity; human_review_required",
        },
        {
            "span_text": "GBP 4,871.83",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "net_revenue",
            "reason_template": "Generated answer amount is GBP 4,871.83, but the gold net revenue is {gold_display}.",
            "notes": "seed_batch_draft; wrong_answer_amount; human_review_required",
        },
    ],
    "q_0005": [
        {
            "span_text": "May 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month for the deterministic question.",
            "notes": "seed_batch_draft; prompt_copied_key_context; human_review_required",
        },
        {
            "span_text": "Spain",
            "fact_type": "country",
            "label": "hallucinated_key_fact",
            "gold_field": "country",
            "reason_template": "Generated top country is Spain, but the gold top country is {gold_display}.",
            "notes": "seed_batch_draft; wrong_answer_entity; first_mention; human_review_required",
        },
        {
            "span_text": "Spain",
            "occurrence": 2,
            "fact_type": "country",
            "label": "hallucinated_key_fact",
            "gold_field": "country",
            "reason_template": "Generated repeats Spain as the answer country, but the gold top country is {gold_display}.",
            "notes": "seed_batch_draft; wrong_answer_entity; repeated_mention; human_review_required",
        },
        {
            "span_text": "GBP 3257.60",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "net_revenue",
            "reason_template": "Generated answer amount is GBP 3257.60, but the gold net revenue is {gold_display}.",
            "notes": "seed_batch_draft; wrong_answer_amount; human_review_required",
        },
    ],
    "q_0009": [
        {
            "span_text": "September 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month for the deterministic question.",
            "notes": "seed_batch_draft; prompt_copied_key_context; human_review_required",
        },
        {
            "span_text": "France",
            "fact_type": "country",
            "label": "hallucinated_key_fact",
            "gold_field": "country",
            "reason_template": "Generated top country is France, but the gold top country is {gold_display}.",
            "notes": "seed_batch_draft; wrong_answer_entity; human_review_required",
        },
        {
            "span_text": "23,198.87 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "net_revenue",
            "reason_template": "Generated answer amount is 23,198.87 GBP, but the gold net revenue is {gold_display}.",
            "notes": "seed_batch_draft; wrong_answer_amount; human_review_required",
        },
        {
            "span_text": "ranking is **second**",
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": {
                "field": "rank",
                "fact_type": "ranking",
                "gold_value": 1,
                "gold_display_value": "rank 1: EIRE",
                "ranking_basis": "net_revenue_gbp among non-UK countries in September 2011",
            },
            "reason_template": (
                "Generated explicit ranking claim says the selected country is second, but the "
                "gold rank-1 country is EIRE and France is not rank 2 in the evidence table."
            ),
            "notes": "seed_policy_review; explicit_extra_ranking_claim; human_review_required",
        },
    ],
    "q_0010": [
        {
            "span_text": "October 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month for the deterministic question.",
            "notes": "seed_batch_draft; prompt_copied_key_context; human_review_required",
        },
        {
            "span_text": "Switzerland",
            "fact_type": "country",
            "label": "hallucinated_key_fact",
            "gold_field": "country",
            "reason_template": "Generated top country is Switzerland, but the gold top country is {gold_display}.",
            "notes": "seed_batch_draft; wrong_answer_entity; human_review_required",
        },
        {
            "span_text": "GBP 80,19.53",
            "fact_type": "malformed_number",
            "label": "hallucinated_key_fact",
            "gold_field": "net_revenue",
            "reason_template": "Generated answer amount is malformed and does not match the gold net revenue of {gold_display}.",
            "notes": "seed_batch_draft; malformed_answer_amount; human_review_required",
        },
    ],
    "q_0014": [
        {
            "span_text": "June 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month for the deterministic question.",
            "notes": "seed_batch_draft; prompt_copied_key_context; human_review_required",
        },
        {
            "span_text": "Norway",
            "fact_type": "country",
            "label": "hallucinated_key_fact",
            "gold_field": "country",
            "reason_template": "Generated top country is Norway, but the gold top country is {gold_display}.",
            "notes": "seed_batch_draft; wrong_answer_entity; human_review_required",
        },
        {
            "span_text": "GBP 58,86.86",
            "fact_type": "malformed_number",
            "label": "hallucinated_key_fact",
            "gold_field": "net_revenue",
            "reason_template": "Generated answer amount is malformed and does not match the gold net revenue of {gold_display}.",
            "notes": "seed_batch_draft; malformed_answer_amount; human_review_required",
        },
        {
            "span_text": "ranking is **1**",
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": {
                "field": "rank",
                "fact_type": "ranking",
                "gold_value": 1,
                "gold_display_value": "rank 1: United Kingdom",
                "ranking_basis": "net_revenue_gbp among all countries in June 2011",
            },
            "reason_template": (
                "Generated explicit ranking claim assigns rank 1 to Norway in context, but the "
                "gold rank-1 country is United Kingdom."
            ),
            "notes": "seed_policy_review; explicit_extra_ranking_claim; human_review_required",
        },
    ],
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def find_occurrence(text: str, needle: str, occurrence: int = 1) -> tuple[int, int]:
    start = -1
    cursor = 0
    for _ in range(occurrence):
        start = text.find(needle, cursor)
        if start == -1:
            raise ValueError(f"Could not find occurrence {occurrence} of {needle!r}")
        cursor = start + len(needle)
    return start, start + len(needle)


def gold_fact_by_field(batch_record: dict[str, Any], field: str) -> dict[str, Any]:
    for fact in batch_record["gold_facts"]:
        if fact["field"] == field:
            return fact
    raise KeyError(f"{batch_record['question_id']} has no gold fact field {field!r}")


def compact_gold_reference(fact: dict[str, Any]) -> dict[str, Any]:
    return {
        "field": fact["field"],
        "fact_type": fact["fact_type"],
        "gold_value": fact["value"],
        "gold_display_value": fact["display_value"],
        "tolerance": fact["tolerance"],
    }


def build_annotation(
    batch_record: dict[str, Any],
    generation_record: dict[str, Any],
    spec: dict[str, Any],
    span_index: int,
) -> dict[str, Any]:
    occurrence = int(spec.get("occurrence", 1))
    start, end = find_occurrence(generation_record["generated_text"], spec["span_text"], occurrence)
    if "gold_reference" in spec:
        gold_reference = dict(spec["gold_reference"])
        gold_display = str(gold_reference.get("gold_display_value", ""))
    else:
        gold_fact = gold_fact_by_field(batch_record, spec["gold_field"])
        gold_reference = compact_gold_reference(gold_fact)
        gold_display = gold_fact["display_value"]
    return {
        "annotation_id": f"ann_full100_seed_{batch_record['question_id']}_{span_index:03d}",
        "question_id": batch_record["question_id"],
        "prompt_id": batch_record["prompt_id"],
        "source_generation_file": SOURCE_GENERATION_FILE,
        "annotation_version": ANNOTATION_VERSION,
        "span_text": spec["span_text"],
        "span_start_char": start,
        "span_end_char": end,
        "fact_type": spec["fact_type"],
        "label": spec["label"],
        "gold_reference": gold_reference,
        "reason": spec["reason_template"].format(gold_display=gold_display),
        "confidence": "high",
        "notes": spec["notes"],
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")


def write_preview(path: Path, annotations: list[dict[str, Any]], batch_by_qid: dict[str, dict[str, Any]]) -> None:
    fieldnames = [
        "annotation_id",
        "question_id",
        "split",
        "question_type",
        "label",
        "fact_type",
        "span_text",
        "span_start_char",
        "span_end_char",
        "gold_display_value",
        "reason",
        "notes",
        "generated_text",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for annotation in annotations:
            batch_record = batch_by_qid[annotation["question_id"]]
            writer.writerow(
                {
                    "annotation_id": annotation["annotation_id"],
                    "question_id": annotation["question_id"],
                    "split": batch_record["split"],
                    "question_type": batch_record["question_type"],
                    "label": annotation["label"],
                    "fact_type": annotation["fact_type"],
                    "span_text": annotation["span_text"],
                    "span_start_char": annotation["span_start_char"],
                    "span_end_char": annotation["span_end_char"],
                    "gold_display_value": annotation["gold_reference"]["gold_display_value"],
                    "reason": annotation["reason"],
                    "notes": annotation["notes"],
                    "generated_text": batch_record["generated_text"],
                }
            )


def main() -> None:
    batch_records = load_jsonl(BATCH_PATH)
    generation_records = load_jsonl(GENERATION_PATH)
    batch_by_qid = {record["question_id"]: record for record in batch_records}
    generation_by_qid = {record["question_id"]: record for record in generation_records}

    missing_from_batch = sorted(set(SEED_QUESTION_IDS) - set(batch_by_qid))
    missing_from_generations = sorted(set(SEED_QUESTION_IDS) - set(generation_by_qid))
    if missing_from_batch or missing_from_generations:
        raise SystemExit(
            json.dumps(
                {
                    "missing_from_batch": missing_from_batch,
                    "missing_from_generations": missing_from_generations,
                },
                indent=2,
            )
        )

    annotations: list[dict[str, Any]] = []
    for question_id in SEED_QUESTION_IDS:
        batch_record = batch_by_qid[question_id]
        generation_record = generation_by_qid[question_id]
        if generation_record["prompt_id"] != batch_record["prompt_id"]:
            raise ValueError(f"{question_id} prompt_id mismatch")
        for span_index, spec in enumerate(SEED_SPECS[question_id], start=1):
            annotations.append(build_annotation(batch_record, generation_record, spec, span_index))

    write_jsonl(ANNOTATION_PATH, annotations)
    write_preview(PREVIEW_PATH, annotations, batch_by_qid)

    report = {
        "annotation_path": str(ANNOTATION_PATH),
        "preview_path": str(PREVIEW_PATH),
        "policy_review_path": str(POLICY_REVIEW_PATH),
        "source_generation_file": SOURCE_GENERATION_FILE,
        "annotation_version": ANNOTATION_VERSION,
        "status": "policy-reviewed draft seed annotations; human review is still required before final evaluation",
        "question_count": len(SEED_QUESTION_IDS),
        "span_count": len(annotations),
        "seed_question_ids": SEED_QUESTION_IDS,
        "split_counts": dict(sorted(Counter(batch_by_qid[qid]["split"] for qid in SEED_QUESTION_IDS).items())),
        "label_counts": dict(sorted(Counter(record["label"] for record in annotations).items())),
        "fact_type_counts": dict(sorted(Counter(record["fact_type"] for record in annotations).items())),
        "spans_by_question": dict(sorted(Counter(record["question_id"] for record in annotations).items())),
        "policy_decisions": POLICY_DECISIONS,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    policy_review = {
        "status": "reviewed",
        "annotation_version": ANNOTATION_VERSION,
        "seed_question_ids": SEED_QUESTION_IDS,
        "policy_decisions": POLICY_DECISIONS,
        "seed_changes": [
            "Added explicit ranking span for q_0009: ranking is **second**.",
            "Added explicit ranking span for q_0014: ranking is **1**.",
            "Kept q_0005 repeated Spain span because it binds the wrong entity to a separate amount claim.",
            "Kept q_0010 and q_0014 malformed answer amounts as fact_type=malformed_number.",
            "Did not add q_0004 vague decline explanation to the core seed; revisit during secondary-claim annotation if needed.",
        ],
    }
    POLICY_REVIEW_PATH.write_text(json.dumps(policy_review, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
