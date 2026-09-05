"""Independent counting and failure cases for the retrospective B2 supplement."""
import copy
from fractions import Fraction
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import q0048_dev_sensitivity as b2


def independent_threshold(rows, field):
    """Count at every observed cutoff; use rational arithmetic for the tie policy."""
    candidates = []
    for cutoff in set(r[field] for r in rows):
        tp = sum(r['binary_label'] == 1 and r[field] >= cutoff for r in rows)
        fp = sum(r['binary_label'] == 0 and r[field] >= cutoff for r in rows)
        fn = sum(r['binary_label'] == 1 and r[field] < cutoff for r in rows)
        tn = len(rows) - tp - fp - fn
        def ratio(a, b):
            return Fraction(a, b) if b else Fraction(0)
        key = (ratio(2*tp, 2*tp+fp+fn), ratio(tp, tp+fp), ratio(tp, tp+fn),
               ratio(tp+tn, len(rows)), -cutoff)
        candidates.append((key, cutoff))
    return max(candidates)[1]


class Q0048SensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packet, cls.annotations = b2.check_packet()
        cls.config = cls.packet['config']
        cls.report = b2.b1.load(b2.REPORT)
        cls.base = b2.base_rows()
        cls.supplement = [{**r, 'binary_label': int(r['binary_label']),
                           **{f: float(r[f]) for f in b2.b1.signals()}}
                          for r in b2.b1.read_csv(b2.SCORES)]

    def test_nine_offsets_and_rounding_have_source_support(self):
        b2.validate_annotations(self.annotations, self.packet['case'], self.config)
        gold = self.packet['case']['gold_answer']
        delta = Fraction(str(gold['country_a_net_revenue'])) - Fraction(str(gold['country_b_net_revenue']))
        self.assertEqual(delta, Fraction('27507.89'))
        self.assertEqual(Fraction(27508) - delta, Fraction('.11'))
        self.assertEqual(round(delta), 27508)
        for a in self.annotations:
            self.assertEqual(self.packet['case']['generated_text'][a['span_start_char']:a['span_end_char']], a['span_text'])
        self.assertEqual(sum(a['label'] == 'correct_key_fact' for a in self.annotations), 9)

    def test_annotation_mutations_require_new_review(self):
        mutations = [('annotation_id', 'duplicate'), ('span_start_char', -1),
                     ('span_end_char', 999), ('span_text', 'different'),
                     ('question_id', 'q_0064'), ('label', 'hallucinated_key_fact'),
                     ('annotation_version', 'unversioned'), ('notes', 'human reviewed')]
        for key, value in mutations:
            with self.subTest(key=key):
                rows = copy.deepcopy(self.annotations)
                rows[0][key] = rows[1]['annotation_id'] if value == 'duplicate' else value
                with self.assertRaises(ValueError):
                    b2.validate_annotations(rows, self.packet['case'], self.config)

    def test_only_missing_dev_answer_is_eligible(self):
        for split in ['test', 'train', 'confirmation']:
            case = copy.deepcopy(self.packet['case'])
            case['split'] = split
            with self.assertRaises(ValueError):
                b2.validate_annotations(self.annotations, case, self.config)

    def test_score_metadata_duplicates_and_nonfinite_fail(self):
        mutations = [('fact_type', 'ranking'), ('question_id', 'q_0064'),
                     ('binary_label', 1), ('split', 'test'), ('arm', 'invented'),
                     ('mean_token_entropy', math.nan), ('mean_token_entropy', math.inf)]
        for key, value in mutations:
            with self.subTest(key=key, value=value):
                rows = copy.deepcopy(self.supplement)
                rows[0][key] = value
                with self.assertRaises(ValueError):
                    b2.check_score_rows(rows, self.annotations, self.config)
        with self.assertRaises(ValueError):
            b2.check_score_rows(self.supplement + [self.supplement[0]], self.annotations, self.config)

    def test_fit_rejects_test_and_confirmation_inputs(self):
        recipe = b2.b1.load(b2.b1.CONFIG)
        dev = [r for r in self.base if r['arm'] == 'saved_trace_precision' and r['split'] == 'dev']
        for split in ['test', 'confirmation', 'train']:
            contaminated = copy.deepcopy(dev)
            contaminated[0]['split'] = split
            with self.assertRaises(ValueError):
                b2.fit_dev(contaminated, recipe)

    def test_thresholds_and_prior_fit_match_independent_counting(self):
        fields = b2.b1.signals() + ['dev_fact_type_prior']
        for arm in self.config['arms']:
            dev = [r for r in self.base if r['arm'] == arm and r['split'] == 'dev']
            added = [r for r in self.supplement if r['arm'] == arm]
            for condition in self.config['conditions']:
                selected = dev if condition == 'original_dev17' else dev + added
                fit = self.report['fits'][arm + ':' + condition]
                types = {r['fact_type'] for r in selected}
                rates = {t: sum(r['binary_label'] for r in selected if r['fact_type'] == t) /
                         sum(r['fact_type'] == t for r in selected) for t in types}
                self.assertEqual(rates, fit['prior']['rates'])
                enriched = [{**r, 'dev_fact_type_prior': rates[r['fact_type']]} for r in selected]
                for field in fields:
                    with self.subTest(arm=arm, condition=condition, field=field):
                        self.assertEqual(independent_threshold(enriched, field), fit['thresholds'][field])
                for constant in ['all_positive', 'all_negative']:
                    self.assertEqual(fit['thresholds'][constant], .5)

    def test_all_test_confusions_and_changed_ids_match_independent_counting(self):
        changes = []
        for item in self.report['comparisons']:
            arm, field = item['arm'], item['signal']
            test = [r for r in self.base if r['arm'] == arm and r['split'] == 'test']
            flags = []
            for condition, suffix in [('original_dev17', 'before'), ('supplemented_dev18', 'after')]:
                fit = self.report['fits'][arm + ':' + condition]
                predictions = []
                for row in test:
                    value = row[field]
                    if field == 'dev_fact_type_prior':
                        value = fit['prior']['rates'].get(row['fact_type'], fit['prior']['fallback'])
                    predictions.append(value >= fit['thresholds'][field])
                expected = item['test_metrics_' + suffix]
                tp = sum(p and r['binary_label'] == 1 for r, p in zip(test, predictions))
                fp = sum(p and r['binary_label'] == 0 for r, p in zip(test, predictions))
                fn = sum(not p and r['binary_label'] == 1 for r, p in zip(test, predictions))
                tn = len(test) - tp - fp - fn
                self.assertEqual([expected[k] for k in ['tp','fp','tn','fn']], [tp,fp,tn,fn])
                self.assertEqual(expected['f1'], 2*tp/(2*tp+fp+fn))
                flags.append(predictions)
            for row, old, new in zip(test, *flags):
                if old != new:
                    changes.append({'arm':arm,'signal':field,'annotation_id':row['annotation_id'],
                                    'question_id':row['question_id'],'binary_label':row['binary_label'],
                                    'original_flag':old,'supplemented_flag':new})
        self.assertEqual(changes, self.report['changed_test_predictions'])

    def test_fixed_scores_keep_ap_and_original_condition_matches_b1(self):
        old = [{k:v for k,v in r.items() if k != 'condition'} for r in self.report['metrics']
               if r['condition'] == 'original_dev17']
        self.assertEqual(old, b2.b1.load(b2.b1.REPORT)['metrics'])
        self.assertEqual(len(old), 60)
        for c in self.report['comparisons']:
            if c['signal'] in b2.b1.signals():
                self.assertEqual(c['test_metrics_before']['average_precision'], c['test_metrics_after']['average_precision'])
            flags = c['supplement_flag_counts_not_heldout_metrics']
            self.assertEqual(set(flags), set(self.config['conditions']))
            self.assertTrue(all(type(n) is int and 0 <= n <= 9 for n in flags.values()))

    def test_negative_only_supplement_cannot_fit_its_own_cutoff(self):
        added = [r for r in self.supplement if r['arm'] == 'saved_trace_precision']
        with self.assertRaises(ValueError):
            b2.fit_dev(added, b2.b1.load(b2.b1.CONFIG))

    def test_protected_artifacts_and_label_status_are_unchanged(self):
        for path in b2.PUBLIC_PROTECTED:
            self.assertEqual(b2.b1.digest(path), self.report['protected_input_text_sha256'][b2.rel(path)])
        self.assertFalse(self.report['independent_human_review'])
        self.assertFalse(self.report['new_headline_claim'])
        self.assertFalse(self.report['model_inference_run'])
        self.assertEqual(self.report['original_span_count'], 205)
        self.assertEqual(self.report['augmented_span_count'], 214)
        self.assertEqual(self.report['unchanged_test_span_count'], 103)

    def test_public_replay_checks_actual_artifacts(self):
        report, status = b2.validate()
        self.assertEqual(report, self.report)
        self.assertIn('not_run_public_tier', status)

    def test_presentation_exposes_sensitivity_and_keeps_historical_scope(self):
        markup = b2.presentation_html(self.report)
        for text in ['0.7520', '53 / 22 / 20 / 8', '47 / 17 / 25 / 14', '214 spans',
                     'not a replacement benchmark', 'no independent human review',
                     'All candidates and both precision arms', 'Approximately GBP 27,508']:
            self.assertIn(text, markup)
        self.assertEqual(markup.count('id="b2-dev-sensitivity"'), 1)
        self.assertEqual(markup.count('<table>'), markup.count('</table>'))


if __name__ == '__main__':
    unittest.main()
