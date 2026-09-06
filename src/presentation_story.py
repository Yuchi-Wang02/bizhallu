"""English interview content derived from checked presentation evidence."""
from __future__ import annotations

import html
import json
from pathlib import Path

from presentation_evidence import statistical_context, walkthrough, METRIC_NOTE, TIMING_NOTE, b2_context, b2_note_text

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'english_research_B1_B2_2026_09_06'
POSITIONING = 'Auditing AI-generated business analysis against transaction evidence'


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
        'BizHallu studies whether AI-generated business analysis is supported by transaction evidence. My accounting and supply-management background motivates a practical question: can an answer copy the right numbers and still reach the wrong business conclusion?',
        f"One retail example makes that distinction concrete. Qwen lists {april['product_name']} third at {april['amount_lexical']} pounds. That product and amount match a source row, but the product is seventh among the eight rows shown to the model. The copying is correct; the ranking is wrong.",
        'I directed the project with AI-assisted implementation and review. The pipeline contains 100 deterministic questions, local Qwen3-0.6B answers, and 205 provisional fact spans aligned to saved token traces. It checks whether uncertainty signals identify the labeled errors.',
        f"The original entropy F1 was {rows['mean_token_entropy']['f1']:.3f}, versus {rows['all_positive']['f1']:.3f} for flagging every span. Adding one omitted dev answer changes entropy F1 to {sensitivity['entropy']['test_metrics_after']['f1']:.3f} on the same old test. That sensitivity and provisional labels rule out a stable superiority claim.",
        'The next study will compare internal uncertainty with an independent evidence checker on complete product-ranking relationships. I am seeking feedback on relation annotation and a fair comparison design before expanding the evaluation.',
    ]
    comparison = f"Entropy F1 {rows['mean_token_entropy']['f1']:.3f}; flag-every-span F1 {rows['all_positive']['f1']:.3f}."
    interval_text = f"Paired F1 difference {diff['point_difference']:+.4f}; exploratory 95% interval [{diff['lower_95']:.4f}, {diff['upper_95']:.4f}]."
    sources = {
        'cases': 'reports/bizhallu_demo_v2_data.json',
        'statistics': stats['source'],
        'contract': 'configs/business_metric_contract_v1_1.json',
        'protocol': 'configs/relation_annotation_v2.json',
        'dev_sensitivity': sensitivity['source'],
        'confirmation': 'configs/confirmation_set_v1_protocol.json',
        'methodology': 'configs/methodology_protocol_v1.json',
        'data_source': 'https://doi.org/10.24432/C5BW33',
    }
    slides = [
        {'title': 'BizHallu', 'seconds': 20, 'kind': 'title',
         'lines': [POSITIONING, 'Yuchi Wang\nAccounting and supply management', 'Exploratory study of fact spans and business relationships'],
         'script': 'BizHallu asks whether AI-generated business conclusions follow from the transaction evidence. I directed the project with AI-assisted implementation and review. My accounting and supply-management background motivates the distinction between a number that reconciles and a relationship that supports a decision. I will begin with a concrete ranking error, then discuss the evaluation and a proposed comparison.', 'sources': [sources['cases'], sources['data_source']]},
        {'title': 'April: a correct amount with an incorrect rank', 'seconds': 35, 'kind': 'case',
         'lines': [april['product_name'], f"Qwen: rank 3 | GBP {april['amount_lexical']}",
                   f"Source row {april['source_row']}: amount matches | rank {april['rank_in_shown_evidence']} of 8 shown rows"],
         'script': f"Here is April 2011. The answer places {april['product_name']} third with revenue of {april['amount_lexical']} pounds. We can locate that exact product and amount in the source table. But six shown products have larger values. The correct third product is {april['expected_product_at_stated_rank']} at {april['expected_amount_at_stated_rank']} pounds. A check that only asks whether the amount appears in the table would miss the ranking error.", 'sources': [sources['cases']]},
        {'title': 'September: the same relationship error', 'seconds': 30, 'kind': 'relations',
         'lines': ['Each product-amount pair matches its own row.', 'The stated ranks are 1 / 2 / 3; evidence ranks are 3 / 8 / 2.', 'Ranking scope: eight rows shown to Qwen. Both examples omit requested stock codes.'],
         'script': 'The September answer repeats the pattern across all three listed products. Their stated ranks are one, two and three, while their ranks in the eight shown evidence rows are three, eight and two. Every product still matches its own amount. I use these cases to distinguish row fidelity from relationship correctness. They are selected historical examples, not evidence of a general error rate or an automatic verifier.', 'sources': [sources['cases']]},
        {'title': 'Research question: complete business relationships', 'seconds': 30, 'kind': 'definition',
         'lines': ['What do uncertainty signals miss when copied facts form an incorrect relationship?', 'A claim binds a period and product to a metric, amount and rank.', 'Comparison target: internal uncertainty and an independent evidence checker'],
         'script': 'The research question is what uncertainty signals miss when copied facts form an incorrect business relationship. A rank only makes sense with its product, metric and comparison scope. The proposed comparison asks whether an evidence checker adds useful information under matched conditions. Business definitions remain part of the task: negative transaction value can include fees and adjustments, so it cannot establish physical returns. The historical merchandise definition uses a documented stock-code heuristic.', 'sources': [sources['protocol'], sources['contract']]},
        {'title': 'Historical evaluation and its sample', 'seconds': 35, 'kind': 'pipeline',
         'lines': ['100 deterministic retail questions and local Qwen3-0.6B answers', 'Original B1: 205 provisional spans across 35 dev/test answers', '103 test spans across 18 questions, including 61 labeled errors', 'B2 separately adds 9 provisional atoms from the omitted dev answer'],
         'script': 'The pipeline turns retail transactions into deterministic questions and evidence tables, then captures local Qwen answers and token traces. B1 retains the original 205 provisional spans across 35 development and test answers. A separate B2 sensitivity adds nine assistant-provisional atoms for the omitted dev answer, without changing the 103 old test spans. Fifteen selected original spans received additional assistant review. None of this is independent human annotation or end-to-end claim extraction.', 'sources': [sources['statistics'], sources['cases'], sources['dev_sensitivity']]},
        {'title': 'The F1 advantage remains uncertain', 'seconds': 45, 'kind': 'metrics',
         'lines': [comparison, interval_text, 'Top-2 margin has exploratory maximum AP 0.835; entropy has maximum F1 0.779.', 'Different retrospectively selected signals; no stable superiority claim'],
         'script': f"The chart preserves B1's original test results. {comparison} {interval_text} That interval is conditional on fixed thresholds and is not a B2 interval. B2 adds one previously omitted dev answer with nine provisional correct facts. Refitting on dev lowers entropy F1 to {sensitivity['entropy']['test_metrics_after']['f1']:.3f} on the same old test, with five fewer false alarms and six more missed errors. Margin is unchanged in this check. We report sensitivity, not a new winner or fresh confirmation.", 'sources': [sources['statistics'], sources['dev_sensitivity']]},
        {'title': 'A fair comparison needs the same information', 'seconds': 30, 'kind': 'timing',
         'lines': ['The list marker appears before its product and amount.', 'An early token score cannot judge a relationship that is still incomplete.', 'Compare complete claims at a defined point in the answer.', 'Saved scores use raw logits. Same-step energy gap equals token NLL.'],
         'script': 'One methodological correction is especially important. A list marker is generated before the product and amount that follow it. Low uncertainty on that marker cannot establish that the completed relationship was confidently wrong. The saved raw teacher-forced logits also differ from generation probabilities after sampling transformations. Some nominally different features are mathematical aliases: same-step energy gap is token negative log probability. These distinctions prevent an unfair comparison with a checker that sees the whole answer.', 'sources': [sources['statistics'], sources['cases']]},
        {'title': 'What the current evidence supports', 'seconds': 25, 'kind': 'limits',
         'lines': ['Reproducible exploratory comparisons on provisional fact spans', 'Answer quality influenced selection. Dev and test share periods and evidence.', 'Independent human agreement and automatic claim extraction remain open.'],
         'script': 'The results describe a limited retrospective study. The annotation queue depended on generated-answer status, development and test share contexts, and independent human agreement has not been measured. The six curated relationships clarify particular cases; they do not replace the 205 labels. No result here establishes performance on larger models, unseen periods, automatically extracted claims or production business reports.', 'sources': [sources['statistics'], sources['protocol']]},
        {'title': 'Proposed comparison: product-ranking verification', 'seconds': 25, 'kind': 'role',
         'lines': ['Inputs: question, generated answer, metric contract and evidence rows', 'Independent output: support status, evidence reference and abstention', 'Compare with uncertainty on the same complete claims.', 'Report extraction coverage and errors. Evaluation labels stay outside prediction.'],
         'script': 'The next implementation targets product rankings. It will use the question, generated answer, metric contract and evidence rows to return a support decision, evidence reference and abstention when needed. Gold answers and evaluation labels stay outside prediction. Two independent reviewers will establish relation labels. The comparison will report extraction coverage and abstentions, because a checker can appear accurate by avoiding difficult claims. This verifier is proposed work, not a completed result.', 'sources': [sources['protocol'], sources['confirmation']]},
        {'title': 'A focused discussion with a research mentor', 'seconds': 25, 'kind': 'next',
         'lines': ['Feedback request: the unit of annotation and a fair comparison design', 'First study: calibrate product-ranking relationships with independent reviewers.', 'Then freeze predictions and evaluate on separated evidence contexts.', 'The 48-context confirmation design remains unexecuted and estimation-focused.'],
         'script': 'My request is a focused discussion of the annotation unit and comparison design. The immediate deliverable would be a small independently reviewed relation set and one evidence checker. The existing 48-context design offers a later evaluation path, but it remains unexecuted and estimation-focused. Model and prompt settings, reviewers, and the prediction protocol must be ready first. A second dataset or model would follow only after this smaller comparison is credible.', 'sources': [sources['protocol'], sources['confirmation']]},
    ]
    faq = [
        ('What is the main business finding?', 'A copied amount can match its product while the product has the wrong rank. April and September demonstrate that distinction within the shown evidence; they do not establish a population error rate.'),
        ('Why examine spans and also full relationships?', 'Atomic spans locate an error, but a rank belongs to a product, period and metric. A relationship record preserves those dependencies and avoids interpreting an early list marker as the completed claim.'),
        ('Why use Qwen3-0.6B?', 'It fit the local compute budget and exposed inspectable failures. Small size does not establish external validity. Reproduction also needs frozen model/tokenizer versions, decoding settings, data policies and saved artifacts.'),
        ('Did the detector beat simple references?', comparison + ' ' + interval_text + ' ' + b2_note_text(sensitivity) + ' These checks do not establish stable F1 superiority.'),
        ('Why is the fact-type prior not a new winning detector?', 'It uses supplied annotation categories, some with correctness hints. It diagnoses sample composition rather than providing an information-matched automatic prediction system.'),
        ('Is this an independently human-labeled benchmark?', 'No. There are 205 AI-assisted provisional labels and 15 selected presentation spans with additional assistant review. Independent human annotation and agreement remain uncompleted.'),
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
        'Potential reporting applications have no measured deployment outcome or financial benefit in this study.',
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
<style>*{{box-sizing:border-box;letter-spacing:0}}body{{margin:0;background:#f6f7f9;color:#202124;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}}nav,main,footer{{max-width:1000px;margin:auto;padding:20px 26px}}nav{{display:flex;gap:20px;flex-wrap:wrap;border-bottom:1px solid #d6dde0}}a{{color:#145e77}}:focus-visible{{outline:3px solid #b65c0b;outline-offset:4px}}.skip-link{{position:absolute;left:16px;top:-100px;background:#fff;padding:10px;z-index:10}}.skip-link:focus{{top:10px}}main:focus{{outline:none}}h1{{font-size:30px;line-height:1.25}}h2{{font-size:23px;line-height:1.3}}h3{{font-size:18px;line-height:1.35}}section{{padding:15px 0;border-bottom:1px solid #d6dde0;scroll-margin-top:24px}}p{{margin:8px 0 15px}}li{{margin:10px 0}}small,.muted{{color:#59656b;font-size:14px}}blockquote{{margin:16px 0;padding:4px 18px;border-left:3px solid #18765e}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;border-bottom:1px solid #d6dde0;padding:9px}}h1,h2,h3,p,li,td,th,a{{overflow-wrap:anywhere}}summary{{cursor:pointer;font-weight:700}}@media(max-width:650px){{main,nav,footer{{padding:16px}}nav{{gap:14px}}}}@media print{{nav,.skip-link{{display:none}}body{{background:white}}}}</style></head>
<body><a class="skip-link" href="#main">Skip to content</a><nav aria-label="Primary"><a href="./index.html">Home</a><a href="./portfolio_demo_v2.html">Cases</a><a href="./detector_interpretation.html">Methods</a><a href="./research_one_pager.html">Research</a></nav><main id="main" tabindex="-1"><h1>{html.escape(title)}</h1>{body}</main>
<footer>Updated September 6, 2026. Exploratory evidence from AI-assisted provisional labels. Independent human agreement and confirmation results remain pending.</footer></body></html>'''
