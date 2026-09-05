import copy
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import build_retrospective_statistics as build


def question(qid, periods, value=1):
    filters = {'year_month':periods[0]} if len(periods)==1 else {'previous_month':periods[0], 'current_month':periods[1]}
    return {'question_id':qid, 'evidence':{'filters':filters, 'rows':[{'value':value}]}}


class RetrospectiveTests(unittest.TestCase):
    def test_period_components_are_transitive(self):
        q = [question('a',['2011-01']), question('b',['2011-02']), question('c',['2011-01','2011-02']), question('d',['2011-04'])]
        out = build.assign_clusters(q)
        self.assertEqual(out['a']['period_component'], out['b']['period_component'])
        self.assertNotEqual(out['a']['period_component'], out['d']['period_component'])
        self.assertEqual(out, build.assign_clusters(list(reversed(q))))

    def test_evidence_order_and_numeric_spelling_do_not_change_group(self):
        a = question('a',['2011-01'])
        a['evidence']['rows'] = [{'value':1}, {'value':2.0}]
        b = question('b',['2011-02'])
        b['evidence']['rows'] = [{'value':2}, {'value':1.0}]
        groups = build.assign_clusters([a,b])
        self.assertEqual(groups['a']['evidence_cluster'], groups['b']['evidence_cluster'])

    def test_duplicate_or_unrecognized_period_rejected(self):
        with self.assertRaises(ValueError):
            build.assign_clusters([question('a',['2011-01'])]*2)
        with self.assertRaises(ValueError):
            build.assign_clusters([{'question_id':'a', 'evidence':{'filters':{},'rows':[]}}])

    def test_test_labels_do_not_change_any_fit(self):
        config = build.load(build.CONFIG)
        rows = [{'arm':'test_fixture','annotation_id':f'a{i}', 'question_id':f'q{i}',
                 'split':'dev' if i<4 else 'test','fact_type':'month' if i%2 else 'amount',
                 'binary_label': i%2, **{s:(i+1)*.01 for s in build.signals()}} for i in range(8)]
        first = build.analyze_arm(rows, config)
        altered = copy.deepcopy(rows)
        for r in altered[4:]:
            r['binary_label'] = 1-r['binary_label']
        second = build.analyze_arm(altered, config)
        self.assertEqual(first[2:], second[2:])
        self.assertEqual([r['dev_fact_type_prior'] for r in first[1]], [r['dev_fact_type_prior'] for r in second[1]])

    def test_precision_is_not_rounded(self):
        token = {'token_logprob':-.123456789123, 'token_entropy':.432109876543, 'top2_margin':.23456789123,
                 'spilled_energy_abs_delta':.1,'spilled_energy_delta':-.1,
                 'spilled_probability_mass_after_top1':.1,'spilled_probability_mass_after_top2':.05,
                 'selected_step_energy_gap':.123456789123}
        scores = build.aggregate([token])
        self.assertEqual(scores['mean_token_nll'], .123456789123)
        self.assertEqual(scores['mean_spilled_energy_delta'], -scores['negative_mean_spilled_energy_delta'])
        with self.assertRaises(ValueError):
            build.aggregate([{**token, 'token_entropy':math.nan}])

    def test_historical_control_independently_from_counts(self):
        if not build.REPORT.exists():
            self.skipTest('Appendix not built')
        report = build.load(build.REPORT)
        stored, _, _ = build.historical_rows()
        dev_counts = {}
        for r in stored:
            if r['split']=='dev':
                pos,total = dev_counts.get(r['fact_type'],(0,0))
                dev_counts[r['fact_type']] = pos+r['binary_label'],total+1
        rates = {f:p/n for f,(p,n) in dev_counts.items()}
        self.assertEqual(rates, report['dev_fact_type_priors']['saved_trace_precision']['rates'])
        row = next(r for r in report['metrics'] if r['arm']=='saved_trace_precision' and r['split']=='test' and r['signal']=='dev_fact_type_prior')
        predicted = [r for r in stored if r['split']=='test' and rates.get(r['fact_type'],61/102)>=row['threshold']]
        tp = sum(r['binary_label'] for r in predicted)
        fp = len(predicted)-tp
        positives = sum(r['binary_label'] for r in stored if r['split']=='test')
        self.assertEqual((row['tp'],row['fp'],row['fn']), (tp,fp,positives-tp))
        self.assertEqual(row['f1'], 2*tp/(len(predicted)+positives))


if __name__ == '__main__':
    unittest.main()
