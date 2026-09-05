"""Generate an outcome-blind v1.1 without modifying either original private manifest."""
from __future__ import annotations

import copy
import json
from collections import Counter

from business_metric_audit import ROOT, canonical, decimal_value, digest, flag, load, money, write_json

CONFIG = ROOT / "configs/confirmation_metric_amendment_v1_1.json"
REPORT = ROOT / "reports/bizhallu_metric_amendment_v1_1_report.json"


def rename_fields(value, aliases, schema_strings=False):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            target = aliases.get(key, key)
            if target in result:
                raise ValueError("Colliding metric aliases")
            result[target] = rename_fields(item, aliases, key in {"field", "columns"})
        return result
    if isinstance(value, list):
        return [rename_fields(item, aliases, schema_strings) for item in value]
    return aliases.get(value, value) if schema_strings and isinstance(value, str) else value


def amend_record(old, config, contract, legacy_config):
    from validate_confirmation_question_design import evidence_content_sha256
    item = rename_fields(copy.deepcopy(old), config["field_renames"])
    template = old["template_id"]
    family = template.split("_")[0]
    item["source_question_id"] = old["question_id"]
    item["source_template_id"] = template
    item["template_id"] = template.removesuffix("_v1") + "_v1_1"
    gold = item["gold_answer"]
    params = dict(gold)
    if family == "prr":
        for slot in ["a", "b"]:
            params[f"product_{slot}_name"] = gold[f"product_{slot}"]["product_name"]
            params[f"product_{slot}_code"] = gold[f"product_{slot}"]["stock_code"]
    item["question"] = config["templates"][template].format(**params)
    if template == "nrr_weekly_reconciliation_v1":
        p, n, total = (gold[k] for k in ["positive_transaction_value_gbp", "negative_transaction_magnitude_gbp", "net_transaction_value_gbp"])
        item["gold_short_answer"] = f"Positive transaction value GBP {p:,.2f} minus negative magnitude GBP {n:,.2f} equals net transaction value GBP {total:,.2f}. This includes non-merchandise lines."
    elif template == "nrr_daily_cancellation_hotspot_v1":
        item["gold_short_answer"] = (f"{gold['business_date']} had negative transaction magnitude GBP "
            f"{gold['negative_transaction_magnitude_gbp']:,.2f}, positive transaction value GBP "
            f"{gold['positive_transaction_value_gbp']:,.2f}, and a negative-to-positive value ratio of "
            f"{gold['negative_value_share_of_positive_percentage']:.2f}%.")
    elif family == "cpe":
        item["gold_short_answer"] = old["gold_short_answer"].replace("merchandise net revenue", "merchandise net transaction value")
    evidence = item["evidence"]
    evidence["schema_version"] = "1.1"
    evidence["template_id"] = item["template_id"]
    evidence["metadata"] = {
        **{k: v for k, v in old["evidence"]["metadata"].items() if k in {"period_start", "period_end_inclusive", "country"}},
        "metric_contract_id": contract["contract_id"],
        "metric_contract_sha256": canonical(contract, "bizhallu:metric-contract:v1.1"),
        "metric_definition": config["metadata_rules"][family],
    }
    item["metric_contract_id"] = contract["contract_id"]
    item["evidence_payload_sha256"] = canonical(evidence, config["payload_domain"])
    # Field names change, not business content. Normalize aliases to the ORIGINAL domain.
    comparison = copy.deepcopy(legacy_config)
    aliases = comparison["fingerprint_policy"]["content_field_aliases"]
    for old_key, new_key in config["field_renames"].items():
        aliases[new_key] = aliases.get(old_key, old_key)
    item["evidence_content_sha256"] = evidence_content_sha256(evidence, comparison)
    item["question_id"] = "cv1_1q_" + canonical({"context_id": item["context_id"],
        "template_id": item["template_id"], "payload": item["evidence_payload_sha256"]}, config["question_id_domain"])[:20]
    return item


