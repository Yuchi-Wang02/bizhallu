import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from business_metric_audit import ROOT, decimal_value, flag, ledger_profile, load, money, ratio
from build_metric_amendment import rename_fields
from build_metric_amendment import CONFIG, amend_record
from validate_confirmation_question_design import evidence_table_projection


class FakeFrame:
    def __init__(self, rows):
        self.rows = rows

    def __len__(self):
        return len(self.rows)

    def itertuples(self, index=False):
        return iter(SimpleNamespace(**x) for x in self.rows)


class BusinessMetricTests(unittest.TestCase):
    def test_half_up_and_no_early_rounding(self):
        self.assertEqual(money("1.005"), 1.01)
        self.assertEqual(money(decimal_value("0.004")*3), .01)

    def test_nonfinite_rejected(self):
        for value in ["NaN", "Infinity", "-Infinity"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                money(value)

    def test_undefined_ratio_is_not_zero(self):
        for value in [0, -1]:
            with self.assertRaises(ValueError):
                ratio(5, value)
        self.assertEqual(ratio(15, 10), 150)

    def test_boolean_not_python_string_truthiness(self):
        self.assertFalse(flag("False"))
        self.assertTrue(flag("true"))
        with self.assertRaises(ValueError):
            flag("missing")

    def test_sign_scope_and_cancel_flag_are_independent(self):
        rows = [dict(quantity=q, unit_price=p, stock_code=c, is_non_merchandise=n, is_cancel_invoice=f)
                for q, p, c, n, f in [(2, 10, "100A", False, False), (-1, 10, "100A", False, True),
                                      (-1, 50, "M", True, True), (1, 3, "POST", True, True)]]
        result = ledger_profile(FakeFrame(rows), load(ROOT / "configs/business_metric_contract_v1_1.json"))
        self.assertEqual(result["positive_transaction_value_gbp"], 23)
        self.assertEqual(result["negative_transaction_value_gbp"], -60)
        self.assertEqual(result["net_transaction_value_gbp"], -37)
        self.assertEqual(result["positive_cancel_flagged_line_count"], 1)
        self.assertEqual(result["non_merchandise_share_of_negative_value_percentage"], 83.33)
        self.assertIsNone(result["physical_return_value"])

    def test_recursive_aliases_are_reversible_and_do_not_change_numbers(self):
        item = {"old": -12.01, "columns": ["old"], "facts": [{"field": "old", "value": 17}]}
        updated = rename_fields(item, {"old": "new"})
        self.assertEqual(rename_fields(updated, {"new": "old"}), item)
        self.assertEqual(updated["new"], -12.01)

    def test_alias_collision_rejected(self):
        with self.assertRaises(ValueError):
            rename_fields({"a": 1, "b": 2}, {"a": "b"})

    def test_entity_name_matching_field_name_is_not_rewritten(self):
        row = {"product_name": "returned_units", "returned_units": 4, "field": "returned_units"}
        changed = rename_fields(row, {"returned_units": "negative_units_magnitude"})
        self.assertEqual(changed["product_name"], "returned_units")
        self.assertEqual(changed["negative_units_magnitude"], 4)
        self.assertEqual(changed["field"], "negative_units_magnitude")

    def test_all_six_template_adapters_preserve_numeric_evidence(self):
        config = load(CONFIG)
        contract = load(ROOT / config["metric_contract"])
        legacy = load(ROOT / config["historical_design"])
        gold = {"period_start": "synthetic-start", "period_end_inclusive": "synthetic-end",
                "business_date": "synthetic-day", "country": "Synthetic country",
                "gross_positive_revenue_gbp": 100, "cancellation_return_revenue_gbp": -20,
                "cancellation_return_reduction_gbp": 20, "net_revenue_gbp": 80,
                "reduction_percentage_of_gross": 20,
                "product_a": {"stock_code": "1A", "product_name": "Synthetic A"},
                "product_b": {"stock_code": "2B", "product_name": "Synthetic B"}}
        for template in config["templates"]:
            with self.subTest(template=template):
                old = {"question_id": "synthetic", "context_id": "synthetic-context", "template_id": template,
                       "gold_answer": copy.deepcopy(gold), "gold_facts": [{"field": "gross_positive_revenue_gbp", "value": 100}],
                       "gold_short_answer": "Synthetic merchandise net revenue", "question": "Synthetic question",
                       "evidence": {"rows": [{"gross_positive_revenue_gbp": 100, "cancellation_return_revenue_gbp": -20}],
                                    "columns": ["gross_positive_revenue_gbp", "cancellation_return_revenue_gbp"], "metadata": {}}}
                new = amend_record(old, config, contract, legacy)
                inverse = {v: k for k, v in config["field_renames"].items()}
                self.assertEqual(rename_fields(new["gold_answer"], inverse), old["gold_answer"])
                self.assertEqual(rename_fields(new["evidence"]["rows"], inverse), old["evidence"]["rows"])
                self.assertNotEqual(new["question_id"], old["question_id"])
                self.assertEqual(new["source_question_id"], old["question_id"])

    def test_public_validator_rejects_count_tampering(self):
        import validate_metric_amendment as validator
        from unittest.mock import patch
        original_load = validator.load

        def altered(path):
            value = original_load(path)
            if path == validator.REPORT:
                value["question_count"] = 95
            return value

        with patch.object(validator, "load", side_effect=altered):
            self.assertIn("96_questions", validator.validate_public())

    def test_fingerprints_cannot_hide_overlap_by_renaming(self):
        old = {"rows": [{"gross_positive_revenue_gbp": 4.0, "cancellation_return_revenue_gbp": -1}]}
        new = {"rows": [{"positive_transaction_value_gbp": 4, "negative_transaction_value_gbp": -1.0}]}
        aliases = {"positive_transaction_value_gbp": "gross_positive_revenue_gbp", "negative_transaction_value_gbp": "cancellation_return_revenue_gbp"}
        self.assertEqual(evidence_table_projection(old, {}), evidence_table_projection(new, aliases))
        changed = copy.deepcopy(new)
        changed["rows"][0]["negative_transaction_value_gbp"] = -2
        self.assertNotEqual(evidence_table_projection(old, {}), evidence_table_projection(changed, aliases))


if __name__ == "__main__":
    unittest.main()
