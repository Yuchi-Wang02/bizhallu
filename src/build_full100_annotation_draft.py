from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERATION_PATH = PROJECT_ROOT / "outputs" / "qwen_full100_generations.jsonl"
BATCH_PATH = PROJECT_ROOT / "outputs" / "full100_heldout_high_annotation_batch.jsonl"
SEED_ANNOTATION_PATH = PROJECT_ROOT / "data" / "annotations" / "span_annotations_full100_seed.jsonl"
DRAFT_ANNOTATION_PATH = PROJECT_ROOT / "data" / "annotations" / "span_annotations_full100_draft.jsonl"
PREVIEW_PATH = PROJECT_ROOT / "outputs" / "full100_annotation_draft_preview.csv"
REPORT_PATH = PROJECT_ROOT / "outputs" / "full100_annotation_draft_report.json"
ROUND1_REVIEW_PATH = PROJECT_ROOT / "outputs" / "full100_annotation_draft_round1_review.json"
ROUND2_REVIEW_PATH = PROJECT_ROOT / "outputs" / "full100_annotation_draft_round2_review.json"
ROUND3_REVIEW_PATH = PROJECT_ROOT / "outputs" / "full100_annotation_draft_round3_review.json"
ROUND4_REVIEW_PATH = PROJECT_ROOT / "outputs" / "full100_annotation_draft_round4_review.json"

SOURCE_GENERATION_FILE = "outputs/qwen_full100_generations.jsonl"
ANNOTATION_VERSION = "0.4-full100-heldout-high-draft"
ROUND1_QUESTION_IDS = ["q_0020", "q_0033", "q_0034", "q_0053", "q_0059", "q_0063", "q_0077", "q_0093"]
ROUND2_QUESTION_IDS = ["q_0015", "q_0021", "q_0025", "q_0038", "q_0054", "q_0068", "q_0082", "q_0092"]
ROUND3_QUESTION_IDS = ["q_0026", "q_0039", "q_0043", "q_0058", "q_0064", "q_0076"]
ROUND4_QUESTION_IDS = ["q_0044", "q_0049", "q_0069", "q_0081", "q_0086", "q_0087", "q_0097", "q_0098"]
EXPANSION_QUESTION_IDS = ROUND1_QUESTION_IDS + ROUND2_QUESTION_IDS + ROUND3_QUESTION_IDS + ROUND4_QUESTION_IDS


def gold_ref(field: str, fact_type: str, value: Any, display: str, **extra: Any) -> dict[str, Any]:
    ref = {"field": field, "fact_type": fact_type, "gold_value": value, "gold_display_value": display}
    ref.update(extra)
    return ref