def assert_numeric_source(record, frame):
    """Independent source arithmetic using Decimal, not saved line_revenue or gold totals."""
    rows = record["evidence"]["rows"]
    kind = record["template_id"].split("_")[0]
    eligible = frame.loc[frame.is_valid_net_revenue_line]
    checks = 0

    def amount(data, sign=0):
        values = [decimal_value(q)*decimal_value(p) for q, p in zip(data.quantity, data.unit_price)]
        if sign:
            values = [x for x in values if (x > 0 if sign > 0 else x < 0)]
        return money(sum(values, decimal_value(0)))

    def close(a, b):
        nonlocal checks
        if abs(decimal_value(a)-decimal_value(b)) > decimal_value("0.01"):
            raise ValueError("Independent source arithmetic mismatch (private values omitted)")
        checks += 1

    for row in rows:
        if kind == "nrr":
            data = eligible
            if "business_date" in row:
                data = data.loc[data.invoice_date.dt.strftime("%Y-%m-%d").eq(row["business_date"])]
            close(row["gross_positive_revenue_gbp"], amount(data, 1))
            close(row["cancellation_return_revenue_gbp"], amount(data, -1))
        elif kind == "prr":
            data = eligible.loc[eligible.is_merchandise_net_revenue_line & eligible.stock_code.eq(row["stock_code"])]
            positive, negative = data.loc[data.quantity > 0], data.loc[data.quantity < 0]
            for key, value in {"positive_units": int(positive.quantity.sum()), "returned_units": int(-negative.quantity.sum()),
                               "positive_invoice_count": positive.invoice_no.nunique(), "return_invoice_count": negative.invoice_no.nunique()}.items():
                if row[key] != value:
                    raise ValueError("Independent unit/invoice count mismatch")
                checks += 1
        elif kind == "cpe":
            country = eligible.loc[eligible.is_merchandise_net_revenue_line & eligible.country.eq(row["country"])]
            close(row["country_merchandise_net_revenue_gbp"], amount(country))
            close(row["product_merchandise_net_revenue_gbp"], amount(country.loc[country.stock_code.eq(row["stock_code"])]))
        else:
            raise ValueError("Unknown template family")
    return checks


