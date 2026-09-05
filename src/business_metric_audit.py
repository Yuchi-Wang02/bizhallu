"""Stage A business-scope sensitivity. Never overwrite historical gold or traces."""
from __future__ import annotations

import copy
import csv
import hashlib
import json
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/business_metric_contract_v1_1.json"
REPORT = ROOT / "reports/bizhallu_business_metric_audit_report.json"
ROWS = ROOT / "reports/bizhallu_historical_metric_sensitivity.csv"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def canonical(value, domain):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256((domain + "\0" + payload).encode()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")


def decimal_value(value):
    out = Decimal(str(value))
    if not out.is_finite():
        raise ValueError("Non-finite business value")
    return out


def money(value):
    return float(decimal_value(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def ratio(numerator, denominator):
    if decimal_value(denominator) <= 0:
        raise ValueError("Ratio requires a positive denominator")
    return money(decimal_value(numerator) / decimal_value(denominator) * 100)


def flag(value):
    if value is True or str(value).lower() == "true":
        return True
    if value is False or str(value).lower() == "false":
        return False
    raise ValueError("Invalid source boolean")


def ledger_profile(frame, contract):
    """Independent Decimal aggregation from quantity and source price, not saved revenue."""
    bins = {}
    positive_cancel_count = 0
    cancel_negative = decimal_value(0)
    cancel_positive = decimal_value(0)
    unflagged_negative = decimal_value(0)
    for row in frame.itertuples(index=False):
        value = decimal_value(row.quantity) * decimal_value(row.unit_price)
        nonmerch = flag(row.is_non_merchandise)
        code = str(row.stock_code).strip().upper()
        bucket = "merchandise"
        if nonmerch:
            bucket = next((name for name, codes in contract["non_merchandise_categories"].items()
                           if code in codes), "unknown_non_merchandise")
        item = bins.setdefault(bucket, {"row_count": 0, "positive": Decimal(0), "negative": Decimal(0)})
        item["row_count"] += 1
        item["positive" if value > 0 else "negative"] += value
        if flag(row.is_cancel_invoice):
            if value > 0:
                positive_cancel_count += 1
                cancel_positive += value
            else:
                cancel_negative += value
        elif value < 0:
            unflagged_negative += value
    positive = sum((x["positive"] for x in bins.values()), Decimal(0))
    negative = sum((x["negative"] for x in bins.values()), Decimal(0))
    nonmerch_negative = sum((x["negative"] for k, x in bins.items() if k != "merchandise"), Decimal(0))
    return {
        "eligible_line_count": len(frame),
        "positive_transaction_value_gbp": money(positive),
        "negative_transaction_value_gbp": money(negative),
        "net_transaction_value_gbp": money(positive + negative),
        "non_merchandise_negative_magnitude_gbp": money(-nonmerch_negative),
        "non_merchandise_share_of_negative_value_percentage": ratio(-nonmerch_negative, -negative),
        "positive_cancel_flagged_line_count": positive_cancel_count,
        "positive_cancel_flagged_value_gbp": money(cancel_positive),
        "negative_cancel_flagged_value_gbp": money(cancel_negative),
        "negative_value_without_cancel_flag_gbp": money(unflagged_negative),
        "categories": [{"category": k, "row_count": v["row_count"],
                        "positive_value_gbp": money(v["positive"]), "negative_value_gbp": money(v["negative"]),
                        "net_value_gbp": money(v["positive"] + v["negative"])} for k, v in sorted(bins.items())],
        "reconciliation_residual_gbp": money(positive + negative - sum(
            (x["positive"] + x["negative"] for x in bins.values()), Decimal(0))),
        "physical_return_value": None,
        "physical_return_value_status": "not_identifiable_from_source_fields",
    }


def aggregate_tables(frame, stock_grain=False):
    work = frame.copy()
    work["positive"] = work.revenue.clip(lower=0)
    work["negative"] = work.revenue.clip(upper=0)

    def group(data, keys):
        return data.groupby(keys, as_index=False).agg(
            net_revenue=("revenue", "sum"), gross_positive_revenue=("positive", "sum"),
            cancellation_revenue=("negative", "sum"), invoice_count=("invoice_no", "nunique"))

    merch = work.loc[~work.is_non_merchandise]
    if stock_grain:
        product = group(merch, ["year_month", "stock_code"])
        names = merch.groupby(["year_month", "stock_code", "description"]).size().reset_index(name="n")
        names = names.sort_values(["year_month", "stock_code", "n", "description"], ascending=[True, True, False, True])
        names = names.drop_duplicates(["year_month", "stock_code"])
        product = product.merge(names[["year_month", "stock_code", "description"]], on=["year_month", "stock_code"], validate="one_to_one")
    else:
        product = group(merch, ["year_month", "stock_code", "description"])
    return {"monthly_net": group(work, ["year_month"]),
            "country_month_net": group(work, ["year_month", "country"]), "product_month_net": product}


def answer_for(question, tables):
    """Re-evaluate the original filters; never let a scope change choose new questions."""
    gold = copy.deepcopy(question["gold_answer"])
    kind, filters = question["question_type"], question["evidence"]["filters"]
    if kind in {"top_country_month", "country_comparison_month"}:
        rows = tables["country_month_net"]
        rows = rows.loc[rows.year_month.eq(filters["year_month"])]
        if kind == "top_country_month":
            rows = rows.loc[~rows.country.isin(filters["exclude_countries"])].sort_values(["net_revenue", "country"], ascending=[False, True])
            gold.update(country=str(rows.iloc[0].country), net_revenue=money(rows.iloc[0].net_revenue))
        else:
            a, b = gold["country_a"], gold["country_b"]
            va = money(rows.loc[rows.country.eq(a)].iloc[0].net_revenue)
            vb = money(rows.loc[rows.country.eq(b)].iloc[0].net_revenue)
            gold.update(country_a_net_revenue=va, country_b_net_revenue=vb,
                        higher_country=a if va >= vb else b, lower_country=b if va >= vb else a, revenue_delta=money(abs(va-vb)))
    elif kind in {"monthly_revenue_change", "return_impact_month"}:
        monthly = tables["monthly_net"].set_index("year_month")
        if kind == "monthly_revenue_change":
            prev = money(monthly.loc[filters["previous_month"], "net_revenue"])
            curr = money(monthly.loc[filters["current_month"], "net_revenue"])
            change = money(curr-prev)
            gold.update(previous_net_revenue=prev, current_net_revenue=curr, absolute_change=change,
                        percent_change=ratio(change, abs(prev)), direction="increase" if change >= 0 else "decrease")
        else:
            row = monthly.loc[filters["year_month"]]
            p, n = money(row.gross_positive_revenue), money(row.cancellation_revenue)
            gold.update(gross_positive_revenue=p, cancellation_revenue=n, reduction_amount=abs(n),
                        reduction_rate_percent=ratio(abs(n), p), net_revenue=money(row.net_revenue))
    elif kind in {"top_product_month", "top3_products_month", "product_revenue_share_month"}:
        rows = tables["product_month_net"]
        rows = rows.loc[rows.year_month.eq(filters["year_month"])].sort_values(
            ["net_revenue", "stock_code", "description"], ascending=[False, True, True])
        k = filters.get("top_k", filters.get("top_n", 1))
        top = rows.head(k)
        ranking = [{"rank": i+1, "stock_code": str(r.stock_code), "description": str(r.description),
                    "merchandise_net_revenue": money(r.net_revenue)} for i, r in enumerate(top.itertuples())]
        if kind == "top_product_month":
            gold.update({key: value for key, value in ranking[0].items() if key != "rank"})
        else:
            gold["top_products"] = ranking
        if kind == "product_revenue_share_month":
            numerator, denominator = money(top.net_revenue.sum()), money(rows.net_revenue.sum())
            gold.update(numerator_merchandise_net_revenue=numerator, total_merchandise_net_revenue=denominator,
                        share_percent=ratio(numerator, denominator))
    else:
        raise ValueError(f"Unsupported historical question type: {kind}")
    return gold


def differences(old, new, path=""):
    if isinstance(old, dict):
        if set(old) != set(new):
            raise ValueError("Gold schema drift")
        return [v for k in old for v in differences(old[k], new[k], f"{path}.{k}".strip("."))]
    if isinstance(old, list):
        if len(old) != len(new):
            return [{"field": path, "old": old, "new": new, "kind": "categorical"}]
        return [v for i, (a, b) in enumerate(zip(old, new)) for v in differences(a, b, f"{path}[{i}]")]
    if old == new:
        return []
    return [{"field": path, "old": old, "new": new,
             "kind": "numeric" if isinstance(old, (int, float)) else "categorical"}]


def main():
    import pandas as pd
    import clean_online_retail as cleaner
    import generate_questions as historical
    contract = load(CONTRACT)
    source = ROOT / "data/processed/retail_net_revenue_lines.csv"
    gold_path = ROOT / "data/processed/business_questions_gold.jsonl"
    frame = pd.read_csv(source, dtype={"invoice_no": str, "stock_code": str, "description": str}, low_memory=False)
    for col in ["is_non_merchandise", "is_cancel_invoice", "is_exact_duplicate", "is_nonpositive_unit_price", "is_missing_description"]:
        frame[col] = frame[col].map(flag)
    if frame[["is_exact_duplicate", "is_nonpositive_unit_price", "is_missing_description"]].any().any():
        raise ValueError("Historical eligible table includes excluded lines")
    source_products = frame.quantity * frame.unit_price
    if (source_products-frame.revenue).abs().max() > 1e-8:
        raise ValueError("Historical stored line values differ from quantity times price")
    questions = [json.loads(line) for line in gold_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(questions) != 100 or len({q["question_id"] for q in questions}) != 100:
        raise ValueError("Historical inventory is not 100 unique questions")
    # Exact replay uses original functions and original pandas/round policy, without their writers.
    legacy_tables = {"monthly_net": cleaner._summarize_monthly_net(frame),
                     "country_month_net": cleaner._summarize_country_month_net(frame),
                     "product_month_net": cleaner._summarize_product_month_net(frame.loc[~frame.is_non_merchandise]),
                     "monthly_coverage": historical.load_tables()["monthly_coverage"]}
    replay = []
    for kind in historical.QUESTION_TYPE_QUOTAS:
        replay.extend(getattr(historical, f"generate_{kind}")(legacy_tables))
    replay = historical.assign_ids_and_splits(replay)
    if len(replay) != 100 or any(a["question_id"] != b["question_id"] or a["gold_answer"] != b["gold_answer"] for a, b in zip(questions, replay)):
        raise ValueError("Historical gold does not reproduce; stop before sensitivity analysis")

    # Explicit retrospective candidate records, not an inferred cancellation matching algorithm.
    candidates = [("541431", "23166", 74215, "1.04"), ("C541433", "23166", -74215, "1.04"),
                  ("556444", "22502", 60, "649.50"), ("C556445", "M", -1, "38970.00")]
    scenario_mask = pd.Series(False, index=frame.index)
    candidate_rows = []
    for invoice, code, qty, price in candidates:
        mask = frame.invoice_no.eq(invoice) & frame.stock_code.eq(code) & frame.quantity.eq(qty) & frame.unit_price.eq(float(price))
        if int(mask.sum()) != 1:
            raise ValueError("Documented candidate record is not unique")
        scenario_mask |= mask
        row = frame.loc[mask].iloc[0]
        candidate_rows.append({"invoice_no": invoice, "stock_code": code, "quantity": qty,
                               "unit_price_gbp": price, "value_gbp": money(decimal_value(qty)*decimal_value(price)),
                               "scope": "non_merchandise" if row.is_non_merchandise else "merchandise"})
    scenarios = {
        "wording_only": None,
        "merchandise_scope": aggregate_tables(frame.loc[~frame.is_non_merchandise]),
        "stock_code_grain": aggregate_tables(frame, True),
        "merchandise_scope_and_stock_code_grain": aggregate_tables(frame.loc[~frame.is_non_merchandise], True),
        "exclude_documented_candidate_pairs": aggregate_tables(frame.loc[~scenario_mask]),
    }
    rows = []
    for name, tables in scenarios.items():
        for q in questions:
            alt = q["gold_answer"] if tables is None else answer_for(q, tables)
            diff = differences(q["gold_answer"], alt)
            ranking_keys = {"stock_code", "country", "higher_country", "lower_country", "direction"}
            rank_changed = any(d["field"].split(".")[-1] in ranking_keys for d in diff)
            numeric_changed = any(d["kind"] == "numeric" for d in diff)
            rows.append({"question_id": q["question_id"], "split": q["split"], "question_type": q["question_type"],
                         "scenario": name, "answer_changed": bool(diff), "numeric_changed": numeric_changed,
                         "entity_rank_or_direction_changed": rank_changed,
                         "interpretation_changed": name == "wording_only" and q["question_type"] in {
                             "return_impact_month", "monthly_revenue_change", "top_country_month", "country_comparison_month"},
                         "changed_fields": json.dumps(diff, ensure_ascii=True, allow_nan=False),
                         "historical_gold": json.dumps(q["gold_answer"], ensure_ascii=True, allow_nan=False),
                         "scenario_answer": json.dumps(alt, ensure_ascii=True, allow_nan=False)})
    ROWS.parent.mkdir(parents=True, exist_ok=True)
    with ROWS.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    strict = ROOT / "data/processed/confirmation_online_retail_ii/strict_window_lines.csv.gz"
    new = pd.read_csv(strict, dtype={"invoice_no": str, "stock_code": str}, low_memory=False)
    for dataset in [frame, new]:
        codes = dataset.stock_code.str.strip().str.upper()
        expected_nonmerch = codes.isin(contract["merchandise_policy"]["exclude_stock_codes"]) | ~codes.str.contains(r"\d", regex=True)
        if not expected_nonmerch.equals(dataset.is_non_merchandise.map(flag)):
            raise ValueError("Source merchandise flags disagree with metric contract")
    expected_valid = ~(new.is_exact_duplicate.map(flag) | new.is_nonpositive_unit_price.map(flag) | new.is_missing_description.map(flag))
    if not expected_valid.equals(new.is_valid_net_revenue_line.map(flag)):
        raise ValueError("Strict-window validity flags disagree with source rules")
    valid = new.loc[new.is_valid_net_revenue_line.map(flag)]
    old_profile, new_profile = ledger_profile(frame, contract), ledger_profile(valid, contract)
    baseline_net = money(frame.revenue.sum())
    if abs(baseline_net-old_profile["net_transaction_value_gbp"]) > .01 or abs(money(valid.line_revenue.sum())-new_profile["net_transaction_value_gbp"]) > .01:
        raise ValueError("Independent Decimal ledger reconciliation differs")
    summary = [{"scenario": name, "question_count": 100,
                **{k: sum(bool(r[k]) for r in rows if r["scenario"] == name) for k in [
                    "answer_changed", "numeric_changed", "entity_rank_or_direction_changed", "interpretation_changed"]}}
               for name in scenarios]
    report = {"status": "business_metric_scope_audit_complete", "contract": str(CONTRACT.relative_to(ROOT)).replace("\\", "/"),
              "contract_sha256": canonical(contract, "bizhallu:metric-contract:v1.1"),
              "historical_question_count": 100, "historical_gold_replay_count": 100,
              "scenario_row_count": len(rows), "scenario_summary": summary,
              "historical_eligible_ledger": old_profile, "strict_prior_window_eligible_ledger": new_profile,
              "source_raw_counts": {"historical": 541909, "strict_prior_window": len(new)},
              "source_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p) for p in [source, gold_path, strict]},
              "candidate_pair_sensitivity": {"records": candidate_rows,
                  "justification": "Same-code January reversal and cross-code June amount match flagged in retrospective audit. Matching magnitude and nearby time do not prove business linkage.",
                  "interpretation": "What-if excluding these four specified records only, preserving every other source row; not a corrected dataset or automatic offset."},
              "historical_metrics_changed": False, "model_run_performed": False,
              "new_confirmation_periods_disclosed": False, "num_failures": 0,
              "limitations": ["Business categories are code heuristics, not physical-return adjudication.",
                  "Sensitivity counts describe gold answer changes, not model correctness or detector performance.",
                  "Product grain scenario uses modal description per stock code; name-only changes are separate from rank changes.",
                  "Legacy source filters and raw-data policy remain unchanged; partial December 2011 remains partial."]}
    write_json(REPORT, report)
    print(json.dumps({"report": str(REPORT.relative_to(ROOT)), "scenario_summary": summary}))


if __name__ == "__main__":
    main()