EXPANSION_SPECS: dict[str, list[dict[str, Any]]] = {
    "q_0020": [
        {
            "span_text": "March 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round1; top_product_month; correct_context",
        },
        {
            "span_text": "JUMBO BAG STRAWBERRY",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_field": "description",
            "reason_template": "Generated top product name is wrong; gold top product is {gold_display}.",
            "notes": "draft_round1; wrong_top_product",
        },
        {
            "span_text": "85099F",
            "fact_type": "product_stock_code",
            "label": "hallucinated_key_fact",
            "gold_field": "stock_code",
            "reason_template": "Generated top product stock code is wrong; gold stock code is {gold_display}.",
            "notes": "draft_round1; wrong_top_product",
        },
        {
            "span_text": "5853.80 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "merchandise_net_revenue",
            "reason_template": "Generated amount is for the wrong top product; gold top-product revenue is {gold_display}.",
            "notes": "draft_round1; wrong_top_product_amount",
        },
        {
            "span_text": "ranking is second",
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("rank", "ranking", 1, "rank 1: 22423"),
            "reason": "Generated explicit ranking claim is wrong for the selected product; the gold answer requires rank 1 product 22423.",
            "notes": "draft_round1; explicit_extra_ranking_claim",
        },
    ],
    "q_0033": [
        {
            "span_text": "April 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round1; comparison_month; correct_context",
        },
        {
            "span_text": "France",
            "fact_type": "country",
            "label": "hallucinated_key_fact",
            "gold_field": "higher_country",
            "reason_template": "Generated answer treats France as the higher country, but the gold higher country is {gold_display}.",
            "notes": "draft_round1; wrong_higher_country; first_mention",
        },
        {
            "span_text": "generated more net revenue",
            "fact_type": "comparison_direction",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("higher_country", "comparison_direction", "Germany > France", "Germany generated more than France"),
            "reason": "The local predicate assigns the higher-revenue relationship to France, but Germany generated more net revenue.",
            "notes": "draft_round1; direction_mismatch; predicate_follows_france",
        },
        {
            "span_text": "4195.21 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "country_b_net_revenue",
            "reason_template": "Generated France net revenue matches the gold France net revenue of {gold_display}.",
            "notes": "draft_round1; correct_france_amount",
        },
        {
            "span_text": "11963.37 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "country_a_net_revenue",
            "reason_template": "Generated Germany net revenue matches the gold Germany net revenue of {gold_display}.",
            "notes": "draft_round1; correct_germany_amount",
        },
        {
            "span_text": "-1334.40 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "country_b_net_revenue",
            "reason_template": "Generated incorrectly states France net revenue as cancellation revenue; gold France net revenue is {gold_display}.",
            "notes": "draft_round1; field_confusion; cancellation_as_net_revenue",
        },
        {
            "span_text": "-352.17 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "country_a_net_revenue",
            "reason_template": "Generated incorrectly states Germany net revenue as cancellation revenue; gold Germany net revenue is {gold_display}.",
            "notes": "draft_round1; field_confusion; cancellation_as_net_revenue",
        },
        {
            "span_text": "-1334.40 GBP",
            "occurrence": 2,
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "revenue_delta",
            "reason_template": "Generated repeats the cancellation amount as the comparison delta; gold difference is {gold_display}.",
            "notes": "draft_round1; wrong_difference; repeated_distinct_claim",
        },
    ],
    "q_0034": [
        {
            "span_text": "France",
            "fact_type": "country",
            "label": "hallucinated_key_fact",
            "gold_field": "higher_country",
            "reason_template": "Generated answer treats France as the higher country, but the gold higher country is {gold_display}.",
            "notes": "draft_round1; wrong_higher_country; first_mention",
        },
        {
            "span_text": "generated more net revenue",
            "fact_type": "comparison_direction",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("higher_country", "comparison_direction", "Germany > France", "Germany generated more than France"),
            "reason": "The local predicate assigns the higher-revenue relationship to France, but Germany generated more net revenue.",
            "notes": "draft_round1; direction_mismatch; predicate_follows_france",
        },
        {
            "span_text": "17518.68 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "country_b_net_revenue",
            "reason_template": "Generated France net revenue matches the gold France net revenue of {gold_display}.",
            "notes": "draft_round1; correct_france_amount",
        },
        {
            "span_text": "25554.85 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "country_a_net_revenue",
            "reason_template": "Generated Germany net revenue matches the gold Germany net revenue of {gold_display}.",
            "notes": "draft_round1; correct_germany_amount",
        },
        {
            "span_text": "-87.80 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "revenue_delta",
            "reason_template": "Generated uses France cancellation revenue as the difference; gold difference is {gold_display}.",
            "notes": "draft_round1; wrong_difference; field_confusion",
        },
        {
            "span_text": "The Netherlands and United Kingdom have the lowest net revenues",
            "fact_type": "unsupported_business_claim",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("extra_claim", "unsupported_business_claim", "contradicted_by_evidence", "Netherlands and United Kingdom are not the lowest in the evidence table"),
            "reason": "The extra business claim is contradicted by the evidence table.",
            "notes": "draft_round1; extra_business_claim; contradicted_by_evidence",
        },
    ],
    "q_0053": [
        {
            "span_text": "April 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "previous_month",
            "reason_template": "Generated previous month matches the gold previous month.",
            "notes": "draft_round1; monthly_change; correct_context",
        },
        {
            "span_text": "492,367.84 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "previous_net_revenue",
            "reason_template": "Generated previous-month net revenue matches {gold_display}.",
            "notes": "draft_round1; correct_previous_revenue",
        },
        {
            "span_text": "May 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "current_month",
            "reason_template": "Generated current month matches the gold current month.",
            "notes": "draft_round1; monthly_change; correct_context",
        },
        {
            "span_text": "722,094.10 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "current_net_revenue",
            "reason_template": "Generated current-month net revenue matches {gold_display}.",
            "notes": "draft_round1; correct_current_revenue",
        },
        {
            "span_text": "229,726.26 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "absolute_change",
            "reason_template": "Generated absolute change matches {gold_display}.",
            "notes": "draft_round1; correct_absolute_change",
        },
        {
            "span_text": "48.97%",
            "fact_type": "percentage",
            "label": "hallucinated_key_fact",
            "gold_field": "percent_change",
            "reason_template": "Generated percentage change is outside tolerance; gold percentage change is {gold_display}.",
            "notes": "draft_round1; wrong_percent_change",
        },
    ],
    "q_0059": [
        {
            "span_text": "November 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "current_month",
            "reason_template": "Generated current month matches the gold current month.",
            "notes": "draft_round1; monthly_change; correct_context",
        },
        {
            "span_text": "145,614.50 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "current_net_revenue",
            "reason_template": "Generated current-month net revenue is off by about a factor of ten; gold value is {gold_display}.",
            "notes": "draft_round1; wrong_current_revenue",
        },
        {
            "span_text": "29.75%",
            "fact_type": "percentage",
            "label": "hallucinated_key_fact",
            "gold_field": "percent_change",
            "reason_template": "Generated percentage change is outside tolerance; gold percentage change is {gold_display}.",
            "notes": "draft_round1; wrong_percent_change",
        },
        {
            "span_text": "increase",
            "fact_type": "comparison_direction",
            "label": "correct_key_fact",
            "gold_field": "direction",
            "reason_template": "Generated direction matches the gold direction.",
            "notes": "draft_round1; correct_direction",
        },
        {
            "span_text": "October 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "previous_month",
            "reason_template": "Generated previous month matches the gold previous month.",
            "notes": "draft_round1; monthly_change; correct_context",
        },
        {
            "span_text": "106,936.83 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "previous_net_revenue",
            "reason_template": "Generated previous-month net revenue is off by about a factor of ten; gold value is {gold_display}.",
            "notes": "draft_round1; wrong_previous_revenue",
        },
        {
            "span_text": "38,677.67 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "absolute_change",
            "reason_template": "Generated absolute change is off by about a factor of ten; gold value is {gold_display}.",
            "notes": "draft_round1; wrong_absolute_change",
        },
    ],
    "q_0063": [
        {
            "span_text": "March 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round1; top3_products; correct_context",
        },
        {
            "span_text": "1.",
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[0].rank_item", "ranking", "1. 22423", "1. 22423 / REGENCY CAKESTAND 3 TIER"),
            "reason": "The rank-1 marker is tied to the wrong generated product.",
            "notes": "draft_round1; list_rank_marker; wrong_rank1_item",
        },
        {
            "span_text": "JUMBO BAG STRAWBERRY",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[0].description", "product_name", "REGENCY CAKESTAND 3 TIER", "REGENCY CAKESTAND 3 TIER"),
            "reason": "Gold rank-1 product is REGENCY CAKESTAND 3 TIER, not JUMBO BAG STRAWBERRY.",
            "notes": "draft_round1; wrong_rank1_product",
        },
        {
            "span_text": "85099F",
            "fact_type": "product_stock_code",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[0].stock_code", "product_stock_code", "22423", "22423"),
            "reason": "Gold rank-1 stock code is 22423, not 85099F.",
            "notes": "draft_round1; wrong_rank1_stock_code",
        },
        {
            "span_text": "GBP 5853.80",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[0].merchandise_net_revenue", "currency_amount", 16817.85, "GBP 16,817.85"),
            "reason": "Gold rank-1 revenue is GBP 16,817.85, not GBP 5,853.80.",
            "notes": "draft_round1; wrong_rank1_amount",
        },
        {
            "span_text": "2.",
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[1].rank_item", "ranking", "2. 85099B", "2. 85099B / JUMBO BAG RED RETROSPOT"),
            "reason": "The rank-2 marker is tied to the wrong generated product.",
            "notes": "draft_round1; list_rank_marker; wrong_rank2_item",
        },
        {
            "span_text": "JUMBO BAG PINK POLKADOT",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[1].description", "product_name", "JUMBO BAG RED RETROSPOT", "JUMBO BAG RED RETROSPOT"),
            "reason": "Gold rank-2 product is JUMBO BAG RED RETROSPOT, not JUMBO BAG PINK POLKADOT.",
            "notes": "draft_round1; wrong_rank2_product",
        },
        {
            "span_text": "22386",
            "fact_type": "product_stock_code",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[1].stock_code", "product_stock_code", "85099B", "85099B"),
            "reason": "Gold rank-2 stock code is 85099B, not 22386.",
            "notes": "draft_round1; wrong_rank2_stock_code",
        },
        {
            "span_text": "GBP 5079.29",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[1].merchandise_net_revenue", "currency_amount", 10116.43, "GBP 10,116.43"),
            "reason": "Gold rank-2 revenue is GBP 10,116.43, not GBP 5,079.29.",
            "notes": "draft_round1; wrong_rank2_amount",
        },
        {
            "span_text": "3.",
            "occurrence": 2,
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[2].rank_item", "ranking", "3. 47566", "3. 47566 / PARTY BUNTING"),
            "reason": "The rank-3 marker is tied to the wrong generated product.",
            "notes": "draft_round1; list_rank_marker; wrong_rank3_item",
        },
        {
            "span_text": "VINTAGE UNION JACK BUNTING",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[2].description", "product_name", "PARTY BUNTING", "PARTY BUNTING"),
            "reason": "Gold rank-3 product is PARTY BUNTING, not VINTAGE UNION JACK BUNTING.",
            "notes": "draft_round1; wrong_rank3_product",
        },
        {
            "span_text": "21621",
            "fact_type": "product_stock_code",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[2].stock_code", "product_stock_code", "47566", "47566"),
            "reason": "Gold rank-3 stock code is 47566, not 21621.",
            "notes": "draft_round1; wrong_rank3_stock_code",
        },
        {
            "span_text": "GBP 5214.33",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[2].merchandise_net_revenue", "currency_amount", 9098.27, "GBP 9,098.27"),
            "reason": "Gold rank-3 revenue is GBP 9,098.27, not GBP 5,214.33.",
            "notes": "draft_round1; wrong_rank3_amount",
        },
        {
            "span_text": "The rankings are based on the provided net_revenue_gbp values",
            "fact_type": "unsupported_business_claim",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products", "unsupported_business_claim", "1. 22423 > 2. 85099B > 3. 47566", "1. 22423 > 2. 85099B > 3. 47566"),
            "reason": "The conclusion is contradicted because the listed products are not the top 3 by merchandise net revenue.",
            "notes": "draft_round1; contradicted_business_conclusion",
        },
    ],
    "q_0077": [
        {
            "span_text": "May 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round1; product_share; correct_context",
        },
        {
            "span_text": "WHITE HANGING HEART T-LIGHT HOLDER",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[0].description", "product_name", "PARTY BUNTING", "PARTY BUNTING"),
            "reason": "Generated top product is wrong; gold top product is PARTY BUNTING.",
            "notes": "draft_round1; wrong_top_product",
        },
        {
            "span_text": "11.78%",
            "fact_type": "percentage",
            "label": "hallucinated_key_fact",
            "gold_field": "share_percent",
            "reason_template": "Generated share percentage is outside tolerance; gold share is {gold_display}.",
            "notes": "draft_round1; wrong_share_percent; first_mention",
        },
        {
            "span_text": "GBP 11,172.17",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "numerator_merchandise_net_revenue",
            "reason_template": "Generated numerator is for the wrong top product; gold numerator is {gold_display}.",
            "notes": "draft_round1; wrong_share_numerator",
        },
        {
            "span_text": "GBP 731,051.91",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "total_merchandise_net_revenue",
            "reason_template": "Generated denominator matches the gold total merchandise net revenue of {gold_display}.",
            "notes": "draft_round1; correct_denominator",
        },
        {
            "span_text": "11.78%",
            "occurrence": 2,
            "fact_type": "percentage",
            "label": "hallucinated_key_fact",
            "gold_field": "share_percent",
            "reason_template": "Generated repeats the wrong share percentage; gold share is {gold_display}.",
            "notes": "draft_round1; wrong_share_percent; repeated_result_claim",
        },
    ],
    "q_0093": [
        {
            "span_text": "April 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round1; return_impact; correct_context",
        },
        {
            "span_text": "\u00a344,600.65",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "reduction_amount",
            "reason_template": "Generated reduction amount matches {gold_display}; the pound symbol is treated as GBP-compatible in this context.",
            "notes": "draft_round1; correct_reduction_amount; pound_symbol_for_gbp",
        },
        {
            "span_text": "\u00a344,600.65",
            "occurrence": 2,
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "net_revenue",
            "reason_template": "Generated final net revenue repeats the reduction amount; gold net revenue is {gold_display}.",
            "notes": "draft_round1; wrong_final_net_revenue; repeated_distinct_claim",
        },
    ],
    "q_0015": [
        {
            "span_text": "September 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round2; top_country_month; correct_context",
        },
        {
            "span_text": "United Kingdom",
            "fact_type": "country",
            "label": "correct_key_fact",
            "gold_field": "country",
            "reason_template": "Generated top country matches the gold top country.",
            "notes": "draft_round2; correct_top_country; first_mention",
        },
        {
            "span_text": "\u00a38,601,043.66",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "net_revenue",
            "reason_template": "Generated amount is off by a factor of ten; gold net revenue is {gold_display}.",
            "notes": "draft_round2; wrong_top_country_amount; pound_symbol_for_gbp",
        },
    ],
    "q_0021": [
        {
            "span_text": "April 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round2; top_product_month; correct_context",
        },
        {
            "span_text": "WOODEN UNION JACK BUNTING",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_field": "description",
            "reason_template": "Generated top product name is wrong; gold top product is {gold_display}.",
            "notes": "draft_round2; wrong_top_product",
        },
        {
            "span_text": "GBP 4173.18",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "merchandise_net_revenue",
            "reason_template": "Generated amount is for the wrong product; gold top-product revenue is {gold_display}.",
            "notes": "draft_round2; wrong_top_product_amount",
        },
        {
            "span_text": "ranked 2nd",
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("rank", "ranking", 1, "rank 1: 22423"),
            "reason": "Generated explicit ranking claim is wrong for the selected product; the gold answer requires rank 1 product 22423.",
            "notes": "draft_round2; explicit_extra_ranking_claim",
        },
        {
            "span_text": "1.3% increase",
            "fact_type": "percentage",
            "label": "unsupported_claim",
            "gold_reference": gold_ref("extra_claim", "percentage", "not_in_prompt_evidence", "no previous-month product-change evidence supplied"),
            "reason": "The prompt evidence does not include previous-month product revenue needed to verify this increase claim.",
            "notes": "draft_round2; unsupported_extra_product_change_claim",
        },
    ],
    "q_0025": [
        {
            "span_text": "August 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round2; top_product_month; correct_context",
        },
        {
            "span_text": "JUMBO BAG APPLES",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_field": "description",
            "reason_template": "Generated top product name is wrong; gold top product is {gold_display}.",
            "notes": "draft_round2; wrong_top_product; first_mention",
        },
        {
            "span_text": "85099B",
            "fact_type": "product_stock_code",
            "label": "correct_key_fact",
            "gold_field": "stock_code",
            "reason_template": "Generated stock code matches the gold top-product stock code despite an inconsistent product name.",
            "notes": "draft_round2; correct_stock_code_in_inconsistent_product_bundle",
        },
        {
            "span_text": "JUMBO BAG APPLES",
            "occurrence": 2,
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_field": "description",
            "reason_template": "Generated repeats the wrong product name; gold top product is {gold_display}.",
            "notes": "draft_round2; wrong_top_product; repeated_product_name_field",
        },
        {
            "span_text": "GBP 6,204.89",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "merchandise_net_revenue",
            "reason_template": "Generated amount is for the wrong product; gold top-product revenue is {gold_display}.",
            "notes": "draft_round2; wrong_top_product_amount",
        },
        {
            "span_text": "ranked 2nd",
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("rank", "ranking", 1, "rank 1: 85099B"),
            "reason": "Generated explicit ranking claim contradicts the gold rank-1 top product.",
            "notes": "draft_round2; explicit_extra_ranking_claim",
        },
    ],
    "q_0038": [
        {
            "span_text": "September 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round2; comparison_month; correct_context",
        },
        {
            "span_text": "Germany",
            "fact_type": "country",
            "label": "hallucinated_key_fact",
            "gold_field": "higher_country",
            "reason_template": "Generated answer treats Germany as the higher country, but the gold higher country is {gold_display}.",
            "notes": "draft_round2; wrong_higher_country; first_mention",
        },
        {
            "span_text": "generated more net revenue",
            "fact_type": "comparison_direction",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("higher_country", "comparison_direction", "France > Germany", "France generated more than Germany"),
            "reason": "The local predicate assigns the higher-revenue relationship to Germany, but France generated more net revenue.",
            "notes": "draft_round2; direction_mismatch; predicate_follows_germany",
        },
        {
            "span_text": "17708.56 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "country_a_net_revenue",
            "reason_template": "Generated Germany net revenue matches the gold Germany net revenue of {gold_display}.",
            "notes": "draft_round2; correct_germany_amount",
        },
        {
            "span_text": "23198.87 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "country_b_net_revenue",
            "reason_template": "Generated France net revenue matches the gold France net revenue of {gold_display}.",
            "notes": "draft_round2; correct_france_amount",
        },
        {
            "span_text": "5,899.99 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "revenue_delta",
            "reason_template": "Generated comparison delta is outside tolerance; gold difference is {gold_display}.",
            "notes": "draft_round2; wrong_difference",
        },
    ],
    "q_0054": [
        {
            "span_text": "May 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "previous_month",
            "reason_template": "Generated previous month matches the gold previous month.",
            "notes": "draft_round2; monthly_change; correct_context",
        },
        {
            "span_text": "June 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "current_month",
            "reason_template": "Generated current month matches the gold current month.",
            "notes": "draft_round2; monthly_change; correct_context",
        },
        {
            "span_text": "decreased",
            "fact_type": "comparison_direction",
            "label": "correct_key_fact",
            "gold_field": "direction",
            "reason_template": "Generated direction matches the gold direction.",
            "notes": "draft_round2; correct_direction",
        },
        {
            "span_text": "GBP 3,121.37",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "absolute_change",
            "reason_template": "Generated absolute change is off by about a factor of ten; gold value is {gold_display}.",
            "notes": "draft_round2; wrong_absolute_change; first_result_claim",
        },
        {
            "span_text": "-4.14%",
            "fact_type": "percentage",
            "label": "correct_key_fact",
            "gold_field": "percent_change",
            "reason_template": "Generated percentage change is within tolerance of {gold_display}.",
            "notes": "draft_round2; correct_percent_change; first_result_claim",
        },
        {
            "span_text": "-GBP 3,121.37",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "absolute_change",
            "reason_template": "Generated repeats the wrong absolute change; gold value is {gold_display}.",
            "notes": "draft_round2; wrong_absolute_change; repeated_result_claim",
        },
        {
            "span_text": "-4.14%",
            "occurrence": 2,
            "fact_type": "percentage",
            "label": "correct_key_fact",
            "gold_field": "percent_change",
            "reason_template": "Generated repeats a percentage change within tolerance of {gold_display}.",
            "notes": "draft_round2; correct_percent_change; repeated_result_claim",
        },
    ],
    "q_0068": [
        {
            "span_text": "August 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round2; top3_products; correct_context",
        },
        {
            "span_text": "1.",
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[0].rank_item", "ranking", "1. 85099B", "1. 85099B / JUMBO BAG RED RETROSPOT"),
            "reason": "The rank-1 marker is tied to the wrong generated product.",
            "notes": "draft_round2; list_rank_marker; wrong_rank1_item",
        },
        {
            "span_text": "JUMBO BAG PINK POLKADOT",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[0].description", "product_name", "JUMBO BAG RED RETROSPOT", "JUMBO BAG RED RETROSPOT"),
            "reason": "Gold rank-1 product is JUMBO BAG RED RETROSPOT, not JUMBO BAG PINK POLKADOT.",
            "notes": "draft_round2; wrong_rank1_product",
        },
        {
            "span_text": "GBP 4,728.73",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[0].merchandise_net_revenue", "currency_amount", 10441.77, "GBP 10,441.77"),
            "reason": "Gold rank-1 revenue is GBP 10,441.77, not GBP 4,728.73.",
            "notes": "draft_round2; wrong_rank1_amount",
        },
        {
            "span_text": "2.",
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[1].rank_item", "ranking", "2. 84879", "2. 84879 / ASSORTED COLOUR BIRD ORNAMENT"),
            "reason": "The rank-2 marker is tied to the wrong generated product.",
            "notes": "draft_round2; list_rank_marker; wrong_rank2_item",
        },
        {
            "span_text": "JUMBO BAG RED RETROSPOT",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[1].description", "product_name", "ASSORTED COLOUR BIRD ORNAMENT", "ASSORTED COLOUR BIRD ORNAMENT"),
            "reason": "JUMBO BAG RED RETROSPOT is the gold rank-1 product, but the generated answer places it at rank 2.",
            "notes": "draft_round2; correct_product_used_in_wrong_rank",
        },
        {
            "span_text": "GBP 10,441.77",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[1].merchandise_net_revenue", "currency_amount", 9867.04, "GBP 9,867.04"),
            "reason": "GBP 10,441.77 is the gold rank-1 revenue, but the generated answer uses it for rank 2.",
            "notes": "draft_round2; correct_amount_used_in_wrong_rank",
        },
        {
            "span_text": "3.",
            "occurrence": 2,
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[2].rank_item", "ranking", "3. 47566", "3. 47566 / PARTY BUNTING"),
            "reason": "The rank-3 marker is tied to the wrong generated product.",
            "notes": "draft_round2; list_rank_marker; wrong_rank3_item",
        },
        {
            "span_text": "SPOTTY BUNTING",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[2].description", "product_name", "PARTY BUNTING", "PARTY BUNTING"),
            "reason": "Gold rank-3 product is PARTY BUNTING, not SPOTTY BUNTING.",
            "notes": "draft_round2; wrong_rank3_product",
        },
        {
            "span_text": "GBP 7,864.43",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[2].merchandise_net_revenue", "currency_amount", 9655.25, "GBP 9,655.25"),
            "reason": "Gold rank-3 revenue is GBP 9,655.25, not GBP 7,864.43.",
            "notes": "draft_round2; wrong_rank3_amount",
        },
    ],
    "q_0082": [
        {
            "span_text": "October 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round2; product_share; correct_context",
        },
        {
            "span_text": "JUMBO BAG RED RETROSPOT",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[0].description", "product_name", "REGENCY CAKESTAND 3 TIER", "REGENCY CAKESTAND 3 TIER"),
            "reason": "Generated top product is wrong; gold top product is REGENCY CAKESTAND 3 TIER.",
            "notes": "draft_round2; wrong_top_product",
        },
        {
            "span_text": "50.55%",
            "fact_type": "percentage",
            "label": "hallucinated_key_fact",
            "gold_field": "share_percent",
            "reason_template": "Generated share percentage is outside tolerance; gold share is {gold_display}.",
            "notes": "draft_round2; wrong_share_percent",
        },
        {
            "span_text": "GBP 9409.95",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "numerator_merchandise_net_revenue",
            "reason_template": "Generated numerator is for the wrong top product; gold numerator is {gold_display}.",
            "notes": "draft_round2; wrong_share_numerator",
        },
    ],
    "q_0092": [
        {
            "span_text": "March 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round2; return_impact; correct_context",
        },
        {
            "span_text": "GBP 342,012.88",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "reduction_amount",
            "reason_template": "Generated reduction amount is off by a factor of ten; gold reduction amount is {gold_display}.",
            "notes": "draft_round2; wrong_reduction_amount",
        },
        {
            "span_text": "GBP 682,013.98",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "net_revenue",
            "reason_template": "Generated final net revenue matches {gold_display}.",
            "notes": "draft_round2; correct_final_net_revenue",
        },
    ],
    "q_0026": [
        {
            "span_text": "September 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round3; top_product_month; correct_context",
        },
        {
            "span_text": "JUMBO BAG RED RETROSPOT",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_field": "description",
            "reason_template": "Generated top product name is wrong; gold top product is {gold_display}.",
            "notes": "draft_round3; wrong_top_product",
        },
        {
            "span_text": "85099B",
            "fact_type": "product_stock_code",
            "label": "hallucinated_key_fact",
            "gold_field": "stock_code",
            "reason_template": "Generated top product stock code is wrong; gold stock code is {gold_display}.",
            "notes": "draft_round3; wrong_top_product",
        },
        {
            "span_text": "GBP 8630.45",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "merchandise_net_revenue",
            "reason_template": "Generated top-product net revenue is for the wrong product; gold value is {gold_display}.",
            "notes": "draft_round3; wrong_top_product_amount; first_result_claim",
        },
        {
            "span_text": "GBP 8880.17",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref(
                "top_product_gross_positive_revenue",
                "currency_amount",
                9981.41,
                "GBP 9,981.41",
                tolerance={"absolute": 1.0, "relative_percent": 0.5},
            ),
            "reason": "Generated gross-positive revenue is for the wrong product; gold top-product gross-positive revenue is GBP 9,981.41.",
            "notes": "draft_round3; wrong_top_product_supporting_amount; gross_positive_revenue",
        },
        {
            "span_text": "-249.72",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref(
                "top_product_cancellation_return_revenue",
                "currency_amount",
                -9.90,
                "GBP -9.90",
                tolerance={"absolute": 1.0, "relative_percent": 0.5},
            ),
            "reason": "Generated cancellation-return revenue is for the wrong product; gold top-product cancellation-return revenue is GBP -9.90.",
            "notes": "draft_round3; wrong_top_product_supporting_amount; cancellation_return_revenue",
        },
        {
            "span_text": "GBP 8630.45",
            "occurrence": 2,
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "merchandise_net_revenue",
            "reason_template": "Generated repeats the wrong top-product net revenue; gold value is {gold_display}.",
            "notes": "draft_round3; wrong_top_product_amount; repeated_result_claim",
        },
    ],
    "q_0039": [
        {
            "span_text": "France",
            "fact_type": "country",
            "label": "hallucinated_key_fact",
            "gold_field": "higher_country",
            "reason_template": "Generated answer treats France as the higher country, but the gold higher country is {gold_display}.",
            "notes": "draft_round3; wrong_higher_country; first_mention",
        },
        {
            "span_text": "generated more net revenue",
            "fact_type": "comparison_direction",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("higher_country", "comparison_direction", "Germany > France", "Germany generated more than France"),
            "reason": "The local predicate assigns the higher-revenue relationship to France, but Germany generated more net revenue.",
            "notes": "draft_round3; direction_mismatch; predicate_follows_france",
        },
        {
            "span_text": "25,017.64 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "country_b_net_revenue",
            "reason_template": "Generated France net revenue matches the gold France net revenue of {gold_display}.",
            "notes": "draft_round3; correct_france_amount",
        },
        {
            "span_text": "30,604.27 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "country_a_net_revenue",
            "reason_template": "Generated Germany net revenue matches the gold Germany net revenue of {gold_display}.",
            "notes": "draft_round3; correct_germany_amount",
        },
        {
            "span_text": "-8,453.41 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "country_b_net_revenue",
            "reason_template": "Generated states France cancellation-return revenue as net revenue; gold France net revenue is {gold_display}.",
            "notes": "draft_round3; field_confusion; cancellation_as_net_revenue",
        },
        {
            "span_text": "5,586.83 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "revenue_delta",
            "reason_template": "Generated comparison difference is within tolerance of {gold_display}.",
            "notes": "draft_round3; correct_difference",
        },
    ],
    "q_0043": [
        {
            "span_text": "March 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round3; comparison_month; correct_context",
        },
        {
            "span_text": "Netherlands",
            "fact_type": "country",
            "label": "correct_key_fact",
            "gold_field": "higher_country",
            "reason_template": "Generated higher country matches the gold higher country.",
            "notes": "draft_round3; correct_higher_country; first_mention",
        },
        {
            "span_text": "generated more net revenue",
            "fact_type": "comparison_direction",
            "label": "correct_key_fact",
            "gold_reference": gold_ref("higher_country", "comparison_direction", "Netherlands > EIRE", "Netherlands generated more than EIRE"),
            "reason": "Generated comparison direction correctly assigns higher net revenue to Netherlands.",
            "notes": "draft_round3; correct_direction",
        },
        {
            "span_text": "22416.49 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "revenue_delta",
            "reason_template": "Generated uses Netherlands net revenue as the difference; gold difference is {gold_display}.",
            "notes": "draft_round3; wrong_difference; net_revenue_as_delta",
        },
        {
            "span_text": "EIRE",
            "fact_type": "country",
            "label": "correct_key_fact",
            "gold_field": "lower_country",
            "reason_template": "Generated comparison entity matches the gold lower country.",
            "notes": "draft_round3; correct_lower_country",
        },
    ],
    "q_0058": [
        {
            "span_text": "September 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "previous_month",
            "reason_template": "Generated previous month matches the gold previous month.",
            "notes": "draft_round3; monthly_change; correct_context",
        },
        {
            "span_text": "\u00a31,017,596.68",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "previous_net_revenue",
            "reason_template": "Generated previous-month net revenue matches {gold_display}.",
            "notes": "draft_round3; correct_previous_revenue; pound_symbol_for_gbp",
        },
        {
            "span_text": "October 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "current_month",
            "reason_template": "Generated current month matches the gold current month.",
            "notes": "draft_round3; monthly_change; correct_context",
        },
        {
            "span_text": "\u00a31,069,368.23",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "current_net_revenue",
            "reason_template": "Generated current-month net revenue matches {gold_display}.",
            "notes": "draft_round3; correct_current_revenue; pound_symbol_for_gbp",
        },
        {
            "span_text": "\u00a351,771.55",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "absolute_change",
            "reason_template": "Generated absolute change matches {gold_display}.",
            "notes": "draft_round3; correct_absolute_change; pound_symbol_for_gbp",
        },
        {
            "span_text": "5.03%",
            "fact_type": "percentage",
            "label": "correct_key_fact",
            "gold_field": "percent_change",
            "reason_template": "Generated percentage change is within tolerance of {gold_display}.",
            "notes": "draft_round3; correct_percent_change",
        },
    ],
    "q_0064": [
        {
            "span_text": "April 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round3; top3_products; correct_context",
        },
        {
            "span_text": "1.",
            "fact_type": "ranking",
            "label": "correct_key_fact",
            "gold_reference": gold_ref("top_products[0].rank_item", "ranking", "1. 22423", "1. 22423 / REGENCY CAKESTAND 3 TIER"),
            "reason": "The rank-1 marker is tied to the correct rank-1 product.",
            "notes": "draft_round3; list_rank_marker; correct_rank1_item",
        },
        {
            "span_text": "REGENCY CAKESTAND 3 TIER",
            "fact_type": "product_name",
            "label": "correct_key_fact",
            "gold_reference": gold_ref("top_products[0].description", "product_name", "REGENCY CAKESTAND 3 TIER", "REGENCY CAKESTAND 3 TIER"),
            "reason": "Generated rank-1 product matches the gold rank-1 product.",
            "notes": "draft_round3; correct_rank1_product",
        },
        {
            "span_text": "GBP 14,280.90",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_reference": gold_ref("top_products[0].merchandise_net_revenue", "currency_amount", 14280.90, "GBP 14,280.90"),
            "reason": "Generated rank-1 revenue matches the gold rank-1 revenue.",
            "notes": "draft_round3; correct_rank1_amount",
        },
        {
            "span_text": "2.",
            "fact_type": "ranking",
            "label": "correct_key_fact",
            "gold_reference": gold_ref("top_products[1].rank_item", "ranking", "2. 47566", "2. 47566 / PARTY BUNTING"),
            "reason": "The rank-2 marker is tied to the correct rank-2 product.",
            "notes": "draft_round3; list_rank_marker; correct_rank2_item",
        },
        {
            "span_text": "PARTY BUNTING",
            "fact_type": "product_name",
            "label": "correct_key_fact",
            "gold_reference": gold_ref("top_products[1].description", "product_name", "PARTY BUNTING", "PARTY BUNTING"),
            "reason": "Generated rank-2 product matches the gold rank-2 product.",
            "notes": "draft_round3; correct_rank2_product",
        },
        {
            "span_text": "GBP 10,323.87",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_reference": gold_ref("top_products[1].merchandise_net_revenue", "currency_amount", 10323.87, "GBP 10,323.87"),
            "reason": "Generated rank-2 revenue matches the gold rank-2 revenue.",
            "notes": "draft_round3; correct_rank2_amount",
        },
        {
            "span_text": "3.",
            "occurrence": 2,
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[2].rank_item", "ranking", "3. 22084", "3. 22084 / PAPER CHAIN KIT EMPIRE"),
            "reason": "The rank-3 marker is tied to the wrong generated product.",
            "notes": "draft_round3; list_rank_marker; wrong_rank3_item",
        },
        {
            "span_text": "WOODEN UNION JACK BUNTING",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[2].description", "product_name", "PAPER CHAIN KIT EMPIRE", "PAPER CHAIN KIT EMPIRE"),
            "reason": "Gold rank-3 product is PAPER CHAIN KIT EMPIRE, not WOODEN UNION JACK BUNTING.",
            "notes": "draft_round3; wrong_rank3_product",
        },
        {
            "span_text": "GBP 4,173.18",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[2].merchandise_net_revenue", "currency_amount", 6619.51, "GBP 6,619.51"),
            "reason": "Gold rank-3 revenue is GBP 6,619.51, not GBP 4,173.18.",
            "notes": "draft_round3; wrong_rank3_amount",
        },
    ],
    "q_0076": [
        {
            "span_text": "April 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round3; product_share; correct_context",
        },
        {
            "span_text": "PAPER BUNTING WHITE LACE",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[0].description", "product_name", "REGENCY CAKESTAND 3 TIER", "REGENCY CAKESTAND 3 TIER"),
            "reason": "Generated top product is wrong; gold top product is REGENCY CAKESTAND 3 TIER.",
            "notes": "draft_round3; wrong_top_product",
        },
        {
            "span_text": "3512.24 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "numerator_merchandise_net_revenue",
            "reason_template": "Generated share numerator is for the wrong product; gold numerator is {gold_display}.",
            "notes": "draft_round3; wrong_share_numerator",
        },
        {
            "span_text": "3579.69 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref(
                "top_product_gross_positive_revenue",
                "currency_amount",
                14812.95,
                "GBP 14,812.95",
                tolerance={"absolute": 1.0, "relative_percent": 0.5},
            ),
            "reason": "Generated gross-positive revenue is for the wrong product; gold top-product gross-positive revenue is GBP 14,812.95.",
            "notes": "draft_round3; wrong_top_product_supporting_amount; gross_positive_revenue",
        },
        {
            "span_text": "-67.45 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref(
                "top_product_cancellation_return_revenue",
                "currency_amount",
                -532.05,
                "GBP -532.05",
                tolerance={"absolute": 1.0, "relative_percent": 0.5},
            ),
            "reason": "Generated cancellation-return revenue is for the wrong product; gold top-product cancellation-return revenue is GBP -532.05.",
            "notes": "draft_round3; wrong_top_product_supporting_amount; cancellation_return_revenue",
        },
        {
            "span_text": "3.29%",
            "fact_type": "percentage",
            "label": "hallucinated_key_fact",
            "gold_field": "share_percent",
            "reason_template": "Generated percentage is attached to the wrong top product and wrong numerator; gold top-product share is {gold_display}.",
            "notes": "draft_round3; wrong_share_percent; wrong_entity_binding",
        },
    ],
    "q_0044": [
        {
            "span_text": "April 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round4; comparison_month; correct_context",
        },
        {
            "span_text": "Netherlands",
            "fact_type": "country",
            "label": "hallucinated_key_fact",
            "gold_field": "higher_country",
            "reason_template": "Generated answer treats Netherlands as the higher country, but the gold higher country is {gold_display}.",
            "notes": "draft_round4; wrong_higher_country; first_mention",
        },
        {
            "span_text": "generated more net revenue",
            "fact_type": "comparison_direction",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("higher_country", "comparison_direction", "EIRE > Netherlands", "EIRE generated more than Netherlands"),
            "reason": "The local predicate assigns the higher-revenue relationship to Netherlands, but EIRE generated more net revenue.",
            "notes": "draft_round4; direction_mismatch; predicate_follows_netherlands",
        },
        {
            "span_text": "2976.56 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "country_a_net_revenue",
            "reason_template": "Generated Netherlands net revenue matches {gold_display}.",
            "notes": "draft_round4; correct_netherlands_amount",
        },
        {
            "span_text": "7570.50 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "country_b_net_revenue",
            "reason_template": "Generated EIRE net revenue matches {gold_display}.",
            "notes": "draft_round4; correct_eire_amount",
        },
        {
            "span_text": "-4593.94 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "revenue_delta",
            "reason_template": "Generated difference has the wrong sign and country binding; gold absolute difference is {gold_display}.",
            "notes": "draft_round4; wrong_difference_sign; wrong_higher_country_binding",
        },
    ],
    "q_0049": [
        {
            "span_text": "September 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round4; comparison_month; correct_context",
        },
        {
            "span_text": "Netherlands",
            "fact_type": "country",
            "label": "hallucinated_key_fact",
            "gold_field": "higher_country",
            "reason_template": "Generated answer treats Netherlands as the higher country, but the gold higher country is {gold_display}.",
            "notes": "draft_round4; wrong_higher_country; first_mention",
        },
        {
            "span_text": "generated more net revenue",
            "fact_type": "comparison_direction",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("higher_country", "comparison_direction", "EIRE > Netherlands", "EIRE generated more than Netherlands"),
            "reason": "The local predicate assigns the higher-revenue relationship to Netherlands, but EIRE generated more net revenue.",
            "notes": "draft_round4; direction_mismatch; predicate_follows_netherlands",
        },
        {
            "span_text": "26,937.26 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "country_a_net_revenue",
            "reason_template": "Generated Netherlands net revenue matches {gold_display}.",
            "notes": "draft_round4; correct_netherlands_amount",
        },
        {
            "span_text": "42,476.20 GBP",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "country_b_net_revenue",
            "reason_template": "Generated EIRE net revenue matches {gold_display}.",
            "notes": "draft_round4; correct_eire_amount",
        },
        {
            "span_text": "24.5% difference",
            "fact_type": "percentage",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref(
                "derived_percentage_difference",
                "percentage",
                "not_24.5_percent",
                "No standard percentage difference from GBP 26,937.26 and GBP 42,476.20 equals 24.5%; required absolute difference is GBP 15,538.94",
            ),
            "reason": "The prompt evidence gives both net revenues, and 24.5% is not a supported percentage difference under standard denominators; the requested answer requires GBP 15,538.94.",
            "notes": "draft_round4; contradicted_extra_percentage_difference; missing_absolute_difference",
        },
    ],
    "q_0069": [
        {
            "span_text": "September 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round4; top3_products; correct_context",
        },
        {
            "span_text": "1.",
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[0].rank_item", "ranking", "1. 23243", "1. 23243 / SET OF TEA COFFEE SUGAR TINS PANTRY"),
            "reason": "The rank-1 marker is tied to the wrong generated product.",
            "notes": "draft_round4; list_rank_marker; wrong_rank1_item",
        },
        {
            "span_text": "JUMBO BAG RED RETROSPOT",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[0].description", "product_name", "SET OF TEA COFFEE SUGAR TINS PANTRY", "SET OF TEA COFFEE SUGAR TINS PANTRY"),
            "reason": "Gold rank-1 product is SET OF TEA COFFEE SUGAR TINS PANTRY, not JUMBO BAG RED RETROSPOT.",
            "notes": "draft_round4; wrong_rank1_product; correct_product_used_in_wrong_rank",
        },
        {
            "span_text": "GBP 8630.45",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[0].merchandise_net_revenue", "currency_amount", 9971.51, "GBP 9,971.51"),
            "reason": "GBP 8,630.45 is the gold rank-3 revenue, but the generated answer uses it for rank 1.",
            "notes": "draft_round4; wrong_rank1_amount; correct_amount_used_in_wrong_rank",
        },
        {
            "span_text": "2.",
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[1].rank_item", "ranking", "2. 22423", "2. 22423 / REGENCY CAKESTAND 3 TIER"),
            "reason": "The rank-2 marker is tied to the wrong generated product.",
            "notes": "draft_round4; list_rank_marker; wrong_rank2_item",
        },
        {
            "span_text": "PAPER CHAIN KIT 50'S CHRISTMAS",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[1].description", "product_name", "REGENCY CAKESTAND 3 TIER", "REGENCY CAKESTAND 3 TIER"),
            "reason": "Gold rank-2 product is REGENCY CAKESTAND 3 TIER, not PAPER CHAIN KIT 50'S CHRISTMAS.",
            "notes": "draft_round4; wrong_rank2_product",
        },
        {
            "span_text": "GBP 5997.25",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[1].merchandise_net_revenue", "currency_amount", 9315.03, "GBP 9,315.03"),
            "reason": "Gold rank-2 revenue is GBP 9,315.03, not GBP 5,997.25.",
            "notes": "draft_round4; wrong_rank2_amount",
        },
        {
            "span_text": "3.",
            "fact_type": "ranking",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[2].rank_item", "ranking", "3. 85099B", "3. 85099B / JUMBO BAG RED RETROSPOT"),
            "reason": "The rank-3 marker is tied to the wrong generated product.",
            "notes": "draft_round4; list_rank_marker; wrong_rank3_item",
        },
        {
            "span_text": "REGENCY CAKESTAND 3 TIER",
            "fact_type": "product_name",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[2].description", "product_name", "JUMBO BAG RED RETROSPOT", "JUMBO BAG RED RETROSPOT"),
            "reason": "REGENCY CAKESTAND 3 TIER is the gold rank-2 product, but the generated answer places it at rank 3.",
            "notes": "draft_round4; wrong_rank3_product; correct_product_used_in_wrong_rank",
        },
        {
            "span_text": "GBP 9315.03",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[2].merchandise_net_revenue", "currency_amount", 8630.45, "GBP 8,630.45"),
            "reason": "GBP 9,315.03 is the gold rank-2 revenue, but the generated answer uses it for rank 3.",
            "notes": "draft_round4; wrong_rank3_amount; correct_amount_used_in_wrong_rank",
        },
    ],
    "q_0081": [
        {
            "span_text": "September 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round4; product_share; correct_context",
        },
        {
            "span_text": "25.5%",
            "fact_type": "percentage",
            "label": "hallucinated_key_fact",
            "gold_field": "share_percent",
            "reason_template": "Generated top-product share is outside tolerance; gold share is {gold_display}.",
            "notes": "draft_round4; wrong_share_percent",
        },
        {
            "span_text": "6113.70",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "numerator_merchandise_net_revenue",
            "reason_template": "Generated share numerator is for the wrong product; gold numerator is {gold_display}.",
            "notes": "draft_round4; wrong_share_numerator",
        },
        {
            "span_text": "1,011,358.16",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "total_merchandise_net_revenue",
            "reason_template": "Generated denominator matches {gold_display}.",
            "notes": "draft_round4; correct_share_denominator",
        },
    ],
    "q_0086": [
        {
            "span_text": "June 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round4; top3_product_share; correct_context",
        },
        {
            "span_text": "63.15%",
            "fact_type": "percentage",
            "label": "hallucinated_key_fact",
            "gold_field": "share_percent",
            "reason_template": "Generated top-3 share is outside tolerance; gold share is {gold_display}.",
            "notes": "draft_round4; wrong_share_percent; first_result_claim",
        },
        {
            "span_text": "6311.68",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products[1].merchandise_net_revenue", "currency_amount", 12452.17, "GBP 12,452.17"),
            "reason": "Generated includes SPOTTY BUNTING's amount instead of the gold rank-2 PARTY BUNTING amount.",
            "notes": "draft_round4; wrong_top3_component_amount",
        },
        {
            "span_text": "9453.64",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_reference": gold_ref("top_products[2].merchandise_net_revenue", "currency_amount", 9453.64, "GBP 9,453.64"),
            "reason": "Generated includes the correct gold rank-3 product amount.",
            "notes": "draft_round4; correct_top3_component_amount; rank3_amount",
        },
        {
            "span_text": "39619.50",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_reference": gold_ref("top_products[0].merchandise_net_revenue", "currency_amount", 39619.50, "GBP 39,619.50"),
            "reason": "Generated includes the correct gold rank-1 product amount.",
            "notes": "draft_round4; correct_top3_component_amount; rank1_amount",
        },
        {
            "span_text": "45,964.82 GBP",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "numerator_merchandise_net_revenue",
            "reason_template": "Generated combined top-3 numerator is wrong; gold numerator is {gold_display}.",
            "notes": "draft_round4; wrong_share_numerator; arithmetic_error",
        },
        {
            "span_text": "45,964.82",
            "occurrence": 2,
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "numerator_merchandise_net_revenue",
            "reason_template": "Generated repeats the wrong combined top-3 numerator; gold numerator is {gold_display}.",
            "notes": "draft_round4; wrong_share_numerator; repeated_calculation_claim",
        },
        {
            "span_text": "723,970.15",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "total_merchandise_net_revenue",
            "reason_template": "Generated denominator matches {gold_display}.",
            "notes": "draft_round4; correct_share_denominator",
        },
        {
            "span_text": "63.15%",
            "occurrence": 2,
            "fact_type": "percentage",
            "label": "hallucinated_key_fact",
            "gold_field": "share_percent",
            "reason_template": "Generated repeats a top-3 share outside tolerance; gold share is {gold_display}.",
            "notes": "draft_round4; wrong_share_percent; repeated_calculation_claim",
        },
    ],
    "q_0087": [
        {
            "span_text": "September 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round4; top3_product_share; correct_context",
        },
        {
            "span_text": "10.6%",
            "fact_type": "percentage",
            "label": "hallucinated_key_fact",
            "gold_field": "share_percent",
            "reason_template": "Generated top-3 share is outside tolerance; gold share is {gold_display}.",
            "notes": "draft_round4; wrong_share_percent",
        },
        {
            "span_text": "6229.79",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products", "currency_amount", [9971.51, 9315.03, 8630.45], "GBP 9,971.51 + GBP 9,315.03 + GBP 8,630.45"),
            "reason": "Generated component amount is not one of the gold top-3 product amounts.",
            "notes": "draft_round4; wrong_top3_component_amount",
        },
        {
            "span_text": "5997.25",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products", "currency_amount", [9971.51, 9315.03, 8630.45], "GBP 9,971.51 + GBP 9,315.03 + GBP 8,630.45"),
            "reason": "Generated component amount is not one of the gold top-3 product amounts.",
            "notes": "draft_round4; wrong_top3_component_amount",
        },
        {
            "span_text": "6113.70",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_reference": gold_ref("top_products", "currency_amount", [9971.51, 9315.03, 8630.45], "GBP 9,971.51 + GBP 9,315.03 + GBP 8,630.45"),
            "reason": "Generated component amount is not one of the gold top-3 product amounts.",
            "notes": "draft_round4; wrong_top3_component_amount",
        },
        {
            "span_text": "GBP 18,730.74",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "numerator_merchandise_net_revenue",
            "reason_template": "Generated combined top-3 numerator is wrong; gold numerator is {gold_display}.",
            "notes": "draft_round4; wrong_share_numerator",
        },
        {
            "span_text": "GBP 1,011,358.16",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "total_merchandise_net_revenue",
            "reason_template": "Generated denominator matches {gold_display}.",
            "notes": "draft_round4; correct_share_denominator",
        },
    ],
    "q_0097": [
        {
            "span_text": "August 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round4; return_impact; correct_context",
        },
        {
            "span_text": "\u00a354,330.80",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "reduction_amount",
            "reason_template": "Generated reduction amount matches {gold_display}.",
            "notes": "draft_round4; correct_reduction_amount; pound_symbol_for_gbp",
        },
        {
            "span_text": "\u00a3703,510.58",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "net_revenue",
            "reason_template": "Generated final net revenue matches {gold_display}.",
            "notes": "draft_round4; correct_final_net_revenue; pound_symbol_for_gbp",
        },
    ],
    "q_0098": [
        {
            "span_text": "September 2011",
            "fact_type": "month",
            "label": "correct_key_fact",
            "gold_field": "year_month",
            "reason_template": "Generated month matches the gold month.",
            "notes": "draft_round4; return_impact; correct_context",
        },
        {
            "span_text": "GBP 38,838.51",
            "fact_type": "currency_amount",
            "label": "correct_key_fact",
            "gold_field": "reduction_amount",
            "reason_template": "Generated reduction amount matches {gold_display}.",
            "notes": "draft_round4; correct_reduction_amount",
        },
        {
            "span_text": "GBP 101,759.68",
            "fact_type": "currency_amount",
            "label": "hallucinated_key_fact",
            "gold_field": "net_revenue",
            "reason_template": "Generated final net revenue is off by a factor of ten; gold value is {gold_display}.",
            "notes": "draft_round4; wrong_final_net_revenue",
        },
    ],
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")


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
        reference = dict(spec["gold_reference"])
        reason = spec["reason"]
    else:
        fact = gold_fact_by_field(batch_record, spec["gold_field"])
        reference = compact_gold_reference(fact)
        reason = spec["reason_template"].format(gold_display=fact["display_value"])
    return {
        "annotation_id": f"ann_full100_draft_{batch_record['question_id']}_{span_index:03d}",
        "question_id": batch_record["question_id"],
        "prompt_id": batch_record["prompt_id"],
        "source_generation_file": SOURCE_GENERATION_FILE,
        "annotation_version": ANNOTATION_VERSION,
        "span_text": spec["span_text"],
        "span_start_char": start,
        "span_end_char": end,
        "fact_type": spec["fact_type"],
        "label": spec["label"],
        "gold_reference": reference,
        "reason": reason,
        "confidence": "high",
        "notes": spec["notes"],
    }


