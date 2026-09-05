"""Independent counterexamples for curated presentation facts, not new labels."""
import copy
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from presentation_evidence import walkthrough, statistical_context
from validate_portfolio_demo_v2 import validate_data_contract, validate_historical_projection, validate_embedded_data


class PresentationEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'docs/assets/bizhallu_demo_v2_data.json').read_text(encoding='utf-8'))
        self.cases = {c['question_id']: c for c in self.data['cases']}

    def test_checked_ranks_and_own_amounts(self):
        for qid, expected in [('q_0064', [1, 2, 7]), ('q_0069', [3, 8, 2])]:
            result = walkthrough(self.cases[qid])
            self.assertFalse(result['automatic_claim_extraction'])
            self.assertEqual([c['rank_in_shown_evidence'] for c in result['claims']], expected)
            self.assertTrue(all(c['row_value_supported'] for c in result['claims']))

    def test_source_references_and_complete_quotes(self):
        for qid in ['q_0064', 'q_0069']:
            case = self.cases[qid]
            for claim in walkthrough(case)['claims']:
                self.assertEqual(case['generated_text'][claim['start']:claim['end']], claim['quote'])
                source = case['prompt_evidence_rows'][claim['source_row'] - 1]
                self.assertEqual(source['stock_code'], claim['stock_code_from_evidence'])
                self.assertEqual(source['description'], claim['product_name'])
                self.assertEqual(float(claim['amount_lexical'].replace(',', '')), source['net_revenue'])

    def test_curated_checks_ignore_evaluation_only_inputs(self):
        case = self.cases['q_0064']
        expected = walkthrough(case)
        for key in ['spans', 'gold_short_answer', 'takeaway', 'review_note', 'detector_outcome']:
            mutated = copy.deepcopy(case)
            mutated[key] = 'not available to presentation evidence checks'
            self.assertEqual(walkthrough(mutated), expected)

    def test_other_cases_are_not_automatically_verified(self):
        for qid, case in self.cases.items():
            if qid not in ['q_0064', 'q_0069']:
                self.assertIsNone(walkthrough(case))

    def test_duplicate_tied_nonfinite_and_changed_values_fail_closed(self):
        for kind in ['duplicate', 'tie', 'nan', 'inf', 'amount']:
            with self.subTest(kind=kind):
                case = copy.deepcopy(self.cases['q_0064'])
                rows = case['prompt_evidence_rows']
                if kind == 'duplicate':
                    rows.append(copy.deepcopy(rows[0]))
                elif kind == 'tie':
                    rows[1]['net_revenue'] = rows[0]['net_revenue']
                else:
                    rows[0]['net_revenue'] = {'nan': math.nan, 'inf': math.inf, 'amount': 1.0}[kind]
                with self.assertRaises(ValueError):
                    walkthrough(case)

    def test_changed_quote_or_period_requires_new_review(self):
        for old, new in [('4,173.18', '4,173.19'), ('April 2011', 'May 2011')]:
            case = copy.deepcopy(self.cases['q_0064'])
            case['generated_text'] = case['generated_text'].replace(old, new)
            with self.assertRaises(ValueError):
                walkthrough(case)

    def test_reordering_evidence_changes_references_not_ranks(self):
        case = copy.deepcopy(self.cases['q_0064'])
        before = walkthrough(case)['claims']
        case['prompt_evidence_rows'].reverse()
        after = walkthrough(case)['claims']
        for a, b in zip(before, after):
            self.assertEqual(a['rank_in_shown_evidence'], b['rank_in_shown_evidence'])
            self.assertEqual(a['source_row'] + b['source_row'], 9)

    def test_offsets_are_unicode_codepoints(self):
        case = copy.deepcopy(self.cases['q_0064'])
        before = walkthrough(case)['claims']
        case['generated_text'] = '\U0001f4c8\n' + case['generated_text']
        after = walkthrough(case)['claims']
        for a, b in zip(before, after):
            self.assertEqual(b['start'], a['start'] + 2)
            self.assertEqual(case['generated_text'][b['start']:b['end']], b['quote'])

    def test_reference_arithmetic_and_uncertainty_scope(self):
        context = statistical_context()
        rows = {r['signal']: r for r in context['test_rows']}
        self.assertAlmostEqual(rows['all_positive']['f1'], 2 * 61 / (103 + 61))
        diff = context['entropy_minus_all_positive']
        self.assertAlmostEqual(diff['point_difference'], 106 / 136 - 122 / 164)
        self.assertLess(diff['lower_95'], 0)
        self.assertGreater(diff['upper_95'], 0)
        self.assertFalse(context['confirmatory'])
        self.assertFalse(context['independent_human_annotation'])

    def test_public_bundle_passes_contract(self):
        validate_data_contract(self.data)
        validate_historical_projection(self.data)
        validate_embedded_data((ROOT / 'docs/portfolio_demo_v2.html').read_text(encoding='utf-8'), self.data)

    def test_finite_score_and_threshold_drift_are_rejected(self):
        for field in ['simple_score', 'entropy_score', 'energy_score']:
            data = copy.deepcopy(self.data)
            data['cases'][0]['spans'][0][field] += .1
            with self.assertRaises(ValueError):
                validate_historical_projection(data)
        self.data['meta']['simple_threshold'] += .1
        with self.assertRaises(ValueError):
            validate_historical_projection(self.data)

    def test_embedded_data_must_match_download(self):
        html = (ROOT / 'docs/portfolio_demo_v2.html').read_text(encoding='utf-8')
        self.data['cases'][0]['takeaway'] = 'different downloadable content'
        with self.assertRaises(ValueError):
            validate_embedded_data(html, self.data)

    def test_tampered_walkthrough_offsets_and_duplicates_are_rejected(self):
        for kind in ['rank', 'source', 'offset', 'duplicate']:
            with self.subTest(kind=kind):
                data = copy.deepcopy(self.data)
                case = next(c for c in data['cases'] if c['question_id'] == 'q_0064')
                if kind in ['rank', 'source']:
                    field = 'stated_rank' if kind == 'rank' else 'source_row'
                    case['presentation_walkthrough']['claims'][0][field] = 99
                elif kind == 'offset':
                    case['spans'][0]['span_start_char'] += 1
                else:
                    case['spans'][1]['annotation_id'] = case['spans'][0]['annotation_id']
                with self.assertRaises(ValueError):
                    validate_data_contract(data)

    def test_bad_scores_outcomes_labels_and_scope_are_rejected(self):
        mutations = [('simple_score', math.nan), ('entropy_score', math.inf),
                     ('energy_score', True), ('simple_outcome', 'invented'), ('label', 'unknown')]
        for field, value in mutations:
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                data['cases'][0]['spans'][0][field] = value
                with self.assertRaises(ValueError):
                    validate_data_contract(data)
        for field, value in [('independent_human_annotation', True), ('automatic_claim_extraction', True),
                             ('metric_selection_status', 'confirmatory')]:
            data = copy.deepcopy(self.data)
            data['meta'][field] = value
            with self.assertRaises(ValueError):
                validate_data_contract(data)

    def test_changed_statistical_source_is_rejected(self):
        self.data['statistical_review']['test_rows'][0]['f1'] = 1.0
        with self.assertRaises(ValueError):
            validate_data_contract(self.data)


if __name__ == '__main__':
    unittest.main()
