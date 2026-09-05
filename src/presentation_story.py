"""English interview content derived from checked presentation evidence."""
from __future__ import annotations

import html
import json
from pathlib import Path

from presentation_evidence import statistical_context, walkthrough, METRIC_NOTE, TIMING_NOTE, b2_context, b2_note_text

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'english_interview_B1_B2_review_2026_09_05'
POSITIONING = 'Business analytics with evidence checks for AI-generated analysis'


def build_story():
    data = json.loads((ROOT / 'reports/bizhallu_demo_v2_data.json').read_text(encoding='utf-8'))
    cases = {c['question_id']: c for c in data['cases']}
    april = walkthrough(cases['q_0064'])['claims'][2]
    september = walkthrough(cases['q_0069'])['claims']
    stats = statistical_context()
    sensitivity = b2_context()
    rows = {r['signal']: r for r in stats['test_rows']}
    diff = stats['entropy_minus_all_positive']
    pitch = [
        'BizHallu is my business analytics project on checking AI-generated analysis against transaction evidence. My accounting and supply-management background makes me interested in the difference between a number that reconciles and a business conclusion that is actually supported.',
        f"One retail example makes that distinction concrete. Qwen lists {april['product_name']} third at {april['amount_lexical']} pounds. That product and amount match a source row, but the product is seventh among the eight rows shown to the model. The copying is correct; the ranking is wrong.",
        'I directed the project with AI-assisted implementation and review. The pipeline contains 100 deterministic questions, local Qwen3-0.6B answers, and 205 provisional fact spans aligned to saved token traces. It checks whether uncertainty signals identify the labeled errors.',
        f"The original entropy F1 was {rows['mean_token_entropy']['f1']:.3f}, versus {rows['all_positive']['f1']:.3f} for flagging every span. Adding one omitted dev answer changes entropy F1 to {sensitivity['entropy']['test_metrics_after']['f1']:.3f} on the same old test. That sensitivity and provisional labels rule out a stable superiority claim.",
        'The business lesson is that source-row accuracy and relationship accuracy need separate checks. My next technical step is a small independent verifier, while keeping statistical evaluation and alternative uncertainty methods open for comparison.',
    ]
    comparison = f"Entropy F1 {rows['mean_token_entropy']['f1']:.3f}; flag-every-span F1 {rows['all_positive']['f1']:.3f}."
    interval_text = f"Paired F1 difference {diff['point_difference']:+.4f}; exploratory 95% interval [{diff['lower_95']:.4f}, {diff['upper_95']:.4f}]."
    sources = {
        'cases': 'reports/bizhallu_demo_v2_data.json',
        'statistics': stats['source'],
        'contract': 'configs/business_metric_contract_v1_1.json',
        'protocol': 'configs/relation_annotation_v2.json',
        'dev_sensitivity': sensitivity['source'],
    }
    slides = [
        {'title': 'BizHallu', 'seconds': 20, 'kind': 'title',
         'lines': [POSITIONING, 'Yuchi Wang | Accounting and supply management | JHU Carey BAAI', 'Exploratory portfolio study'],
         'script': 'BizHallu studies a practical reporting problem: when an AI writes business analysis, can we trace its claims back to the evidence? I directed the project with AI-assisted implementation and review. My focus is on the accounting and operational decisions behind the numbers, alongside the model evaluation.', 'sources': [sources['cases']]},
        {'title': 'April product ranking', 'seconds': 35, 'kind': 'case',
         'lines': [april['product_name'], f"Qwen: rank 3 | GBP {april['amount_lexical']}",
                   f"Source row {april['source_row']}: amount matches | rank {april['rank_in_shown_evidence']} of 8 shown rows"],
         'script': f"Here is April 2011. The answer places {april['product_name']} third with revenue of {april['amount_lexical']} pounds. We can locate that exact product and amount in the source table. But six shown products have larger values. The correct third product is {april['expected_product_at_stated_rank']} at {april['expected_amount_at_stated_rank']} pounds. A check that only asks whether the amount appears in the table would miss the ranking error.", 'sources': [sources['cases']]},
        {'title': 'September: all three ranks differ', 'seconds': 30, 'kind': 'relations',
         'lines': ['Each product-amount pair matches its own row.', 'The stated ranks are 1 / 2 / 3; evidence ranks are 3 / 8 / 2.', 'Ranking scope: eight rows shown to Qwen. Both examples omit requested stock codes.'],
         'script': 'The September answer repeats the pattern across all three listed products. Their stated ranks are one, two and three, while their ranks in the eight shown evidence rows are three, eight and two. Every product still matches its own amount. I use these cases to distinguish row fidelity from relationship correctness. They are selected historical examples, not evidence of a general error rate or an automatic verifier.', 'sources': [sources['cases']]},
        {'title': 'Business metric scope', 'seconds': 30, 'kind': 'definition',
         'lines': ['Positive / negative transaction value: sign-based ledger quantities', 'Negative value can include fees and adjustments; physical returns are not separately verified.', 'Merchandise scope: stock-code heuristic; historical product grain: code + description'],
         'script': 'Metric definitions matter before we judge an answer. Negative transaction value is not the same as confirmed physical returns, because fee and adjustment records can contribute. Merchandise scope also depends on a documented stock-code rule. I preserve the historical calculation and provide a versioned definition amendment instead of silently rewriting old gold answers. Without cost, inventory or delivery data, I cannot claim profit analysis or inventory optimization.', 'sources': [sources['contract']]},
        {'title': 'The historical evaluation pipeline', 'seconds': 35, 'kind': 'pipeline',
         'lines': ['100 deterministic questions / 7 task types / Qwen3-0.6B', 'Original B1: 205 provisional spans across 35 dev/test answers', '103 test spans / all 18 test questions; B2 separately assesses omitted dev q_0048', 'Evidence > answer > pre-identified spans > saved token scores > evaluation'],
         'script': 'The pipeline turns retail transactions into deterministic questions and evidence tables, then captures local Qwen answers and token traces. B1 retains the original 205 provisional spans across 35 development and test answers. A separate B2 sensitivity adds nine assistant-provisional atoms for the omitted dev answer, without changing the 103 old test spans. Fifteen selected original spans received additional assistant review. None of this is independent human annotation or end-to-end claim extraction.', 'sources': [sources['statistics'], sources['cases'], sources['dev_sensitivity']]},
        {'title': 'Historical B1 references and B2 sensitivity', 'seconds': 45, 'kind': 'metrics',
         'lines': [comparison, interval_text, 'Top-2 margin has exploratory maximum AP 0.835; entropy has maximum F1 0.779.', 'Different retrospectively selected signals; no stable superiority claim'],
         'script': f"The chart preserves B1's original test results. {comparison} {interval_text} That interval is conditional on fixed thresholds and is not a B2 interval. B2 adds one previously omitted dev answer with nine provisional correct facts. Refitting on dev lowers entropy F1 to {sensitivity['entropy']['test_metrics_after']['f1']:.3f} on the same old test, with five fewer false alarms and six more missed errors. Margin is unchanged in this check. We report sensitivity, not a new winner or fresh confirmation.", 'sources': [sources['statistics'], sources['dev_sensitivity']]},
        {'title': 'Token timing and completed relationships', 'seconds': 30, 'kind': 'timing',
         'lines': ['The model generates the list marker before the product and amount.', 'Low uncertainty on "3." does not establish confidence in the completed relationship.', 'Raw teacher-forced logits are not the sampling distribution.', 'Same-step energy gap equals token NLL; residual mass is a probability control.'],
         'script': 'One methodological correction is especially important. A list marker is generated before the product and amount that follow it. Low uncertainty on that marker cannot establish that the completed relationship was confidently wrong. The saved raw teacher-forced logits also differ from generation probabilities after sampling transformations. Some nominally different features are mathematical aliases: same-step energy gap is token negative log probability. These distinctions prevent an unfair comparison with a checker that sees the whole answer.', 'sources': [sources['statistics'], sources['cases']]},
        {'title': 'Scope of the evidence', 'seconds': 25, 'kind': 'limits',
         'lines': ['Provisional labels; no independent human agreement', 'Outcome-informed annotation queue; shared business periods and evidence', 'One small model; pre-identified fact spans; no production performance estimate'],
         'script': 'The results describe a limited retrospective study. The annotation queue depended on generated-answer status, development and test share contexts, and independent human agreement has not been measured. The six curated relationships clarify particular cases; they do not replace the 205 labels. No result here establishes performance on larger models, unseen periods, automatically extracted claims or production business reports.', 'sources': [sources['statistics'], sources['protocol']]},
        {'title': 'Analyst contribution and business use', 'seconds': 25, 'kind': 'role',
         'lines': ['Project direction with AI-assisted coding and review', 'Auditable metric definitions, traceable evidence and reproducible calculations', 'Potential use: review AI-generated reporting before a business decision', 'No measured cost saving, deployed control or verified independent mastery'],
         'script': 'For an analyst role, I would emphasize metric definitions, reproducible calculations and explaining what evidence supports. The potential use is reviewing generated reports before a business decision, not a claim that I have deployed a control or measured savings. AI assistance is part of the provenance. My next learning step is to explain and modify the analysis directly, supported by a small SQL and BI companion project.', 'sources': [sources['contract'], sources['statistics']]},
        {'title': 'Research questions and next steps', 'seconds': 25, 'kind': 'next',
         'lines': ['Calibrate relation labels and independent review', 'Build a top3 verifier without gold, labels or detector outcomes as prediction inputs', 'Compare information budgets, coverage and costs before expanding methods', 'Feedback request: annotation unit and comparison design'],
         'script': 'For a professor, my concrete request is feedback on the unit of annotation and comparison design. I would begin with a top-three verifier that uses the question, answer, metric contract and evidence, without evaluation labels or gold answers as inputs. Semantic consistency, attention methods and a faithful adjacent-step energy implementation remain comparison options. The new confirmation study stays sealed until the prediction and evaluation process is ready.', 'sources': [sources['protocol'], sources['statistics']]},
    ]
    faq = [
        ('What is the main business finding?', 'A copied amount can match its product while the product has the wrong rank. April and September demonstrate that distinction within the shown evidence; they do not establish a population error rate.'),
        ('Why examine spans and also full relationships?', 'Atomic spans locate an error, but a rank belongs to a product, period and metric. A relationship record preserves those dependencies and avoids interpreting an early list marker as the completed claim.'),
        ('Why use Qwen3-0.6B?', 'It fit the local compute budget and exposed inspectable failures. Small size does not establish external validity. Reproduction also needs frozen model/tokenizer versions, decoding settings, data policies and saved artifacts.'),
        ('Did the detector beat simple references?', comparison + ' ' + interval_text + ' ' + b2_note_text(sensitivity) + ' These checks do not establish stable F1 superiority.'),
        ('Why is the fact-type prior not a new winning detector?', 'It uses supplied annotation categories, some with correctness hints. It diagnoses sample composition rather than providing an information-matched automatic prediction system.'),
        ('Is this an independently human-labeled benchmark?', 'No. There are 205 AI-assisted provisional labels and 15 selected presentation spans with additional assistant review. Independent human annotation and agreement remain uncompleted; owner review is currently deferred.'),
        ('What changed about the energy interpretation?', 'Same-step selected energy gap equals NLL. Probability outside the top two choices is a concentration control. A faithful adjacent-step Spilled Energy comparison still needs a separate formula and time-index audit.'),
        ('Does negative transaction value measure returns?', METRIC_NOTE + ' Without separate inventory, cost and delivery records, this project cannot prove inventory optimization, profit improvement or supply-chain optimization.'),
        ('What did you do, and where did AI assist?', 'I directed the project with AI-assisted implementation and review. The repository documents the calculation, annotation and evaluation work. These artifacts are not evidence that every step was coded unaided or that independent human review occurred.'),
        ('What is the next comparison?', 'A small independent top3 verifier versus internal uncertainty, with extraction coverage, abstention and information conditions reported. Semantic Entropy, TOHA and entity probes remain research candidates subject to compatibility and cost checks, not promised results.'),
    ]
    bullets = [
        'Directed BizHallu with AI-assisted implementation, connecting retail metric definitions with evidence checks for generated business analysis.',
        'Developed a documented pipeline for 100 deterministic retail questions and local Qwen3-0.6B answers with saved token-level traces.',
        'Built an AI-assisted provisional review workflow for 205 pre-identified fact spans and separated source-row fidelity from product-ranking correctness.',
        'Audited retrospective detector evaluation with tied-score AP, simple reference policies and paired cluster uncertainty; retained historical maxima as exploratory.',
        'Created inspectable business cases and English methods materials for explaining model errors, metric scope and limitations to business and technical readers.',
    ]
    guardrails = [
        '205 provisional labels; 15 additionally assistant-reviewed spans; no independent human agreement.',
        '0.835 AP and 0.779 F1 are exploratory maxima from different signals, not a single confirmatory detector result.',
        'B2 adds nine assistant-provisional dev atoms separately; the same 103 old test spans are reused, not newly held out.',
        'Complete relation correctness is different from source-row fidelity and early-token confidence.',
        'Negative transaction value is not verified physical returns; no inventory or profit optimization claim.',
        'The public review schema uses existing labels; it is not an independent verifier.',
        'Sharing a project does not establish owner mastery, a deployed business control or measured financial benefit.',
    ]
    return {'revision': REVISION, 'positioning': POSITIONING, 'pitch_90_seconds': pitch,
            'pitch_word_count': len(' '.join(pitch).split()), 'timing_basis': 'planning budget, not a recorded speaking-time measurement',
            'slides': slides, 'five_minute_seconds': sum(s['seconds'] for s in slides),
            'five_minute_word_count': len(' '.join(s['script'] for s in slides).split()),
            'resume_bullets': bullets, 'faq': [{'question': q, 'answer': a} for q, a in faq],
            'guardrails': guardrails, 'statistical_review': stats, 'april': april,
            'b2_sensitivity': sensitivity,
            'september': september, 'sources': sources, 'independent_human_annotation': False,
            'linkedin_blurb': 'I am developing business analytics skills through BizHallu, an AI-assisted project on auditing generated retail analysis. The work connects metric definitions, transaction evidence and retrospective model evaluation. Its selected cases show that correctly copied product amounts can still support an incorrect ranking. The results remain exploratory and the labels provisional.',
            'profile_blurb': 'Business and operations analytics | Accounting and supply management | Evidence checks for AI-generated analysis'}


