"""Calculation/display counterexamples; constructed fixtures are not new observations."""
import copy
import csv
import json
from html.parser import HTMLParser
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from audit_calibration_sources import check_case, number, percent, quote, replay_ledger
from build_business_risk_lens import build_summary, validate_ledger, render as render_risk
from validate_business_risk_lens import check as check_risk
from build_portfolio_demo import load_data, build_summary as demo_summary, render as render_demo
from validate_portfolio_demo import check as check_demo


def fixtures():
    # Exact-quote-compatible constructions for deterministic arithmetic, not a review export.
    return [
        {'question_id': 'q_0048', 'question': 'August 2011 comparison',
         'generated_text': "In August 2011, the Netherlands generated more net revenue (39,655.81 GBP) compared to EIRE (12,147.92 GBP). The Netherlands' net revenue was higher by approximately 27,508 GBP.",
         'prompt_evidence_rows': [{'country': 'Netherlands', 'net_revenue': 39655.81, 'gross_positive_revenue': 40327.81, 'cancellation_revenue': -672},
                                  {'country': 'EIRE', 'net_revenue': 12147.92, 'gross_positive_revenue': 18344.20, 'cancellation_revenue': -6196.28}]},
        {'question_id': 'q_0053', 'question': 'April 2011 to May 2011 change',
         'generated_text': 'April 2011 was **492,367.84 GBP**; May 2011, it was **722,094.10 GBP**. The absolute change is **229,726.26 GBP** and the percentage change is **48.97%**.',
         'prompt_evidence_rows': [{'year_month': '2011-04', 'net_revenue': 492367.84, 'gross_positive_revenue': 536968.49, 'cancellation_revenue': -44600.65},
                                  {'year_month': '2011-05', 'net_revenue': 722094.10, 'gross_positive_revenue': 769296.61, 'cancellation_revenue': -47202.51}]},
        {'question_id': 'q_0092', 'question': 'March 2011 reconciliation',
         'generated_text': 'cancellations and returns reduced gross positive revenue by GBP 342,012.88, resulting in a final net revenue of GBP 682,013.98. The reduction is reported as a positive amount due to the negative cancellation_return_revenue.',
         'prompt_evidence_rows': [{'year_month': '2011-03', 'net_revenue': 682013.98, 'gross_positive_revenue': 716215.26, 'cancellation_revenue': -34201.28}]},
    ]


