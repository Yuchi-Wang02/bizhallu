"""English career materials from the checked, shared presentation script."""
import html
import json
from pathlib import Path
from presentation_story import build_story, page, paragraphs, timed_script_html
from presentation_evidence import statistics_html

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'


def main():
    s = build_story()
    n = json.loads((REPORTS / 'bizhallu_portfolio_narrative_summary.json').read_text(encoding='utf-8'))
    bullets = ''.join(f'<li>{html.escape(x)}</li>' for x in s['resume_bullets'])
    faq = ''.join(f'<section><h3>{html.escape(x["question"])}</h3><p>{html.escape(x["answer"])}</p></section>' for x in s['faq'])
    guards = ''.join(f'<li>{html.escape(x)}</li>' for x in s['guardrails'])
    body = f'''<p>Career package for business, data and operations analyst conversations. Accounting and supply management provide the business context; AI reliability is a differentiator, not readiness for every data-science role.</p>
<section id="brief"><h2>Project Brief</h2><p>BizHallu connects transaction evidence, deterministic questions, local Qwen3-0.6B answers and retrospective evaluation of pre-identified fact spans. Its potential business use is reviewing AI-generated analysis before a reporting decision. It has not demonstrated deployed savings or operational impact.</p><p>Project direction used AI-assisted implementation and review. The 205 labels are provisional; 15 selected presentation spans received additional assistant review. There is no independent human annotation. The historical exploratory maximum AP and F1 remain 0.835 and 0.779 from different signals, not production estimates.</p></section>
<section id="pitch"><h2>90-second version</h2>{paragraphs(s['pitch_90_seconds'])}<p class="muted">{s['pitch_word_count']} words. A rehearsal draft; timing and owner mastery have not been measured.</p></section>
<section id="walkthrough"><h2>5-minute version</h2><p>Ten segments total a 300-second planning budget, not a recorded presentation time. <a href="./portfolio_demo_v2.html?case=q_0064">April case</a> · <a href="./portfolio_demo_v2.html?case=q_0069">September case</a>.</p>{timed_script_html(s)}</section>
{statistics_html(s['statistical_review'])}
<section id="resume"><h2>Resume bullets</h2><p>Candidate wording for discussion and practice. Use only claims you can explain with a source or a fresh calculation; the draft does not certify independent mastery.</p><ul>{bullets}</ul><h3>LinkedIn / GitHub profile</h3><p>{html.escape(s['linkedin_blurb'])}</p><p>{html.escape(s['profile_blurb'])}</p></section>
<section id="faq"><h2>Interview FAQ</h2>{faq}</section>
<section id="guardrails"><h2>Public Claim Guardrails</h2><ul>{guards}</ul><p>Personal review is deferred, not completed. New comparisons require an independent predictor and a frozen evaluation protocol; confirmation remains sealed.</p></section>'''
    summary = {k:n[k] for k in ['question_count','question_type_count','annotated_span_count','best_test_auprc',
        'best_test_auprc_baseline','best_test_f1','best_test_f1_baseline','primary_question_ids','label_lock_basis']}
    summary.update(status='career_package_ready', career_html_path='reports/bizhallu_career_package.html',
        career_markdown_path='reports/bizhallu_career_package.md', heldout_test_span_count=103,
        provisional_annotation_count=205, presentation_reviewed_span_count=15, independent_human_annotation=False,
        automatic_claim_extraction=False, metric_selection_status='exploratory_test_maxima',
        resume_bullet_count=len(s['resume_bullets']), faq_count=len(s['faq']), guardrail_count=len(s['guardrails']),
        ready_for_current_stage=True, presentation_revision=s['revision'], owner_mastery_verified=False,
        statistical_source_sha256=s['statistical_review']['source_sha256'], story=s, num_failures=0, failures=[])
    md = '# BizHallu Career Package\n\n## Project Brief\n\n' + s['positioning']
    md += '\n\n## 90-Second Pitch\n\n' + '\n\n'.join(s['pitch_90_seconds'])
    md += '\n\n## 5-Minute Interview Flow\n\n' + '\n\n'.join(f"### {i}. {x['title']} ({x['seconds']} seconds planned)\n\n{x['script']}" for i,x in enumerate(s['slides'],1))
    md += '\n\n## Resume Bullets\n\n' + '\n'.join('- '+x for x in s['resume_bullets'])
    md += '\n\n## Interview FAQ\n\n' + '\n\n'.join(f"### {x['question']}\n\n{x['answer']}" for x in s['faq'])
    md += '\n\n## Public Claim Guardrails\n\n' + '\n'.join('- '+x for x in s['guardrails']) + '\n'
    (REPORTS/'bizhallu_career_package.html').write_text(page('BizHallu Career Package',body),encoding='utf-8')
    (REPORTS/'bizhallu_career_package.md').write_text(md,encoding='utf-8')
    (REPORTS/'bizhallu_career_package_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=True),encoding='utf-8')
    print(json.dumps({'status':summary['status'],'pitch_words':s['pitch_word_count'],'five_minute_words':s['five_minute_word_count']}))


if __name__ == '__main__':
    main()
