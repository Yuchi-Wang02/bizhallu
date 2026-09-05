"""Standard-library public checks; --require-local independently replays private/source checks."""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter

from business_metric_audit import ROOT, REPORT as AUDIT, ROWS, canonical, decimal_value, differences, load, write_json
from build_metric_amendment import CONFIG, REPORT
from public_paths import contains_local_path

OUTPUT = ROOT / "reports/bizhallu_metric_amendment_v1_1_validation.json"


def validate_public():
    cfg = load(CONFIG)
    contract = load(ROOT / cfg["metric_contract"])
    report, audit = load(REPORT), load(AUDIT)
    failures = []

    def check(name, actual):
        if not actual:
            failures.append(name)

    check("config_hash", report.get("config_sha256") == canonical(cfg, "bizhallu:metric-amendment-config:v1.1"))
    expected_contract = canonical(contract, "bizhallu:metric-contract:v1.1")
    check("contract_hash", report.get("metric_contract_sha256") == audit.get("contract_sha256") == expected_contract)
    active = load(ROOT / "configs/confirmation_set_v1_protocol.json").get("active_business_definition", {})
    check("active_amendment_pointer", active.get("amendment") == "configs/confirmation_metric_amendment_v1_1.json"
          and active.get("private_question_manifest") == cfg["private_output"]
          and active.get("private_question_manifest_commitment_sha256") == report.get("amended_question_commitment"))
    check("original_commitments", report.get("source_context_commitment") == cfg["source_context_commitment"] and report.get("source_question_commitment") == cfg["source_question_commitment"])
    check("amended_commitment", bool(re.fullmatch("[0-9a-f]{64}", report.get("amended_question_commitment", ""))))
    check("execution_closed", report.get("execution_boundary") == cfg["execution_boundary"] and not any(cfg["execution_boundary"].values()))
    check("gate3_scope", report.get("gate_status") == "3_complete_4_pending_no_run_authorized")
    check("96_questions", report.get("question_count") == report.get("replayed_original_question_count") == report.get("unchanged_gold_numeric_and_entity_payloads") == report.get("unchanged_evidence_content_count") == report.get("unique_amended_payloads") == 96)
    check("48_contexts", report.get("context_count") == 48)
    check("split_preserved", report.get("question_counts_by_split") == {"protocol_pilot": 12, "development": 30, "confirmation": 54})
    check("source_checks_recorded", report.get("independent_source_arithmetic_checks", 0) > 0)
    check("no_overlap", report.get("cross_split_evidence_overlap") == report.get("historical_evidence_overlap") == 0)
    check("source_unchanged", report.get("source_artifacts_unchanged") is True)
    check("all_100_replayed", audit.get("historical_question_count") == audit.get("historical_gold_replay_count") == 100)
    check("no_model_or_metric_changes", audit.get("model_run_performed") is False and audit.get("historical_metrics_changed") is False)
    for key in ["historical_eligible_ledger", "strict_prior_window_eligible_ledger"]:
        item = audit[key]
        p, n, net = [decimal_value(item[x]) for x in ["positive_transaction_value_gbp", "negative_transaction_value_gbp", "net_transaction_value_gbp"]]
        check(key+"_signs", p >= 0 and n <= 0)
        check(key+"_reconciliation", abs(p+n-net) <= decimal_value("0.01"))
        check(key+"_partition", sum(x["row_count"] for x in item["categories"]) == item["eligible_line_count"])
        for category_key, total in [("positive_value_gbp", p), ("negative_value_gbp", n), ("net_value_gbp", net)]:
            check(key+category_key, abs(sum((decimal_value(x[category_key]) for x in item["categories"]), decimal_value(0))-total) <= decimal_value("0.02"))
        check(key+"_return_unknown", item["physical_return_value"] is None and item["physical_return_value_status"] == "not_identifiable_from_source_fields")
    with ROWS.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    check("500_sensitivity_rows", len(rows) == audit.get("scenario_row_count") == 500)
    check("unique_question_scenario", len({(r["question_id"], r["scenario"]) for r in rows}) == 500)
    for summary in audit["scenario_summary"]:
        group = [r for r in rows if r["scenario"] == summary["scenario"]]
        check("scenario_inventory_"+summary["scenario"], len(group) == len({r["question_id"] for r in group}) == 100)
        for field in ["answer_changed", "numeric_changed", "entity_rank_or_direction_changed", "interpretation_changed"]:
            check("scenario_count_"+summary["scenario"]+field, summary[field] == sum(r[field] == "True" for r in group))
    for row in rows:
        diff = differences(json.loads(row["historical_gold"]), json.loads(row["scenario_answer"]))
        check("row_changes_"+row["question_id"]+row["scenario"], diff == json.loads(row["changed_fields"]) and bool(diff) == (row["answer_changed"] == "True"))
        check("numeric_changes_"+row["question_id"]+row["scenario"], any(x["kind"] == "numeric" for x in diff) == (row["numeric_changed"] == "True"))
    public_text = json.dumps([cfg, contract, report, audit, rows], ensure_ascii=True, allow_nan=False)
    check("public_path_hygiene", not contains_local_path(public_text))
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-local", action="store_true")
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    try:
        failures = validate_public()
    except (KeyError, TypeError, ValueError, OSError) as error:
        failures = ["public_validation_exception_" + type(error).__name__]
    local = "not_run_public_artifact_validation_only"
    if args.require_local:
        try:
            from build_metric_amendment import generate
            expected_private, expected_report = generate()
            if expected_report != load(REPORT):
                failures.append("source_replayed_public_report_mismatch")
            if expected_private != load(ROOT / load(CONFIG)["private_output"]):
                failures.append("source_replayed_private_manifest_mismatch")
            public_text = "\n".join(p.read_text(encoding="utf-8") for p in [CONFIG, REPORT, AUDIT, ROWS])
            for record in expected_private["questions"]:
                protected_values = [record[k] for k in ["question_id", "source_question_id", "context_id", "question", "evidence_payload_sha256", "evidence_content_sha256"]]
                if any(value in public_text for value in protected_values):
                    failures.append("private_record_identifiers_or_content_leaked")
                    break
            local = "96_questions_48_contexts_and_source_arithmetic_replayed"
        except (KeyError, TypeError, ValueError, OSError, RuntimeError) as error:
            failures.append("local_replay_exception_" + type(error).__name__)
            local = "failed_or_required_private_inputs_missing"
    result = {"status": "metric_amendment_validation_passed" if not failures else "failed",
              "public_artifacts_valid": not failures, "local_validation": local,
              "research_execution_authorized": False, "failures": failures, "num_failures": len(failures)}
    from pathlib import Path
    write_json(Path(args.output), result)
    print(json.dumps(result))
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
