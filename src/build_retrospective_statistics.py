"""Versioned retrospective appendix; never rewrites full100 draft artifacts."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

import detector_metrics as dm
from build_span_token_alignment import build_token_char_spans, overlapping_tokens, summarize_scores
from validate_confirmation_question_design import evidence_table_projection

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/retrospective_statistics_v2.json"
LEGACY = ROOT / "results/full100_draft_detector_scores.csv"
SCORES = ROOT / "results/full100_statistics_v2_scores.csv"
METRICS = ROOT / "results/full100_statistics_v2_metrics.csv"
REPORT = ROOT / "reports/bizhallu_statistics_v2_report.json"
LOCAL_PATHS = ["outputs/qwen_full100_token_traces.jsonl", "outputs/qwen_full100_generations.jsonl",
               "outputs/full100_draft_span_token_alignment.jsonl"]
PUBLIC_INPUTS = ["configs/retrospective_statistics_v2.json", "configs/detector_baseline_suite.json",
                 "data/processed/business_questions_gold.jsonl", "data/annotations/span_annotations_full100_draft.jsonl",
                 "results/full100_draft_detector_scores.csv", "results/full100_draft_simple_split_metrics.csv",
                 "results/full100_draft_energy_split_metrics.csv"]


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=True, allow_nan=False) + "\n", encoding="utf-8")


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def digest(path):
    # Text hashing remains stable in Windows and Linux clean clones.
    text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def indexed(rows, key):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows) or not all(result):
        raise ValueError(f"Duplicate or empty {key}")
    return result


def signals():
    suite = load(ROOT / "configs/detector_baseline_suite.json")
    return [row["score_field"] for family in ["simple", "energy"] for row in suite["families"][family]]


def assign_clusters(questions):
    """Join all questions sharing any month, including transitive change questions."""
    indexed(questions, "question_id")
    months, content = {}, {}
    for q in questions:
        filters = q["evidence"]["filters"]
        periods = {filters[k] for k in ["year_month", "previous_month", "current_month"] if k in filters}
        if not periods:
            raise ValueError("Historical question lacks a recognized period")
        months[q["question_id"]] = periods
        projection = evidence_table_projection(q["evidence"], {})
        content[q["question_id"]] = hashlib.sha256(json.dumps(projection, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    groups = []
    for qid, periods in sorted(months.items()):
        touching = [g for g in groups if g[1] & periods]
        combined_ids, combined_periods = {qid}, set(periods)
        for group in touching:
            combined_ids.update(group[0])
            combined_periods.update(group[1])
            groups.remove(group)
        groups.append((combined_ids, combined_periods))
    component = {qid: f"period_component_{i+1:02}" for i, (ids, _) in enumerate(sorted(groups, key=lambda g: min(g[0]))) for qid in ids}
    return {qid: {"evidence_cluster": content[qid], "period_component": component[qid]} for qid in months}


def historical_rows():
    annotations = indexed(jsonl(ROOT / PUBLIC_INPUTS[3]), "annotation_id")
    questions = indexed(jsonl(ROOT / PUBLIC_INPUTS[2]), "question_id")
    legacy = read_csv(LEGACY)
    if set(indexed(legacy, "annotation_id")) != set(annotations):
        raise ValueError("Score and annotation coverage differ")
    # Components use only evaluated questions, not unannotated bridging questions.
    cluster_map = assign_clusters([questions[qid] for qid in sorted({r['question_id'] for r in legacy})])
    rows = []
    for row in legacy:
        ann, q = annotations[row["annotation_id"]], questions[row["question_id"]]
        for key in ["question_id", "prompt_id", "fact_type", "label", "span_text"]:
            if ann[key] != row[key]:
                raise ValueError(f"Score/annotation mismatch: {key}")
        if row["split"] != q["split"] or row["question_type"] != q["question_type"]:
            raise ValueError("Question metadata mismatch")
        expected = {"correct_key_fact": 0, "hallucinated_key_fact": 1, "unsupported_claim": 1}[ann["label"]]
        if int(row["binary_label"]) != expected:
            raise ValueError("Binary label mismatch")
        rows.append({"arm": "stored_six_decimal_scores", "annotation_id": row["annotation_id"],
                     "question_id": row["question_id"], "split": row["split"], "question_type": row["question_type"],
                     "fact_type": row["fact_type"], "binary_label": expected, **cluster_map[row["question_id"]],
                     **{field: dm.finite_score(row[field]) for field in signals()}})
    dm.validate_rows(rows)
    return rows, annotations, questions


def aggregate(tokens):
    if not tokens:
        raise ValueError("No tokens in span")
    def values(field):
        return [dm.finite_score(token[field]) for token in tokens]
    def mean(field):
        return math.fsum(values(field)) / len(tokens)
    return {"mean_token_nll": -mean("token_logprob"), "mean_token_entropy": mean("token_entropy"),
            "max_token_entropy": max(values("token_entropy")), "one_minus_mean_top2_margin": 1-mean("top2_margin"),
            "one_minus_min_top2_margin": 1-min(values("top2_margin")),
            "mean_spilled_energy_abs_delta": mean("spilled_energy_abs_delta"),
            "max_spilled_energy_abs_delta": max(values("spilled_energy_abs_delta")),
            "mean_spilled_energy_delta": mean("spilled_energy_delta"),
            "negative_mean_spilled_energy_delta": -mean("spilled_energy_delta"),
            "mean_spilled_probability_mass_after_top1": mean("spilled_probability_mass_after_top1"),
            "mean_spilled_probability_mass_after_top2": mean("spilled_probability_mass_after_top2"),
            "max_selected_step_energy_gap": max(values("selected_step_energy_gap"))}


def replay_precision(stored, annotations):
    traces = indexed(jsonl(ROOT / LOCAL_PATHS[0]), "question_id")
    generations = indexed(jsonl(ROOT / LOCAL_PATHS[1]), "question_id")
    alignment = indexed(jsonl(ROOT / LOCAL_PATHS[2]), "annotation_id")
    if set(traces) != set(generations) or len(traces) != 100 or set(alignment) != set(annotations):
        raise ValueError("Trace/generation/alignment coverage mismatch")
    token_spans = {}
    token_gap_errors, mass_errors, correction_count = [], [], 0
    for qid, trace in traces.items():
        tokens = trace["token_traces"]
        if [t["position"] for t in tokens] != list(range(len(tokens))):
            raise ValueError("Noncontiguous token positions")
        if [t["token_id"] for t in tokens] != generations[qid]["generated_token_ids"]:
            raise ValueError("Token IDs differ from saved generation")
        spans, failures = build_token_char_spans(qid, generations[qid]["generated_text"], tokens)
        if failures:
            raise ValueError(f"Token reconstruction failed: {qid}")
        correction_count += sum(t['aligned_text'] != t['token_text'] for t in spans if not t['is_special_token'])
        token_spans[qid] = spans
        for t in tokens:
            if t["score_source"] != "raw_forward_logits_after_generation":
                raise ValueError("Unexpected probability source")
            token_gap_errors.append(abs(dm.finite_score(t["selected_step_energy_gap"])+dm.finite_score(t["token_logprob"])))
            mass_errors.append(abs(dm.finite_score(t["spilled_probability_mass_after_top1"])-(1-dm.finite_score(t["top1_probability"]))))
    rows, maximum_rounding_difference = [], 0.0
    span_mean_gaps, span_mean_nlls, span_max_errors = [], [], []
    for row in stored:
        ann, aligned = annotations[row["annotation_id"]], alignment[row["annotation_id"]]
        start, end = ann["span_start_char"], ann["span_end_char"]
        text = generations[row["question_id"]]["generated_text"]
        if not 0 <= start < end <= len(text) or text[start:end] != ann["span_text"]:
            raise ValueError("Annotation offset mismatch")
        selected = overlapping_tokens(token_spans[row["question_id"]], start, end)
        if not selected or [t["position"] for t in selected] != aligned["token_positions"]:
            raise ValueError("Saved alignment differs from reconstructed character overlap")
        rounded = summarize_scores(selected)
        rounded.update(one_minus_mean_top2_margin=1-rounded["mean_top2_margin"],
                       one_minus_min_top2_margin=1-rounded["min_top2_margin"],
                       negative_mean_spilled_energy_delta=-rounded["mean_spilled_energy_delta"])
        for field in signals():
            if not math.isclose(row[field], rounded[field], rel_tol=0, abs_tol=1e-12):
                raise ValueError(f"Historical six-decimal replay failed: {row['annotation_id']} {field}")
        scores = aggregate(selected)
        maximum_rounding_difference = max(maximum_rounding_difference, *(abs(row[f]-scores[f]) for f in signals()))
        mean_gap = math.fsum(t["selected_step_energy_gap"] for t in selected)/len(selected)
        span_mean_gaps.append(mean_gap)
        span_mean_nlls.append(scores["mean_token_nll"])
        span_max_errors.append(abs(scores["max_selected_step_energy_gap"]-max(-t["token_logprob"] for t in selected)))
        rows.append({**row, "arm": "saved_trace_precision", **scores})
    xbar, ybar = math.fsum(span_mean_gaps)/len(rows), math.fsum(span_mean_nlls)/len(rows)
    corr = math.fsum((x-xbar)*(y-ybar) for x, y in zip(span_mean_gaps, span_mean_nlls))/math.sqrt(
        math.fsum((x-xbar)**2 for x in span_mean_gaps)*math.fsum((y-ybar)**2 for y in span_mean_nlls))
    return rows, {"reconstructed_questions": len(traces), "replayed_spans": len(rows),
                  "legacy_six_decimal_replay": "matched_all_12_signals",
                  "max_aggregate_rounding_difference": maximum_rounding_difference,
                  "retained_legacy_unicode_normalization_token_count": correction_count,
                  "same_step_gap_equals_nll": {"identity": "logsumexp(logits) - selected_logit = -log_softmax(logits)[selected]",
                     "token_max_abs_difference": max(token_gap_errors), "span_mean_pearson": corr,
                     "span_mean_max_abs_difference": max(abs(x-y) for x, y in zip(span_mean_gaps, span_mean_nlls)),
                     "span_max_max_abs_difference": max(span_max_errors), "independent_detector_family": False},
                  "non_top1_mass_equals_one_minus_top1_probability_max_abs_difference": max(mass_errors)}


def analyze_arm(rows, config):
    dm.validate_rows(rows)
    dev = [r for r in rows if r["split"] == "dev"]
    prior = dm.fit_fact_type_prior(dev)
    enriched = [{**r, "all_positive": 1., "all_negative": 0.,
                 "dev_fact_type_prior": prior["rates"].get(r["fact_type"], prior["fallback"])} for r in rows]
    dev = [r for r in enriched if r["split"] == "dev"]
    fields = signals()+config["references"]
    thresholds = {field: .5 if field in {"all_positive", "all_negative"} else dm.dev_threshold(dev, field) for field in fields}
    measured = []
    for field in fields:
        for split in ["dev", "test"]:
            selected = [r for r in enriched if r["split"] == split]
            measured.append({"arm": rows[0]["arm"], "signal": field, "split": split, "threshold": thresholds[field],
                             **dm.evaluate([r["binary_label"] for r in selected], [r[field] for r in selected], thresholds[field])})
    return measured, enriched, thresholds, prior


def bootstrap_all(rows, thresholds, config):
    policy = config["bootstrap"]
    pairs = [(signal, ref) for signal in [config["primary_signal"], config["secondary_signal"]] for ref in policy["comparison_references"]]
    test = [r for r in rows if r["split"] == "test"]
    return [dm.paired_cluster_bootstrap(test, thresholds, pairs, cluster, policy["replicates"], policy["seed"]) for cluster in policy["cluster_fields"]]


def main():
    config = load(CONFIG)
    before = {name: digest(ROOT / name) for name in PUBLIC_INPUTS}
    stored, annotations, questions = historical_rows()
    precision, replay = replay_precision(stored, annotations)
    metric_rows, arm_rows, priors, thresholds = [], [], {}, {}
    for rows in [stored, precision]:
        measured, enriched, chosen, prior = analyze_arm(rows, config)
        metric_rows.extend(measured)
        arm_rows.extend(enriched)
        priors[rows[0]["arm"]] = prior
        thresholds[rows[0]["arm"]] = chosen
    intervals = bootstrap_all([r for r in arm_rows if r["arm"] == "saved_trace_precision"], thresholds["saved_trace_precision"], config)
    legacy_metrics = read_csv(ROOT / PUBLIC_INPUTS[-2])+read_csv(ROOT / PUBLIC_INPUTS[-1])
    changes = []
    for old in legacy_metrics:
        new = next(r for r in metric_rows if r['arm'] == 'stored_six_decimal_scores' and r['signal'] == old['baseline'] and r['split'] == old['evaluated_split'])
        changes.append({"signal": new['signal'], "split": new['split'], "published_legacy_auprc": float(old['auprc']),
                        "tied_score_average_precision": new['average_precision'], "published_legacy_f1": float(old['f1']),
                        "new_f1": new['f1'], "legacy_confusion_reproduced": all(int(old[k]) == new[k] for k in ['tp','fp','tn','fn'])})
    evaluated_ids = {r['question_id'] for r in stored}
    scope = {split: {"questions": len({r['question_id'] for r in stored if r['split'] == split}),
                    "spans": sum(r['split'] == split for r in stored),
                    "positive_spans": sum(r['binary_label'] for r in stored if r['split'] == split),
                    "missing_question_ids": sorted(qid for qid, q in questions.items() if q['split'] == split and qid not in evaluated_ids)} for split in ['dev','test']}
    evidence_sets = {s: {r['evidence_cluster'] for r in stored if r['split'] == s} for s in ['dev','test']}
    report = {"version": config['version'], "metric_version": dm.METRIC_VERSION, "status": "retrospective_B1_not_confirmatory",
              "implementation_text_sha256": {p: digest(ROOT/p) for p in ['src/detector_metrics.py', 'src/build_retrospective_statistics.py', 'src/build_span_token_alignment.py']},
              "source_text_sha256": before, "local_source_text_sha256": {p: digest(ROOT/p) for p in LOCAL_PATHS},
              "scope": scope, "label_basis": "205 AI-assisted provisional spans; only 15 additionally assistant-reviewed; no independent human agreement",
              "fact_type_counts": {s: dict(sorted(Counter(r['fact_type'] for r in stored if r['split'] == s).items())) for s in ['dev','test']},
              "label_counts": dict(sorted(Counter(a['label'] for a in annotations.values()).items())),
              "prior_annotation_audit": {
                  "outcome_hinting_type_names": ['malformed_number', 'unsupported_business_claim'],
                  "test_decision_equals_non_month": all(
                      (r['dev_fact_type_prior'] >= thresholds[r['arm']]['dev_fact_type_prior']) == (r['fact_type'] != 'month')
                      for r in arm_rows if r['split']=='test'),
                  "fair_information_matched_detector_comparison": False},
              "dev_test_shared_evidence_table_contents": len(evidence_sets['dev'] & evidence_sets['test']),
              "recipe": config, "replay": replay, "dev_fact_type_priors": priors,
              "metrics": metric_rows, "legacy_comparison": changes, "paired_intervals": intervals,
              "precision_comparison": [{"signal": field,
                  "changed_test_predictions": sum((s[field] >= thresholds['stored_six_decimal_scores'][field]) != (p[field] >= thresholds['saved_trace_precision'][field]) for s,p in zip(stored,precision) if s['split']=='test')}
                  for field in signals()],
              "caveats": ["Both retrospective analysis arms preserve old labels, spans, question selection and business definitions.",
                  "No new winner is selected. max_selected_step_energy_gap is retained only as an NLL alias diagnostic, not independent energy-family evidence.",
                  "AP is non-interpolated average precision, not trapezoidal PR area. All-constant-score AP equals the observed positive prevalence.",
                  "Intervals are exploratory and conditional on fixed dev policies; they do not correct test-selection bias, annotation error, or unknown dependencies.",
                  "Exact-evidence grouping and overlapping-month components are sensitivity analyses. Components are constructed from all 35 evaluated dev/test questions (including dev bridges), then resampled on test only. Only two period components remain: their intervals are not reliable inferential confidence bounds.",
                  "Fact-type prior uses pre-annotated types, including outcome-hinting names such as malformed_number. It is an annotation-composition control, not an information-matched detector or automatic extraction system.",
                  "No-positive AP, one-class AUROC and one-class balanced accuracy are undefined (null). Zero-denominator MCC and zero-predicted-positive precision are set to zero.",
                  "B2 q_0048 review and threshold sensitivity remain pending. No new model generations or confirmation data are read.",
                  "Legacy Unicode fallback normalization is preserved and checked against complete saved answers, not a general tokenizer alignment solution."],
              "historical_inputs_unchanged": before == {p: digest(ROOT/p) for p in PUBLIC_INPUTS}}
    if not report['historical_inputs_unchanged'] or not all(r['legacy_confusion_reproduced'] for r in changes):
        raise ValueError("Historical replay failed; do not publish appendix")
    write_csv(SCORES, arm_rows)
    write_csv(METRICS, metric_rows)
    report['output_text_sha256'] = {str(p.relative_to(ROOT)).replace('\\','/'): digest(p) for p in [SCORES,METRICS]}
    write_json(REPORT, report)
    print(json.dumps({"status": report['status'], "scope": scope, "clusters": [(x['cluster_field'],x['cluster_count']) for x in intervals], "metric_rows":len(metric_rows)}))


if __name__ == "__main__":
    main()