def write_preview(path: Path, records: list[dict[str, Any]], batch_by_qid: dict[str, dict[str, Any]]) -> None:
    fieldnames = [
        "source_batch",
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
        for record in records:
            batch_record = batch_by_qid[record["question_id"]]
            writer.writerow(
                {
                    "source_batch": (
                        "seed"
                        if record["annotation_id"].startswith("ann_full100_seed_")
                        else "draft_round4"
                        if "draft_round4" in record["notes"]
                        else "draft_round3"
                        if "draft_round3" in record["notes"]
                        else "draft_round2"
                        if "draft_round2" in record["notes"]
                        else "draft_round1"
                    ),
                    "annotation_id": record["annotation_id"],
                    "question_id": record["question_id"],
                    "split": batch_record["split"],
                    "question_type": batch_record["question_type"],
                    "label": record["label"],
                    "fact_type": record["fact_type"],
                    "span_text": record["span_text"],
                    "span_start_char": record["span_start_char"],
                    "span_end_char": record["span_end_char"],
                    "gold_display_value": record["gold_reference"].get("gold_display_value", ""),
                    "reason": record["reason"],
                    "notes": record["notes"],
                    "generated_text": batch_record["generated_text"],
                }
            )


def main() -> None:
    seed_records = load_jsonl(SEED_ANNOTATION_PATH)
    batch_records = load_jsonl(BATCH_PATH)
    generation_records = load_jsonl(GENERATION_PATH)
    batch_by_qid = {record["question_id"]: record for record in batch_records}
    generation_by_qid = {record["question_id"]: record for record in generation_records}

    missing_from_batch = sorted(set(EXPANSION_QUESTION_IDS) - set(batch_by_qid))
    missing_from_generations = sorted(set(EXPANSION_QUESTION_IDS) - set(generation_by_qid))
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

    expansion_records: list[dict[str, Any]] = []
    for question_id in EXPANSION_QUESTION_IDS:
        batch_record = batch_by_qid[question_id]
        generation_record = generation_by_qid[question_id]
        if generation_record["prompt_id"] != batch_record["prompt_id"]:
            raise ValueError(f"{question_id} prompt_id mismatch")
        for span_index, spec in enumerate(EXPANSION_SPECS[question_id], start=1):
            expansion_records.append(build_annotation(batch_record, generation_record, spec, span_index))

    all_records = seed_records + expansion_records
    write_jsonl(DRAFT_ANNOTATION_PATH, all_records)
    write_preview(PREVIEW_PATH, all_records, batch_by_qid)

    annotated_qids = sorted({record["question_id"] for record in all_records})
    round1_review = {
        "status": "draft_round1_complete",
        "annotation_version": "0.1-full100-draft-round1",
        "expansion_question_ids": ROUND1_QUESTION_IDS,
        "selection_policy": (
            "Add a balanced 4 dev / 4 test round across top_product, country_comparison, "
            "monthly_change, top3_products, product_revenue_share, and return_impact after "
            "the top_country seed."
        ),
        "review_notes": [
            "q_0033 and q_0034 include correct country revenue amounts inside an incorrect comparison direction.",
            "q_0063 follows pilot top3 annotation style with list rank markers tied to generated row items.",
            "q_0077 labels the repeated wrong share percentage twice because it appears as both answer and calculation result.",
            "q_0093 treats the first pound-symbol reduction amount as correct, but the repeated final net revenue claim as wrong.",
        ],
    }
    round2_review = {
        "status": "draft_round2_complete",
        "annotation_version": "0.2-full100-draft-round2",
        "expansion_question_ids": ROUND2_QUESTION_IDS,
        "selection_policy": (
            "Add another balanced 4 dev / 4 test round to deepen coverage of top_country, "
            "top_product, country_comparison, monthly_change, top3_products, product_share, "
            "and return_impact before completing the remaining heldout high-priority rows."
        ),
        "review_notes": [
            "q_0015 has the correct top country but a factor-of-ten wrong amount with a pound symbol.",
            "q_0025 has the correct stock code inside an inconsistent product-name and amount bundle.",
            "q_0054 has wrong absolute-change amounts but a percentage within the configured tolerance.",
            "q_0068 follows pilot top3 annotation style for products used in the wrong rank position.",
            "q_0092 has a wrong reduction amount but a correct final net revenue.",
        ],
    }
    round3_review = {
        "status": "draft_round3_complete",
        "annotation_version": "0.3-full100-draft-round3",
        "expansion_question_ids": ROUND3_QUESTION_IDS,
        "selection_policy": (
            "Add a balanced 3 dev / 3 test round from the remaining heldout high-priority "
            "rows, prioritizing one top_product, two country_comparison, one monthly_change, "
            "one top3_products, and one product_share example."
        ),
        "review_notes": [
            "q_0026 labels extra gross-positive and cancellation-return amounts because they support the wrong top-product answer.",
            "q_0039 has the right country amounts and nearly exact absolute difference, but assigns the higher-revenue relation to France.",
            "q_0058 has correct generated numbers but omits the explicit increase direction; missing facts are not forced into span labels.",
            "q_0064 labels correct rank-1 and rank-2 list items, wrong rank-3 binding, and does not invent labels for omitted stock codes.",
            "q_0076 treats the percentage as hallucinated because it is attached to the wrong top product and wrong numerator.",
        ],
    }
    round4_review = {
        "status": "heldout_high_draft_complete",
        "annotation_version": ANNOTATION_VERSION,
        "expansion_question_ids": ROUND4_QUESTION_IDS,
        "selection_policy": (
            "Final 8-row heldout high-priority round: two country_comparison, one top3_products, "
            "three product_share, and two return_impact examples."
        ),
        "review_notes": [
            "q_0044 and q_0049 keep correct country amount spans while labeling the wrong higher-country direction.",
            "q_0069 follows top3 row-binding policy and does not invent stock-code labels that were omitted by the model.",
            "q_0086 labels correct component amounts separately but marks the wrong combined numerator and repeated wrong percentage.",
            "q_0097 contains correct generated facts but omits gross revenue and reduction-rate facts, so no missing-fact hallucination span is forced.",
            "q_0098 has a correct reduction amount but a factor-of-ten wrong final net revenue.",
        ],
    }
    ROUND1_REVIEW_PATH.write_text(json.dumps(round1_review, indent=2, ensure_ascii=True), encoding="utf-8")
    ROUND2_REVIEW_PATH.write_text(json.dumps(round2_review, indent=2, ensure_ascii=True), encoding="utf-8")
    ROUND3_REVIEW_PATH.write_text(json.dumps(round3_review, indent=2, ensure_ascii=True), encoding="utf-8")
    ROUND4_REVIEW_PATH.write_text(json.dumps(round4_review, indent=2, ensure_ascii=True), encoding="utf-8")

    report = {
        "annotation_path": str(DRAFT_ANNOTATION_PATH),
        "seed_annotation_path": str(SEED_ANNOTATION_PATH),
        "preview_path": str(PREVIEW_PATH),
        "round_review_path": str(ROUND4_REVIEW_PATH),
        "round_review_paths": [str(ROUND1_REVIEW_PATH), str(ROUND2_REVIEW_PATH), str(ROUND3_REVIEW_PATH), str(ROUND4_REVIEW_PATH)],
        "source_generation_file": SOURCE_GENERATION_FILE,
        "annotation_version": ANNOTATION_VERSION,
        "status": "draft annotation file; requires review before final full100 scoring",
        "seed_span_count": len(seed_records),
        "expansion_span_count": len(expansion_records),
        "round1_question_ids": ROUND1_QUESTION_IDS,
        "round2_question_ids": ROUND2_QUESTION_IDS,
        "round3_question_ids": ROUND3_QUESTION_IDS,
        "round4_question_ids": ROUND4_QUESTION_IDS,
        "total_span_count": len(all_records),
        "annotated_question_count": len(annotated_qids),
        "annotated_question_ids": annotated_qids,
        "expansion_question_ids": EXPANSION_QUESTION_IDS,
        "split_counts": dict(sorted(Counter(batch_by_qid[qid]["split"] for qid in annotated_qids).items())),
        "expansion_split_counts": dict(sorted(Counter(batch_by_qid[qid]["split"] for qid in EXPANSION_QUESTION_IDS).items())),
        "round2_split_counts": dict(sorted(Counter(batch_by_qid[qid]["split"] for qid in ROUND2_QUESTION_IDS).items())),
        "round3_split_counts": dict(sorted(Counter(batch_by_qid[qid]["split"] for qid in ROUND3_QUESTION_IDS).items())),
        "round4_split_counts": dict(sorted(Counter(batch_by_qid[qid]["split"] for qid in ROUND4_QUESTION_IDS).items())),
        "question_type_counts": dict(sorted(Counter(batch_by_qid[qid]["question_type"] for qid in annotated_qids).items())),
        "label_counts": dict(sorted(Counter(record["label"] for record in all_records).items())),
        "fact_type_counts": dict(sorted(Counter(record["fact_type"] for record in all_records).items())),
        "spans_by_question": dict(sorted(Counter(record["question_id"] for record in all_records).items())),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
