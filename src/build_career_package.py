"""English career materials from the checked, shared presentation script."""
import html
import json
import math
from decimal import Decimal
from pathlib import Path
from presentation_story import build_story, page, paragraphs, timed_script_html
from presentation_evidence import statistics_html
from build_business_risk_lens import build_summary as business_summary

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'


def build_rehearsal(story, business):
    """Worked historical examples, not reviewer submissions or new deck content."""
    ledger = business['ledger']
    positive, negative, net = [Decimal(str(ledger[k])) for k in (
        'positive_transaction_value_gbp', 'negative_transaction_value_gbp', 'net_transaction_value_gbp')]
    merchandise = Decimal(str(business['merchandise_net_revenue']))
    if not all(x.is_finite() for x in (positive, negative, net, merchandise)) or positive + negative != net:
        raise ValueError('Rehearsal ledger does not reconcile')
    rows = {r['signal']: r for r in story['statistical_review']['test_rows']}
    entropy, reference = rows['mean_token_entropy'], rows['all_positive']
    for row in (entropy, reference):
        counts = [row[k] for k in ('tp', 'fp', 'tn', 'fn')]
        if any(type(x) is not int or x < 0 for x in counts) or sum(counts) != row['span_count']:
            raise ValueError('Rehearsal confusion counts do not match the population')
        denominator = 2 * row['tp'] + row['fp'] + row['fn']
        if not denominator or not math.isclose(2 * row['tp'] / denominator, row['f1'], rel_tol=0, abs_tol=1e-12):
            raise ValueError('Rehearsal F1 does not match source counts')
    if (entropy['tp'] + entropy['fn'], entropy['fp'] + entropy['tn']) != (reference['tp'], reference['fp']) or reference['tn'] or reference['fn']:
        raise ValueError('Flag-every-span reference has a different label population')
    april = story['april']
    interval = story['statistical_review']['entropy_minus_all_positive']
    b2 = story['b2_sensitivity']['entropy']
    exercises = [
        {'id': 'ledger', 'title': 'Reconcile the amount and its scope',
         'given': [f"{business['period']}. Historical eligible population: {ledger['eligible_line_count']:,} lines, GBP.", business['eligible_line_policy'],
                   f"Positive transaction value: {positive:,.2f}. Signed negative transaction value: {negative:,.2f}. Merchandise net value: {merchandise:,.2f}."],
         'question': 'Calculate all-ledger net value and the net contribution outside merchandise. Does the negative value identify physical returns?',
         'solution': [f"{positive:,.2f} + ({negative:,.2f}) = GBP {net:,.2f}. The negative input is already signed: adding it reduces the total. Subtracting it would double-reverse its sign.",
                      f"All-ledger net minus merchandise net = {net:,.2f} - {merchandise:,.2f} = GBP {net - merchandise:,.2f}. Merchandise net is higher because the other categories have a negative net contribution. These are different scopes, not competing estimates of the same population.",
                      'Physical returns are not separately identifiable. Negative entries may include fees and adjustments; merchandise is a stock-code heuristic. Net transaction value is not audited financial-statement revenue, profit or cash collected.'],
         'follow_up': 'What extra records would be needed to link returns to original sales? Why is a partial December unsuitable for an unqualified full-month comparison?',
         'evidence_href': './business_risk_lens.html', 'evidence_label': 'Ledger categories and metric contract', 'source': business['source']},
        {'id': 'binding', 'title': 'Check the complete ranked statement',
         'given': [f"April 2011, q_0064. Qwen's exact statement: {april['quote']}",
                   'Use the original eight-row evidence table in the April case. Preserve its product, period, metric and GBP scope.'],
         'question': 'Find the product and amount. Count shown rows with larger values. Which part is supported, which relationship is wrong, and what belongs at rank three?',
         'solution': [f"Source row {april['source_row']} matches {april['product_name']} and GBP {april['amount_lexical']}. Source-row fidelity is supported.",
                      f"{april['rank_in_shown_evidence'] - 1} shown rows have larger values. With no ties here, rank = 1 + that count = {april['rank_in_shown_evidence']}, not {april['stated_rank']}. The third product is {april['expected_product_at_stated_rank']} at GBP {april['expected_amount_at_stated_rank']}.",
                      'This is a curated check within the shown evidence, not automatic extraction or a population error rate. Low uncertainty on a list marker cannot establish confidence in its later completed product-rank-amount relationship.'],
         'follow_up': 'If a real amount appeared beside a different product, would a number-only lookup be enough? If evidence were incomplete or values tied, what scope or ranking rule would be needed?',
         'evidence_href': './portfolio_demo_v2.html?case=q_0064', 'evidence_label': 'April answer and original evidence rows', 'source': story['sources']['cases']},
        {'id': 'metrics', 'title': 'Recompute F1 before interpreting it',
         'given': ['Original B1: 103 pre-identified test spans with provisional labels. Positive means a span labeled hallucinated, not a positive sales value.',
                   f"Entropy: TP={entropy['tp']}, FP={entropy['fp']}, TN={entropy['tn']}, FN={entropy['fn']}. Flag every span: TP={reference['tp']}, FP={reference['fp']}, TN={reference['tn']}, FN={reference['fn']}.",
                   'F1 = 2TP / (2TP + FP + FN). TP is a flagged labeled error; FP is a flagged labeled-correct span; FN is a missed labeled error.'],
         'question': 'Compute both F1 values. How many fewer false alarms and how many more misses does entropy have? Does its higher point estimate prove stable superiority?',
         'solution': [f"Entropy: {2 * entropy['tp']} / ({2 * entropy['tp']} + {entropy['fp']} + {entropy['fn']}) = {entropy['f1']:.4f}. Flag every span: {2 * reference['tp']} / ({2 * reference['tp']} + {reference['fp']} + {reference['fn']}) = {reference['f1']:.4f}.",
                      f"Entropy makes {reference['fp'] - entropy['fp']} fewer false alarms, but misses {entropy['fn'] - reference['fn']} additional labeled errors. F1 does not include true negatives or monetary costs; this is not an estimate of avoided business loss.",
                      f"The paired question-bootstrap F1 difference is {interval['point_difference']:+.4f}, with exploratory 95% interval [{interval['lower_95']:.4f}, {interval['upper_95']:.4f}]. Crossing zero is not proof of equality, and this analysis does not establish stable superiority. It remains conditional on provisional labels and fixed thresholds, without resolving test-based signal selection or shared-period dependence.",
                      f"Separately, B2 adds nine provisional dev atoms and refits dev thresholds. Entropy F1 becomes {b2['test_metrics_after']['f1']:.3f} on the same old test. B1's interval is not a B2 interval; neither analysis is fresh confirmation."],
         'follow_up': 'Why can flagging everything have a high F1 here? What false-alarm and missed-error costs would you need before choosing a reporting policy?',
         'evidence_href': './detector_interpretation.html#statistical-review', 'evidence_label': 'B1 references and separate B2 sensitivity', 'source': story['sources']['statistics']},
    ]
    return {'revision': 'historical_explanation_practice_2026_09_05', 'exercise_count': len(exercises),
            'scope': 'Optional worked historical examples, not blind annotation or a scored assessment. No responses, identity or progress are collected. Disclose prior exposure in any later review.',
            'owner_mastery_verified': False, 'independent_human_review': False,
            'new_model_run': False, 'exercises': exercises}


