"""Source-backed English presentation facts; not a predictor or annotation dataset."""
from __future__ import annotations

import hashlib
import html
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATS = ROOT / 'reports/bizhallu_statistics_v2_report.json'
CURATED_CASES = {
    'q_0064': ('April 2011', ['22423', '47566', '22499'], ['14,280.90', '10,323.87', '4,173.18']),
    'q_0069': ('September 2011', ['85099B', '22086', '22423'], ['8630.45', '5997.25', '9315.03']),
}
REVIEW_BASIS = 'assistant-curated historical walkthrough with deterministic source checks; not independent human labels or verifier predictions'
TIMING_NOTE = (
    'A list marker is generated before the following product and amount. Its low token uncertainty '
    'does not establish that the model was confident about the completed business relationship. '
    'Raw teacher-forced token scores and completed-answer evidence checks have different information budgets.'
)
METRIC_NOTE = (
    'Positive and negative transaction values are sign-based accounting quantities. Negative value is '
    'not a verified measure of physical returns; fees and adjustments may be included. Merchandise '
    'scope uses a stock-code heuristic, and the historical product grain is stock code plus description.'
)


def historical_thresholds():
    """Read original dev thresholds, not another regenerated presentation summary."""
    names = [('simple', 'simple', 'one_minus_min_top2_margin'),
             ('entropy', 'simple', 'mean_token_entropy'),
             ('energy', 'energy', 'mean_spilled_probability_mass_after_top2')]
    result = {}
    for display, family, signal in names:
        report = json.loads((ROOT / f'results/full100_draft_{family}_split_report.json').read_text(encoding='utf-8'))
        rows = [r for r in report['thresholds'] if r['baseline'] == signal and r['score_field'] == signal]
        if report['dev_split'] != 'dev' or report['test_split'] != 'test' or len(rows) != 1:
            raise ValueError('Historical threshold source is ambiguous or uses the wrong split')
        threshold = rows[0]['threshold']
        if type(threshold) not in (int, float) or not Decimal(str(threshold)).is_finite():
            raise ValueError('Non-finite historical threshold')
        result[display] = threshold
    return result


def walkthrough(case):
    """Check six explicitly selected statements, never discover claims in new answers."""
    if case['question_id'] not in CURATED_CASES:
        return None
    period, codes, lexical_amounts = CURATED_CASES[case['question_id']]
    if period not in case['question'] or period not in case['generated_text']:
        raise ValueError('Curated period no longer matches the question and answer')
    rows = case['prompt_evidence_rows']
    by_code = {row['stock_code']: row for row in rows}
    if len(by_code) != len(rows):
        raise ValueError('Walkthrough requires unambiguous stock codes in these two curated tables')
    values = [Decimal(str(row['net_revenue'])) for row in rows]
    if not values or any(not value.is_finite() for value in values) or len(set(values)) != len(values):
        raise ValueError('Curated examples require finite, untied evidence values')
    ordered = sorted(rows, key=lambda row: Decimal(str(row['net_revenue'])), reverse=True)
    claims = []
    for rank, (code, lexical) in enumerate(zip(codes, lexical_amounts), 1):
        source = by_code[code]
        quote = f"{rank}. **{source['description']}** (rank {rank}) with a net revenue of GBP {lexical}."
        if case['generated_text'].count(quote) != 1:
            raise ValueError('Curated quote changed; re-review rather than silently matching another statement')
        value = Decimal(lexical.replace(',', ''))
        if value != Decimal(str(source['net_revenue'])):
            raise ValueError('Curated amount is not supported by its product row')
        start = case['generated_text'].index(quote)
        observed_rank = 1 + sum(v > value for v in values)
        expected = ordered[rank - 1]
        claims.append({
            'quote': quote, 'start': start, 'end': start + len(quote), 'period': period,
            'product_name': source['description'], 'stock_code_from_evidence': code,
            'stated_rank': rank, 'rank_in_shown_evidence': observed_rank,
            'amount_lexical': lexical, 'row_value_supported': True,
            'rank_supported_in_shown_evidence': observed_rank == rank,
            'source_row': 1 + rows.index(source),
            'expected_product_at_stated_rank': expected['description'],
            'expected_amount_at_stated_rank': format(Decimal(str(expected['net_revenue'])), ',.2f'),
        })
    return {
        'review_basis': REVIEW_BASIS, 'automatic_claim_extraction': False,
        'scope': 'Ranking within the eight rows shown to Qwen; historical corpus scope is separately documented.',
        'claims': claims, 'information_timing_note': TIMING_NOTE,
        'coverage_note': 'Both answers omit the requested stock codes. The six curated relationships are not a whole-answer correctness score.',
    }


