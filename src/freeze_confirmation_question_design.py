from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import pandas as pd

from freeze_confirmation_context_manifest import (
    canonical_json_sha256,
    context_evidence,
    seeded_hash,
)
from profile_confirmation_dataset_overlap import (
    CANONICAL_FIELDS,
    fingerprint_counters,
    inventory_manifest_sha256,
    normalize_frame,
)
from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "confirmation_question_design_v1.json"
PROTOCOL_PATH = PROJECT_ROOT / "configs" / "confirmation_set_v1_protocol.json"
FEASIBILITY_CONFIG_PATH = PROJECT_ROOT / "configs" / "confirmation_context_feasibility_v1.json"
CONTEXT_REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_manifest_report.json"
METHODOLOGY_PATH = PROJECT_ROOT / "reports" / "bizhallu_methodology_hardening_summary.json"
STRICT_TABLE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "confirmation_online_retail_ii"
    / "strict_window_lines.csv.gz"
)
PRIVATE_CONTEXT_PATH = STRICT_TABLE_PATH.parent / "context_manifest_v1_private.json"
PRIVATE_QUESTIONS_PATH = STRICT_TABLE_PATH.parent / "questions_gold_v1_private.json"
HISTORICAL_QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_question_design_report.json"

EXPECTED_FAMILIES = [
    "net_revenue_reconciliation_by_period",
    "product_return_rate_comparison",
    "country_product_exposure",
]
EXPECTED_SPLIT_QUESTION_COUNTS = {
    "protocol_pilot": 12,
    "development": 30,
    "confirmation": 54,
}
EXPECTED_CONTEXT_COMMITMENT = "002b484b3b59c52db0a2213b8d896750cdb2bb9157998d48bf015eff27f19e5a"
EXPECTED_STRICT_TABLE_SHA256 = "ab875caaf527d5d528f4edad4fd372b15d4e1ae9c39f6cea20f8211178e256fc"
EXPECTED_HISTORICAL_AUPRC = 0.835073
EXPECTED_HISTORICAL_F1 = 0.779412
TEXT_HASH_SUFFIXES = {".json", ".jsonl", ".csv", ".md", ".html", ".py", ".yml", ".yaml"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    if path.suffix.lower() in TEXT_HASH_SUFFIXES:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def money(value: float | int) -> float:
    return float(Decimal(str(float(value))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def percentage(value: float | int) -> float:
    return float(Decimal(str(float(value))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def boolean_series(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series.dtype):
        return series.fillna(False).astype(bool)
    return series.astype("string").str.strip().str.casefold().eq("true").fillna(False)


def normalize_text(value: Any) -> str:
    return " ".join(str(value).strip().split())


def canonical_product_name(frame: pd.DataFrame, stock_code: str) -> str:
    names = frame.loc[frame["stock_code"].eq(stock_code), "description"].dropna().map(normalize_text)
    names = names.loc[names.ne("")]
    if names.empty:
        raise RuntimeError(f"No normalized product name for stock code {stock_code}")
    counts = names.value_counts().rename_axis("name").reset_index(name="count")
    counts = counts.sort_values(["count", "name"], ascending=[False, True], kind="mergesort")
    return str(counts.iloc[0]["name"])


def evidence_payload(
    *,
    family: str,
    template_id: str,
    columns: list[str],
    metadata: dict[str, Any],
    rows: list[dict[str, Any]],
    fingerprint_domain: str,
) -> tuple[dict[str, Any], str]:
    payload = {
        "schema_version": "1.0",
        "question_family": family,
        "template_id": template_id,
        "columns": columns,
        "metadata": metadata,
        "rows": rows,
    }
    return payload, canonical_json_sha256(payload, fingerprint_domain)


def evidence_table_projection(
    evidence: dict[str, Any],
    field_aliases: dict[str, str],
) -> dict[str, Any]:
    """Build a wrapper-independent multiset projection of visible evidence rows."""
    normalized_rows: list[dict[str, Any]] = []
    for source_row in evidence.get("rows", []):
        normalized_row: dict[str, Any] = {}
        for source_key, value in source_row.items():
            key = field_aliases.get(source_key, source_key)
            normalized_value = normalize_evidence_value(value)
            if key in normalized_row and normalized_row[key] != normalized_value:
                raise RuntimeError(f"Conflicting evidence field alias for {source_key} -> {key}")
            normalized_row[key] = normalized_value
        normalized_rows.append(dict(sorted(normalized_row.items())))
    normalized_rows.sort(
        key=lambda row: json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    )
    return {"rows": normalized_rows}


def normalize_evidence_value(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        numeric = Decimal(str(value))
        if not numeric.is_finite():
            raise ValueError(f"Non-finite evidence value: {value}")
        normalized = format(numeric.normalize(), "f")
        return "0" if normalized in {"-0", "-0.0"} else normalized
    if isinstance(value, str):
        return normalize_text(value)
    return value


def evidence_content_sha256(evidence: dict[str, Any], config: dict[str, Any]) -> str:
    return canonical_json_sha256(
        evidence_table_projection(
            evidence,
            config["fingerprint_policy"]["content_field_aliases"],
        ),
        config["assignment"]["evidence_content_comparison_domain"],
    )


def fact(field: str, fact_type: str, value: Any, display_value: str, tolerance: Any) -> dict[str, Any]:
    return {
        "field": field,
        "fact_type": fact_type,
        "value": value,
        "display_value": display_value,
        "tolerance": tolerance,
    }


def question_id(
    *,
    config: dict[str, Any],
    context_id: str,
    template_id: str,
    evidence_fingerprint: str,
) -> str:
    digest = canonical_json_sha256(
        {
            "context_id": context_id,
            "template_id": template_id,
            "evidence_fingerprint": evidence_fingerprint,
        },
        config["assignment"]["question_id_domain"],
    )
    return f"cv1q_{digest[:20]}"


def base_record(
    *,
    config: dict[str, Any],
    context: dict[str, Any],
    template_id: str,
    question_text: str,
    gold_answer: dict[str, Any],
    gold_facts: list[dict[str, Any]],
    gold_short_answer: str,
    evidence: dict[str, Any],
    evidence_fingerprint: str,
    selection_provenance: dict[str, Any],
) -> dict[str, Any]:
    return {
        "question_id": question_id(
            config=config,
            context_id=context["context_id"],
            template_id=template_id,
            evidence_fingerprint=evidence_fingerprint,
        ),
        "context_id": context["context_id"],
        "question_family": context["question_family"],
        "template_id": template_id,
        "split": context["split"],
        "period_start": context["period_start"],
        "period_end_exclusive": context["period_end_exclusive"],
        "question": question_text,
        "gold_short_answer": gold_short_answer,
        "gold_answer": gold_answer,
        "gold_facts": gold_facts,
        "evidence": evidence,
        "evidence_payload_sha256": evidence_fingerprint,
        "evidence_content_sha256": evidence_content_sha256(evidence, config),
        "selection_provenance": selection_provenance,
        "generation_guidance": {
            "must_use_only_provided_evidence": True,
            "answer_style": "concise auditable business analysis",
            "prompt_not_created": True,
        },
    }


def period_label(context: dict[str, Any]) -> tuple[str, str]:
    start = pd.Timestamp(context["period_start"])
    end_inclusive = pd.Timestamp(context["period_end_exclusive"]) - pd.Timedelta(days=1)
    return start.strftime("%Y-%m-%d"), end_inclusive.strftime("%Y-%m-%d")


def build_reconciliation_questions(
    *,
    config: dict[str, Any],
    context: dict[str, Any],
    period_frame: pd.DataFrame,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    valid = period_frame.loc[period_frame["is_valid_net_revenue_line"]].copy()
    if valid.empty:
        raise RuntimeError(f"No reconciliation evidence for {context['context_id']}")
    start, end_inclusive = period_label(context)
    fingerprint_domain = config["assignment"]["question_evidence_payload_domain"]
    money_tolerance = {"absolute_gbp": config["shared_calculation_rules"]["money_reconciliation_tolerance_gbp"]}
    percentage_tolerance = {
        "absolute_percentage_points": config["shared_calculation_rules"]["percentage_tolerance_points"]
    }

    gross = money(valid.loc[valid["line_revenue"] > 0, "line_revenue"].sum())
    cancellation_revenue = money(valid.loc[valid["line_revenue"] < 0, "line_revenue"].sum())
    reduction = money(abs(cancellation_revenue))
    net = money(valid["line_revenue"].sum())
    reconciliation_error = money(gross + cancellation_revenue - net)
    positive_cancel_flagged_rows = int(
        (
            (valid["line_revenue"] > 0)
            & valid["is_cancellation_or_return_line"]
        ).sum()
    )
    if abs(reconciliation_error) > config["shared_calculation_rules"]["money_reconciliation_tolerance_gbp"]:
        raise RuntimeError(f"Weekly reconciliation failed for {context['context_id']}: {reconciliation_error}")

    template_id = "nrr_weekly_reconciliation_v1"
    weekly_rows = [
        {
            "gross_positive_revenue_gbp": gross,
            "cancellation_return_revenue_gbp": cancellation_revenue,
        }
    ]
    weekly_evidence, weekly_fingerprint = evidence_payload(
        family=context["question_family"],
        template_id=template_id,
        columns=["gross_positive_revenue_gbp", "cancellation_return_revenue_gbp"],
        metadata={
            "period_start": start,
            "period_end_inclusive": end_inclusive,
            "metric_definition": "gross positive line revenue sums positive line revenue; negative cancellation-and-return revenue sums negative line revenue; net revenue is their arithmetic sum after frozen evidence filters",
        },
        rows=weekly_rows,
        fingerprint_domain=fingerprint_domain,
    )
    weekly_gold = {
        "period_start": start,
        "period_end_inclusive": end_inclusive,
        "gross_positive_revenue_gbp": gross,
        "cancellation_return_revenue_gbp": cancellation_revenue,
        "cancellation_return_reduction_gbp": reduction,
        "net_revenue_gbp": net,
        "currency": "GBP",
    }
    weekly_facts = [
        fact("period_start", "date", start, start, "exact_match"),
        fact("period_end_inclusive", "date", end_inclusive, end_inclusive, "exact_match"),
        fact("gross_positive_revenue_gbp", "currency_amount", gross, f"GBP {gross:,.2f}", money_tolerance),
        fact("cancellation_return_reduction_gbp", "currency_amount", reduction, f"GBP {reduction:,.2f}", money_tolerance),
        fact("net_revenue_gbp", "currency_amount", net, f"GBP {net:,.2f}", money_tolerance),
    ]
    weekly = base_record(
        config=config,
        context=context,
        template_id=template_id,
        question_text=(
            f"For the complete week from {start} through {end_inclusive}, reconcile gross positive line revenue, "
            "negative cancellation-and-return revenue, and final net revenue. Report the positive amount, the "
            "reduction as a positive amount, and net revenue in GBP, then show the arithmetic relationship."
        ),
        gold_answer=weekly_gold,
        gold_facts=weekly_facts,
        gold_short_answer=(
            f"Gross positive revenue was GBP {gross:,.2f}; cancellations and returns reduced it by "
            f"GBP {reduction:,.2f}, leaving net revenue of GBP {net:,.2f}."
        ),
        evidence=weekly_evidence,
        evidence_fingerprint=weekly_fingerprint,
        selection_provenance={"scope": "all frozen valid net-revenue lines in the context week"},
    )

    daily = valid.assign(business_date=valid["invoice_date"].dt.strftime("%Y-%m-%d"))
    daily_rows: list[dict[str, Any]] = []
    for business_date, day in daily.groupby("business_date", sort=True):
        day_gross = money(day.loc[day["line_revenue"] > 0, "line_revenue"].sum())
        day_cancellation = money(day.loc[day["line_revenue"] < 0, "line_revenue"].sum())
        daily_rows.append(
            {
                "business_date": str(business_date),
                "gross_positive_revenue_gbp": day_gross,
                "cancellation_return_revenue_gbp": day_cancellation,
            }
        )
    eligible_days = [
        row for row in daily_rows if row["gross_positive_revenue_gbp"] > 0 and row["cancellation_return_revenue_gbp"] < 0
    ]
    if not eligible_days:
        raise RuntimeError(f"No daily cancellation hotspot for {context['context_id']}")
    hotspot = sorted(
        eligible_days,
        key=lambda row: (-abs(row["cancellation_return_revenue_gbp"]), row["business_date"]),
    )[0]
    hotspot_reduction = money(abs(hotspot["cancellation_return_revenue_gbp"]))
    hotspot_pct = percentage(hotspot_reduction / hotspot["gross_positive_revenue_gbp"] * 100)
    template_id = "nrr_daily_cancellation_hotspot_v1"
    daily_evidence, daily_fingerprint = evidence_payload(
        family=context["question_family"],
        template_id=template_id,
        columns=["business_date", "gross_positive_revenue_gbp", "cancellation_return_revenue_gbp"],
        metadata={
            "period_start": start,
            "period_end_inclusive": end_inclusive,
            "row_grain": "observed trading day",
            "metric_definition": "cancellation-and-return reduction is the absolute value of negative line revenue; gross positive line revenue sums positive line revenue",
        },
        rows=daily_rows,
        fingerprint_domain=fingerprint_domain,
    )
    hotspot_gold = {
        "period_start": start,
        "period_end_inclusive": end_inclusive,
        "business_date": hotspot["business_date"],
        "cancellation_return_reduction_gbp": hotspot_reduction,
        "gross_positive_revenue_gbp": hotspot["gross_positive_revenue_gbp"],
        "reduction_percentage_of_gross": hotspot_pct,
        "currency": "GBP",
    }
    hotspot_facts = [
        fact("business_date", "date", hotspot["business_date"], hotspot["business_date"], "exact_match"),
        fact("cancellation_return_reduction_gbp", "currency_amount", hotspot_reduction, f"GBP {hotspot_reduction:,.2f}", money_tolerance),
        fact("gross_positive_revenue_gbp", "currency_amount", hotspot["gross_positive_revenue_gbp"], f"GBP {hotspot['gross_positive_revenue_gbp']:,.2f}", money_tolerance),
        fact("reduction_percentage_of_gross", "percentage", hotspot_pct, f"{hotspot_pct:.2f}%", percentage_tolerance),
    ]
    hotspot_record = base_record(
        config=config,
        context=context,
        template_id=template_id,
        question_text=(
            f"During the complete week from {start} through {end_inclusive}, which observed trading day had "
            "the largest negative cancellation-and-return revenue reduction? Report the date, reduction as a "
            "positive amount in GBP, that day's gross positive line revenue, and the reduction as a percentage "
            "of that gross positive line revenue."
        ),
        gold_answer=hotspot_gold,
        gold_facts=hotspot_facts,
        gold_short_answer=(
            f"{hotspot['business_date']} had the largest reduction: GBP {hotspot_reduction:,.2f}, equal to "
            f"{hotspot_pct:.2f}% of that day's GBP {hotspot['gross_positive_revenue_gbp']:,.2f} gross positive revenue."
        ),
        evidence=daily_evidence,
        evidence_fingerprint=daily_fingerprint,
        selection_provenance={
            "candidate_grain": "observed trading day with positive gross revenue and negative cancellation/return revenue",
            "gold_selection": "maximum absolute negative revenue; ISO date tie-break",
        },
    )
    return [weekly, hotspot_record], {
        "weekly_reconciliation_error_gbp": abs(reconciliation_error),
        "daily_evidence_row_count": len(daily_rows),
        "hotspot_percentage": hotspot_pct,
        "positive_cancel_flagged_row_count": positive_cancel_flagged_rows,
    }


def product_aggregate(frame: pd.DataFrame, scope_entities: list[str]) -> dict[str, dict[str, Any]]:
    merchandise = frame.loc[frame["is_merchandise_net_revenue_line"]].copy()
    merchandise["stock_code"] = merchandise["stock_code"].astype("string").str.strip()
    scoped = merchandise.loc[merchandise["stock_code"].isin(scope_entities)].copy()
    aggregate: dict[str, dict[str, Any]] = {}
    for stock_code, product in scoped.groupby("stock_code", sort=False):
        code = str(stock_code)
        positive_units = int(product.loc[product["quantity"] > 0, "quantity"].sum())
        returned_units = int(-product.loc[product["quantity"] < 0, "quantity"].sum())
        if positive_units <= 0 or returned_units <= 0:
            raise RuntimeError(f"Invalid frozen return support for {code}")
        ratio = returned_units / positive_units
        aggregate[code] = {
            "stock_code": code,
            "product_name": canonical_product_name(scoped, code),
            "positive_units": positive_units,
            "returned_units": returned_units,
            "positive_invoice_count": int(product.loc[product["quantity"] > 0, "invoice_no"].nunique()),
            "return_invoice_count": int(product.loc[product["quantity"] < 0, "invoice_no"].nunique()),
            "ratio": ratio,
            "ratio_six_decimals": round(ratio, 6),
            "ratio_percentage": percentage(ratio * 100),
        }
    return aggregate


def choose_product_pairs(
    *,
    config: dict[str, Any],
    context: dict[str, Any],
    aggregate: dict[str, dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    seed = int(config["assignment"]["seed"])
    domain = config["assignment"]["product_pair_order_domain"]
    available = set(aggregate)
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for slot in [1, 2]:
        ordered = sorted(
            available,
            key=lambda code: (seeded_hash(domain, seed, context["context_id"], str(slot), code), code),
        )
        selected: tuple[str, str] | None = None
        for code_a in ordered:
            for code_b in ordered:
                if code_a == code_b:
                    continue
                a = aggregate[code_a]
                b = aggregate[code_b]
                if (
                    a["ratio_six_decimals"] != b["ratio_six_decimals"]
                    and a["ratio_percentage"] != b["ratio_percentage"]
                ):
                    selected = (code_a, code_b)
                    break
            if selected:
                break
        if selected is None:
            raise RuntimeError(f"Cannot select a distinct displayed ratio pair for {context['context_id']} slot {slot}")
        pairs.append((aggregate[selected[0]], aggregate[selected[1]]))
        available.difference_update(selected)
    return pairs


def build_product_return_questions(
    *,
    config: dict[str, Any],
    context: dict[str, Any],
    period_frame: pd.DataFrame,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    start, end_inclusive = period_label(context)
    aggregate = product_aggregate(period_frame, [str(value) for value in context["scope_entities"]])
    if set(aggregate) != set(str(value) for value in context["scope_entities"]):
        raise RuntimeError(f"Product scope mismatch for {context['context_id']}")
    pairs = choose_product_pairs(config=config, context=context, aggregate=aggregate)
    fingerprint_domain = config["assignment"]["question_evidence_payload_domain"]
    pct_tolerance = {"absolute_percentage_points": config["shared_calculation_rules"]["percentage_tolerance_points"]}
    records: list[dict[str, Any]] = []
    selected_codes: list[str] = []
    differences: list[float] = []
    selected_ratio_percentages: list[float] = []
    for slot, (a, b) in enumerate(pairs, start=1):
        template_id = f"prr_pair_comparison_{slot}_v1"
        selected_codes.extend([a["stock_code"], b["stock_code"]])
        selected_ratio_percentages.extend([a["ratio_percentage"], b["ratio_percentage"]])
        evidence_rows = [
            {
                key: item[key]
                for key in [
                    "stock_code",
                    "product_name",
                    "positive_units",
                    "returned_units",
                    "positive_invoice_count",
                    "return_invoice_count",
                ]
            }
            for item in [a, b]
        ]
        evidence, evidence_fingerprint = evidence_payload(
            family=context["question_family"],
            template_id=template_id,
            columns=[
                "stock_code",
                "product_name",
                "positive_units",
                "returned_units",
                "positive_invoice_count",
                "return_invoice_count",
            ],
            metadata={
                "period_start": start,
                "period_end_inclusive": end_inclusive,
                "ratio_definition": "absolute negative quantity divided by positive quantity in the same week",
                "claim_limit": "recorded unit ratio; not customer-linked or original-sale-linked",
            },
            rows=evidence_rows,
            fingerprint_domain=fingerprint_domain,
        )
        higher = a if a["ratio"] > b["ratio"] else b
        difference = percentage(abs(a["ratio"] - b["ratio"]) * 100)
        differences.append(difference)
        gold = {
            "period_start": start,
            "period_end_inclusive": end_inclusive,
            "product_a": {
                "stock_code": a["stock_code"],
                "product_name": a["product_name"],
                "ratio_percentage": a["ratio_percentage"],
            },
            "product_b": {
                "stock_code": b["stock_code"],
                "product_name": b["product_name"],
                "ratio_percentage": b["ratio_percentage"],
            },
            "higher_ratio_stock_code": higher["stock_code"],
            "higher_ratio_product_name": higher["product_name"],
            "percentage_point_difference": difference,
        }
        facts = [
            fact("product_a_stock_code", "product_stock_code", a["stock_code"], a["stock_code"], "exact_normalized_match"),
            fact("product_a_ratio_percentage", "percentage", a["ratio_percentage"], f"{a['ratio_percentage']:.2f}%", pct_tolerance),
            fact("product_b_stock_code", "product_stock_code", b["stock_code"], b["stock_code"], "exact_normalized_match"),
            fact("product_b_ratio_percentage", "percentage", b["ratio_percentage"], f"{b['ratio_percentage']:.2f}%", pct_tolerance),
            fact("higher_ratio_stock_code", "product_stock_code", higher["stock_code"], higher["stock_code"], "exact_normalized_match"),
            fact("percentage_point_difference", "percentage_point_difference", difference, f"{difference:.2f} percentage points", pct_tolerance),
        ]
        records.append(
            base_record(
                config=config,
                context=context,
                template_id=template_id,
                question_text=(
                    f"For the complete week from {start} through {end_inclusive}, compare the recorded "
                    f"return-to-positive-sales unit ratios for {a['product_name']} ({a['stock_code']}) and "
                    f"{b['product_name']} ({b['stock_code']}). Which ratio was higher, what was each ratio, "
                    "and what was the percentage-point difference?"
                ),
                gold_answer=gold,
                gold_facts=facts,
                gold_short_answer=(
                    f"{a['stock_code']} was {a['ratio_percentage']:.2f}% and {b['stock_code']} was "
                    f"{b['ratio_percentage']:.2f}%; {higher['stock_code']} was higher by {difference:.2f} percentage points."
                ),
                evidence=evidence,
                evidence_fingerprint=evidence_fingerprint,
                selection_provenance={
                    "pair_slot": slot,
                    "selection": "domain-separated seeded hash order with distinct six-decimal and displayed ratios",
                    "products_reused_across_context_questions": False,
                },
            )
        )
    return records, {
        "eligible_product_count": len(aggregate),
        "selected_product_count": len(set(selected_codes)),
        "minimum_percentage_point_difference": min(differences),
        "minimum_selected_ratio_percentage": min(selected_ratio_percentages),
        "maximum_selected_ratio_percentage": max(selected_ratio_percentages),
        "selected_ratio_over_100_count": sum(
            value > 100 for value in selected_ratio_percentages
        ),
    }


def country_product_aggregate(frame: pd.DataFrame, country: str) -> tuple[dict[str, dict[str, Any]], float]:
    merchandise = frame.loc[
        frame["is_merchandise_net_revenue_line"] & frame["country"].eq(country)
    ].copy()
    merchandise["stock_code"] = merchandise["stock_code"].astype("string").str.strip()
    country_total = money(merchandise["line_revenue"].sum())
    aggregate: dict[str, dict[str, Any]] = {}
    for stock_code, product in merchandise.groupby("stock_code", sort=False):
        code = str(stock_code)
        net_revenue = money(product["line_revenue"].sum())
        if net_revenue <= 0:
            continue
        aggregate[code] = {
            "country": country,
            "stock_code": code,
            "product_name": canonical_product_name(merchandise, code),
            "product_merchandise_net_revenue_gbp": net_revenue,
            "country_merchandise_net_revenue_gbp": country_total,
        }
    return aggregate, country_total


def build_country_exposure_questions(
    *,
    config: dict[str, Any],
    context: dict[str, Any],
    period_frame: pd.DataFrame,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    start, end_inclusive = period_label(context)
    seed = int(config["assignment"]["seed"])
    country_domain = config["assignment"]["country_order_domain"]
    product_domain = config["assignment"]["country_product_order_domain"]
    countries = sorted(
        [str(value) for value in context["scope_entities"]],
        key=lambda country: (seeded_hash(country_domain, seed, context["context_id"], country), country),
    )[:2]
    if len(countries) != 2 or len(set(countries)) != 2:
        raise RuntimeError(f"Cannot select two countries for {context['context_id']}")
    fingerprint_domain = config["assignment"]["question_evidence_payload_domain"]
    candidate_count = next(
        item["candidate_product_count"]
        for item in config["family_designs"]
        if item["family"] == "country_product_exposure"
    )
    money_tolerance = {"absolute_gbp": config["shared_calculation_rules"]["money_reconciliation_tolerance_gbp"]}
    pct_tolerance = {"absolute_percentage_points": config["shared_calculation_rules"]["percentage_tolerance_points"]}
    records: list[dict[str, Any]] = []
    candidate_pool_counts: list[int] = []
    shares: list[float] = []
    gold_positions: list[int] = []
    accidentally_descending_count = 0
    for slot, country in enumerate(countries, start=1):
        aggregate, country_total = country_product_aggregate(period_frame, country)
        if country_total <= 0 or len(aggregate) < candidate_count:
            raise RuntimeError(
                f"Insufficient positive product evidence for {context['context_id']} / {country}: "
                f"total={country_total}, products={len(aggregate)}"
            )
        candidate_pool_counts.append(len(aggregate))
        selected_codes = sorted(
            aggregate,
            key=lambda code: (
                seeded_hash(product_domain, seed, context["context_id"], str(slot), country, code),
                code,
            ),
        )[:candidate_count]
        evidence_rows = [aggregate[code] for code in selected_codes]
        gold_row = sorted(
            evidence_rows,
            key=lambda row: (-row["product_merchandise_net_revenue_gbp"], row["stock_code"]),
        )[0]
        gold_positions.append(evidence_rows.index(gold_row) + 1)
        revenues_in_order = [
            row["product_merchandise_net_revenue_gbp"] for row in evidence_rows
        ]
        if all(
            left >= right
            for left, right in zip(revenues_in_order, revenues_in_order[1:])
        ):
            accidentally_descending_count += 1
        share = percentage(
            gold_row["product_merchandise_net_revenue_gbp"] / country_total * 100
        )
        if not 0 < share <= 100:
            raise RuntimeError(f"Invalid country exposure share for {context['context_id']} / {country}: {share}")
        shares.append(share)
        template_id = f"cpe_candidate_product_exposure_{slot}_v1"
        evidence, evidence_fingerprint = evidence_payload(
            family=context["question_family"],
            template_id=template_id,
            columns=[
                "country",
                "stock_code",
                "product_name",
                "product_merchandise_net_revenue_gbp",
                "country_merchandise_net_revenue_gbp",
            ],
            metadata={
                "period_start": start,
                "period_end_inclusive": end_inclusive,
                "candidate_scope": "five outcome-blind hash-selected positive-net-revenue products",
                "metric_definition": "merchandise net revenue retains negative quantities and excludes non-merchandise rows",
            },
            rows=evidence_rows,
            fingerprint_domain=fingerprint_domain,
        )
        gold = {
            "period_start": start,
            "period_end_inclusive": end_inclusive,
            "country": country,
            "candidate_product_count": candidate_count,
            "stock_code": gold_row["stock_code"],
            "product_name": gold_row["product_name"],
            "product_merchandise_net_revenue_gbp": gold_row["product_merchandise_net_revenue_gbp"],
            "country_merchandise_net_revenue_gbp": country_total,
            "share_of_country_merchandise_net_revenue_percentage": share,
            "rank_scope": "highest among the five listed products",
        }
        facts = [
            fact("country", "country", country, country, "exact_normalized_match"),
            fact("stock_code", "product_stock_code", gold_row["stock_code"], gold_row["stock_code"], "exact_normalized_match"),
            fact("product_name", "product_name", gold_row["product_name"], gold_row["product_name"], "exact_normalized_match"),
            fact("product_merchandise_net_revenue_gbp", "currency_amount", gold_row["product_merchandise_net_revenue_gbp"], f"GBP {gold_row['product_merchandise_net_revenue_gbp']:,.2f}", money_tolerance),
            fact("share_of_country_merchandise_net_revenue_percentage", "percentage", share, f"{share:.2f}%", pct_tolerance),
            fact("rank_scope", "ranking", 1, "highest among five listed products", "exact_context_bound_match"),
        ]
        records.append(
            base_record(
                config=config,
                context=context,
                template_id=template_id,
                question_text=(
                    f"For {country} during the complete week from {start} through {end_inclusive}, which of "
                    "the five listed products had the highest merchandise net revenue? Report the stock code, "
                    "product name, net revenue in GBP, and its share of the country's total merchandise net revenue."
                ),
                gold_answer=gold,
                gold_facts=facts,
                gold_short_answer=(
                    f"Among the five listed products for {country}, {gold_row['stock_code']} "
                    f"({gold_row['product_name']}) was highest at GBP "
                    f"{gold_row['product_merchandise_net_revenue_gbp']:,.2f}, or {share:.2f}% of country merchandise net revenue."
                ),
                evidence=evidence,
                evidence_fingerprint=evidence_fingerprint,
                selection_provenance={
                    "country_slot": slot,
                    "country_selection": "first two frozen eligible countries under seeded hash order",
                    "candidate_product_selection": "first five positive-net-revenue products under independent seeded hash order",
                    "evidence_sorted_by_gold_rank": False,
                },
            )
        )
    return records, {
        "selected_country_count": len(countries),
        "minimum_positive_product_candidate_pool": min(candidate_pool_counts),
        "minimum_gold_share_percentage": min(shares),
        "maximum_gold_share_percentage": max(shares),
        "gold_positions": gold_positions,
        "accidentally_fully_descending_count": accidentally_descending_count,
    }


def historical_evidence_content_fingerprints(config: dict[str, Any]) -> set[str]:
    fingerprints: set[str] = set()
    for record in load_jsonl(HISTORICAL_QUESTIONS_PATH):
        evidence = record.get("evidence", {})
        fingerprints.add(evidence_content_sha256(evidence, config))
    return fingerprints


def main() -> None:
    required = [
        CONFIG_PATH,
        PROTOCOL_PATH,
        FEASIBILITY_CONFIG_PATH,
        CONTEXT_REPORT_PATH,
        METHODOLOGY_PATH,
        STRICT_TABLE_PATH,
        PRIVATE_CONTEXT_PATH,
        HISTORICAL_QUESTIONS_PATH,
    ]
    missing = [repo_path(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required Gate 3 inputs: {missing}")

    config = load_json(CONFIG_PATH)
    protocol = load_json(PROTOCOL_PATH)
    feasibility_config = load_json(FEASIBILITY_CONFIG_PATH)
    context_report = load_json(CONTEXT_REPORT_PATH)
    methodology = load_json(METHODOLOGY_PATH)
    private_context = load_json(PRIVATE_CONTEXT_PATH)

    if config.get("status") != "question_and_gold_rules_frozen":
        raise RuntimeError("Question design rules are not frozen")
    if sha256_file(STRICT_TABLE_PATH) != EXPECTED_STRICT_TABLE_SHA256:
        raise RuntimeError("Strict-window source hash drifted")
    if context_report["private_manifest_commitment"]["canonical_sha256"] != EXPECTED_CONTEXT_COMMITMENT:
        raise RuntimeError("Context-manifest commitment drifted")
    observed_context_commitment = canonical_json_sha256(
        private_context,
        "bizhallu:confirmation-private-context-manifest:v1",
    )
    if observed_context_commitment != EXPECTED_CONTEXT_COMMITMENT:
        raise RuntimeError("Private context manifest no longer matches its public commitment")
    protocol_boundary = protocol.get("current_result_boundary", {})
    methodology_boundary = methodology.get("locked_public_results", {})
    for metric_name, expected in {
        "exploratory_max_test_auprc": EXPECTED_HISTORICAL_AUPRC,
        "exploratory_max_test_f1": EXPECTED_HISTORICAL_F1,
    }.items():
        if protocol_boundary.get(metric_name) != expected:
            raise RuntimeError(f"Protocol historical {metric_name} boundary drifted")
        if methodology_boundary.get(metric_name) != expected:
            raise RuntimeError(f"Methodology historical {metric_name} boundary drifted")

    frame = pd.read_csv(
        STRICT_TABLE_PATH,
        dtype={
            "invoice_no": "string",
            "stock_code": "string",
            "description": "string",
            "country": "string",
        },
        low_memory=False,
    )
    frame["invoice_date"] = pd.to_datetime(frame["invoice_date"], errors="raise")
    for column in [
        "is_valid_net_revenue_line",
        "is_merchandise_net_revenue_line",
        "is_positive_sales_line",
        "is_cancellation_or_return_line",
    ]:
        frame[column] = boolean_series(frame[column])

    records: list[dict[str, Any]] = []
    family_diagnostics: dict[str, list[dict[str, Any]]] = defaultdict(list)
    verified_context_hashes = 0
    for context in private_context["contexts"]:
        start = pd.Timestamp(context["period_start"])
        end = pd.Timestamp(context["period_end_exclusive"])
        period_frame = frame.loc[
            frame["invoice_date"].ge(start) & frame["invoice_date"].lt(end)
        ].copy()
        scope_entities, source_evidence = context_evidence(
            period_frame,
            context["question_family"],
            feasibility_config,
        )
        if scope_entities != context["scope_entities"]:
            raise RuntimeError(f"Frozen scope entity mismatch for {context['context_id']}")
        source_counter = fingerprint_counters(
            normalize_frame(source_evidence[CANONICAL_FIELDS]),
            include_sensitivity_families=False,
        )["canonical_record"]
        source_hash = inventory_manifest_sha256(source_counter)
        if source_hash != context["canonical_evidence_rows_sha256"]:
            raise RuntimeError(f"Frozen context evidence hash mismatch for {context['context_id']}")
        verified_context_hashes += 1

        family = context["question_family"]
        if family == "net_revenue_reconciliation_by_period":
            context_records, diagnostic = build_reconciliation_questions(
                config=config,
                context=context,
                period_frame=period_frame,
            )
        elif family == "product_return_rate_comparison":
            context_records, diagnostic = build_product_return_questions(
                config=config,
                context=context,
                period_frame=period_frame,
            )
        elif family == "country_product_exposure":
            context_records, diagnostic = build_country_exposure_questions(
                config=config,
                context=context,
                period_frame=period_frame,
            )
        else:
            raise RuntimeError(f"Unsupported frozen question family: {family}")
        if len(context_records) != 2:
            raise RuntimeError(f"Expected two questions for {context['context_id']}")
        records.extend(context_records)
        family_diagnostics[family].append(diagnostic)

    split_order = {"protocol_pilot": 0, "development": 1, "confirmation": 2}
    records.sort(
        key=lambda row: (
            split_order[row["split"]],
            row["question_family"],
            row["context_id"],
            row["template_id"],
        )
    )
    question_ids = [row["question_id"] for row in records]
    payload_fingerprints = [row["evidence_payload_sha256"] for row in records]
    content_fingerprints = [row["evidence_content_sha256"] for row in records]
    if len(records) != 96 or len(set(question_ids)) != 96:
        raise RuntimeError(f"Question inventory mismatch: rows={len(records)}, ids={len(set(question_ids))}")

    split_counts = Counter(row["split"] for row in records)
    family_counts = Counter(row["question_family"] for row in records)
    template_counts = Counter(row["template_id"] for row in records)
    context_counts = Counter(row["context_id"] for row in records)
    payload_fingerprint_splits: dict[str, set[str]] = defaultdict(set)
    payload_fingerprint_contexts: dict[str, set[str]] = defaultdict(set)
    content_fingerprint_splits: dict[str, set[str]] = defaultdict(set)
    content_fingerprint_contexts: dict[str, set[str]] = defaultdict(set)
    for row in records:
        payload_fingerprint_splits[row["evidence_payload_sha256"]].add(row["split"])
        payload_fingerprint_contexts[row["evidence_payload_sha256"]].add(row["context_id"])
        content_fingerprint_splits[row["evidence_content_sha256"]].add(row["split"])
        content_fingerprint_contexts[row["evidence_content_sha256"]].add(row["context_id"])
    payload_cross_split = [
        key for key, values in payload_fingerprint_splits.items() if len(values) > 1
    ]
    payload_cross_context = [
        key for key, values in payload_fingerprint_contexts.items() if len(values) > 1
    ]
    content_cross_split = [
        key for key, values in content_fingerprint_splits.items() if len(values) > 1
    ]
    content_cross_context = [
        key for key, values in content_fingerprint_contexts.items() if len(values) > 1
    ]
    historical_content_fingerprints = historical_evidence_content_fingerprints(config)
    historical_content_overlap = sorted(
        set(content_fingerprints).intersection(historical_content_fingerprints)
    )

    critical_checks = {
        "source_context_commitment_matches": observed_context_commitment == EXPECTED_CONTEXT_COMMITMENT,
        "all_48_context_evidence_hashes_recomputed": verified_context_hashes == 48,
        "question_count_is_96": len(records) == 96,
        "two_questions_per_context": len(context_counts) == 48 and set(context_counts.values()) == {2},
        "question_ids_are_unique": len(set(question_ids)) == 96,
        "question_ids_do_not_reuse_historical_ids": not set(question_ids).intersection(
            row["question_id"] for row in load_jsonl(HISTORICAL_QUESTIONS_PATH)
        ),
        "split_question_counts_match_12_30_54": dict(split_counts) == EXPECTED_SPLIT_QUESTION_COUNTS,
        "family_question_counts_are_32_each": dict(family_counts) == {family: 32 for family in EXPECTED_FAMILIES},
        "six_templates_have_16_questions_each": len(template_counts) == 6 and set(template_counts.values()) == {16},
        "all_question_payloads_are_fingerprinted": len(payload_fingerprints) == 96 and all(len(value) == 64 for value in payload_fingerprints),
        "all_evidence_contents_are_fingerprinted": len(content_fingerprints) == 96 and all(len(value) == 64 for value in content_fingerprints),
        "question_payloads_do_not_cross_splits": not payload_cross_split,
        "question_payloads_do_not_cross_contexts": not payload_cross_context,
        "evidence_contents_do_not_cross_splits": not content_cross_split,
        "evidence_contents_do_not_cross_contexts": not content_cross_context,
        "evidence_contents_do_not_match_historical_full100": not historical_content_overlap,
        "all_records_have_gold_answers_and_facts": all(row["gold_answer"] and row["gold_facts"] for row in records),
        "no_prompt_or_model_output_created": all(
            "prompt" not in row and "generated_text" not in row and "model_output" not in row
            for row in records
        ),
    }
    failed_checks = [key for key, value in critical_checks.items() if not value]
    if failed_checks:
        raise RuntimeError(f"Gate 3 critical checks failed: {failed_checks}")

    private_questions = {
        "schema_version": "1.0",
        "status": "confirmation_question_design_v1_private_frozen",
        "study_name": "Confirmation Set v1",
        "frozen_on": config["frozen_on"],
        "public_config_path": repo_path(CONFIG_PATH),
        "public_config_canonical_sha256": canonical_json_sha256(
            config,
            "bizhallu:confirmation-question-design-config:v1",
        ),
        "source": {
            "private_context_manifest_commitment_sha256": observed_context_commitment,
            "strict_window_table_sha256": sha256_file(STRICT_TABLE_PATH),
            "historical_question_count": len(load_jsonl(HISTORICAL_QUESTIONS_PATH)),
            "historical_evidence_content_fingerprint_count": len(historical_content_fingerprints),
        },
        "inventory": {
            "question_count": len(records),
            "split_counts": dict(split_counts),
            "family_counts": dict(family_counts),
            "template_counts": dict(template_counts),
        },
        "questions": records,
        "critical_checks": critical_checks,
        "failed_critical_checks": failed_checks,
        "execution_boundary": {
            "questions_created": True,
            "gold_answers_created": True,
            "evidence_payloads_created": True,
            "prompts_created": False,
            "model_outputs_created": False,
            "labels_created": False,
            "detector_or_verifier_scores_created": False,
            "new_empirical_metrics_created": False,
        },
        "next_gate": {
            "gate": "model_prompt_and_detector_configs_frozen",
            "prompt_generation_authorized": False,
            "model_run_authorized": False,
        },
    }
    PRIVATE_QUESTIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE_QUESTIONS_PATH.write_text(
        json.dumps(private_questions, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    private_commitment = canonical_json_sha256(
        private_questions,
        config["assignment"]["private_question_manifest_domain"],
    )

    nrr_diagnostics = family_diagnostics["net_revenue_reconciliation_by_period"]
    prr_diagnostics = family_diagnostics["product_return_rate_comparison"]
    cpe_diagnostics = family_diagnostics["country_product_exposure"]
    report = {
        "schema_version": "1.0",
        "status": "confirmation_question_design_v1_frozen",
        "study_name": "Confirmation Set v1",
        "frozen_on": config["frozen_on"],
        "scope": "aggregate public commitment to 96 deterministic private questions, gold answers, and question-level evidence payloads",
        "config": {
            "path": repo_path(CONFIG_PATH),
            "status": config["status"],
            "canonical_sha256": canonical_json_sha256(
                config,
                "bizhallu:confirmation-question-design-config:v1",
            ),
        },
        "source_commitments": {
            "private_context_manifest_canonical_sha256": observed_context_commitment,
            "strict_window_table_sha256": sha256_file(STRICT_TABLE_PATH),
            "historical_full100_question_count": 100,
            "historical_full100_evidence_content_fingerprint_count": len(historical_content_fingerprints),
        },
        "private_question_manifest_commitment": {
            "path": repo_path(PRIVATE_QUESTIONS_PATH),
            "git_ignored": True,
            "canonical_sha256": private_commitment,
            "commitment_domain": config["assignment"]["private_question_manifest_domain"],
            "published_contents": False,
        },
        "frozen_inventory": {
            "context_count": len(context_counts),
            "question_count": len(records),
            "questions_per_context": 2,
            "split_counts": dict(split_counts),
            "family_counts": dict(family_counts),
            "template_counts": dict(template_counts),
        },
        "selection_integrity": {
            "outcome_blind": True,
            "selection_seed": config["assignment"]["seed"],
            "question_id_count": len(question_ids),
            "unique_question_id_count": len(set(question_ids)),
            "historical_question_id_overlap_count": 0,
            "product_pairs_reuse_entities_within_context": False,
            "country_questions_reuse_countries_within_context": False,
            "evidence_order_selection_uses_gold_answer": False,
            "country_gold_position_counts": dict(
                sorted(
                    Counter(
                        position
                        for item in cpe_diagnostics
                        for position in item["gold_positions"]
                    ).items()
                )
            ),
            "country_candidate_tables_accidentally_fully_descending": sum(
                item["accidentally_fully_descending_count"]
                for item in cpe_diagnostics
            ),
        },
        "gold_calculation_integrity": {
            "validated_question_count": len(records),
            "recomputed_context_evidence_hash_count": verified_context_hashes,
            "maximum_weekly_reconciliation_error_gbp": max(
                item["weekly_reconciliation_error_gbp"] for item in nrr_diagnostics
            ),
            "selected_reconciliation_positive_cancel_flagged_row_count": sum(
                item["positive_cancel_flagged_row_count"] for item in nrr_diagnostics
            ),
            "reconciliation_sign_policy": "Gross positive line revenue is sign-based. Negative cancellation-and-return revenue is sign-based. One selected source row has a cancellation invoice prefix but positive quantity and revenue; it remains in gross positive line revenue and is disclosed rather than silently removed.",
            "minimum_daily_evidence_row_count": min(
                item["daily_evidence_row_count"] for item in nrr_diagnostics
            ),
            "minimum_eligible_product_count": min(
                item["eligible_product_count"] for item in prr_diagnostics
            ),
            "minimum_selected_product_count_per_context": min(
                item["selected_product_count"] for item in prr_diagnostics
            ),
            "minimum_product_pair_percentage_point_difference": min(
                item["minimum_percentage_point_difference"] for item in prr_diagnostics
            ),
            "selected_product_return_ratio_percentage_range": [
                min(item["minimum_selected_ratio_percentage"] for item in prr_diagnostics),
                max(item["maximum_selected_ratio_percentage"] for item in prr_diagnostics),
            ],
            "selected_product_return_ratio_over_100_count": sum(
                item["selected_ratio_over_100_count"] for item in prr_diagnostics
            ),
            "selected_product_return_ratio_interpretation": "A value above 100% can occur because same-week negative units are not linked to the original positive sale; retain as a recorded ratio, not a causal return rate.",
            "minimum_country_positive_product_candidate_pool": min(
                item["minimum_positive_product_candidate_pool"] for item in cpe_diagnostics
            ),
            "country_gold_share_percentage_range": [
                min(item["minimum_gold_share_percentage"] for item in cpe_diagnostics),
                max(item["maximum_gold_share_percentage"] for item in cpe_diagnostics),
            ],
        },
        "evidence_payload_integrity": {
            "fingerprint_domain": config["assignment"]["question_evidence_payload_domain"],
            "fingerprint_count": len(payload_fingerprints),
            "unique_fingerprint_count": len(set(payload_fingerprints)),
            "cross_split_fingerprint_count": len(payload_cross_split),
            "cross_context_fingerprint_count": len(payload_cross_context),
            "content_comparison_domain": config["assignment"]["evidence_content_comparison_domain"],
            "content_projection": "normalized evidence-table row multiset with documented field aliases; wrapper metadata excluded",
            "content_fingerprint_count": len(content_fingerprints),
            "unique_content_fingerprint_count": len(set(content_fingerprints)),
            "content_cross_split_fingerprint_count": len(content_cross_split),
            "content_cross_context_fingerprint_count": len(content_cross_context),
            "historical_full100_content_fingerprint_count": len(historical_content_fingerprints),
            "historical_full100_content_fingerprint_overlap_count": len(historical_content_overlap),
            "question_level_evidence_payload_fingerprint_check": "complete",
        },
        "privacy": {
            "contains_question_text": False,
            "contains_question_ids": False,
            "contains_selected_periods": False,
            "contains_context_ids": False,
            "contains_scope_entity_values": False,
            "contains_evidence_rows": False,
            "contains_only_rules_aggregate_counts_and_whole_manifest_commitment": True,
        },
        "current_result_boundary": {
            "historical_exploratory_max_test_auprc": protocol_boundary["exploratory_max_test_auprc"],
            "historical_exploratory_max_test_f1": protocol_boundary["exploratory_max_test_f1"],
            "new_confirmation_metric_reported": False,
            "detector_superiority_claim_authorized": False,
        },
        "execution_boundary": {
            "question_created": True,
            "gold_answer_created": True,
            "evidence_payload_created": True,
            "prompt_created": False,
            "model_run_performed": False,
            "annotation_created": False,
            "detector_or_verifier_scoring_performed": False,
            "new_metrics_reported": False,
            "execution_ready": False,
            "no_new_results": True,
        },
        "next_gate": {
            "gate": "model_prompt_and_detector_configs_frozen",
            "authorized_scope": "Freeze model revision, tokenizer revision, prompt template, decoding policy, internal detector fields, literature-baseline feasibility decisions, and metric implementations before protocol-pilot generation.",
            "still_forbidden": [
                "Qwen execution",
                "annotation",
                "detector or verifier scoring",
                "confirmation-set access",
                "new empirical metrics",
            ],
        },
        "critical_checks": critical_checks,
        "num_failures": 0,
        "failures": [],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "question_count": report["frozen_inventory"]["question_count"],
                "split_counts": report["frozen_inventory"]["split_counts"],
                "family_counts": report["frozen_inventory"]["family_counts"],
                "unique_evidence_payloads": report["evidence_payload_integrity"]["unique_fingerprint_count"],
                "unique_evidence_contents": report["evidence_payload_integrity"]["unique_content_fingerprint_count"],
                "cross_split_payloads": report["evidence_payload_integrity"]["cross_split_fingerprint_count"],
                "cross_split_evidence_contents": report["evidence_payload_integrity"]["content_cross_split_fingerprint_count"],
                "historical_evidence_content_overlap": report["evidence_payload_integrity"]["historical_full100_content_fingerprint_overlap_count"],
                "private_commitment": private_commitment,
                "next_gate": report["next_gate"]["gate"],
            },
            indent=2,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
