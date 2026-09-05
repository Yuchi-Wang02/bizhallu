"""Preserved seven-span case readout with corrected relationship interpretation."""
from __future__ import annotations
import html
import json
from collections import Counter
from pathlib import Path

from presentation_evidence import walkthrough, statistical_context, statistics_html, historical_thresholds, TIMING_NOTE, METRIC_NOTE
from presentation_story import page

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
HTML_PATH = REPORTS / 'bizhallu_portfolio_demo.html'
SUMMARY_PATH = REPORTS / 'bizhallu_portfolio_demo_summary.json'
PRIMARY_QUESTION_IDS = ['q_0064', 'q_0069']
REVISION = 'historical_case_interpretation_2026_09_05'


def load_data():
    return json.loads((REPORTS / 'bizhallu_demo_v2_data.json').read_text(encoding='utf-8'))


def selected_cases(data):
    cases = [c for qid in PRIMARY_QUESTION_IDS for c in data['cases'] if c['question_id'] == qid]
    if len(cases) != 2 or [c['question_id'] for c in cases] != PRIMARY_QUESTION_IDS:
        raise ValueError('Missing or duplicate primary cases')
    if sum(len(c['spans']) for c in cases) != 7:
        raise ValueError('Seven preserved selected spans required')
    for case in cases:
        if case['presentation_walkthrough'] != walkthrough(case):
            raise ValueError('Primary evidence proof drift')
    return cases


def build_summary(data):
    cases = selected_cases(data)
    spans = [s for c in cases for s in c['spans']]
    meta = data['meta']
    thresholds = historical_thresholds()
    if any(meta[f + '_threshold'] != value for f, value in thresholds.items()):
        raise ValueError('Demo thresholds differ from original dev threshold reports')
    interpretation = json.loads((REPORTS / 'full100_detector_interpretation_summary.json').read_text(encoding='utf-8'))
    ap = interpretation['best_overall_by_test_auprc']
    f1 = interpretation['best_overall_by_test_f1']
    if meta['best_test_auprc'] != ap['test_auprc'] or meta['best_test_f1'] != f1['test_f1']:
        raise ValueError('Historical maxima disagree across preserved sources')
    summary = {
        'status': 'portfolio_demo_ready', 'portfolio_demo_html_path': 'reports/bizhallu_portfolio_demo.html',
        'source_label_lock_summary_path': 'reports/full100_label_lock_summary.json',
        'source_detector_interpretation_summary_path': 'reports/full100_detector_interpretation_summary.json',
        'primary_question_ids': PRIMARY_QUESTION_IDS, 'case_count': 2, 'locked_primary_span_count': 7,
        'by_label': dict(sorted(Counter(s['label'] for s in spans).items())),
        'best_test_auprc': meta['best_test_auprc'], 'best_test_auprc_baseline': ap['baseline'],
        'best_test_f1': meta['best_test_f1'], 'best_test_f1_baseline': f1['baseline'],
        'label_lock_status': 'presentation_labels_locked', 'label_lock_basis': 'assistant_full_review',
        'labels_locked': True, 'human_confirmation_required': False,
        'historical_lock_scope': 'Seven primary-demo spans among fifteen additional assistant-reviewed spans; not human confirmation',
        'revision': REVISION, 'independent_human_review': False,
        'statistical_source_sha256': statistical_context()['source_sha256'], 'num_failures': 0, 'failures': [],
    }
    for family in ('simple', 'entropy', 'energy'):
        summary[family + '_threshold'] = thresholds[family]
        summary[family + '_outcomes'] = dict(sorted(Counter(s[family + '_outcome'] for s in spans).items()))
    return summary


def highlighted_answer(case):
    parts, cursor = [], 0
    text = case['generated_text']
    for span in sorted(case['spans'], key=lambda s: (s['span_start_char'], s['span_end_char'])):
        start, end = span['span_start_char'], span['span_end_char']
        if start < cursor or not start < end or text[start:end] != span['span_text']:
            raise ValueError('Invalid or overlapping historical span')
        parts.append(html.escape(text[cursor:start]))
        color = '#e1f0e9' if span['label'] == 'correct_key_fact' else '#f8e0e1'
        parts.append(f'<mark style="background:{color}" title="{html.escape(span["label"], quote=True)}">{html.escape(text[start:end])}</mark>')
        cursor = end
    rendered = ''.join(parts) + html.escape(text[cursor:])
    # Preserve model whitespace in DOM text without trailing whitespace in HTML source.
    return rendered.replace('\r', '&#13;').replace('\n', '&#10;')


