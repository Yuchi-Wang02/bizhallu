"""Scoring and reports of the decision battery v2 (standard library only).

Rows are one labelled span each, from every span set whose file exists. Thresholds follow the
config's threshold_rule; ranking metrics carry percentile cluster-bootstrap intervals. Reports
never contain directional wording: estimates and intervals only.
"""
from __future__ import annotations

import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import detector_metrics as metrics  # noqa: E402
from bizhallu import cluster_bootstrap as cb  # noqa: E402

REFERENCE_ARM = "one_minus_min_top2_margin"
UNCERTAINTY_ARMS = ["one_minus_min_top2_margin", "mean_token_entropy"]
OFFLINE_CONTINUOUS_ARMS = UNCERTAINTY_ARMS + ["dev_span_kind_prior", "dev_question_type_prior"]
LEGACY_PRIOR_ARM = "dev_fact_type_prior"
BINARY_ARMS = {"rule_checker": ("contradicted", "abstain"), "evidence_lookup": ("flagged", "abstain")}
TWO_VALUE_TYPES = {"country_comparison_month", "monthly_revenue_change"}
ABSTAIN_OPTIONS = {"status": "x9", "value_faithful": "f4"}
DESCRIPTIVE_QUESTIONS = ["relation", "rank_claim", "direction_claim", "source_row", "source_column"]
SCORE_DECIMALS = 6
HISTORICAL_REFERENCE_LINE = ("Historical reference (AI provisional labels, 103 test spans): prevalence 61/103 = 0.592, "
                             "all-positive F1 0.744, fact-type prior AUROC 0.768.")
HUMAN_LABEL_DISCLOSURE = ("The 205 AI provisional labels and the detector scores are in the public repository. "
                          "Their separation from the human labels rests on the raters' declarations, not on a "
                          "technical control.")


def dm_column(score, arm_id):
    return f"{score}@{arm_id}"


def derivation_need(span_kind, question_type):
    if span_kind == "month" or question_type == "return_impact_month":
        return "read"
    return "two_value" if question_type in TWO_VALUE_TYPES else "top_k"