def generate():
    import pandas as pd
    import freeze_confirmation_question_design as legacy
    from validate_confirmation_question_design import validate_gold_record
    from freeze_confirmation_context_manifest import context_evidence
    from profile_confirmation_dataset_overlap import CANONICAL_FIELDS, fingerprint_counters, inventory_manifest_sha256, normalize_frame

    config = load(CONFIG)
    contract = load(ROOT / config["metric_contract"])
    legacy_config = load(ROOT / config["historical_design"])
    context_path = legacy.PRIVATE_CONTEXT_PATH
    old_path = legacy.PRIVATE_QUESTIONS_PATH
    source_paths = [context_path, old_path, legacy.STRICT_TABLE_PATH, ROOT / config["historical_design"]]
    before = {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p) for p in source_paths}
    contexts, old = load(context_path), load(old_path)
    if canonical(contexts, "bizhallu:confirmation-private-context-manifest:v1") != config["source_context_commitment"]:
        raise ValueError("Context commitment mismatch")
    if canonical(old, "bizhallu:confirmation-private-question-manifest:v1") != config["source_question_commitment"]:
        raise ValueError("Original question commitment mismatch")
    if digest(legacy.STRICT_TABLE_PATH) != legacy_config["inputs"]["strict_window_table_sha256"]:
        raise ValueError("Strict-window source hash mismatch")
    frame = pd.read_csv(legacy.STRICT_TABLE_PATH, dtype={"invoice_no": "string", "stock_code": "string", "description": "string", "country": "string"}, low_memory=False)
    frame["invoice_date"] = pd.to_datetime(frame.invoice_date, errors="raise")
    for key in ["is_valid_net_revenue_line", "is_merchandise_net_revenue_line", "is_positive_sales_line", "is_cancellation_or_return_line"]:
        frame[key] = frame[key].map(flag)
    feasibility = load(legacy.FEASIBILITY_CONFIG_PATH)
    old_map = {q["question_id"]: q for q in old["questions"]}
    if len(old_map) != 96:
        raise ValueError("Original question inventory mismatch")
    generated, source_checks, checked_contexts = {}, 0, 0
    for context in contexts["contexts"]:
        data = frame.loc[frame.invoice_date.ge(pd.Timestamp(context["period_start"])) & frame.invoice_date.lt(pd.Timestamp(context["period_end_exclusive"]))].copy()
        entities, evidence = context_evidence(data, context["question_family"], feasibility)
        if entities != context["scope_entities"]:
            raise ValueError("Frozen entities changed")
        fingerprint = inventory_manifest_sha256(fingerprint_counters(normalize_frame(evidence[CANONICAL_FIELDS]), include_sensitivity_families=False)["canonical_record"])
        if fingerprint != context["canonical_evidence_rows_sha256"]:
            raise ValueError("Frozen context evidence changed")
        checked_contexts += 1
        function = {"net_revenue_reconciliation_by_period": legacy.build_reconciliation_questions,
                    "product_return_rate_comparison": legacy.build_product_return_questions,
                    "country_product_exposure": legacy.build_country_exposure_questions}[context["question_family"]]
        records, _ = function(config=legacy_config, context=context, period_frame=data)
        for record in records:
            if record != old_map.get(record["question_id"]):
                raise ValueError("Source replay changed original question/gold/evidence")
            failures = []
            validate_gold_record(record, failures)
            if failures:
                raise ValueError("Independent gold arithmetic failed (details kept private)")
            source_checks += assert_numeric_source(record, data)
            generated[record["question_id"]] = amend_record(record, config, contract, legacy_config)
    new = [generated[q["question_id"]] for q in old["questions"]]
    reverse = {v: k for k, v in config["field_renames"].items()}
    for original, amended in zip(old["questions"], new):
        for key in ["context_id", "split", "question_family", "period_start", "period_end_exclusive", "selection_provenance"]:
            if amended[key] != original[key]:
                raise ValueError("Amendment changed allocation or selection")
        for key in ["gold_answer", "gold_facts"]:
            if rename_fields(amended[key], reverse) != original[key]:
                raise ValueError("Amendment changed numeric gold or targets")
        if rename_fields(amended["evidence"]["rows"], reverse) != original["evidence"]["rows"]:
            raise ValueError("Evidence values or row order changed")
        if amended["evidence_content_sha256"] != original["evidence_content_sha256"]:
            raise ValueError("Schema rename altered normalized business content")
    if len(new) != 96 or len({q["question_id"] for q in new}) != 96 or len({q["evidence_content_sha256"] for q in new}) != 96:
        raise ValueError("Amended inventory is not 96 unique questions and contents")
    if {q["evidence_content_sha256"] for q in new} & legacy.historical_evidence_content_fingerprints(legacy_config):
        raise ValueError("Amended contents overlap historical evidence")
    after = {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p) for p in source_paths}
    if before != after:
        raise ValueError("Protected inputs changed during amendment")
    private = {"schema_version": "1.1", "status": "business_definition_amendment_frozen_not_execution_ready",
               "amendment_id": config["amendment_id"], "config_sha256": canonical(config, "bizhallu:metric-amendment-config:v1.1"),
               "metric_contract_sha256": canonical(contract, "bizhallu:metric-contract:v1.1"),
               "source_context_commitment": config["source_context_commitment"],
               "source_question_commitment": config["source_question_commitment"],
               "questions": new, "execution_boundary": config["execution_boundary"]}
    report = {"status": "metric_amendment_v1_1_gate3_revalidated", "amendment_id": config["amendment_id"],
              "config_sha256": private["config_sha256"], "metric_contract_sha256": private["metric_contract_sha256"],
              "source_context_commitment": config["source_context_commitment"], "source_question_commitment": config["source_question_commitment"],
              "amended_question_commitment": canonical(private, config["commitment_domain"]),
              "question_count": len(new), "context_count": checked_contexts,
              "question_counts_by_split": dict(Counter(q["split"] for q in new)),
              "question_counts_by_family": dict(Counter(q["question_family"] for q in new)),
              "replayed_original_question_count": len(generated), "independent_source_arithmetic_checks": source_checks,
              "unchanged_gold_numeric_and_entity_payloads": 96, "unchanged_evidence_content_count": 96,
              "changed_question_wording_count": sum(a["question"] != b["question"] for a, b in zip(old["questions"], new)),
              "unique_amended_payloads": len({q["evidence_payload_sha256"] for q in new}),
              "cross_split_evidence_overlap": 0, "historical_evidence_overlap": 0,
              "source_artifacts_unchanged": before == after, "protected_source_sha256": before,
              "execution_boundary": config["execution_boundary"],
              "gate_status": "3_complete_4_pending_no_run_authorized", "num_failures": 0,
              "scope_note": "Gate 3 business-definition amendment only. Independent human review, metric hardening, model freeze and verifier remain incomplete."}
    return private, report


def main():
    config = load(CONFIG)
    private, report = generate()
    path = ROOT / config["private_output"]
    if path.exists() and load(path) != private:
        raise ValueError("Existing v1.1 private manifest differs; use a new version, never overwrite a frozen amendment")
    write_json(path, private)
    write_json(REPORT, report)
    print(json.dumps({k: report[k] for k in ["status", "question_count", "context_count", "independent_source_arithmetic_checks", "amended_question_commitment"]}))


if __name__ == "__main__":
    main()