def render_case(case):
    esc = html.escape
    proof = walkthrough(case)
    relation_rows = ''.join(f"<tr><td>{esc(c['product_name'])}</td><td>GBP {esc(c['amount_lexical'])}</td><td>Matches own row</td>"
                            f"<td>{c['stated_rank']}</td><td>{c['rank_in_shown_evidence']}</td></tr>" for c in proof['claims'])
    evidence_rows = ''.join(f"<tr><td>{esc(r['stock_code'])}</td><td>{esc(r['description'])}</td>"
                           + ''.join(f"<td>GBP {r[k]:,.2f}</td>" for k in ['net_revenue','gross_positive_revenue','cancellation_revenue']) + '</tr>'
                           for r in case['prompt_evidence_rows'])
    span_rows = ''.join(f"<tr><td>{esc(s['annotation_id'])}</td><td>{esc(s['span_text'])}</td><td>{esc(s['label'])}</td>"
                       + ''.join(f"<td>{esc(s[f+'_outcome'])}<br>{s[f+'_score']:.6g}</td>" for f in ['simple','entropy','energy']) + '</tr>'
                       for s in case['spans'])
    return f'''<section id="{esc(case['question_id'])}"><h2>{esc(case['question_id'])}: product amounts and ranking relations</h2>
<p>{esc(case['question'])}</p><h3>Original Qwen answer; historical selected spans</h3>
<pre style="white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.7 ui-monospace,Consolas,monospace">{highlighted_answer(case)}</pre>
<p>Highlight colors preserve the earlier context-bound span judgments. A red amount is not necessarily a number copied from another product. These marks do not assign new relationship labels.</p>
<h3>Current interpretation: row fidelity is separate from rank</h3>
<div style="overflow-x:auto"><table><thead><tr><th>Generated product</th><th>Generated value</th><th>Amount fidelity</th><th>Stated rank</th><th>Rank in shown evidence</th></tr></thead><tbody>{relation_rows}</tbody></table></div>
<p>{esc(proof['scope'])} {esc(proof['coverage_note'])}</p>
<details><summary>Original evidence order and historical gold</summary>
<p>{esc(case['gold_short_answer'])}</p><p>Headers below use current sign-based terminology; original values and row order are unchanged.</p>
<div style="overflow-x:auto"><table><thead><tr><th>Stock code</th><th>Product</th><th>Net value</th><th>Positive value</th><th>Negative value</th></tr></thead><tbody>{evidence_rows}</tbody></table></div></details>
<details><summary>Historical detector readout for the selected spans</summary>
<p>These outcomes use the original atomic labels and fixed dev thresholds; they are not predictions of the completed relationships above. Residual mass is a probability concentration control.</p>
<div style="overflow-x:auto"><table><thead><tr><th>Annotation</th><th>Text</th><th>Historical label</th><th>Top-2 margin</th><th>Entropy</th><th>Top-2 residual mass</th></tr></thead><tbody>{span_rows}</tbody></table></div></details></section>'''


def render(data, summary):
    meta = data['meta']
    body = f'''<p>Two historical cases and 7 selected spans with additional assistant review. This page preserves the earlier span-level readout; <a href="./portfolio_demo_v2.html">Demo v2</a> is the primary interactive entry.</p>
<p><a href="#q_0064">April</a> | <a href="#q_0069">September</a></p>
{''.join(render_case(case) for case in selected_cases(data))}
<section><h2>What the case readouts do not prove</h2><p>{html.escape(TIMING_NOTE)}</p><p>{html.escape(METRIC_NOTE)}</p>
<p>There is no independent human benchmark, automatic claim extraction or completed-answer detector here. Seven selected examples of atomic outcomes cannot establish detector superiority, error prevalence or measured business loss.</p>
<p>Historical thresholds: one_minus_min_top2_margin &gt;= {meta['simple_threshold']:.6f}; mean_token_entropy &gt;= {meta['entropy_threshold']:.6f}; mean_spilled_probability_mass_after_top2 &gt;= {meta['energy_threshold']:.6f}.</p>
<p>Exploratory max test AUPRC {summary['best_test_auprc']:.6f}; exploratory max test F1 {summary['best_test_f1']:.6f}. These are different test-selected signals, not preregistered winners.</p></section>
{statistics_html()}'''
    return page('BizHallu Portfolio Demo: historical case readout', body)


def main():
    data = load_data()
    summary = build_summary(data)
    HTML_PATH.write_text(render(data, summary), encoding='utf-8')
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': summary['status'], 'revision': REVISION, 'new_labels': 0}))


if __name__ == '__main__':
    main()
