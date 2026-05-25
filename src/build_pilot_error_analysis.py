from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ERROR_REVIEW_PATH = PROJECT_ROOT / "results" / "pilot20_baseline_error_review.csv"
ERROR_SUMMARY_PATH = PROJECT_ROOT / "results" / "pilot20_baseline_error_summary.json"

ANALYSIS_SUMMARY_PATH = PROJECT_ROOT / "results" / "pilot20_error_analysis_summary.json"
ANALYSIS_BY_FAMILY_PATH = PROJECT_ROOT / "results" / "pilot20_error_analysis_by_family.csv"
ANALYSIS_EXAMPLES_PATH = PROJECT_ROOT / "results" / "pilot20_error_analysis_examples.csv"


FAMILY_INFO = {
    "confident_wrong_top3_ranked_item": {
        "short_name": "Confident wrong top-3 ranking",
        "diagnosis": (
            "The model binds products, ranks, and amounts incorrectly in top-3 list answers, "
            "but the generated tokens still look highly confident."
        ),
        "next_action": "Inspect list/rank binding before full100; consider a structured-output prompt variant.",
    },
    "confident_wrong_product_identity": {
        "short_name": "Confident wrong product identity",
        "diagnosis": "Wrong product names or stock codes can be emitted with low uncertainty.",
        "next_action": "Keep product identity spans as a key stress test for any paper-style detector.",
    },
    "confident_wrong_numeric_value": {
        "short_name": "Confident wrong numeric value",
        "diagnosis": "Some incorrect amounts or percentages are produced with confident token scores.",
        "next_action": "Add numeric consistency checks or compare against deterministic evidence where possible.",
    },
    "confident_wrong_other_fact": {
        "short_name": "Confident wrong other fact",
        "diagnosis": "A non-ranking hallucinated fact was not surfaced by simple uncertainty.",
        "next_action": "Review manually before deciding whether this is a systematic failure family.",
    },
    "correct_numeric_flagged_uncertain": {
        "short_name": "Correct numeric fact flagged",
        "diagnosis": (
            "Correct currency or percentage spans are often multi-token strings, so a single low-margin "
            "token can trigger a false alarm."
        ),
        "next_action": "Avoid relying on max-token thresholds alone for report-ready numeric claims.",
    },
    "correct_business_definition_flagged_uncertain": {
        "short_name": "Correct business definition flagged",
        "diagnosis": "Correct gross/net/return definition spans can look uncertain despite being supported.",
        "next_action": "Separate business-definition spans in later error breakdowns.",
    },
    "correct_context_fact_flagged_uncertain": {
        "short_name": "Correct context fact flagged",
        "diagnosis": "Correct countries, months, date ranges, and comparison directions can be over-flagged.",
        "next_action": "Check whether context spans need a different threshold from numeric spans.",
    },
    "correct_ranking_flagged_uncertain": {
        "short_name": "Correct ranking fact flagged",
        "diagnosis": "Some correct rank statements still receive high uncertainty scores.",
        "next_action": "Compare correct and incorrect ranking spans separately before scaling.",
    },
    "correct_other_fact_flagged_uncertain": {
        "short_name": "Correct other fact flagged",
        "diagnosis": "A supported span outside the main false-positive families was over-flagged.",
        "next_action": "Review manually and decide whether to merge into an existing family.",
    },
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def classify(row: dict[str, str]) -> str:
    error_type = row["error_type"]
    fact_type = row["fact_type"]
    question_type = row["question_type"]

    if error_type == "false_negative":
        if question_type == "top3_products_month":
            return "confident_wrong_top3_ranked_item"
        if fact_type in {"product_name", "product_stock_code"}:
            return "confident_wrong_product_identity"
        if fact_type in {"currency_amount", "percentage", "malformed_number"}:
            return "confident_wrong_numeric_value"
        return "confident_wrong_other_fact"

    if error_type == "false_positive":
        if fact_type in {"currency_amount", "percentage"}:
            return "correct_numeric_flagged_uncertain"
        if fact_type == "business_definition":
            return "correct_business_definition_flagged_uncertain"
        if fact_type in {"country", "month", "date_range", "comparison_direction", "product_name", "product_stock_code"}:
            return "correct_context_fact_flagged_uncertain"
        if fact_type == "ranking":
            return "correct_ranking_flagged_uncertain"
        return "correct_other_fact_flagged_uncertain"

    raise ValueError(f"Unknown error_type: {error_type}")


def severity(row: dict[str, str]) -> float:
    margin = float(row["score_minus_threshold"])
    if row["error_type"] == "false_negative":
        return -margin
    return margin


def compact_counter(counter: Counter[str]) -> str:
    return "; ".join(f"{key}:{count}" for key, count in counter.most_common())


def build_analysis() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    review_rows = read_csv(ERROR_REVIEW_PATH)
    source_summary = json.loads(ERROR_SUMMARY_PATH.read_text(encoding="utf-8"))

    for row in review_rows:
        row["error_family"] = classify(row)
        row["severity"] = round(severity(row), 6)

    by_family: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in review_rows:
        by_family[row["error_family"]].append(row)

    family_rows: list[dict[str, Any]] = []
    example_rows: list[dict[str, Any]] = []
    for family in sorted(by_family):
        rows = by_family[family]
        info = FAMILY_INFO[family]
        baselines = Counter(row["baseline"] for row in rows)
        error_types = Counter(row["error_type"] for row in rows)
        fact_types = Counter(row["fact_type"] for row in rows)
        question_types = Counter(row["question_type"] for row in rows)
        unique_annotations = {row["annotation_id"] for row in rows}
        unique_questions = {row["question_id"] for row in rows}

        family_rows.append(
            {
                "error_family": family,
                "short_name": info["short_name"],
                "baseline_error_rows": len(rows),
                "unique_annotation_errors": len(unique_annotations),
                "unique_questions": len(unique_questions),
                "error_types": compact_counter(error_types),
                "baselines": compact_counter(baselines),
                "top_fact_types": compact_counter(fact_types),
                "top_question_types": compact_counter(question_types),
                "diagnosis": info["diagnosis"],
                "next_action": info["next_action"],
            }
        )

        for rank, row in enumerate(sorted(rows, key=severity, reverse=True)[:3], start=1):
            example_rows.append(
                {
                    "error_family": family,
                    "short_name": info["short_name"],
                    "example_rank": rank,
                    "baseline": row["baseline"],
                    "error_type": row["error_type"],
                    "severity": row["severity"],
                    "score": row["score"],
                    "threshold": row["threshold"],
                    "annotation_id": row["annotation_id"],
                    "question_id": row["question_id"],
                    "question_type": row["question_type"],
                    "fact_type": row["fact_type"],
                    "span_text": row["span_text"],
                    "gold_short_answer": row["gold_short_answer"],
                    "annotation_reason": row["annotation_reason"],
                    "generated_excerpt": row["generated_excerpt"],
                }
            )

    family_rows.sort(key=lambda row: (-int(row["baseline_error_rows"]), row["error_family"]))

    false_negative_rows = [row for row in review_rows if row["error_type"] == "false_negative"]
    false_positive_rows = [row for row in review_rows if row["error_type"] == "false_positive"]
    top_families = [
        {
            "error_family": row["error_family"],
            "short_name": row["short_name"],
            "baseline_error_rows": row["baseline_error_rows"],
            "unique_annotation_errors": row["unique_annotation_errors"],
        }
        for row in family_rows[:4]
    ]
    summary = {
        "source_error_review_path": str(ERROR_REVIEW_PATH),
        "source_error_summary_path": str(ERROR_SUMMARY_PATH),
        "analysis_by_family_path": str(ANALYSIS_BY_FAMILY_PATH),
        "analysis_examples_path": str(ANALYSIS_EXAMPLES_PATH),
        "baseline_error_rows": len(review_rows),
        "unique_annotation_errors": len({row["annotation_id"] for row in review_rows}),
        "false_positive_rows": len(false_positive_rows),
        "false_negative_rows": len(false_negative_rows),
        "family_count": len(family_rows),
        "top_families": top_families,
        "source_selected_baselines": source_summary.get("selected_baselines", []),
        "main_findings": [
            "False negatives are concentrated in confident wrong top-3 product ranking spans.",
            "False positives are dominated by correct numeric spans that look uncertain to simple token metrics.",
            "The pilot supports the project thesis: internal uncertainty is useful but not reliable enough by itself for business fact verification.",
        ],
        "recommended_next_step": (
            "Run the 3-question top3 structured prompt pilot before full100, then decide whether "
            "to test all 13 top3 structured prompts or proceed to a stronger detector such as Spilled Energy."
        ),
    }
    return family_rows, example_rows, summary


def main() -> None:
    family_rows, example_rows, summary = build_analysis()
    write_csv(
        ANALYSIS_BY_FAMILY_PATH,
        [
            "error_family",
            "short_name",
            "baseline_error_rows",
            "unique_annotation_errors",
            "unique_questions",
            "error_types",
            "baselines",
            "top_fact_types",
            "top_question_types",
            "diagnosis",
            "next_action",
        ],
        family_rows,
    )
    write_csv(
        ANALYSIS_EXAMPLES_PATH,
        [
            "error_family",
            "short_name",
            "example_rank",
            "baseline",
            "error_type",
            "severity",
            "score",
            "threshold",
            "annotation_id",
            "question_id",
            "question_type",
            "fact_type",
            "span_text",
            "gold_short_answer",
            "annotation_reason",
            "generated_excerpt",
        ],
        example_rows,
    )
    ANALYSIS_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
