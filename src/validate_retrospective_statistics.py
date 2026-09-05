"""Recompute public appendix calculations; private trace replay is an explicit tier."""
from __future__ import annotations

import argparse
import json
import math

import detector_metrics as dm
import build_retrospective_statistics as build


def require_equal(actual, expected, name):
    if actual != expected:
        raise ValueError(f"Mismatch: {name}")


def check_public():
    report, config = build.load(build.REPORT), build.load(build.CONFIG)
    require_equal(report['recipe'], config, 'recipe')
    require_equal(report['metric_version'], dm.METRIC_VERSION, 'metric version')
    for group in ['source_text_sha256', 'implementation_text_sha256', 'output_text_sha256']:
        for path, value in report[group].items():
            require_equal(build.digest(build.ROOT/path), value, path)
    stored, annotations, questions = build.historical_rows()
    raw = build.read_csv(build.SCORES)
    require_equal(len(raw), 2*len(stored), 'two arms coverage')
    require_equal(set(r['arm'] for r in raw), set(config['arms']), 'arm names')
    numeric = build.signals()+config['references']
    parsed = [{**r, 'binary_label': int(r['binary_label']), **{f: dm.finite_score(r[f]) for f in numeric}} for r in raw]
    measured, priors, full, chosen = [], {}, None, None
    for arm in config['arms']:
        rows = [r for r in parsed if r['arm'] == arm]
        dm.validate_rows(rows)
        require_equal([r['annotation_id'] for r in rows], [r['annotation_id'] for r in stored], 'ordered coverage')
        for row, old in zip(rows, stored):
            for key in ['annotation_id','question_id','split','question_type','fact_type','binary_label','evidence_cluster','period_component']:
                require_equal(row[key], old[key], key)
            if arm == 'stored_six_decimal_scores':
                require_equal({f:row[f] for f in build.signals()}, {f:old[f] for f in build.signals()}, 'historical scores')
        metrics, enriched, thresholds, prior = build.analyze_arm(rows, config)
        require_equal(enriched, rows, 'dev-fitted reference scores')
        measured.extend(metrics)
        priors[arm] = prior
        if arm == 'saved_trace_precision':
            full, chosen = enriched, thresholds
    require_equal(measured, report['metrics'], 'all 60 metric rows')
    require_equal(priors, report['dev_fact_type_priors'], 'dev prior')
    expected_csv = [{k:str(v) if v is not None else '' for k,v in r.items()} for r in measured]
    require_equal(build.read_csv(build.METRICS), expected_csv, 'metric CSV')
    require_equal(build.bootstrap_all(full, chosen, config), report['paired_intervals'], 'all paired bootstrap differences')
    expected_scope = {}
    ids = {r['question_id'] for r in stored}
    for split in ['dev','test']:
        rows = [r for r in stored if r['split'] == split]
        expected_scope[split] = {'questions': len({r['question_id'] for r in rows}), 'spans':len(rows),
            'positive_spans':sum(r['binary_label'] for r in rows),
            'missing_question_ids':sorted(qid for qid,q in questions.items() if q['split']==split and qid not in ids)}
    require_equal(expected_scope, report['scope'], 'scope and missing questions')
    require_equal(expected_scope['dev']['missing_question_ids'], ['q_0048'], 'B2 remains pending')
    require_equal(expected_scope['test']['spans'], 103, 'historical test denominator')
    require_equal(len(stored), 205, 'historical annotation denominator')
    require_equal(report['historical_inputs_unchanged'], True, 'preserved inputs')
    equivalent = all((r['dev_fact_type_prior'] >= chosen['dev_fact_type_prior']) == (r['fact_type'] != 'month') for r in full if r['split']=='test')
    require_equal(report['prior_annotation_audit'], {
        'outcome_hinting_type_names':['malformed_number','unsupported_business_claim'],
        'test_decision_equals_non_month':equivalent, 'fair_information_matched_detector_comparison':False}, 'prior interpretation')
    return report, stored, annotations, full


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-local', action='store_true')
    parser.add_argument('--output', default='reports/bizhallu_statistics_v2_validation.json')
    args = parser.parse_args()
    failures = []
    local_status = 'not_run_public_tier_cannot_verify_private_traces'
    try:
        report, stored, annotations, full = check_public()
        if args.require_local:
            for path, value in report['local_source_text_sha256'].items():
                require_equal(build.digest(build.ROOT/path), value, 'local source hash')
            precision, replay = build.replay_precision(stored, annotations)
            require_equal(replay, report['replay'], '100-answer reconstruction and 205-span replay')
            for row, expected in zip(full, precision):
                for field in build.signals():
                    require_equal(row[field], expected[field], 'unrounded saved-trace aggregation')
            local_status = '100_answers_205_spans_12_signals_replayed_no_model_inference'
    except (ValueError, KeyError, TypeError, OSError, AssertionError) as exc:
        failures.append(str(exc))
    result = {'status':'failed' if failures else 'retrospective_statistics_B1_validated',
              'validated_report_text_sha256':build.digest(build.REPORT) if not failures else None,
              'public_checks':'recompute_60_metric_rows_dev_fits_15000_paired_cluster_draws_source_and_output_hashes',
              'local_checks':local_status, 'research_validity':'not_confirmatory_not_independently_human_annotated',
              'num_failures':len(failures), 'failures':failures}
    build.write_json(build.ROOT/args.output, result)
    print(json.dumps(result, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