def paragraphs(items):
    return ''.join(f'<p>{html.escape(item)}</p>' for item in items)


def timed_script_html(story):
    elapsed = 0
    parts = []
    for index, slide in enumerate(story['slides'], 1):
        end = elapsed + slide['seconds']
        label = f'{elapsed//60}:{elapsed%60:02d}-{end//60}:{end%60:02d}'
        parts.append(f'<section id="slide-{index}"><h3>{index}. {html.escape(slide["title"])} <small>{label}</small></h3><p>{html.escape(slide["script"])}</p></section>')
        elapsed = end
    return ''.join(parts)


def page(title, body):
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title>
<style>*{{box-sizing:border-box;letter-spacing:0}}body{{margin:0;background:#f6f7f9;color:#202124;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}}nav,main,footer{{max-width:1000px;margin:auto;padding:20px 26px}}nav{{display:flex;gap:20px;flex-wrap:wrap;border-bottom:1px solid #d6dde0}}a{{color:#145e77}}h1{{font-size:30px;line-height:1.25}}h2{{font-size:23px;line-height:1.3}}h3{{font-size:18px;line-height:1.35}}section{{padding:15px 0;border-bottom:1px solid #d6dde0}}p{{margin:8px 0 15px}}li{{margin:10px 0}}small,.muted{{color:#59656b;font-size:14px}}blockquote{{margin:16px 0;padding:4px 18px;border-left:3px solid #18765e}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;border-bottom:1px solid #d6dde0;padding:9px}}h1,h2,h3,p,li,td,th{{overflow-wrap:anywhere}}summary{{cursor:pointer;font-weight:700}}@media(max-width:650px){{main,nav,footer{{padding:16px}}}}@media print{{nav{{display:none}}body{{background:white}}}}</style></head>
<body><nav><a href="./index.html">BizHallu</a><a href="./portfolio_demo_v2.html">Cases</a><a href="./detector_interpretation.html">Methods</a><a href="./research_one_pager.html">Research</a></nav><main><h1>{html.escape(title)}</h1>{body}</main>
<footer>English interview revision: September 5, 2026. AI-assisted project and presentation review; independent human annotation and owner mastery remain unverified.</footer></body></html>'''