def rehearsal_html(rehearsal):
    sections = []
    for item in rehearsal['exercises']:
        esc = html.escape
        sections.append(f'''<section id="practice-{item['id']}"><h3>{esc(item['title'])}</h3>
{paragraphs(item['given'])}<p><strong>Question:</strong> {esc(item['question'])}</p>
<p><a href="{esc(item['evidence_href'], quote=True)}">{esc(item['evidence_label'])}</a></p>
<details><summary>Worked solution: {esc(item['title'])}</summary>{paragraphs(item['solution'])}</details>
<p><strong>Follow-up:</strong> {esc(item['follow_up'])}</p></section>''')
    return '<section id="practice"><h2>From evidence to explanation</h2><p>' + html.escape(rehearsal['scope']) + '</p>' + ''.join(sections) + '</section>'


def main():
    s = build_story()
    rehearsal = build_rehearsal(s, business_summary())
    n = json.loads((REPORTS / 'bizhallu_portfolio_narrative_summary.json').read_text(encoding='utf-8'))
    bullets = ''.join(f'<li>{html.escape(x)}</li>' for x in s['resume_bullets'])
    faq = ''.join(f'<section><h3>{html.escape(x["question"])}</h3><p>{html.escape(x["answer"])}</p></section>' for x in s['faq'])
    guards = ''.join(f'<li>{html.escape(x)}</li>' for x in s['guardrails'])
    body = f'''<p>Career package for business, data and operations analyst conversations. The project connects accounting and supply management with evidence checks for AI-generated analysis.</p>
<p>For an academic discussion, start with the <a href="./research_one_pager.html">research brief</a>. The <a href="./assets/bizhallu_interview_v2.pptx">editable presentation (PPTX)</a> follows the same evidence and discussion questions as the script below.</p>
<p><a href="#pitch">Short pitch</a> | <a href="#practice">Evidence exercises</a> | <a href="#walkthrough">Presentation script</a> | <a href="#faq">Interview FAQ</a></p>
<section id="brief"><h2>Project Brief</h2><p>BizHallu connects transaction evidence, deterministic questions, local Qwen3-0.6B answers and retrospective evaluation of pre-identified fact spans. Its potential business use is reviewing AI-generated analysis before a reporting decision. It has not demonstrated deployed savings or operational impact.</p><p>Project direction used AI-assisted implementation and review. The 205 labels are provisional; 15 selected presentation spans received additional assistant review. There is no independent human annotation. The historical exploratory maximum AP and F1 remain 0.835 and 0.779 from different signals, not production estimates.</p></section>
<section id="pitch"><h2>90-second version</h2>{paragraphs(s['pitch_90_seconds'])}<p class="muted">{s['pitch_word_count']} words. Suggested speaking time, to be adjusted during rehearsal.</p></section>
<section id="walkthrough"><h2>5-minute version</h2><p>Ten segments total a 300-second planning budget, not a recorded presentation time. <a href="./portfolio_demo_v2.html?case=q_0064">April case</a> · <a href="./portfolio_demo_v2.html?case=q_0069">September case</a>.</p>{timed_script_html(s)}</section>
{rehearsal_html(rehearsal)}
{statistics_html(s['statistical_review'])}
<section id="resume"><h2>Resume bullets</h2><p>Adapt these examples to your actual contribution. Retain the AI-assistance disclosure and exploratory study scope.</p><ul>{bullets}</ul><h3>LinkedIn / GitHub profile</h3><p>{html.escape(s['linkedin_blurb'])}</p><p>{html.escape(s['profile_blurb'])}</p></section>
<section id="faq"><h2>Interview FAQ</h2>{faq}</section>
<section id="guardrails"><h2>Public Claim Guardrails</h2><ul>{guards}</ul><p>Independent human annotation and agreement assessment are pending. New comparisons require an independent predictor and a frozen evaluation protocol; confirmation remains sealed.</p></section>'''
    summary = {k:n[k] for k in ['question_count','question_type_count','annotated_span_count','best_test_auprc',
        'best_test_auprc_baseline','best_test_f1','best_test_f1_baseline','primary_question_ids','label_lock_basis']}
    summary.update(status='career_package_ready', career_html_path='reports/bizhallu_career_package.html',
        career_markdown_path='reports/bizhallu_career_package.md', heldout_test_span_count=103,
        provisional_annotation_count=205, presentation_reviewed_span_count=15, independent_human_annotation=False,
        automatic_claim_extraction=False, metric_selection_status='exploratory_test_maxima',
        resume_bullet_count=len(s['resume_bullets']), faq_count=len(s['faq']), guardrail_count=len(s['guardrails']),
        ready_for_current_stage=True, presentation_revision=s['revision'], owner_mastery_verified=False,
        statistical_source_sha256=s['statistical_review']['source_sha256'], story=s,
        explanation_practice=rehearsal, num_failures=0, failures=[])
    md = '# BizHallu Career Package\n\n## Project Brief\n\n' + s['positioning']
    md += '\n\n## 90-Second Pitch\n\n' + '\n\n'.join(s['pitch_90_seconds'])
    md += '\n\n## 5-Minute Interview Flow\n\n' + '\n\n'.join(f"### {i}. {x['title']} ({x['seconds']} seconds planned)\n\n{x['script']}" for i,x in enumerate(s['slides'],1))
    md += '\n\n## From Evidence to Explanation\n\n' + rehearsal['scope']
    for item in rehearsal['exercises']:
        md += '\n\n### ' + item['title'] + '\n\n' + '\n\n'.join(item['given'])
        md += '\n\nQuestion: ' + item['question'] + '\n\nWorked solution:\n\n' + '\n\n'.join(item['solution'])
        md += '\n\nFollow-up: ' + item['follow_up'] + '\n\nSource: `' + item['source'] + '`'
    md += '\n\n## Resume Bullets\n\n' + '\n'.join('- '+x for x in s['resume_bullets'])
    md += '\n\n## Interview FAQ\n\n' + '\n\n'.join(f"### {x['question']}\n\n{x['answer']}" for x in s['faq'])
    md += '\n\n## Public Claim Guardrails\n\n' + '\n'.join('- '+x for x in s['guardrails']) + '\n'
    (REPORTS/'bizhallu_career_package.html').write_text(page('BizHallu Career Package',body),encoding='utf-8')
    (REPORTS/'bizhallu_career_package.md').write_text(md,encoding='utf-8')
    (REPORTS/'bizhallu_career_package_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=True),encoding='utf-8')
    print(json.dumps({'status':summary['status'],'pitch_words':s['pitch_word_count'],'five_minute_words':s['five_minute_word_count']}))


if __name__ == '__main__':
    main()
