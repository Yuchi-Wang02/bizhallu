"""Percentile cluster bootstrap for ranking metrics, paired differences and proportions (standard library only).

Every statistic of one call is computed on the same resampled clusters, so differences are paired.
Clusters are resampled with replacement within each stratum (for example each evaluation role).
Average precision and AUROC come from src/detector_metrics.py, which is not modified.
"""
from __future__ import annotations

import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import detector_metrics as metrics

APPROXIMATE_BELOW_CLUSTERS = 20


def _key(spec):
    return spec if callable(spec) else (lambda row: row.get(spec))


def cluster_strata(rows, cluster, stratum=None):
    """{stratum: [rows of one cluster, ...]} with clusters and strata in sorted order."""
    cluster_of, stratum_of = _key(cluster), _key(stratum) if stratum is not None else (lambda row: "all")
    grouped = defaultdict(lambda: defaultdict(list))
    for row in rows:
        key = cluster_of(row)
        if key in (None, ""):
            raise ValueError(f"missing cluster id for {row.get('annotation_id')}")
        grouped[stratum_of(row)][key].append(row)
    return {name: [clusters[key] for key in sorted(clusters)] for name, clusters in sorted(grouped.items())}


def resample(strata, rng):
    sample = []
    for name in sorted(strata):
        clusters = strata[name]
        for _ in clusters:
            sample.extend(clusters[rng.randrange(len(clusters))])
    return sample


def _evaluate(statistics, rows):
    """Callables first; ("difference", a, b) entries reuse the values of a and b from the same rows."""
    values = {name: spec(rows) for name, spec in statistics.items() if callable(spec)}
    for name, spec in statistics.items():
        if not callable(spec):
            _, first, second = spec
            a, b = values[first], values[second]
            values[name] = None if a is None or b is None else a - b
    return values


def bootstrap(rows, statistics, cluster, replicates=5000, seed=20260904, stratum=None):
    """Point estimate and percentile 95% interval of every statistic; undefined replicates are counted.

    `statistics` maps a name to a function of a row list, or to ("difference", name_a, name_b).
    """
    if not isinstance(replicates, int) or replicates < 2:
        raise ValueError("at least two bootstrap replicates required")
    strata = cluster_strata(rows, cluster, stratum)
    cluster_count = sum(len(clusters) for clusters in strata.values())
    point = _evaluate(statistics, rows)
    draws = {name: [] for name in statistics}
    rng = random.Random(seed)
    for _ in range(replicates):
        for name, value in _evaluate(statistics, resample(strata, rng)).items():
            if value is not None:
                draws[name].append(value)
    estimates = {}
    for name, values in draws.items():
        estimates[name] = {"point": point[name],
                           "lower_95": metrics.quantile(values, 0.025) if values else None,
                           "upper_95": metrics.quantile(values, 0.975) if values else None,
                           "valid_replicates": len(values), "undefined_replicates": replicates - len(values)}
    return {"cluster": cluster if isinstance(cluster, str) else "per-role cluster unit",
            "cluster_count": cluster_count, "clusters_by_stratum": {name: len(c) for name, c in strata.items()},
            "approximate": cluster_count < APPROXIMATE_BELOW_CLUSTERS, "replicates": replicates, "seed": seed,
            "estimates": estimates}


# ---------------------------------------------------------- statistic makers ---

def _labels_scores(rows, arm, label="binary_label"):
    """Labels and scores of the rows that have a score for this arm (rows excluded for an arm carry None)."""
    kept = [row for row in rows if row.get(arm) is not None]
    return [row[label] for row in kept], [row[arm] for row in kept]


def average_precision_of(arm, label="binary_label"):
    def statistic(rows):
        labels, scores = _labels_scores(rows, arm, label)
        return metrics.average_precision(labels, scores) if labels else None
    return statistic


def auroc_of(arm, label="binary_label"):
    def statistic(rows):
        labels, scores = _labels_scores(rows, arm, label)
        return metrics.auroc(labels, scores) if labels else None
    return statistic


def ratio(numerator, denominator):
    """sum(numerator(row)) / sum(denominator(row)); None when the denominator is zero."""
    def statistic(rows):
        total = sum(denominator(row) for row in rows)
        return None if not total else sum(numerator(row) for row in rows) / total
    return statistic


def ranking_intervals(rows, arms, cluster, contrasts=(), replicates=5000, seed=20260904, stratum=None,
                      label="binary_label"):
    """AP and AUROC of every arm and paired differences for (arm, reference) contrasts."""
    statistics = {}
    for arm in arms:
        statistics[f"{arm}|average_precision"] = average_precision_of(arm, label)
        statistics[f"{arm}|auroc"] = auroc_of(arm, label)
    for arm, reference in contrasts:
        for metric in ("average_precision", "auroc"):
            statistics[f"{arm} minus {reference}|{metric}"] = ("difference", f"{arm}|{metric}",
                                                               f"{reference}|{metric}")
    return bootstrap(rows, statistics, cluster, replicates, seed, stratum)
