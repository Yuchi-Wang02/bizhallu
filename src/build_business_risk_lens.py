"""Business interpretation of the Stage A ledger, not new experimental results."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

from business_metric_audit import canonical, decimal_value, ratio
from presentation_story import page

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
HTML_PATH = REPORTS / 'bizhallu_business_risk_lens.html'
SUMMARY_PATH = REPORTS / 'bizhallu_business_risk_lens_summary.json'
REVISION = 'business_scope_review_2026_09_05'
LENSES = [
    {'title': 'Transaction-value reconciliation', 'audience': 'Accounting and reporting',
     'question': 'Do positive and negative values reconcile to the reported net for the same period and scope?',
     'control': 'Check the sign, period, unit, eligibility policy and additive identity before interpreting change.',
     'limit': 'Net transaction value is not audited financial-statement revenue, profit or cash collected.'},
    {'title': 'Negative-value review', 'audience': 'Accounting and operations',
     'question': 'How much negative value comes from merchandise versus fees, adjustments and unknown codes?',
     'control': 'Keep sign, invoice cancellation flag and merchandise classification separate. Do not allocate unlinked adjustments to products.',
     'limit': 'Negative merchandise lines are not an original-sale-linked physical return rate; cause and timing remain unknown.'},
    {'title': 'Product concentration and ranking', 'audience': 'Supply management and performance reporting',
     'question': 'Are product, period, metric, rank and value supported by the same evidence scope?',
     'control': 'Check complete relationships and the concentration denominator. Preserve stock-code-plus-description grain for the historical study.',
     'limit': 'Sales-value concentration does not establish inventory requirements, demand forecasts, procurement savings or optimal replenishment.'},
    {'title': 'Country exposure and comparison', 'audience': 'Business and operations analysis',
     'question': 'Are the named countries, comparison direction and amount difference consistent?',
     'control': 'Subtract within the same month and scope; distinguish domestic/non-domestic exposure and disclose missing dimensions.',
     'limit': 'Transaction geography alone cannot explain market attractiveness, profitability, customer acquisition or causal growth drivers.'},
]


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def validate_ledger(ledger):
    categories = ledger['categories']
    expected = {'merchandise', 'fee_or_service_code', 'adjustment_or_discount_code', 'unknown_non_merchandise'}
    if {r['category'] for r in categories} != expected or len(categories) != len(expected):
        raise ValueError('Missing or duplicate ledger categories')
    for row in categories:
        p, n, net = [decimal_value(row[k]) for k in ('positive_value_gbp', 'negative_value_gbp', 'net_value_gbp')]
        if p < 0 or n > 0 or p + n != net or type(row['row_count']) is not int or row['row_count'] <= 0:
            raise ValueError('Category sign, grain or reconciliation failure')
    for source, field in [('positive_value_gbp', 'positive_transaction_value_gbp'),
                          ('negative_value_gbp', 'negative_transaction_value_gbp'), ('net_value_gbp', 'net_transaction_value_gbp')]:
        if sum(decimal_value(r[source]) for r in categories) != decimal_value(ledger[field]):
            raise ValueError('Ledger categories do not sum to total')
    if sum(r['row_count'] for r in categories) != ledger['eligible_line_count']:
        raise ValueError('Category row counts differ from eligible population')
    nonmerch = -sum(decimal_value(r['negative_value_gbp']) for r in categories if r['category'] != 'merchandise')
    if nonmerch != decimal_value(ledger['non_merchandise_negative_magnitude_gbp']):
        raise ValueError('Non-merchandise negative value differs')
    if ratio(nonmerch, -decimal_value(ledger['negative_transaction_value_gbp'])) != ledger['non_merchandise_share_of_negative_value_percentage']:
        raise ValueError('Wrong negative-value share denominator or rounding')
    if ledger['physical_return_value'] is not None or ledger['physical_return_value_status'] != 'not_identifiable_from_source_fields':
        raise ValueError('Physical return value cannot be identified')


def build_summary():
    audit_path = REPORTS / 'bizhallu_business_metric_audit_report.json'
    contract_path = ROOT / 'configs/business_metric_contract_v1_1.json'
    audit, contract = load(audit_path), load(contract_path)
    if audit['contract_sha256'] != canonical(contract, 'bizhallu:metric-contract:v1.1'):
        raise ValueError('Metric contract drift')
    ledger = audit['historical_eligible_ledger']
    validate_ledger(ledger)
    questions = load(ROOT / 'data/processed/business_questions_gold_report.json')
    quality = load(ROOT / 'data/processed/data_quality_report.json')
    merchandise = next(r['net_value_gbp'] for r in ledger['categories'] if r['category'] == 'merchandise')
    if ledger['net_transaction_value_gbp'] != quality['net_revenue'] or merchandise != quality['merchandise_net_revenue']:
        raise ValueError('Historical data-quality totals disagree with Stage A')
    if questions['record_count'] != audit['historical_question_count']:
        raise ValueError('Historical question count drift')
    return {'status': 'business_risk_lens_ready', 'revision': REVISION,
            'business_risk_lens_html_path': 'reports/bizhallu_business_risk_lens.html',
            'question_count': questions['record_count'], 'question_type_count': len(questions['question_type_counts']),
            'question_type_counts': questions['question_type_counts'],
            'data_rows_raw': audit['source_raw_counts']['historical'], 'country_count': quality['country_count'],
            'stock_code_count': quality['stock_code_count'], 'net_revenue': ledger['net_transaction_value_gbp'],
            'merchandise_net_revenue': merchandise, 'legacy_value_key_note': 'net_revenue aliases retain numbers, not financial-statement recognition claims',
            'ledger': ledger, 'lens_count': len(LENSES), 'lenses': LENSES,
            'metric_contract_id': contract['contract_id'], 'metric_contract_sha256': audit['contract_sha256'],
            'source_limits': contract['source_limits'], 'eligible_line_policy': contract['eligible_line_policy'],
            'source': 'reports/bizhallu_business_metric_audit_report.json',
            'source_text_sha256': hashlib.sha256(audit_path.read_text(encoding='utf-8').encode()).hexdigest(),
            'period': 'December 2010 through December 9, 2011; December 2011 is partial',
            'new_questions': 0, 'new_model_run': False, 'independent_business_validation': False,
            'measured_business_impact': None, 'num_failures': 0, 'failures': []}


def gbp(value):
    return f"GBP {decimal_value(value):,.2f}"


def render(summary):
    esc = html.escape
    ledger = summary['ledger']
    categories = ''.join(f"<tr><th scope='row'>{esc(r['category'].replace('_', ' '))}</th><td>{r['row_count']:,}</td>"
                         f"<td>{gbp(r['positive_value_gbp'])}</td><td>{gbp(r['negative_value_gbp'])}</td><td>{gbp(r['net_value_gbp'])}</td></tr>"
                         for r in ledger['categories'])
    lenses = ''.join(f"<section><h2>{esc(r['title'])}</h2><p class='muted'>{esc(r['audience'])}</p>"
                     f"<p>{esc(r['question'])}</p><p><strong>Control:</strong> {esc(r['control'])}</p>"
                     f"<p><strong>Boundary:</strong> {esc(r['limit'])}</p></section>" for r in summary['lenses'])
    body = f'''<p>Accounting and operations questions come before the AI score. The current retail evidence supports transaction-value reconciliation and product/country comparisons, not verified physical returns or inventory optimization.</p>
<section><h2>One ledger, explicitly different scopes</h2>
<p>{esc(summary['period'])}. {summary['data_rows_raw']:,} raw records; {ledger['eligible_line_count']:,} eligible ledger lines under the historical cleaning policy.</p>
<p><strong>{gbp(ledger['positive_transaction_value_gbp'])} + ({gbp(ledger['negative_transaction_value_gbp'])}) = {gbp(ledger['net_transaction_value_gbp'])}</strong></p>
<p>Net merchandise value is {gbp(summary['merchandise_net_revenue'])}. It exceeds the all-ledger net here because the other categories have a negative net contribution; these are different scopes, not competing estimates of the same population.</p>
<div style="overflow-x:auto" role="region" aria-label="Historical transaction value by category" tabindex="0"><table><caption>Historical eligible ledger; category assignments use a stock-code heuristic</caption><thead><tr><th scope="col">Category</th><th scope="col">Lines</th><th scope="col">Positive</th><th scope="col">Negative</th><th scope="col">Net</th></tr></thead><tbody>{categories}</tbody></table></div>
<p><strong>{ledger['non_merchandise_share_of_negative_value_percentage']:.2f}% of the absolute negative value</strong> is in non-merchandise categories under that heuristic: {gbp(ledger['non_merchandise_negative_magnitude_gbp'])} / {gbp(-decimal_value(ledger['negative_transaction_value_gbp']))}. This is not a physical return percentage or proof that those records are bad data.</p>
<p>{esc(summary['eligible_line_policy'])}</p><p>{esc(summary['source_limits'])}</p></section>
{lenses}
<section><h2>From a business claim to an evidence check</h2>
<p>In the <a href="./portfolio_demo_v2.html?case=q_0064">April example</a>, the product's own amount is correct while its stated rank is wrong. The <a href="./portfolio_demo_v2.html?case=q_0069">September example</a> shows three such ranking mismatches. These are curated examples, not estimates of business-error frequency or loss.</p>
<p>A low-uncertainty list marker does not establish confidence in the later product-rank-amount relationship. The <a href="./detector_interpretation.html">methods comparison</a> reports exploratory uncertainty signals alongside simple references and limitations.</p></section>
<section><h2>What this project has not measured</h2><p>No avoided loss, analyst time saving, inventory benefit or deployed control effectiveness has been measured. Suggested use is a review control, not an implemented business decision system. Row counts and question coverage do not establish impact.</p>
<p>A useful next assessment would compare these evidence checks with deterministic SQL and template-based reporting, then measure where review adds value. The present examples establish an auditable question, not a quantified operational benefit.</p></section>
<details><summary>Metric definitions and source provenance</summary><p>Contract: {esc(summary['metric_contract_id'])}. Historical field names and question text remain unchanged in the experimental record. The current presentation uses positive/negative transaction value; physical return value is not identifiable.</p>
<p>Stage A source: <code>{esc(summary['source'])}</code>; normalized-text SHA-256 <code>{summary['source_text_sha256']}</code>. Local raw replay is separate from public arithmetic validation.</p>
<p><a href="https://archive.ics.uci.edu/dataset/352/online+retail">UCI Online Retail</a></p></details>'''
    return page('BizHallu: business risk and metric scope', body)


def main():
    summary = build_summary()
    HTML_PATH.write_text(render(summary), encoding='utf-8')
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': summary['status'], 'revision': REVISION, 'new_questions': 0}))


if __name__ == '__main__':
    main()