class CalibrationArithmeticTests(unittest.TestCase):
    def test_whole_pound_rounding_is_not_exact_but_is_supported(self):
        result = check_case(fixtures()[0])['calculations'][-1]
        self.assertFalse(result['exact'])
        self.assertTrue(result['nearest_whole_GBP_match'])
        self.assertEqual(number(result['absolute_rounding_difference_GBP']), number('0.11'))

    def test_monthly_change_has_right_amount_and_wrong_percentage(self):
        result = check_case(fixtures()[1])['calculations']
        self.assertTrue(all(c['exact'] for c in result[:3]))
        self.assertFalse(result[3]['display_rounding_match'])
        self.assertEqual(result[3]['reference_display_percent'], '46.66')
        self.assertGreater(number(result[3]['absolute_difference_percentage_points']), 2)

    def test_reconciliation_does_not_accept_correct_net_as_correct_answer(self):
        result = check_case(fixtures()[2])['calculations']
        self.assertFalse(result[0]['exact'])
        self.assertTrue(result[1]['exact'])
        self.assertFalse(result[2]['reconciles'])
        self.assertEqual(result[2]['implied_net_GBP'], '374202.38')
        self.assertTrue(result[3]['positive_magnitude_of_negative_value'])

    def test_evaluation_only_metadata_cannot_change_arithmetic(self):
        for case in fixtures():
            changed = copy.deepcopy(case)
            changed.update(gold_answer='wrong', old_labels='different', detector_scores={'fake': 100}, auto_review='reversed')
            self.assertEqual(check_case(case), check_case(changed))

    def test_unicode_quotes_and_duplicate_anchors(self):
        self.assertEqual(quote('\U0001f600 e\u0301 value', 'value')['start'], 5)
        with self.assertRaises(ValueError):
            quote('value value', 'value')
        case = fixtures()[0]
        case['generated_text'] = case['generated_text'].replace('27,508', '27,509')
        with self.assertRaises(ValueError):
            check_case(case)

    def test_nonfinite_empty_scope_and_ambiguous_rows_fail(self):
        for value in ('NaN', 'Infinity', '-Infinity'):
            with self.assertRaises(ValueError):
                number(value)
        with self.assertRaises(ValueError):
            percent(number(1), number(0))
        case = fixtures()[0]
        case['prompt_evidence_rows'].append(copy.deepcopy(case['prompt_evidence_rows'][0]))
        with self.assertRaises(ValueError):
            check_case(case)

    def test_local_replay_uses_quantity_price_not_saved_revenue(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'tiny.csv'
            with path.open('w', encoding='utf-8', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=['year_month','country','quantity','unit_price','revenue'])
                writer.writeheader()
                writer.writerows([{'year_month':'2011-03','country':'X','quantity':2,'unit_price':'1.25','revenue':999},
                                  {'year_month':'2011-03','country':'Y','quantity':-1,'unit_price':'0.50','revenue':999}])
            cases = [{'question_id':'q_0092','prompt_evidence_rows':[{'year_month':'2011-03','net_revenue':2,'gross_positive_revenue':2.5,'cancellation_revenue':-.5}]}]
            self.assertEqual(replay_ledger(path,cases)[0]['source_row_count'],2)
            cases[0]['prompt_evidence_rows'][0]['net_revenue'] = 1998
            with self.assertRaises(ValueError):
                replay_ledger(path,cases)


class BusinessPresentationTests(unittest.TestCase):
    def test_original_answer_whitespace_survives_html_serialization(self):
        class Answers(HTMLParser):
            def __init__(self):
                super().__init__()
                self.answers, self.current = [], None
            def handle_starttag(self, tag, attrs):
                if tag == 'pre':
                    self.current = ''
            def handle_endtag(self, tag):
                if tag == 'pre':
                    self.answers.append(self.current)
                    self.current = None
            def handle_data(self, data):
                if self.current is not None:
                    self.current += data
        data = load_data()
        text = render_demo(data, demo_summary(data))
        parser = Answers()
        parser.feed(text)
        by_id = {c['question_id']: c for c in data['cases']}
        self.assertEqual(parser.answers, [by_id[q]['generated_text'] for q in ['q_0064', 'q_0069']])
        self.assertTrue(all(line == line.rstrip() for line in text.splitlines()))

    def test_category_totals_and_denominator(self):
        summary = build_summary()
        ledger = summary['ledger']
        validate_ledger(ledger)
        self.assertEqual(ledger['net_transaction_value_gbp'], 9748131.07)
        self.assertEqual(ledger['non_merchandise_share_of_negative_value_percentage'], 46.77)
        self.assertIsNone(ledger['physical_return_value'])
        self.assertEqual(summary['new_questions'], 0)

    def test_sign_counts_duplicate_and_percentage_mutations_fail(self):
        for field in ('sign', 'count', 'duplicate', 'share', 'physical_returns'):
            ledger = copy.deepcopy(build_summary()['ledger'])
            if field == 'sign':
                ledger['categories'][0]['negative_value_gbp'] *= -1
            elif field == 'count':
                ledger['eligible_line_count'] += 1
            elif field == 'duplicate':
                ledger['categories'].append(copy.deepcopy(ledger['categories'][0]))
            elif field == 'share':
                ledger['non_merchandise_share_of_negative_value_percentage'] = 4.29
            else:
                ledger['physical_return_value'] = 893979.73
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_ledger(ledger)

    def test_displayed_business_values_and_claims_cannot_drift(self):
        summary = build_summary()
        text = render_risk(summary)
        check_risk(summary, text)
        for changed in [text.replace('46.77%', '4.67%'), text.replace('not verified physical returns', 'verified physical returns')]:
            with self.assertRaises(ValueError):
                check_risk(summary, changed)

    def test_primary_case_preserves_seven_atomic_outcomes(self):
        data = load_data()
        summary = demo_summary(data)
        check_demo(data, summary, render_demo(data, summary))
        for family in ['simple', 'entropy', 'energy']:
            self.assertEqual(summary[family + '_outcomes'], {'false alarm': 2, 'missed': 5})
        self.assertFalse(summary['independent_human_review'])

    def test_primary_case_changed_text_and_score_are_rejected(self):
        data = load_data()
        summary = demo_summary(data)
        text = render_demo(data, summary)
        with self.assertRaises(ValueError):
            check_demo(data, summary, text.replace('Matches own row', 'Mismatched amount'))
        changed = copy.deepcopy(data)
        changed['cases'][0]['spans'][0]['simple_score'] += 1
        with self.assertRaises(ValueError):
            check_demo(changed, summary, text)

    def test_regenerating_both_summaries_cannot_redefine_threshold(self):
        data = load_data()
        data['meta']['simple_threshold'] += 0.1
        with self.assertRaises(ValueError):
            demo_summary(data)

    def test_committed_render_matches_builder_and_escapes_source_text(self):
        summary = build_summary()
        self.assertEqual((ROOT/'reports/bizhallu_business_risk_lens.html').read_text(encoding='utf-8'), render_risk(summary))
        summary['lenses'] = copy.deepcopy(summary['lenses'])
        summary['lenses'][0]['question'] = '<script>fake</script>'
        self.assertIn('&lt;script&gt;fake&lt;/script&gt;', render_risk(summary))


if __name__ == '__main__':
    unittest.main()
