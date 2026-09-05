"""Versioned B2 omission sensitivity; never replaces B1, labels or model outputs."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
from collections import Counter
from datetime import datetime, timezone

import build_retrospective_statistics as b1
import detector_metrics as dm
from audit_calibration_sources import check_case, number
from build_span_token_alignment import build_token_char_spans, overlapping_tokens, summarize_scores
from validate_span_annotations import REQUIRED_FIELDS, ALLOWED_FACT_TYPES, ALLOWED_CONFIDENCE

ROOT = b1.ROOT
CONFIG = ROOT / 'configs/q0048_dev_sensitivity_v1.json'
ANNOTATIONS = ROOT / 'data/annotations/span_annotations_q0048_b2_assistant_v1.jsonl'
PACKET = ROOT / 'reports/bizhallu_q0048_supplement_v1.json'
SCORES = ROOT / 'results/q0048_b2_supplement_scores.csv'
METRICS = ROOT / 'results/q0048_b2_sensitivity_metrics.csv'
REPORT = ROOT / 'reports/bizhallu_q0048_dev_sensitivity_report.json'
LOCAL = [ROOT / p for p in b1.LOCAL_PATHS[:2]]
PROTECTED = [ROOT / 'data/annotations/span_annotations_full100_draft.jsonl', b1.LEGACY, b1.REPORT, b1.SCORES, b1.METRICS,
             ROOT / 'results/full100_draft_simple_split_report.json', ROOT / 'results/full100_draft_energy_split_report.json',
             ROOT / 'reports/full100_label_lock_decisions.jsonl',
             ROOT / 'outputs/relation_calibration_v2/packet.json', ROOT / 'outputs/relation_calibration_v2/review_template.json']
PUBLIC_PROTECTED = PROTECTED[:8]


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def rel(path):
    return path.relative_to(ROOT).as_posix()


def hash_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def validate_annotations(annotations, case, config):
    require(len(annotations) == config['expected_span_count'] == 9, 'Expected nine explicitly reviewed atoms')
    require(case['question_id'] == config['question_id'] == 'q_0048' and case['split'] == config['required_split'] == 'dev', 'Supplement must be the missing historical dev question')
    require(len({a['annotation_id'] for a in annotations}) == len(annotations), 'Duplicate supplement annotation ID')
    source = check_case(case)
    require(source['calculations'][-1]['nearest_whole_GBP_match'], 'Whole-pound rounding is not supported')
    types = Counter()
    end = 0
    for i, a in enumerate(annotations, 1):
        require(REQUIRED_FIELDS <= a.keys(), 'Missing v1 annotation fields')
        require(a['annotation_id'] == f'ann_b2_q_0048_{i:03}', 'Supplement IDs or ordering changed')
        require(a['question_id'] == 'q_0048' and a['prompt_id'] == 'p_0048', 'Annotation belongs to another question')
        require(a['source_generation_file'] == 'outputs/qwen_full100_generations.jsonl', 'Wrong source generation')
        require(a['annotation_version'] == config['annotation_version'], 'Wrong supplement version')
        start, stop = a['span_start_char'], a['span_end_char']
        require(type(start) is int and type(stop) is int and end <= start < stop <= len(case['generated_text']), 'Invalid, overlapping or unsorted offsets')
        require(case['generated_text'][start:stop] == a['span_text'], 'Offset/text mismatch')
        end = stop
        require(a['label'] == 'correct_key_fact', 'Revised judgments require a new supplement version')
        require(a['fact_type'] in ALLOWED_FACT_TYPES and a['confidence'] in ALLOWED_CONFIDENCE, 'Invalid schema enum')
        require('assistant-provisional' in a['notes'] and 'no independent human review' in a['notes'] and a['reason'], 'Missing assistant provenance')
        types[a['fact_type']] += 1
        field, reference = a['gold_reference']['field'], a['gold_reference']['value']
        if a['fact_type'] == 'comparison_direction':
            require(reference == 'Netherlands > EIRE' and field == 'higher_country', 'Comparison reference mismatch')
        else:
            require(reference == case['gold_answer'][field], 'Annotation gold reference mismatch')
        if a['fact_type'] == 'currency_amount':
            observed = number(a['span_text'].removesuffix(' GBP'))
            expected = number(reference)
            require(abs(observed-expected) <= max(number(1), abs(expected)*number('.005')), 'Amount outside v1 tolerance')
    require(types == {'month':1,'country':3,'comparison_direction':2,'currency_amount':3}, 'Supplement fact-type coverage changed')
    return source


def prepare():
    config, annotations = b1.load(CONFIG), b1.jsonl(ANNOTATIONS)
    review = b1.indexed(b1.jsonl(ROOT / 'outputs/full100_review.jsonl'), 'question_id')['q_0048']
    case = {key:review[key] for key in ['question_id','prompt_id','split','question','gold_answer','prompt_evidence_rows']}
    case['generated_text'] = review['generation']['generated_text']
    calculations = validate_annotations(annotations, case, config)
    packet = {'version':config['version'], 'status':'assistant_provisional_atoms_prepared_before_B2_scoring',
              'prepared_at_utc':datetime.now(timezone.utc).isoformat(), 'config':config,
              'config_text_sha256':b1.digest(CONFIG), 'annotation_text_sha256':b1.digest(ANNOTATIONS),
              'case':case, 'source_arithmetic':calculations, 'generated_text_sha256':hash_text(case['generated_text']),
              'independent_human_review':False, 'new_owner_submissions':0,
              'sequence_disclosure':'This batch saved and schema-checked the supplement before reading its token scores; historical study familiarity remains. This is not a prospective preregistration.'}
    if PACKET.exists():
        existing = b1.load(PACKET)
        require({k:v for k,v in existing.items() if k != 'prepared_at_utc'} == {k:v for k,v in packet.items() if k != 'prepared_at_utc'}, 'Prepared supplement differs; use a new version instead of refreezing')
    else:
        b1.write_json(PACKET, packet)
    print(json.dumps({'status':packet['status'], 'span_count':len(annotations), 'annotation_commitment':b1.digest(ANNOTATIONS), 'token_scores_read':False}))


def check_packet():
    packet, config, annotations = b1.load(PACKET), b1.load(CONFIG), b1.jsonl(ANNOTATIONS)
    require(packet['config'] == config and packet['config_text_sha256'] == b1.digest(CONFIG), 'B2 recipe changed after preparation')
    require(packet['annotation_text_sha256'] == b1.digest(ANNOTATIONS), 'Annotations changed after preparation')
    require(packet['generated_text_sha256'] == hash_text(packet['case']['generated_text']), 'Answer commitment mismatch')
    require(packet['source_arithmetic'] == validate_annotations(annotations, packet['case'], config), 'Arithmetic review mismatch')
    require(packet['independent_human_review'] is False and packet['new_owner_submissions'] == 0, 'Review provenance changed')
    questions = b1.indexed(b1.jsonl(ROOT / b1.PUBLIC_INPUTS[2]), 'question_id')
    q = questions['q_0048']
    require(q['split'] == 'dev' and q['question'] == packet['case']['question'] and q['gold_answer'] == packet['case']['gold_answer'], 'Public question/gold projection mismatch')
    original_rows = {r['country']:r for r in q['evidence']['rows']}
    require(original_rows == {r['country']:r for r in packet['case']['prompt_evidence_rows']}, 'Evidence projection mismatch')
    require(not any(a['question_id'] == 'q_0048' for a in b1.jsonl(PROTECTED[0])), 'Supplement is already in original annotations')
    return packet, annotations


def score_local(packet, annotations):
    generations = b1.indexed(b1.jsonl(LOCAL[1]), 'question_id')
    traces = b1.indexed(b1.jsonl(LOCAL[0]), 'question_id')
    generation, trace = generations['q_0048'], traces['q_0048']
    require(generation['generated_text'] == packet['case']['generated_text'], 'Local answer differs from prepared answer')
    tokens = trace['token_traces']
    require([t['position'] for t in tokens] == list(range(len(tokens))), 'Noncontiguous token positions')
    require([t['token_id'] for t in tokens] == generation['generated_token_ids'], 'Token IDs differ from generation')
    require(all(t['score_source'] == 'raw_forward_logits_after_generation' for t in tokens), 'Unexpected score source')
    token_spans, failures = build_token_char_spans('q_0048', generation['generated_text'], tokens)
    require(not failures, 'Generated text cannot be reconstructed from tokens')
    require(all(t['aligned_text'] == t['token_text'] for t in token_spans if not t['is_special_token']), 'This ASCII answer should not require Unicode correction')
    rows, coverage = [], []
    for a in annotations:
        start, end = a['span_start_char'], a['span_end_char']
        selected = overlapping_tokens(token_spans, start, end)
        require(selected and all(any(t['char_start'] <= pos < t['char_end'] for t in selected) for pos in range(start,end)), 'Incomplete token coverage')
        saved = summarize_scores(selected)
        saved.update(one_minus_mean_top2_margin=1-saved['mean_top2_margin'], one_minus_min_top2_margin=1-saved['min_top2_margin'],
                     negative_mean_spilled_energy_delta=-saved['mean_spilled_energy_delta'])
        scores = {'stored_six_decimal_scores':{field:round(saved[field],6) for field in b1.signals()},
                  'saved_trace_precision':b1.aggregate(selected)}
        for arm, values in scores.items():
            rows.append({'arm':arm,'annotation_id':a['annotation_id'],'question_id':'q_0048','split':'dev',
                         'question_type':'country_comparison_month','fact_type':a['fact_type'],'binary_label':0,**values})
        coverage.append({'annotation_id':a['annotation_id'],'span_text':a['span_text'],'start':start,'end':end,
                         'token_positions':[t['position'] for t in selected],
                         'left_boundary_slop':start-selected[0]['char_start'], 'right_boundary_slop':selected[-1]['char_end']-end,
                         'all_span_characters_covered':True})
    return rows, coverage


def base_rows():
    report = b1.load(b1.REPORT)
    require(report['output_text_sha256'][rel(b1.SCORES)] == b1.digest(b1.SCORES), 'B1 score package changed')
    rows = b1.read_csv(b1.SCORES)
    return [{**r,'binary_label':int(r['binary_label']),**{f:dm.finite_score(r[f]) for f in b1.signals()+b1.load(b1.CONFIG)['references']}} for r in rows]


def check_score_rows(rows, annotations, config):
    by_id = b1.indexed(annotations, 'annotation_id')
    require(len(rows) == 2*len(annotations) and {r['arm'] for r in rows} == set(config['arms']), 'Score arm coverage differs')
    for arm in config['arms']:
        selected = [r for r in rows if r['arm'] == arm]
        require(set(b1.indexed(selected,'annotation_id')) == set(by_id), 'Score/annotation membership differs')
        dm.validate_rows(selected,'dev')
        for row in selected:
            a = by_id[row['annotation_id']]
            require(row['fact_type'] == a['fact_type'] and row['question_id'] == a['question_id'] and row['binary_label'] == 0
                    and row['question_type'] == 'country_comparison_month', 'Score metadata differs from annotation')
            for field in b1.signals():
                dm.finite_score(row[field])


def fit_dev(dev, recipe):
    dm.validate_rows(dev, 'dev')
    prior = dm.fit_fact_type_prior(dev)
    enriched = [{**r,'all_positive':1.,'all_negative':0.,'dev_fact_type_prior':prior['rates'].get(r['fact_type'],prior['fallback'])} for r in dev]
    thresholds = {f:.5 if f in ['all_positive','all_negative'] else dm.dev_threshold(enriched,f) for f in b1.signals()+recipe['references']}
    return thresholds, prior


def enrich(rows, prior):
    return [{**r,'all_positive':1.,'all_negative':0.,'dev_fact_type_prior':prior['rates'].get(r['fact_type'],prior['fallback'])} for r in rows]


def analyze(base, supplement, config):
    recipe = b1.load(b1.CONFIG)
    require(config['arms'] == recipe['arms'] and config['reference_protocol'] == rel(b1.CONFIG), 'Unexpected B2 analysis arms')
    fields = b1.signals()+recipe['references']
    metrics, fits, changes, comparisons = [], {}, [], []
    for arm in config['arms']:
        original = [r for r in base if r['arm'] == arm]
        added = [r for r in supplement if r['arm'] == arm]
        dm.validate_rows(original)
        dm.validate_rows(added, 'dev')
        require(len(original)==205 and len(added)==9 and {r['question_id'] for r in added}=={'q_0048'}, 'Invalid B2 cohort')
        require(all(r['binary_label']==0 for r in added), 'Supplement judgment changed')
        require(not ({r['annotation_id'] for r in original}&{r['annotation_id'] for r in added}), 'Supplement duplicates historical atoms')
        require('q_0048' not in {r['question_id'] for r in original}, 'Supplement question already evaluated')
        dev, test = [r for r in original if r['split']=='dev'], [r for r in original if r['split']=='test']
        require(len(dev)==102 and len(test)==103 and len({r['question_id'] for r in dev})==17 and len({r['question_id'] for r in test})==18, 'Historical split counts changed')
        test_by_condition = {}
        for condition in config['conditions']:
            require(condition in ['original_dev17','supplemented_dev18'], 'Unknown condition')
            training = dev if condition=='original_dev17' else dev+added
            thresholds, prior = fit_dev(training, recipe)
            fits[arm+':'+condition] = {'thresholds':thresholds,'prior':prior,'dev_span_count':len(training),
                                      'dev_question_count':len({r['question_id'] for r in training}),
                                      'dev_positive_count':sum(r['binary_label'] for r in training)}
            evaluated = enrich(test,prior)
            test_by_condition[condition] = evaluated
            for field in fields:
                for split, selected in [('dev',enrich(training,prior)),('test',evaluated)]:
                    metrics.append({'arm':arm,'condition':condition,'signal':field,'split':split,'threshold':thresholds[field],
                                    **dm.evaluate([r['binary_label'] for r in selected],[r[field] for r in selected],thresholds[field])})
        old_test, new_test = (test_by_condition[k] for k in config['conditions'])
        for field in fields:
            old_t, new_t = (fits[arm+':'+c]['thresholds'][field] for c in config['conditions'])
            altered = []
            for old,new in zip(old_test,new_test):
                require(old['annotation_id']==new['annotation_id'] and old['binary_label']==new['binary_label'], 'Test labels/membership changed')
                a,b = old[field]>=old_t, new[field]>=new_t
                if a != b:
                    item={'arm':arm,'signal':field,'annotation_id':old['annotation_id'],'question_id':old['question_id'],
                          'binary_label':old['binary_label'],'original_flag':a,'supplemented_flag':b}
                    changes.append(item)
                    altered.append(item)
            measured = [next(r for r in metrics if r['arm']==arm and r['condition']==c and r['signal']==field and r['split']=='test') for c in config['conditions']]
            if field in b1.signals():
                require(measured[0]['average_precision']==measured[1]['average_precision'], 'AP changed despite fixed test scores/labels')
            flags = {}
            for c in config['conditions']:
                fit = fits[arm+':'+c]
                flags[c] = sum(r[field] >= fit['thresholds'][field] for r in enrich(added,fit['prior']))
            comparisons.append({'arm':arm,'signal':field,'original_threshold':old_t,'supplemented_threshold':new_t,
                                'threshold_changed':old_t!=new_t,'test_prediction_changes':len(altered),
                                'test_metrics_before':measured[0], 'test_metrics_after':measured[1],
                                'supplement_flag_counts_not_heldout_metrics':flags})
    expected = [{k:v for k,v in r.items() if k!='condition'} for r in metrics if r['condition']=='original_dev17']
    require(expected==b1.load(b1.REPORT)['metrics'], 'B2 original condition does not reproduce B1')
    return {'metrics':metrics,'fits':fits,'comparisons':comparisons,'changed_test_predictions':changes}


def build():
    packet, annotations = check_packet()
    before = {rel(p):b1.digest(p) for p in PROTECTED}
    rows, coverage = score_local(packet,annotations)
    check_score_rows(rows,annotations,packet['config'])
    calculations = analyze(base_rows(),rows,packet['config'])
    require(before == {rel(p):b1.digest(p) for p in PROTECTED}, 'Protected historical inputs changed')
    b1.write_csv(SCORES,rows)
    b1.write_csv(METRICS,calculations['metrics'])
    report = {'version':packet['version'],'status':'B2_assistant_provisional_dev_sensitivity_not_confirmatory',
              'metric_version':dm.METRIC_VERSION,'recipe':packet['config'], 'prepared_packet_text_sha256':b1.digest(PACKET),
              'annotation_basis':packet['config']['label_basis'], 'original_span_count':205,'supplement_span_count':9,
              'augmented_span_count':214,'unchanged_test_span_count':103,'unchanged_test_question_count':18,
              'independent_human_review':False,'model_inference_run':False,'new_headline_claim':False,
              'alignment':coverage, **calculations,
              'source_text_sha256':{rel(p):b1.digest(p) for p in [CONFIG,ANNOTATIONS,PACKET,b1.CONFIG,b1.REPORT,b1.SCORES]},
              'implementation_text_sha256':{p:b1.digest(ROOT/p) for p in ['src/q0048_dev_sensitivity.py','src/detector_metrics.py','src/build_retrospective_statistics.py','src/build_span_token_alignment.py']},
              'local_source_text_sha256':{rel(p):b1.digest(p) for p in LOCAL},'protected_input_text_sha256':before,
              'output_text_sha256':{rel(p):b1.digest(p) for p in [SCORES,METRICS]},
              'limits':['New labels are assistant-provisional; no independent review or agreement.',
                        'Nine correlated spans in one previously omitted dev answer; not nine independent trials.',
                        'Same old test labels/scores; no confirmation access or generalization evidence.',
                        'Fixed internal-score AP is unchanged by threshold refitting; the dev prior can change test ranking.',
                        'No new uncertainty interval and no method ranking chosen from these outcomes.']}
    b1.write_json(REPORT,report)
    print(json.dumps({'status':report['status'],'supplement_spans':9,'metric_rows':len(calculations['metrics']),
                      'changed_threshold_rows':sum(r['threshold_changed'] for r in calculations['comparisons']),
                      'changed_test_prediction_rows':len(calculations['changed_test_predictions'])},indent=2))


def validate(require_local=False):
    packet, annotations = check_packet()
    report = b1.load(REPORT)
    require(report['recipe'] == packet['config'] and report['prepared_packet_text_sha256'] == b1.digest(PACKET), 'Report recipe/preparation differs')
    for key,value in {'version':packet['version'],'status':'B2_assistant_provisional_dev_sensitivity_not_confirmatory',
                      'original_span_count':205,'supplement_span_count':9,'augmented_span_count':214,
                      'unchanged_test_span_count':103,'unchanged_test_question_count':18,'independent_human_review':False,
                      'model_inference_run':False,'new_headline_claim':False,'metric_version':dm.METRIC_VERSION,
                      'annotation_basis':packet['config']['label_basis']}.items():
        require(report.get(key) == value, 'B2 provenance/scope field mismatch: '+key)
    for group in ['source_text_sha256','implementation_text_sha256','output_text_sha256']:
        for path,value in report[group].items():
            require(b1.digest(ROOT/path)==value, 'Hash mismatch: '+path)
    for path in PUBLIC_PROTECTED:
        require(b1.digest(path)==report['protected_input_text_sha256'][rel(path)], 'Protected public input changed')
    rows = [{**r,'binary_label':int(r['binary_label']),**{f:dm.finite_score(r[f]) for f in b1.signals()}} for r in b1.read_csv(SCORES)]
    check_score_rows(rows,annotations,packet['config'])
    alignments = b1.indexed(report['alignment'],'annotation_id')
    require(set(alignments) == {a['annotation_id'] for a in annotations}, 'Alignment membership mismatch')
    for a in annotations:
        aligned = alignments[a['annotation_id']]
        require((aligned['start'],aligned['end'],aligned['span_text']) == (a['span_start_char'],a['span_end_char'],a['span_text']), 'Alignment/annotation mismatch')
        positions = aligned['token_positions']
        require(positions and all(type(p) is int and p >= 0 for p in positions) and positions == sorted(set(positions)), 'Malformed token positions')
        require(all(type(aligned[k]) is int and aligned[k] >= 0 for k in ['left_boundary_slop','right_boundary_slop']), 'Invalid token boundary slop')
        require(aligned['all_span_characters_covered'] is True, 'Uncovered span')
    calculations = analyze(base_rows(),rows,packet['config'])
    for key,value in calculations.items():
        require(report[key]==value, 'Recomputed B2 field differs: '+key)
    expected_csv = [{k:str(v) if v is not None else '' for k,v in r.items()} for r in calculations['metrics']]
    require(b1.read_csv(METRICS)==expected_csv, 'B2 metric CSV differs')
    local_status = 'not_run_public_tier_cannot_verify_private_q0048_trace'
    if require_local:
        for path,value in report['local_source_text_sha256'].items():
            require(b1.digest(ROOT/path)==value, 'Local trace/generation hash mismatch')
        expected, coverage = score_local(packet,annotations)
        require(rows==expected and report['alignment']==coverage, 'Local alignment/score replay differs')
        for path in PROTECTED:
            require(b1.digest(path)==report['protected_input_text_sha256'][rel(path)], 'Protected local/public input changed')
        local_status = 'q0048_nine_spans_two_precision_arms_replayed_no_inference'
    return report,local_status


def presentation_html(report):
    """Render the B2 appendix inside the existing methods page, not a new demo."""
    comparisons = [r for r in report['comparisons'] if r['arm'] == 'saved_trace_precision']
    by_signal = {r['signal']:r for r in comparisons}
    names = {'mean_token_entropy':'Mean entropy', 'one_minus_min_top2_margin':'Minimum top-2 margin risk',
             'all_positive':'Flag all spans', 'dev_fact_type_prior':'Dev fact-type prior (composition control)'}
    def table(rows):
        body = []
        for row in rows:
            before,after = row['test_metrics_before'],row['test_metrics_after']
            body.append('<tr><th scope="row">'+html.escape(names.get(row['signal'],row['signal']))+'</th>'
                        f'<td>{row["original_threshold"]:.6g}<br>{row["supplemented_threshold"]:.6g}</td>'
                        f'<td>{before["f1"]:.4f}<br>{after["f1"]:.4f}</td>'
                        f'<td>{before["average_precision"]:.4f}<br>{after["average_precision"]:.4f}</td>'
                        f'<td>{row["test_prediction_changes"]}</td></tr>')
        return ('<div class="b2-table" tabindex="0" role="region" aria-label="B2 before and after comparison">'
                '<table><thead><tr><th scope="col">Signal / reference</th><th scope="col">Threshold<br>Before / after</th>'
                '<th scope="col">Test F1<br>Before / after</th><th scope="col">Test AP<br>Before / after</th>'
                '<th scope="col">Changed test flags</th></tr></thead><tbody>'+''.join(body)+'</tbody></table></div>')
    entropy = by_signal['mean_token_entropy']
    before,after = entropy['test_metrics_before'],entropy['test_metrics_after']
    pair = lambda row: ' / '.join(str(row[k]) for k in ['tp','fp','tn','fn'])
    preview = table([by_signal[s] for s in names])
    full = ''.join('<h3>'+html.escape(arm)+'</h3>'+table([r for r in report['comparisons'] if r['arm']==arm])
                   for arm in report['recipe']['arms'])
    packet = b1.load(PACKET)
    atoms = ''.join('<tr><td>'+html.escape(a['span_text'])+'</td><td>'+html.escape(a['fact_type'])+'</td>'
                    f'<td>[{a["span_start_char"]}, {a["span_end_char"]})</td></tr>' for a in b1.jsonl(ANNOTATIONS))
    return f'''<section id="b2-dev-sensitivity" aria-labelledby="b2-title">
<h2 id="b2-title">B2: one omitted dev answer changes some thresholds</h2>
<p>September 5, 2026. Separate retrospective sensitivity, not a replacement benchmark.
The original 205 provisional spans and all historical scores remain unchanged.
Nine <strong>assistant-provisional, correct-key-fact</strong> atoms from q_0048 extend dev
from 17 questions / 102 spans to 18 questions / 111 spans. The augmented package has
214 spans; the same 18 test questions / 103 test spans are reused.</p>
<p>All 12 existing signals and three references use the unchanged B1 dev-only fitting policy.
The selected rows below explain the existing comparison, not a new winner.
Both precision arms and all candidates are retained in the expanded table.</p>
{preview}
<p>Displayed values are rounded; fitting uses saved-trace precision. Entropy changes
{entropy['test_prediction_changes']} test decisions: TP / FP / TN / FN moves from
<strong>{pair(before)}</strong> to <strong>{pair(after)}</strong>.
That removes {before['fp']-after['fp']} false alarms while missing {after['fn']-before['fn']} more provisionally labeled errors.
Top-2 margin is unchanged in this sensitivity; this is not evidence of general stability.</p>
<p>AP for fixed internal scores cannot change merely because a threshold changes.
The dev-fitted type prior is refitted, so its ranking can change. Its supplied fact types
contain correctness hints; it is not an information-matched independent detector.</p>
<details><summary>All candidates and both precision arms</summary>{full}</details>
<details><summary>q_0048 evidence, answer and nine provisional boundaries</summary>
<p>The source values are Netherlands GBP 39,655.81 and EIRE GBP 12,147.92.
Their difference is GBP 27,507.89. Approximately GBP 27,508 is correct whole-pound
rounding, not exact pence equality. These are net transaction values under the historical ledger scope.</p>
<blockquote>{html.escape(packet['case']['generated_text'])}</blockquote>
<div class="b2-table" tabindex="0" role="region" aria-label="Supplement atomic boundaries"><table>
<thead><tr><th>Text</th><th>Fact type</th><th>Character range</th></tr></thead><tbody>{atoms}</tbody></table></div>
<p>The sequence and recipe were saved before this supplement's token scores were read;
prior familiarity with the historical study remains. This is not independently blind
annotation or prospective preregistration. Repeated comparison and country facts are correlated.</p></details>
<p><strong>Limits:</strong> no independent human review, new model run, confirmation access,
new uncertainty interval or superiority claim. The all-correct single-answer supplement
supports flag counts, not an estimate of hallucination recall. Original test reuse cannot
establish generalization. Owner calibration remains separate and incomplete.</p>
</section>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command',choices=['prepare','build','validate'])
    parser.add_argument('--require-local',action='store_true')
    args = parser.parse_args()
    if args.command=='prepare':
        prepare()
    elif args.command=='build':
        build()
    else:
        failures, local_status = [], 'not_run'
        try:
            report,local_status = validate(args.require_local)
        except (ValueError,KeyError,TypeError,OSError,ArithmeticError) as exc:
            failures.append(str(exc))
        result={'status':'failed' if failures else 'B2_dev_sensitivity_validated',
                'validated_report_text_sha256':b1.digest(REPORT) if not failures else None,
                'public_checks':'prepared_provisional_atoms_source_commitments_and_120_metric_rows_recomputed',
                'local_checks':local_status,'independent_human_review':False,
                'num_failures':len(failures),'failures':failures}
        target=ROOT/('reports/bizhallu_q0048_dev_sensitivity_local_validation.json' if args.require_local else 'reports/bizhallu_q0048_dev_sensitivity_validation.json')
        b1.write_json(target,result)
        print(json.dumps(result,indent=2))
        if failures:
            raise SystemExit(1)


if __name__=='__main__':
    main()
