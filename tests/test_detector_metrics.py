import itertools
import math
import random
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import detector_metrics as metrics
from evaluate_detector_split_metrics import add_splits, validate_baseline_fields
from evaluate_pilot_simple_baselines import average_precision as compatibility_ap


def rows(labels, scores, split="dev"):
    return [{"annotation_id": f"a{i}", "question_id": f"q{i//2}", "binary_label": y, "score": s,
             "same": s, "all_positive": 1.0, "split": split, "fact_type": "amount" if i % 2 else "month",
             "cluster": str(i//2)} for i, (y, s) in enumerate(zip(labels, scores))]


class DetectorMetricTests(unittest.TestCase):
    def test_tied_ap_is_permutation_invariant(self):
        for labels in [(1, 0), (0, 1)]:
            self.assertEqual(metrics.average_precision(labels, [0.5, 0.5]), .5)
            self.assertEqual(compatibility_ap(labels, [0.5, 0.5]), .5)
        sample = [(1, .9), (0, .9), (1, .5), (0, .1)]
        expected = metrics.average_precision(*zip(*sample))
        for ordered in itertools.permutations(sample):
            self.assertEqual(metrics.average_precision(*zip(*ordered)), expected)

    def test_constant_scores_equal_prevalence(self):
        self.assertEqual(metrics.average_precision([1, 1, 0], [0, 0, 0]), 2/3)
        self.assertEqual(metrics.auroc([1, 1, 0], [0, 0, 0]), .5)

    def test_invalid_arrays_rejected(self):
        for labels, scores in [([], []), ([1], []), ([1, 2], [0, 1]), ([True], [1]), ([1], [math.inf]), ([1], [math.nan]), ([1], [None])]:
            with self.subTest(labels=labels, scores=scores), self.assertRaises(ValueError):
                metrics.average_precision(labels, scores)

    def test_single_class_policy(self):
        self.assertIsNone(metrics.average_precision([0, 0], [1, 2]))
        self.assertEqual(metrics.average_precision([1, 1], [1, 2]), 1)
        self.assertIsNone(metrics.auroc([1, 1], [1, 2]))
        self.assertIsNone(metrics.evaluate([0, 0], [0, 1], .5)["balanced_accuracy"])

    def test_all_positive_and_all_negative_controls(self):
        positive = metrics.evaluate([1, 1, 0], [1, 1, 1], .5)
        negative = metrics.evaluate([1, 1, 0], [0, 0, 0], .5)
        self.assertEqual(positive["f1"], .8)
        self.assertEqual(negative["f1"], 0)
        for value in [positive, negative]:
            self.assertEqual(value["balanced_accuracy"], .5)
            self.assertEqual(value["mcc"], 0)

    def test_mcc_balanced_accuracy_and_confusion(self):
        result = metrics.evaluate([1, 0, 1, 0], [.9, .2, .8, .1], .5)
        self.assertEqual((result["tp"], result["fp"], result["tn"], result["fn"]), (2, 0, 2, 0))
        self.assertEqual(result["mcc"], 1)
        self.assertEqual(result["balanced_accuracy"], 1)
        with self.assertRaises(ValueError):
            metrics.metrics_from_confusion(dict(tp=-1, fp=0, tn=1, fn=0))

    def test_threshold_and_prior_cannot_see_test_or_confirmation(self):
        dev = rows([0, 1, 0, 1], [.1, .8, .3, .6])
        self.assertEqual(metrics.dev_threshold(dev, "score"), .6)
        prior = metrics.fit_fact_type_prior(dev)
        self.assertEqual(prior["rates"], {"amount": 1, "month": 0})
        self.assertEqual(prior["fallback"], .5)
        for split in ["test", "confirmation", "train", "development"]:
            changed = [{**r, "split": split} for r in dev]
            with self.assertRaises(ValueError):
                metrics.dev_threshold(changed, "score")
            with self.assertRaises(ValueError):
                metrics.fit_fact_type_prior(changed)

    def test_duplicate_ids_and_split_mix_rejected(self):
        sample = rows([0, 1], [.2, .8])
        with self.assertRaises(ValueError):
            metrics.validate_rows(sample+sample)
        with self.assertRaises(ValueError):
            metrics.validate_rows([sample[0], {**sample[1], "split": "test"}])

    def test_legacy_field_validator_rejects_all_nonfinite_and_missing(self):
        for value in ["NaN", "Inf", "-Inf", None, True, "bad"]:
            result = validate_baseline_fields([{"annotation_id": "a", "score": value}], [{"baseline": "x", "score_field": "score"}])
            self.assertTrue(result)
        self.assertTrue(validate_baseline_fields([{"score": .1}, {}], [{"baseline": "x", "score_field": "score"}]))

    def test_legacy_split_join_rejects_duplicates_and_conflicts(self):
        q = {'question_id':'q1', 'split':'dev'}
        row = {'annotation_id':'a1', 'question_id':'q1','split':'dev','binary_label':'1'}
        with patch('evaluate_detector_split_metrics.load_jsonl', return_value=[q,q]):
            with self.assertRaises(ValueError):
                add_splits([row], Path('unused'))
        with patch('evaluate_detector_split_metrics.load_jsonl', return_value=[q]):
            self.assertTrue(add_splits([row,row], Path('unused'))[1])
            self.assertTrue(add_splits([{**row,'split':'test'}], Path('unused'))[1])

    def test_paired_bootstrap_identical_methods_are_exactly_zero(self):
        sample = rows([0, 1, 1, 0, 1, 0], [.2, .8, .9, .4, .7, .6], "test")
        result = metrics.paired_cluster_bootstrap(sample, {"score": .5, "same": .5}, [("score", "same")], "cluster", 100)
        for interval in result["intervals"]:
            self.assertEqual((interval["lower_95"], interval["upper_95"]), (0, 0))
            self.assertEqual(interval["valid_replicates"]+interval["undefined_replicates"], 100)

    def test_bootstrap_recomputes_reference_with_same_draw(self):
        sample = rows([1, 1, 1, 0, 0, 0], [.9, .1, .8, .2, .7, .1], "test")
        result = metrics.paired_cluster_bootstrap(sample, {"score": .5, "all_positive": .5}, [("score", "all_positive")], "cluster", 60, 31)
        rng = random.Random(31)
        groups = [sample[i:i+2] for i in range(0, 6, 2)]
        differences = []
        for _ in range(60):
            selected = [r for _ in groups for r in groups[rng.randrange(3)]]
            y = [r["binary_label"] for r in selected]
            f1 = metrics.evaluate(y, [r["score"] for r in selected], .5)["f1"]
            reference = 2*sum(y)/(len(y)+sum(y))
            differences.append(f1-reference)
        actual = next(r for r in result["intervals"] if r["metric"] == "f1")
        self.assertEqual(actual["lower_95"], metrics.quantile(differences, .025))
        self.assertEqual(actual["upper_95"], metrics.quantile(differences, .975))

    def test_no_finite_threshold_rounding(self):
        sample = rows([0, 1], [.50000011, .50000012])
        self.assertEqual(metrics.dev_threshold(sample, "score"), .50000012)
        self.assertEqual(metrics.evaluate([0, 1], [.50000011, .50000012], .50000012)["f1"], 1)


class SklearnCrossChecks(unittest.TestCase):
    def test_actual_appendix_against_sklearn(self):
        try:
            from sklearn.metrics import average_precision_score, balanced_accuracy_score, matthews_corrcoef, roc_auc_score
        except ImportError:
            self.skipTest('Optional local sklearn check; standard-library CI remains lightweight')
        import build_retrospective_statistics as build
        if not build.REPORT.exists():
            self.skipTest('Appendix not built')
        data = build.read_csv(build.SCORES)
        for row in build.load(build.REPORT)['metrics']:
            subset = [r for r in data if r['arm']==row['arm'] and r['split']==row['split']]
            y = [int(r['binary_label']) for r in subset]
            score = [float(r[row['signal']]) for r in subset]
            prediction = [int(s>=row['threshold']) for s in score]
            for name, expected in [('average_precision',average_precision_score(y,score)),
                    ('auroc',roc_auc_score(y,score)), ('balanced_accuracy',balanced_accuracy_score(y,prediction)),
                    ('mcc',matthews_corrcoef(y,prediction))]:
                self.assertAlmostEqual(row[name],expected,places=13)

    def test_random_ties_against_sklearn(self):
        try:
            from sklearn.metrics import average_precision_score, balanced_accuracy_score, matthews_corrcoef, roc_auc_score
        except ImportError:
            self.skipTest("Optional local sklearn cross-check; core tests need only standard library")
        rng = random.Random(730)
        for _ in range(100):
            y = [0, 1]+[rng.randrange(2) for _ in range(28)]
            scores = [rng.randrange(5)/4 for _ in y]
            prediction = [int(x >= .5) for x in scores]
            result = metrics.evaluate(y, scores, .5)
            self.assertAlmostEqual(result["average_precision"], average_precision_score(y, scores), places=13)
            self.assertAlmostEqual(result["auroc"], roc_auc_score(y, scores), places=13)
            self.assertAlmostEqual(result["balanced_accuracy"], balanced_accuracy_score(y, prediction), places=13)
            self.assertAlmostEqual(result["mcc"], matthews_corrcoef(y, prediction), places=13)


if __name__ == "__main__":
    unittest.main()