def rounded(value, annotation_id, name):
    """Aggregated means are rounded to 6 decimals before any threshold comparison; bad values stop the run."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{annotation_id}: {name} is not a finite number: {value!r}")
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{annotation_id}: {name} is outside [0, 1]: {value!r}")
    return round(float(value), SCORE_DECIMALS)


# ------------------------------------------------------------------ rows ---

def binary_flags(verdict, arm):
    flag_value, abstain_value = BINARY_ARMS[arm]
    if verdict is None:
        return None, None
    return int(verdict == flag_value), int(verdict == abstain_value)


def attach_dm_scores(rows, arm_id, aggregated, score_names):
    """Add `<score>@<arm_id>` columns (rounded) and the slot yes-probability used by the funnel."""
    for row in rows:
        item = aggregated.get(row["annotation_id"])
        if item is None:
            continue
        for name in score_names:
            if name in item:
                row[dm_column(name, arm_id)] = rounded(item[name], row["annotation_id"], name)
        if "dm_risk" in item:
            row[dm_column("slot_yes", arm_id)] = round(1.0 - row[dm_column("dm_risk", arm_id)], SCORE_DECIMALS)
    return rows


# ------------------------------------------------------------ thresholds ---

def budget_threshold(fit_rows, arm, budget):
    """Lowest fit-set score whose false-flag share on fit-set negatives is within the budget."""
    if not fit_rows:
        return {"threshold": math.inf, "degenerate": True, "reason": "empty fit set", "fit_size": 0}
    values = sorted({row[arm] for row in fit_rows})
    negatives = [row[arm] for row in fit_rows if row["binary_label"] == 0]
    chosen = math.inf
    for value in values:
        if not negatives or sum(1 for score in negatives if score >= value) / len(negatives) <= budget:
            chosen = value
            break
    flagged_share = sum(1 for row in fit_rows if row[arm] >= chosen) / len(fit_rows)
    if chosen == math.inf:
        reason = "no threshold meets the false-flag budget"
    elif chosen == values[0]:
        reason = "threshold equals the lowest fit-set score"
    elif flagged_share >= 0.95:
        reason = "threshold flags at least 95 percent of the fit set"
    else:
        reason = None
    return {"threshold": chosen, "degenerate": reason is not None, "reason": reason, "fit_size": len(fit_rows),
            "fit_negatives": len(negatives), "fit_flagged_share": flagged_share}


def legacy_threshold(dev_rows, arm):
    rows = [{**row, "split": "dev"} for row in dev_rows]
    return {"threshold": metrics.dev_threshold(rows, arm), "degenerate": False, "reason": None,
            "fit_size": len(rows)}


def fit_sets(rows, span_sources=None):
    """for_test and for_heldout fit sets of analysis_policy.threshold_rule, plus notes."""
    def usable(row):
        return row["role"] == "dev" and row["span_kind"] != "month" and row["binary_label"] is not None
    for_test = [row for row in rows if row["span_set_id"] == "full100_205" and usable(row)]
    extractor = [row for row in rows if row["span_set_id"] == "extractor_only_devtest_v1" and usable(row)]
    notes = []
    if span_sources is None or not extractor:
        notes.append("for_heldout uses the for_test fit set: the extractor-only dev spans or span_source_devtest_v1.jsonl "
                     "are not available")
        return {"for_test": for_test, "for_heldout": for_test}, notes
    both = [row for row in for_test if span_sources.get(row["annotation_id"]) == "both"]
    for_heldout = both + extractor
    if not for_heldout:
        notes.append("for_heldout fit set is empty; it uses the for_test fit set")
        for_heldout = for_test
    return {"for_test": for_test, "for_heldout": for_heldout}, notes


def fit_thresholds(rows, arms, config, mapping, span_sources=None, frozen=None):
    """Thresholds per fit set and arm. ai_provisional uses the legacy dev max-F1 rule only."""
    policy = config["analysis_policy"]
    fixed = {"threshold": 1.0, "degenerate": False, "reason": "fixed: flags every span"}
    if mapping == "ai_provisional":
        dev = [row for row in rows if row["span_set_id"] == "full100_205" and row["role"] == "dev"
               and row["binary_label"] is not None]
        table = {}
        for arm in arms:
            try:
                table[arm] = legacy_threshold(dev, arm)
            except ValueError as error:
                table[arm] = {"threshold": math.inf, "degenerate": True, "reason": str(error)}
        table["all_positive"] = fixed
        return {"rule": policy["threshold_rule"]["legacy"], "source": "legacy dev maximum F1, fitted at scoring time",
                "for_test": table, "for_heldout": table, "notes": ["ai_provisional labels: legacy rule only"]}
    if frozen is not None:
        stored = frozen["dev_thresholds"]
        tables = {key: {arm: {**value, "threshold": math.inf if value["threshold"] is None else value["threshold"]}
                        for arm, value in stored[key].items()} for key in ("for_test", "for_heldout")}
        return {"rule": stored.get("rule"), "source": "freeze record", **tables, "notes": []}
    sets, notes = fit_sets(rows, span_sources)
    budget = policy["false_flag_budget"]
    result = {"rule": policy["threshold_rule"]["rule"], "source": "PRE-FREEZE OFFLINE ARMS: fitted on dev at scoring time",
              "notes": notes}
    for key, fit in sets.items():
        table = {arm: budget_threshold([row for row in fit if row.get(arm) is not None], arm, budget) for arm in arms}
        table["all_positive"] = fixed
        result[key] = table
    return result


def threshold_for(thresholds, role):
    return thresholds["for_heldout"] if role == "heldout" else thresholds["for_test"]


def json_threshold(value):
    return None if value == math.inf else value


# ---------------------------------------------------------- metric blocks ---

def counts_line(rows):
    positives = sum(row["binary_label"] for row in rows)
    return {"spans": len(rows), "positives": positives, "questions": len({row["question_id"] for row in rows}),
            "clusters": len({row["evidence_cluster"] for row in rows}),
            "prevalence": positives / len(rows) if rows else None}


def threshold_metrics(rows, arm, info):
    threshold = info["threshold"]
    rows = [row for row in rows if row.get(arm) is not None]
    labels = [row["binary_label"] for row in rows]
    flags = [int(row[arm] >= threshold) for row in rows]
    counts = metrics.confusion(labels, flags)
    result = {"threshold": json_threshold(threshold), "degenerate": info["degenerate"], "flagged": sum(flags)}
    if not info["degenerate"]:
        derived = metrics.metrics_from_confusion(counts)
        result.update({"precision": derived["precision"], "recall": derived["recall"], "f1": derived["f1"],
                       "false_flag_share": counts["fp"] / (counts["fp"] + counts["tn"]) if counts["fp"] + counts["tn"] else None})
    return result


def binary_arm_statistics(arm):
    flag, abstain = f"{arm}_flag", f"{arm}_abstain"
    return {
        f"{arm}|coverage": cb.ratio(lambda row: 1 - row[abstain], lambda row: 1),
        f"{arm}|precision": cb.ratio(lambda row: row[flag] * row["binary_label"], lambda row: row[flag]),
        f"{arm}|recall": cb.ratio(lambda row: row[flag] * row["binary_label"], lambda row: row["binary_label"]),
    }


def metric_section(rows, continuous_arms, thresholds, cluster, primary, sensitivity_cluster, replicates, seed,
                   exclusions=None):
    """AP and AUROC with intervals for every continuous arm, threshold columns, binary arms and the primary contrast.

    `exclusions` maps an arm to annotation ids that the config excludes for that arm only (extra_excluded);
    those rows carry no score for the arm. Any other missing score makes the arm a status row.
    """
    exclusions = exclusions or {}
    section = {"counts": counts_line(rows), "cluster": cluster, "arms": {}, "binary_arms": {}, "status": {}}
    if not rows:
        section["status"]["all"] = "no labelled spans"
        return section
    rows = [{**row, **{arm: None for arm, ids in exclusions.items() if row["annotation_id"] in ids}} for row in rows]
    available = []
    for arm in continuous_arms:
        missing = sum(1 for row in rows if row.get(arm) is None and row["annotation_id"] not in exclusions.get(arm, ()))
        if missing:
            section["status"][arm] = f"missing for {missing} of {len(rows)} spans"
        else:
            available.append(arm)
            if exclusions.get(arm):
                section["status"][f"{arm} (note)"] = (f"{sum(1 for row in rows if row['annotation_id'] in exclusions[arm])} "
                                                      "spans excluded for this arm by extra_excluded")
    contrasts = [(arm, REFERENCE_ARM) for arm in available if arm != REFERENCE_ARM and REFERENCE_ARM in available]
    statistics = {}
    for arm in available:
        statistics[f"{arm}|average_precision"] = cb.average_precision_of(arm)
        statistics[f"{arm}|auroc"] = cb.auroc_of(arm)
    for arm, reference in contrasts:
        for metric in ("average_precision", "auroc"):
            statistics[f"{arm} minus {reference}|{metric}"] = ("difference", f"{arm}|{metric}", f"{reference}|{metric}")
    binary = [arm for arm in BINARY_ARMS if all(row.get(f"{arm}_flag") is not None for row in rows)]
    for arm in BINARY_ARMS:
        if arm not in binary:
            section["status"][arm] = "not available for every span"
    for arm in binary:
        statistics.update(binary_arm_statistics(arm))
    boot = cb.bootstrap(rows, statistics, cluster, replicates, seed)
    section["bootstrap"] = {key: boot[key] for key in ("cluster", "cluster_count", "approximate", "replicates", "seed")}
    estimates = boot["estimates"]
    for arm in available:
        section["arms"][arm] = {"average_precision": estimates[f"{arm}|average_precision"],
                                "auroc": estimates[f"{arm}|auroc"]}
        if arm in thresholds:
            section["arms"][arm]["at_threshold"] = threshold_metrics(rows, arm, thresholds[arm])
    section["contrasts"] = {f"{arm} minus {reference}": {metric: estimates[f"{arm} minus {reference}|{metric}"]
                                                         for metric in ("average_precision", "auroc")}
                            for arm, reference in contrasts}
    for arm in binary:
        section["binary_arms"][arm] = {name: estimates[f"{arm}|{name}"] for name in ("coverage", "precision", "recall")}
        section["binary_arms"][arm]["abstain"] = sum(row[f"{arm}_abstain"] for row in rows)
    prevalence = section["counts"]["prevalence"]
    section["all_positive"] = {"prevalence": prevalence, "f1": 2 * prevalence / (1 + prevalence) if prevalence else 0.0}
    name = f"{primary} minus {REFERENCE_ARM}"
    if primary in available and REFERENCE_ARM in available:
        section["primary_contrast"] = {"contrast": name, "cluster": cluster, **section["contrasts"][name]}
        if sensitivity_cluster:
            sensitivity = cb.ranking_intervals(rows, [primary, REFERENCE_ARM], sensitivity_cluster,
                                               [(primary, REFERENCE_ARM)], replicates, seed)
            section["primary_contrast_sensitivity"] = {
                "cluster": sensitivity_cluster, "cluster_count": sensitivity["cluster_count"],
                "approximate": sensitivity["approximate"],
                **{metric: sensitivity["estimates"][f"{name}|{metric}"] for metric in ("average_precision", "auroc")}}
    else:
        section["primary_contrast"] = {"contrast": name, "status": f"not computed: {primary} or {REFERENCE_ARM} unavailable"}
    return section


# ------------------------------------------------------- mechanism tables ---

def mechanism_groups(wrong_rows, field):
    groups = defaultdict(list)
    for row in wrong_rows:
        groups[row.get(field)].append(row)
    return groups


def mechanism_table(rows, columns, thresholds, config, human):
    """Rows per mechanism against all correct spans of the same set (config mechanism_table)."""
    spec = config["analysis_policy"]["mechanism_table"]
    minimum = spec["minimum_cell"]
    correct = [row for row in rows if row["binary_label"] == 0]
    wrong = [row for row in rows if row["binary_label"] == 1]
    table = {"heading": "human mechanism codes" if human else "exploratory: checker mechanism families",
             "correct_spans": len(correct), "rows": {}, "notes": []}
    if human:
        unresolved = [row for row in wrong if row.get("mechanism") in (None, "", "unresolved")]
        table["unresolved_mechanism_spans"] = len(unresolved)
        wrong = [row for row in wrong if row not in unresolved]
        groups = mechanism_groups(wrong, "mechanism")
        if len(groups.get("M2", [])) < minimum or len(groups.get("M3", [])) < minimum:
            groups["M2+M3 value-level errors"] = groups.pop("M2", []) + groups.pop("M3", [])
            table["notes"].append("M2 and M3 are reported together as value-level errors (merge_rule)")
        m1 = groups.get("M1", [])
        groups["M1 entity_name"] = [row for row in m1 if row["span_kind"] == "entity_name"]
        groups["M1 other span kinds"] = [row for row in m1 if row["span_kind"] != "entity_name"]
    else:
        groups = mechanism_groups(wrong, "checker_mechanism")
        columns = [column for column in columns if column != "rule_checker"]
    for name, group in sorted(groups.items(), key=lambda item: str(item[0])):
        entry = {"wrong_spans": len(group)}
        if len(group) >= minimum and correct:
            for column in columns:
                entry[column] = mechanism_cell(group, correct, column, thresholds)
        else:
            entry["note"] = f"fewer than {minimum} spans: counts only"
        table["rows"][str(name)] = entry
    table["false_flag_row"] = false_flag_row(correct, columns, thresholds)
    return table


def mechanism_cell(group, correct, column, thresholds):
    if column in BINARY_ARMS:
        flags = [row.get(f"{column}_flag") for row in group]
        if any(flag is None for flag in flags):
            return {"status": "not available"}
        return {"flagged_share": sum(flags) / len(flags)}
    if any(row.get(column) is None for row in group + correct):
        return {"status": "not available"}
    labels = [1] * len(group) + [0] * len(correct)
    cell = {"auroc": metrics.auroc(labels, [row[column] for row in group + correct])}
    info = thresholds.get(column)
    if info is not None and not info["degenerate"]:
        cell["flagged_share"] = sum(1 for row in group if row[column] >= info["threshold"]) / len(group)
    return cell


def false_flag_row(correct, columns, thresholds):
    result = {}
    for column in columns:
        if column in BINARY_ARMS:
            flagged = [row for row in correct if row.get(f"{column}_flag")]
        else:
            info = thresholds.get(column)
            if info is None or info["degenerate"] or any(row.get(column) is None for row in correct):
                result[column] = {"status": "not available or degenerate threshold"}
                continue
            flagged = [row for row in correct if row[column] >= info["threshold"]]
        by_kind = Counter(row["span_kind"] for row in correct)
        flagged_kind = Counter(row["span_kind"] for row in flagged)
        result[column] = {"overall": len(flagged) / len(correct) if correct else None,
                          "by_span_kind": {kind: flagged_kind[kind] / count for kind, count in sorted(by_kind.items())}}
    return result


def derivation_table(rows, arms, minimum=10):
    table = {}
    for stratum in ("read", "two_value", "top_k"):
        group = [row for row in rows if row["derivation_need"] == stratum]
        positives = sum(row["binary_label"] for row in group)
        entry = {"spans": len(group), "positives": positives, "negatives": len(group) - positives}
        if entry["negatives"] >= minimum and positives:
            entry["auroc_point"] = {arm: metrics.auroc([row["binary_label"] for row in group], [row[arm] for row in group])
                                    for arm in arms if all(row.get(arm) is not None for row in group)}
        else:
            entry["note"] = "counts only"
        table[stratum] = entry
    return table


# -------------------------------------------------------- estimands E1-E4 ---

def event_count(rows):
    """Spans of one answer with mechanism M1 and the same matched_row_id count as one event."""
    keys = set()
    singles = 0
    for row in rows:
        if row.get("mechanism") == "M1" and row.get("matched_row_id"):
            keys.add((row["question_id"], row["matched_row_id"]))
        else:
            singles += 1
    return len(keys) + singles


def estimand_e1(rows, replicates, seed):
    wrong = [row for row in rows if row["binary_label"] == 1]

    def numerator(row, kind="currency_or_number"):
        return int(row["binary_label"] == 1 and row.get("slot_label") == "incorrect"
                   and row.get("value_label") == "faithful" and row["span_kind"] == kind)
    statistics = {
        "share_of_all_wrong": cb.ratio(numerator, lambda row: row["binary_label"]),
        "share_of_numeric_wrong": cb.ratio(numerator, lambda row: int(
            row["binary_label"] == 1 and row["span_kind"] in {"currency_or_number", "percentage"})),
    }
    boot = cb.bootstrap(rows, statistics, "evidence_cluster", replicates, seed) if rows else None
    numerator_rows = [row for row in rows if numerator(row)]
    answers_wrong = {row["question_id"] for row in wrong}
    answers_numerator = {row["question_id"] for row in numerator_rows}
    return {
        "numerator_spans": len(numerator_rows), "wrong_spans": len(wrong),
        "estimates": boot["estimates"] if boot else None,
        "cluster_count": boot["cluster_count"] if boot else 0,
        "other_span_kinds": {kind: {"numerator_spans": sum(numerator(row, kind) for row in rows),
                                    "wrong_spans_of_kind": sum(1 for row in wrong if row["span_kind"] == kind)}
                             for kind in ("entity_name", "code", "month", "rank_marker")},
        "answer_level": {"answers_with_numerator_span": len(answers_numerator), "answers_with_wrong_span": len(answers_wrong),
                         "share": len(answers_numerator) / len(answers_wrong) if answers_wrong else None},
        "error_events": {"numerator": event_count(numerator_rows), "all_wrong": event_count(wrong)},
    }


def pooled_auroc(rows, is_positive, is_negative, arm, role_field="role"):
    """AUROC over within-role pairs only; pair counts are summed across roles, ties count one half."""
    concordance = pairs = 0.0
    by_role = defaultdict(list)
    for row in rows:
        by_role[row[role_field]].append(row)
    for group in by_role.values():
        positives = [row[arm] for row in group if is_positive(row)]
        negatives = sorted(row[arm] for row in group if is_negative(row))
        if not positives or not negatives:
            continue
        for score in positives:
            below = _count_below(negatives, score)
            equal = _count_below(negatives, score, inclusive=True) - below
            concordance += below + 0.5 * equal
        pairs += len(positives) * len(negatives)
    return concordance / pairs if pairs else None


def pooled_auroc_of(is_positive, is_negative, arm):
    def statistic(rows):
        return pooled_auroc(rows, is_positive, is_negative, arm)
    return statistic


def _count_below(sorted_values, value, inclusive=False):
    low, high = 0, len(sorted_values)
    while low < high:
        middle = (low + high) // 2
        if sorted_values[middle] < value or (inclusive and sorted_values[middle] == value):
            low = middle + 1
        else:
            high = middle
    return low


def estimand_e2(rows, arms, replicates, seed):
    def m1(row):
        return row["binary_label"] == 1 and row.get("mechanism") == "M1"

    def other_wrong(row):
        return row["binary_label"] == 1 and row.get("mechanism") not in ("M1", None, "", "unresolved")

    def correct(row):
        return row["binary_label"] == 0
    result = {}
    for scope, subset in [("pooled", rows)] + [(role, [row for row in rows if row["role"] == role])
                                              for role in sorted({row["role"] for row in rows})]:
        statistics = {}
        for arm in arms:
            if any(row.get(arm) is None for row in subset):
                continue
            statistics[f"{arm}|m1"] = pooled_auroc_of(m1, correct, arm)
            statistics[f"{arm}|other"] = pooled_auroc_of(other_wrong, correct, arm)
            statistics[f"{arm}|contrast"] = ("difference", f"{arm}|m1", f"{arm}|other")
        if not subset or not statistics:
            result[scope] = {"status": "no spans or no arms"}
            continue
        boot = cb.bootstrap(subset, statistics, "evidence_cluster", replicates, seed, stratum="role")
        result[scope] = {"counts": {"m1": sum(map(m1, subset)), "other_wrong": sum(map(other_wrong, subset)),
                                    "correct": sum(map(correct, subset))},
                         "cluster_count": boot["cluster_count"], "estimates": boot["estimates"]}
    return result


def role_cluster(row):
    return row["question_id"] if row["role"] == "test" else row["evidence_cluster"]


def estimand_e3(rows, arms, thresholds, replicates, seed):
    m1_rows = [row for row in rows if row["binary_label"] == 1 and row.get("mechanism") == "M1"]
    if not m1_rows or any(row.get("rule_checker_flag") is None for row in m1_rows):
        return {"status": "no M1 spans or checker verdicts missing", "m1_spans": len(m1_rows)}

    def flagged(arm):
        def value(row):
            info = threshold_for(thresholds, row["role"]).get(arm)
            return int(info is not None and row[arm] >= info["threshold"])
        return value
    statistics = {"rule_checker": cb.ratio(lambda row: row["rule_checker_flag"], lambda row: 1)}
    for arm in arms:
        if all(row.get(arm) is not None for row in m1_rows):
            statistics[arm] = cb.ratio(flagged(arm), lambda row: 1)
            statistics[f"rule_checker minus {arm}"] = ("difference", "rule_checker", arm)
    result = {"m1_spans": len(m1_rows)}
    for scope, subset in [("pooled", m1_rows)] + [(role, [row for row in m1_rows if row["role"] == role])
                                                 for role in sorted({row["role"] for row in m1_rows})]:
        boot = cb.bootstrap(subset, statistics, role_cluster, replicates, seed, stratum="role")
        result[scope] = {"spans": len(subset), "cluster_count": boot["cluster_count"], "estimates": boot["estimates"]}
    return result


def estimand_e4(rows, primary, replicates, seed, minimum=10):
    subset = [row for row in rows if row.get("rule_checker_abstain") == 1]
    labels = {row["binary_label"] for row in subset}
    entry = {"spans": len(subset), "positives": sum(row["binary_label"] for row in subset)}
    if len(subset) < minimum or labels != {0, 1} or any(row.get(primary) is None for row in subset):
        entry["note"] = "counts only"
        return entry
    boot = cb.bootstrap(subset, {"auroc": cb.auroc_of(primary)}, role_cluster, replicates, seed)
    entry.update({"cluster_count": boot["cluster_count"], "auroc": boot["estimates"]["auroc"]})
    return entry


def funnel(rows, primary_arm_id, thresholds, minimum=10):
    yes_column, risk_column = dm_column("slot_yes", primary_arm_id), dm_column("dm_risk", primary_arm_id)
    layers = {"layer_1": [], "layer_2": [], "layer_3": []}
    for row in rows:
        if row.get("rule_checker_flag") is not None and not row["rule_checker_abstain"]:
            layers["layer_1"].append((row, row["rule_checker_flag"]))
        elif row.get(yes_column) is not None and (row[yes_column] < 0.35 or row[yes_column] > 0.65):
            info = threshold_for(thresholds, row["role"]).get(risk_column)
            prediction = int(info is not None and row[risk_column] >= info["threshold"])
            layers["layer_2"].append((row, prediction))
        else:
            layers["layer_3"].append((row, None))
    result = {}
    for name, items in layers.items():
        entry = {"spans": len(items), "share": len(items) / len(rows) if rows else None}
        if name != "layer_3":
            errors = sum(1 for row, prediction in items if prediction != row["binary_label"])
            entry["errors"] = errors
            if len(items) >= minimum:
                entry["error_share"] = errors / len(items)
        result[name] = entry
    return result


# ---------------------------------------------------------- other tables ---

def repeat_spread(aggregated, arm):
    if (arm.get("notes") or {}).get("deterministic") is True:
        return {"status": "deterministic server, not applicable"}
    if not aggregated:
        return {"status": "no responses"}
    if max(item["repeats"] for item in aggregated.values()) < 2:
        return {"status": "one repeat per span; spread not measured"}
    ranges = defaultdict(list)
    for item in aggregated.values():
        for name, value in item.get("ranges", {}).items():
            ranges[name].append(value)
    return {name: {"mean_range": sum(values) / len(values), "max_range": max(values)} for name, values in sorted(ranges.items())}


def interval_count(value):
    if isinstance(value, dict):
        own = int("lower_95" in value and value.get("lower_95") is not None)
        return own + sum(interval_count(item) for item in value.values())
    if isinstance(value, list):
        return sum(interval_count(item) for item in value)
    return 0


def diagnostics(response_rows, states, config):
    """Label-free diagnostic tables of one arm by span_kind (plan T1.9 item 19)."""
    kinds = {state["annotation_id"]: state.get("span_kind", "unknown") for state in states}
    per_kind = defaultdict(lambda: defaultdict(list))
    models = Counter()
    for row in response_rows:
        if row.get("status") != 200:
            continue
        models[row["response"].get("model")] += 1
        per_kind[kinds.get(row["annotation_id"], "unknown")][row["annotation_id"]].append(row["response"]["answers"])
    table = {}
    for kind, spans in sorted(per_kind.items()):
        rows_out = {}
        for key, spec in config["questions"].items():
            argmax, yes_mid, ranges = [], 0, []
            for answers_list in spans.values():
                for answers in answers_list:
                    answer = answers.get(key)
                    if answer is None:
                        continue
                    if spec["type"] == "noul":
                        yes = float(answer["noul"])
                        argmax.append("yes" if yes >= 0.5 else "no")
                        yes_mid += 0.45 <= yes <= 0.55
                    else:
                        choice = max(answer["probabilities"], key=answer["probabilities"].get)
                        argmax.append(choice)
                values = [float(a[key]["noul"]) if spec["type"] == "noul" else max(a[key]["probabilities"].values())
                          for a in answers_list if key in a]
                if values:
                    ranges.append(max(values) - min(values))
            abstain = ABSTAIN_OPTIONS.get(key)
            options = set(spec.get("criteria") or {}) if "dynamic_criteria" not in spec else None
            rows_out[key] = {
                "responses": len(argmax),
                "abstain_option": abstain,
                "abstain_argmax_share": (sum(1 for c in argmax if c == abstain) / len(argmax)) if abstain and argmax else None,
                "non_abstain_argmax_count": sum(1 for c in argmax if c != abstain),
                "yes_between_0_45_and_0_55_share": (yes_mid / len(argmax)) if spec["type"] == "noul" and argmax else None,
                "never_chosen_options": sorted(options - set(argmax)) if options is not None else "dynamic options",
                "max_repeat_range": max(ranges) if ranges else None,
            }
        descriptive = {key: dict(Counter(max(a[key]["probabilities"], key=a[key]["probabilities"].get)
                                         for answers_list in spans.values() for a in answers_list if key in a))
                       for key in DESCRIPTIVE_QUESTIONS}
        table[kind] = {"spans": len(spans), "questions": rows_out, "descriptive_option_counts": descriptive}
    return {"by_span_kind": table, "models": dict(models)}


def render_diagnostics(result, arm_id, span_set_id):
    lines = [f"# Diagnostics without labels: arm {arm_id}, span set {span_set_id}", "",
             f"Model field values in responses: {result['models']}.", ""]
    for kind, entry in result["by_span_kind"].items():
        lines += [f"## span_kind {kind} ({entry['spans']} spans)", "",
                  ("| question | responses | abstain option argmax share | non-abstain argmax count | "
                   "yes in [0.45, 0.55] | never chosen | max repeat range |"),
                  "| --- | ---: | ---: | ---: | ---: | --- | ---: |"]
        for key, row in entry["questions"].items():
            lines.append(f"| {key} | {row['responses']} | {_fmt(row['abstain_argmax_share'])} | "
                         f"{row['non_abstain_argmax_count']} | {_fmt(row['yes_between_0_45_and_0_55_share'])} | "
                         f"{row['never_chosen_options']} | {_fmt(row['max_repeat_range'])} |")
        lines += ["", "Descriptive questions, argmax option counts:", ""]
        for key, counts in entry["descriptive_option_counts"].items():
            lines.append(f"- {key}: {dict(sorted(counts.items()))}")
        lines.append("")
    return "\n".join(lines) + "\n"


def _fmt(value, digits=3):
    if value is None:
        return "n/a"
    if isinstance(value, float) and value == math.inf:
        return "+inf"
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else str(value)


def _interval(estimate):
    if not estimate or estimate.get("point") is None:
        return "n/a"
    if estimate.get("lower_95") is None:
        return f"{estimate['point']:.3f}"
    return f"{estimate['point']:.3f} [{estimate['lower_95']:.3f}, {estimate['upper_95']:.3f}]"


# ---------------------------------------------------------------- report ---

def render_report(report):
    """Markdown report with every item of plan appendix D; no directional wording."""
    lines = []
    thresholds = report["thresholds"]
    if thresholds["source"].startswith("PRE-FREEZE"):
        listed = ", ".join(f"{arm} {_fmt(value['threshold'], 6)}" for arm, value in sorted(thresholds["for_test"].items()))
        lines += [f"PRE-FREEZE OFFLINE ARMS. Thresholds (for_test): {listed}.", ""]
    if report.get("partial"):
        lines += ["PARTIAL: some spans have fewer scored repeats than the arm setting; see repeat_shortfalls.", ""]
    lines += [f"# Decision battery report: {report['battery_id']}, arms {report['arms_scored']}", "",
              f"Labels: mapping {report['label_mapping']}; files {report['label_files']}.",
              f"Uncertainty signals: {report['signals_source']}. Threshold rule: {thresholds['source']}.", ""]
    for note in thresholds.get("notes", []):
        lines.append(f"- {note}")
    for role, entry in report["roles"].items():
        lines += ["", f"## Role {role} ({entry['sample_status']})", ""]
        for set_name, section in entry["sets"].items():
            lines += _render_section(f"{role}, {set_name}", section)
    if report.get("value_axis"):
        lines += ["", "## Value axis (dm_unfaithful against value labels)", ""]
        for role, section in report["value_axis"].items():
            lines += _render_section(f"value axis, {role}", section)
    lines += ["", "## Primary metric under the label sets for sensitivity", ""]
    sensitivity = report.get("label_set_sensitivity")
    if isinstance(sensitivity, dict) and "status" not in sensitivity:
        for label_set, roles in sensitivity.items():
            for role, contrast in roles.items():
                lines.append(f"- {label_set}, {role}: AP difference {_interval(contrast.get('average_precision'))}; "
                             f"AUROC difference {_interval(contrast.get('auroc'))}")
    else:
        lines.append(f"- {sensitivity.get('status') if isinstance(sensitivity, dict) else sensitivity}")
    lines += ["", "## Coverage", ""]
    for arm_id, coverage in report["coverage"].items():
        lines.append(f"- {arm_id}: {coverage['scored']} of {coverage['expected']} labelled spans scored; "
                     f"missing {coverage['missing'][:10]}{' ...' if len(coverage['missing']) > 10 else ''}")
    lines.append(f"- Label values excluded from binary metrics: {report['excluded_label_values']}")
    lines += ["", "## Decision-model arms", ""]
    for arm_id, info in report["dm_arms"].items():
        lines.append(f"- {arm_id}: requested model {info['requested_model']}; model versions seen {info['model_versions']}; "
                     f"repeats per span {info['repeats_per_span']}; repeat spread {info['repeat_spread']}")
    lines += ["", "## Derivation-need strata (counts)", ""]
    for role, table in report["derivation_need"].items():
        lines.append(f"- {role}: " + "; ".join(f"{name} {entry['spans']} spans, {entry['positives']} positive"
                                                for name, entry in table.items()))
    lines += ["", "## Mechanism tables", ""]
    for role, table in report["mechanism_tables"].items():
        lines.append(f"### {role} ({table['heading']})")
        for name, row in table["rows"].items():
            cells = "; ".join(f"{column} {_render_cell(value)}" for column, value in row.items() if column != "wrong_spans")
            lines.append(f"- {name}: {row['wrong_spans']} wrong spans. {cells}")
        lines.append("")
    lines += ["## Secondary estimands (estimates and intervals only)", ""]
    _flatten_estimates("", report["estimands"], lines)
    lines += ["", "## Funnel", ""]
    _flatten_estimates("", report["funnel"], lines)
    lines += ["", f"Intervals in this report: {report['interval_count']}.", "", "## Module hashes", ""]
    for name, digest in report["module_sha256"].items():
        lines.append(f"- {name}: {digest}")
    if report["human_labels"]:
        lines += ["", HUMAN_LABEL_DISCLOSURE, f"Raters' answers to declaration item 4: {report['rater_declarations']}",
                  "", HISTORICAL_REFERENCE_LINE]
    lines += ["", "## Claim boundary", ""] + [f"- {item}" for item in report["claim_boundary"]]
    return "\n".join(lines) + "\n"


def _flatten_estimates(prefix, value, lines):
    """One line per estimate (point and interval) or count, in nesting order."""
    if isinstance(value, dict):
        if "point" in value and "lower_95" in value:
            lines.append(f"- {prefix}: {_interval(value)}")
            return
        for key, item in value.items():
            _flatten_estimates(f"{prefix} {key}".strip(), item, lines)
    elif value is not None:
        lines.append(f"- {prefix}: {value}")


def _render_cell(value):
    if isinstance(value, dict):
        if "auroc" in value:
            return f"AUROC {_fmt(value['auroc'])}, flagged {_fmt(value.get('flagged_share'))}"
        if "flagged_share" in value:
            return f"flagged {_fmt(value['flagged_share'])}"
        return str(value.get("status"))
    return str(value)


def _render_section(title, section):
    counts = section["counts"]
    boot = section.get("bootstrap", {})
    approximate = " (approximate: fewer than 20 clusters)" if boot.get("approximate") else ""
    lines = [f"### {title}", "",
             (f"Spans {counts['spans']}, positives {counts['positives']}, questions {counts['questions']}, "
              f"clusters {counts['clusters']}; prevalence {_fmt(counts['prevalence'])}. "
              f"Bootstrap cluster unit: {boot.get('cluster')}, {boot.get('cluster_count')} clusters{approximate}; "
              f"{boot.get('replicates')} replicates, seed {boot.get('seed')}."), "",
             "| arm | AP [95% CI] | AUROC [95% CI] | threshold | flagged | precision | recall | F1 |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    for arm, values in section["arms"].items():
        at = values.get("at_threshold", {})
        if at.get("degenerate"):
            tail = f"| DEGENERATE {_fmt(at.get('threshold'), 4)} | {at.get('flagged')} | counts only | | |"
        else:
            tail = (f"| {_fmt(at.get('threshold'), 4)} | {at.get('flagged', 'n/a')} | {_fmt(at.get('precision'))} | "
                    f"{_fmt(at.get('recall'))} | {_fmt(at.get('f1'))} |")
        lines.append(f"| {arm} | {_interval(values['average_precision'])} | {_interval(values['auroc'])} {tail}")
    for arm, status in section.get("status", {}).items():
        lines.append(f"| {arm} | {status} | | | | | | |")
    positive = section.get("all_positive")
    if positive:
        lines.append(f"| all_positive | prevalence {_fmt(positive['prevalence'])} | | 1.0 | {counts['spans']} | | | "
                     f"{_fmt(positive['f1'])} |")
    for arm, values in section.get("binary_arms", {}).items():
        lines.append(f"- {arm}: coverage {_interval(values['coverage'])}, precision {_interval(values['precision'])}, "
                     f"recall {_interval(values['recall'])}; abstain {values['abstain']} (counted as not flagged)")
    primary = section.get("primary_contrast", {})
    if "status" in primary:
        lines.append(f"- Primary contrast {primary['contrast']}: {primary['status']}")
    elif primary:
        lines.append(f"- Primary contrast {primary['contrast']} ({primary['cluster']} clusters): AP difference "
                     f"{_interval(primary['average_precision'])}; AUROC difference {_interval(primary['auroc'])}")
        sensitivity = section.get("primary_contrast_sensitivity")
        if sensitivity:
            lines.append(f"- Same contrast, sensitivity cluster unit {sensitivity['cluster']} "
                         f"({sensitivity['cluster_count']} clusters): AP difference "
                         f"{_interval(sensitivity['average_precision'])}; AUROC difference {_interval(sensitivity['auroc'])}")
    lines.append("")
    return lines
