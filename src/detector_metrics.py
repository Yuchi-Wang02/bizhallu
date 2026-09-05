"""Validated binary metrics and paired cluster diagnostics (standard library only)."""
from __future__ import annotations

import math
import random
from collections import defaultdict
from itertools import groupby
from numbers import Integral

METRIC_VERSION = "binary_metrics_v2_tied_ap"


def finite_score(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a detector score")
    try:
        result = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Score must be numeric and finite") from exc
    if not math.isfinite(result):
        raise ValueError("Score must be finite")
    return result


def checked_arrays(labels, scores):
    labels, scores = list(labels), list(scores)
    if not labels or len(labels) != len(scores):
        raise ValueError("Nonempty arrays of equal length required")
    if any(isinstance(y, bool) or not isinstance(y, Integral) or y not in (0, 1) for y in labels):
        raise ValueError("Labels must be binary integers")
    return labels, [finite_score(x) for x in scores]


def average_precision(labels, scores):
    """Non-interpolated AP, grouping tied scores before precision is calculated.

    No positive labels returns None (explicitly undefined in this project), not
    scikit-learn's warning-plus-zero convention. All-positive AP equals one.
    """
    labels, scores = checked_arrays(labels, scores)
    positives = sum(labels)
    if not positives:
        return None
    seen = true_positives = 0
    contributions = []
    for _, items in groupby(sorted(zip(scores, labels), reverse=True), key=lambda item: item[0]):
        group = list(items)
        hits = sum(y for _, y in group)
        seen += len(group)
        true_positives += hits
        contributions.append(hits * true_positives / seen)
    return math.fsum(contributions) / positives


def auroc(labels, scores):
    labels, scores = checked_arrays(labels, scores)
    positives, negatives = sum(labels), len(labels)-sum(labels)
    if not positives or not negatives:
        return None
    negatives_below = 0
    concordance = 0.0
    for _, items in groupby(sorted(zip(scores, labels)), key=lambda item: item[0]):
        group = list(items)
        pos = sum(y for _, y in group)
        neg = len(group)-pos
        concordance += pos * (negatives_below + .5*neg)
        negatives_below += neg
    return concordance / (positives*negatives)


def confusion(labels, predictions):
    labels, numeric = checked_arrays(labels, predictions)
    if any(value not in (0, 1) for value in numeric):
        raise ValueError("Predictions must be binary")
    result = dict(tp=0, fp=0, tn=0, fn=0)
    for label, prediction in zip(labels, numeric):
        result[{(1, 1): "tp", (0, 1): "fp", (0, 0): "tn", (1, 0): "fn"}[(label, prediction)]] += 1
    return result


def metrics_from_confusion(counts):
    if set(counts) != {"tp", "fp", "tn", "fn"} or any(
        isinstance(n, bool) or not isinstance(n, Integral) or n < 0 for n in counts.values()
    ) or sum(counts.values()) == 0:
        raise ValueError("Nonempty, nonnegative integer confusion counts required")
    tp, fp, tn, fn = (counts[k] for k in ["tp", "fp", "tn", "fn"])
    precision = tp/(tp+fp) if tp+fp else 0.0
    recall = tp/(tp+fn) if tp+fn else None
    specificity = tn/(tn+fp) if tn+fp else None
    denominator = (tp+fp)*(tp+fn)*(tn+fp)*(tn+fn)
    return {"precision": precision, "recall": recall, "specificity": specificity,
            "f1": 2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0,
            "accuracy": (tp+tn)/(tp+fp+tn+fn),
            "balanced_accuracy": (recall+specificity)/2 if recall is not None and specificity is not None else None,
            "mcc": (tp*tn-fp*fn)/math.sqrt(denominator) if denominator else 0.0}


def evaluate(labels, scores, threshold):
    labels, scores = checked_arrays(labels, scores)
    threshold = finite_score(threshold)
    counts = confusion(labels, [int(s >= threshold) for s in scores])
    return {**counts, **metrics_from_confusion(counts), "average_precision": average_precision(labels, scores),
            "auroc": auroc(labels, scores), "positive_prevalence": sum(labels)/len(labels), "span_count": len(labels)}


def validate_rows(rows, expected_split=None):
    if not rows:
        raise ValueError("No rows")
    ids = [r["annotation_id"] for r in rows]
    if any(not isinstance(key, str) or not key for key in ids) or len(ids) != len(set(ids)):
        raise ValueError("Duplicate or empty annotation IDs")
    question_splits = {}
    for row in rows:
        if row.get("split") not in {"dev", "test"} or (expected_split and row["split"] != expected_split):
            raise ValueError("Retrospective dev/test scope only; training/confirmation rows rejected")
        qid = row["question_id"]
        if not qid or question_splits.setdefault(qid, row["split"]) != row["split"]:
            raise ValueError("Question crosses splits")
    checked_arrays([r["binary_label"] for r in rows], [0]*len(rows))


def dev_threshold(rows, score_field):
    validate_rows(rows, "dev")
    labels, scores = checked_arrays([r["binary_label"] for r in rows], [r[score_field] for r in rows])
    if set(labels) != {0, 1}:
        raise ValueError("Both classes required to select a dev threshold")
    best = None
    for threshold in sorted(set(scores)):
        counts = confusion(labels, [int(x >= threshold) for x in scores])
        metrics = metrics_from_confusion(counts)
        key = (metrics["f1"], metrics["precision"], metrics["recall"], metrics["accuracy"], -threshold)
        if best is None or key > best[0]:
            best = (key, threshold)
    return best[1]


def fit_fact_type_prior(dev_rows):
    validate_rows(dev_rows, "dev")
    groups = defaultdict(list)
    for row in dev_rows:
        if not isinstance(row.get("fact_type"), str) or not row["fact_type"]:
            raise ValueError("Missing fact type")
        groups[row["fact_type"]].append(row["binary_label"])
    return {"rates": {key: sum(values)/len(values) for key, values in sorted(groups.items())},
            "counts": {key: len(values) for key, values in sorted(groups.items())},
            "fallback": sum(r["binary_label"] for r in dev_rows)/len(dev_rows), "fit_split": "dev"}


def quantile(values, probability):
    values = sorted(values)
    if not values or not 0 <= probability <= 1:
        raise ValueError("Nonempty quantile sample and probability in [0,1] required")
    index = (len(values)-1)*probability
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo]+(values[hi]-values[lo])*(index-lo)


