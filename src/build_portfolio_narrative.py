"""Keep the existing narrative as a source-backed English walkthrough."""
import html
import json
from pathlib import Path
from presentation_story import build_story, page, paragraphs, timed_script_html
from presentation_evidence import statistics_html

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'


def load(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def main():
    s = build_story()
    demo = load('reports/bizhallu_portfolio_demo_summary.json')
    interpretation = load('reports/full100_detector_interpretation_summary.json')
    lock = load('reports/full100_label_lock_summary.json')
    questions = load('data/processed/business_questions_gold_report.json')
    qwen = load('outputs/qwen_full100_report.json')
    atoms = load('outputs/full100_annotation_draft_report.json')
    alignment = load('outputs/full100_draft_span_token_alignment_report.json')
    ap, f1 = interpretation['best_overall_by_test_auprc'], interpretation['best_overall_by_test_f1']
    energy = load('results/full100_draft_detector_family_comparison_report.json')['energy_best_by_test_f1']
    summary = dict(status='portfolio_narrative_ready', narrative_html_path='reports/bizhallu_portfolio_narrative.html',
        source_portfolio_demo_summary_path='reports/bizhallu_portfolio_demo_summary.json',
        source_detector_interpretation_summary_path='reports/full100_detector_interpretation_summary.json',
        source_label_lock_summary_path='reports/full100_label_lock_summary.json',
        current_preflight_stage='github_pages_ready', ready_for_current_stage=True,
        primary_question_ids=demo['primary_question_ids'], question_count=questions['record_count'],
        question_type_count=len(questions['question_type_counts']), qwen_record_count=qwen['record_count'],
        qwen_model_id='Qwen/Qwen3-0.6B', annotated_question_count=atoms['annotated_question_count'],
        annotated_span_count=atoms['total_span_count'], aligned_span_count=alignment['aligned_span_count'],
        best_test_auprc=ap['test_auprc'], best_test_auprc_baseline=ap['baseline'],
        best_test_f1=f1['test_f1'], best_test_f1_baseline=f1['baseline'],
        energy_best_f1=energy['test_f1'], energy_best_f1_baseline=energy['baseline'],
        error_row_count=interpretation['error_row_count'], locked_selected_span_count=lock['selected_annotation_count'],
        locked_primary_span_count=demo['locked_primary_span_count'], positioning_statement=s['positioning'],
        resume_bullet_count=len(s['resume_bullets']), slide_count=len(s['slides']), guardrail_count=len(s['guardrails']),
        labels_locked=lock['labels_locked'], label_lock_basis=lock['lock_basis'],
        label_lock_scope='15 selected spans only; assistant review', presentation_revision=s['revision'],
        statistical_source_sha256=s['statistical_review']['source_sha256'], independent_human_annotation=False,
        owner_mastery_verified=False, metric_selection_status='exploratory_test_maxima', num_failures=0, failures=[])
    guards = ''.join(f'<li>{html.escape(x)}</li>' for x in s['guardrails'])
    body = f'''<p>A guided account of the business problem, inspectable evidence and limits of the retrospective study. The cases were selected for explanation, not as a fresh evaluation sample.</p>
<p><a href="./assets/bizhallu_interview_v2.pptx">Download the editable presentation (PPTX)</a> or read the <a href="./research_one_pager.html">research brief</a> for the proposed annotation pilot.</p>
<section><h2>90-second pitch</h2>{paragraphs(s['pitch_90_seconds'])}</section>
<section><h2>Five-minute walkthrough</h2><p>Ten segments with a suggested total of five minutes. Adjust the timing to the discussion.</p>{timed_script_html(s)}</section>
{statistics_html(s['statistical_review'])}
<section><h2>Presentation guardrails</h2><ul>{guards}</ul><p>The historical <code>assistant_full_review</code> field applies to 15 selected spans, not independent review of all 205 labels. These artifacts support discussion of business analytics and AI reliability, not a production claim.</p></section>
<section><h2>Reader paths</h2><p><a href="./portfolio_demo_v2.html?case=q_0064">q_0064</a> and <a href="./portfolio_demo_v2.html?case=q_0069">q_0069</a> show source-row fidelity versus ranking. The <a href="./career_package.html">career package</a> contains resume wording and interview FAQ. The <a href="./research_one_pager.html">research brief</a> proposes a limited feedback request and preserves alternative comparison methods.</p></section>'''
    (REPORTS/'bizhallu_portfolio_narrative.html').write_text(page('BizHallu Portfolio Narrative',body),encoding='utf-8')
    (REPORTS/'bizhallu_portfolio_narrative_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=True),encoding='utf-8')
    print(json.dumps({'status':summary['status'],'slide_count':summary['slide_count']}))


if __name__ == '__main__':
    main()