def statistical_context():
    report = json.loads(STATS.read_text(encoding='utf-8'))
    wanted = ['one_minus_min_top2_margin', 'mean_token_entropy', 'all_positive', 'all_negative', 'dev_fact_type_prior']
    rows = [r for r in report['metrics'] if r['arm'] == 'saved_trace_precision' and r['split'] == 'test' and r['signal'] in wanted]
    if len(rows) != len(wanted) or len({r['signal'] for r in rows}) != len(wanted):
        raise ValueError('Missing or duplicate retrospective presentation metrics')
    by_signal = {row['signal']: row for row in rows}
    clusters = [r for r in report['paired_intervals'] if r['cluster_field'] == 'question_id']
    if len(clusters) != 1 or not clusters[0]['paired_resampling']:
        raise ValueError('Missing paired question-cluster analysis')
    intervals = [r for r in clusters[0]['intervals'] if r['signal'] == 'mean_token_entropy' and r['reference'] == 'all_positive' and r['metric'] == 'f1']
    if len(intervals) != 1:
        raise ValueError('Missing entropy-versus-all-positive F1 interval')
    return {'source': 'reports/bizhallu_statistics_v2_report.json',
            'source_sha256': hashlib.sha256(STATS.read_text(encoding='utf-8').encode('utf-8')).hexdigest(),
            'metric_version': report['metric_version'], 'scope': report['scope'],
            'test_rows': [by_signal[key] for key in wanted], 'entropy_minus_all_positive': intervals[0],
            'independent_human_annotation': False, 'confirmatory': False}


def b2_context():
    import q0048_dev_sensitivity as b2
    report, _ = b2.validate()
    rows = {r['signal']:r for r in report['comparisons'] if r['arm']=='saved_trace_precision'}
    return {'source':b2.rel(b2.REPORT), 'source_sha256':b2.b1.digest(b2.REPORT),
            'entropy':rows['mean_token_entropy'], 'margin':rows['one_minus_min_top2_margin'],
            'supplement_span_count':report['supplement_span_count'], 'original_span_count':205,
            'test_span_count':103, 'independent_human_review':False, 'confirmatory':False}


def b2_note_text(context=None):
    c = b2_context() if context is None else context
    e = c['entropy']
    return (f"B2 sensitivity adds {c['supplement_span_count']} assistant-provisional q_0048 dev atoms. "
            f"Dev-only refitting changes entropy F1 from {e['test_metrics_before']['f1']:.3f} to "
            f"{e['test_metrics_after']['f1']:.3f} on the same 103 old test spans; top-2 margin is unchanged. "
            "Original B1 results remain intact. This is not fresh held-out evidence or independent review.")


def b2_note_html():
    return ('<p class="b2-update"><strong>September 5 update.</strong> '+html.escape(b2_note_text())+
            ' <a href="./detector_interpretation.html#b2-dev-sensitivity">B2 methods appendix</a>.</p>')


def statistics_html(context=None):
    context = statistical_context() if context is None else context
    names = {'one_minus_min_top2_margin': 'Top-2 margin', 'mean_token_entropy': 'Token entropy',
             'all_positive': 'Flag every span', 'all_negative': 'Flag no spans',
             'dev_fact_type_prior': 'Dev fact-type prior (composition control)'}
    rows = ''.join('<tr><th scope="row">' + names[r['signal']] + '</th>' +
                   ''.join(f'<td>{r[k]:.3f}</td>' for k in ['average_precision','f1','balanced_accuracy','mcc']) + '</tr>'
                   for r in context['test_rows'])
    diff = context['entropy_minus_all_positive']
    return f'''<section id="statistical-review" class="statistical-review">
<h2>Historical B1 reference checks</h2>
<p>103 test spans from 18 questions, with AI-assisted provisional labels. AP is tied-score-aware average precision, not trapezoidal PR area. Scores use saved-trace precision; historical files are unchanged.</p>
<div style="overflow-x:auto"><table><thead><tr><th>Signal / reference</th><th>AP</th><th>F1</th><th>Balanced accuracy</th><th>MCC</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Entropy minus flag-every-span F1: {diff['point_difference']:+.4f}; exploratory paired question-bootstrap 95% interval [{diff['lower_95']:.4f}, {diff['upper_95']:.4f}]. This interval crosses zero; it is conditional on fixed dev thresholds and provisional labels, not adjusted for test-based signal selection or all shared-period dependence.</p>
<p>The fact-type prior is an annotation-composition control, not an information-matched detector: supplied type names can contain correctness hints. Its higher F1 is not a new headline result. The two overlapping-period components are too few for reliable cluster inference.</p>
<p>Same-step selected energy gap equals token NLL. Probability outside the top two choices is a concentration control, not an independent replication of Spilled Energy. No superiority claim follows from the historical 0.835 / 0.779 maxima.</p>
{b2_note_html()}
</section>'''