def paired_cluster_bootstrap(rows, thresholds, comparisons, cluster_field, replicates=5000, seed=20260904):
    """Paired percentile intervals, resampling complete clusters; thresholds stay fixed.

    Describes uncertainty conditional on already fitted dev policies and provisional
    labels. Does not correct test-set model selection or establish independent data.
    """
    validate_rows(rows, "test")
    if not isinstance(replicates, int) or replicates < 2:
        raise ValueError("At least two bootstrap replicates required")
    clusters = defaultdict(list)
    for row in rows:
        if not row.get(cluster_field):
            raise ValueError("Missing cluster ID")
        clusters[row[cluster_field]].append(row)
    clusters = [clusters[key] for key in sorted(clusters)]
    if len(clusters) < 2:
        return {"cluster_field": cluster_field, "cluster_count": len(clusters), "status": "insufficient_clusters", "intervals": []}
    fields = sorted({x for pair in comparisons for x in pair})
    draws = {(a, b, m): [] for a, b in comparisons for m in ["average_precision", "f1", "balanced_accuracy", "mcc"]}
    point = {f: evaluate([r["binary_label"] for r in rows], [r[f] for r in rows], thresholds[f]) for f in fields}
    rng = random.Random(seed)
    for _ in range(replicates):
        sample = [row for _ in clusters for row in clusters[rng.randrange(len(clusters))]]
        labels = [r["binary_label"] for r in sample]
        measured = {f: evaluate(labels, [r[f] for r in sample], thresholds[f]) for f in fields}
        for (a, b, metric), values in draws.items():
            va, vb = measured[a][metric], measured[b][metric]
            if va is not None and vb is not None:
                values.append(va-vb)
    intervals = [{"signal": a, "reference": b, "metric": metric,
                  "point_difference": point[a][metric]-point[b][metric] if point[a][metric] is not None and point[b][metric] is not None else None,
                  "lower_95": quantile(values, .025) if values else None,
                  "upper_95": quantile(values, .975) if values else None,
                  "valid_replicates": len(values), "undefined_replicates": replicates-len(values)}
                 for (a, b, metric), values in draws.items()]
    return {"cluster_field": cluster_field, "cluster_count": len(clusters), "status": "exploratory_percentile_intervals",
            "replicates": replicates, "seed": seed, "paired_resampling": True, "thresholds_refitted": False,
            "intervals": intervals}
