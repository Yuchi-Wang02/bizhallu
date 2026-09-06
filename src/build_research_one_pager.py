from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"

NARRATIVE_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_narrative_summary.json"
INTERPRETATION_SUMMARY_PATH = REPORTS_DIR / "full100_detector_interpretation_summary.json"
DEMO_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_v2_summary.json"
RISK_SUMMARY_PATH = REPORTS_DIR / "bizhallu_business_risk_lens_summary.json"
VERIFIER_SUMMARY_PATH = REPORTS_DIR / "bizhallu_evidence_verifier_pilot_summary.json"
METHODOLOGY_SUMMARY_PATH = REPORTS_DIR / "bizhallu_methodology_hardening_summary.json"
PRECISION_REPORT_PATH = REPORTS_DIR / "bizhallu_confirmation_precision_review_report.json"
PRECISION_AMENDMENT_PATH = PROJECT_ROOT / "configs" / "confirmation_precision_scope_amendment_v1.json"
CAPACITY_REPORT_PATH = REPORTS_DIR / "bizhallu_confirmation_context_feasibility_report.json"
CONTEXT_MANIFEST_PATH = REPORTS_DIR / "bizhallu_confirmation_context_manifest_report.json"
QUESTION_DESIGN_PATH = REPORTS_DIR / "bizhallu_confirmation_question_design_report.json"

HTML_PATH = REPORTS_DIR / "bizhallu_research_one_pager.html"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_research_one_pager_summary.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_list(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def metric(value: Any) -> str:
    return f"{float(value):.3f}"


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    narrative = load_json(NARRATIVE_SUMMARY_PATH)
    interpretation = load_json(INTERPRETATION_SUMMARY_PATH)
    demo = load_json(DEMO_SUMMARY_PATH)
    risk = load_json(RISK_SUMMARY_PATH)
    verifier = load_json(VERIFIER_SUMMARY_PATH)
    methodology = load_json(METHODOLOGY_SUMMARY_PATH)
    precision = load_json(PRECISION_REPORT_PATH)
    precision_amendment = load_json(PRECISION_AMENDMENT_PATH)
    capacity = load_json(CAPACITY_REPORT_PATH)
    context_manifest = load_json(CONTEXT_MANIFEST_PATH)
    question_design = load_json(QUESTION_DESIGN_PATH)

    best_auprc = interpretation["best_overall_by_test_auprc"]
    best_f1 = interpretation["best_overall_by_test_f1"]

    research_questions = [
        "How should complete entity-rank-amount relationships be annotated and checked without counting one binding error several times?",
        "How should token-time uncertainty and completed-answer verification be compared under different information budgets?",
        "What sample and independent-review design supports uncertainty estimates under shared evidence contexts?",
    ]

    jhu_extensions = [
        "Healthcare analytics: audit whether AI-generated utilization, cost, or quality summaries are grounded in source tables.",
        "Operations analytics: verify product-ranking and transaction-value claims before they influence prioritization decisions.",
        "Responsible AI governance: turn evidence-grounding checks into an audit layer for business decision-support tools.",
        "Capstone direction: compare internal-state signals, literature-grounded baselines, and evidence-aware verifiers on business claims.",
    ]

    research_tracks = [
        "Internal uncertainty: entropy, top-2 margin, and energy-style probability-mass signals already used in this project.",
        "Literature-grounded baselines: Semantic Entropy, TOHA, and entity-level hallucination detection as future comparison candidates.",
        "Evidence-aware verification: future independent decisions from the question, answer, metric contract and evidence; gold answers and evaluation labels are excluded from prediction. The current v0 is only a label-derived review schema.",
    ]

    baseline_backlog = [
        "Semantic Entropy: useful for testing semantic consistency across sampled answers; requires multiple generations per question.",
        "TOHA: relevant as an attention-graph topology baseline; implementation depends on reliable access to attention tensors and runnable reference code.",
        "Real-time hallucinated entity detection: relevant for product, country, month, and stock-code spans; needs entity extraction and entity-level evidence matching.",
        "Spilled Energy: audit adjacent-step formula and time indexing; same-step energy gap is NLL and probability-mass controls are not independent replications.",
    ]

    revised_counts = precision_amendment["revised_planning_counts"]
    capacity_proof = capacity["capacity_proof"]
    precision_pass_count = precision_amendment["failed_strong_comparison_design"][
        "passing_candidate_count"
    ]

    summary = {
        "status": "research_one_pager_ready",
        "research_one_pager_html_path": repo_path(HTML_PATH),
        "title": "BizHallu: Auditing Evidence Binding Errors in LLM-Generated Business Analysis",
        "question_count": narrative["question_count"],
        "annotated_span_count": narrative["annotated_span_count"],
        "heldout_test_span_count": 103,
        "best_test_auprc": best_auprc["test_auprc"],
        "best_test_f1": best_f1["test_f1"],
        "demo_case_count": demo["case_count"],
        "business_risk_lens_count": risk["lens_count"],
        "verifier_pilot_span_count": verifier["span_count"],
        "verifier_pilot_contradicted_count": verifier["review_status_counts"]["contradicted"],
        "research_question_count": len(research_questions),
        "extension_count": len(jhu_extensions),
        "research_track_count": len(research_tracks),
        "baseline_backlog_count": len(baseline_backlog),
        "next_stage_scope": "Proposed relation-annotation calibration and independent verifier design; no completed human review, model execution or confirmation evaluation",
        "confirmation_precision_review_status": precision["status"],
        "confirmation_strong_candidate_pass_count": precision_pass_count,
        "confirmation_candidate_count": len(precision["candidate_summaries"]),
        "confirmation_context_count": revised_counts["confirmation_context_count"],
        "confirmation_total_context_count": revised_counts["total_context_count"],
        "confirmation_total_question_count": revised_counts["total_question_count"],
        "confirmation_capacity_matching_count": capacity_proof["maximum_slot_matching_count"],
        "confirmation_capacity_hall_slack": capacity_proof["minimum_hall_capacity_slack"],
        "confirmation_context_manifest_status": context_manifest["status"],
        "confirmation_context_manifest_created": context_manifest["execution_boundary"]["context_manifest_created"],
        "confirmation_split_assignment_created": context_manifest["execution_boundary"]["split_assignment_created"],
        "confirmation_context_manifest_commitment_sha256": context_manifest["private_manifest_commitment"]["canonical_sha256"],
        "confirmation_reserve_period_count": context_manifest["frozen_inventory"]["reserve_period_count"],
        "confirmation_question_design_status": question_design["status"],
        "confirmation_question_manifest_commitment_sha256": question_design["private_question_manifest_commitment"]["canonical_sha256"],
        "confirmation_question_count_frozen": question_design["frozen_inventory"]["question_count"],
        "confirmation_question_template_count": len(question_design["frozen_inventory"]["template_counts"]),
        "confirmation_question_payload_fingerprint_check": question_design["evidence_payload_integrity"]["question_level_evidence_payload_fingerprint_check"],
        "confirmation_question_payload_cross_split_overlap_count": question_design["evidence_payload_integrity"]["cross_split_fingerprint_count"],
        "confirmation_question_evidence_content_fingerprint_count": question_design["evidence_payload_integrity"]["unique_content_fingerprint_count"],
        "confirmation_question_evidence_content_cross_split_overlap_count": question_design["evidence_payload_integrity"]["content_cross_split_fingerprint_count"],
        "confirmation_historical_unique_evidence_content_fingerprint_count": question_design["evidence_payload_integrity"]["historical_full100_content_fingerprint_count"],
        "confirmation_question_evidence_content_historical_overlap_count": question_design["evidence_payload_integrity"]["historical_full100_content_fingerprint_overlap_count"],
        "confirmation_claim_scope": "estimation_only_no_detector_superiority",
        "methodology_status": methodology["status"],
        "methodology_share_status": methodology["share_status"],
        "label_lock_basis": narrative["label_lock_basis"],
        "num_failures": 0,
        "failures": [],
    }

    from presentation_evidence import statistical_context, walkthrough, b2_context, b2_note_html
    stats = statistical_context()
    by_signal = {row['signal']: row for row in stats['test_rows']}
    interval = stats['entropy_minus_all_positive']
    demo_data = load_json(REPORTS_DIR / 'bizhallu_demo_v2_data.json')
    example = walkthrough(next(c for c in demo_data['cases'] if c['question_id']=='q_0064'))['claims'][2]
    summary['presentation_revision'] = 'professor_review_2026_09_06'
    summary['statistical_review'] = stats
    summary['b2_sensitivity'] = b2_context()
    summary['independent_human_annotation'] = False
    summary['share_status'] = 'exploratory_project_for_method_feedback'
    summary['primary_research_question'] = research_questions[0]
    summary['design_questions'] = research_questions[1:]
    summary['immediate_pilot_status'] = 'proposed_not_executed'
    summary['related_work'] = [
        {
            'name': 'FActScore',
            'citation': 'Min et al., EMNLP 2023',
            'url': 'https://aclanthology.org/2023.emnlp-main.741/',
            'relevance': 'Atomic factual precision motivates explicit units; business relationships also require grouping related facts.',
            'evaluated_in_bizhallu': False,
        },
        {
            'name': 'TabFact',
            'citation': 'Chen et al., ICLR 2020',
            'url': 'https://openreview.net/pdf?id=rkeJRhNYDH',
            'relevance': 'Table-based fact verification motivates structured evidence; this proposal targets transaction scope and generated rankings.',
            'evaluated_in_bizhallu': False,
        },
        {
            'name': 'Semantic Entropy',
            'citation': 'Farquhar et al., Nature 2024',
            'url': 'https://www.nature.com/articles/s41586-024-07421-0',
            'relevance': 'Meaning-level uncertainty requires multiple generations; the current study evaluates token entropy.',
            'evaluated_in_bizhallu': False,
        },
    ]
    related_work_html = ''.join(
        f"<li><a href=\"{esc(item['url'])}\"><strong>{esc(item['name'])}</strong></a> "
        f"<span class=\"muted\">({esc(item['citation'])})</span>. {esc(item['relevance'])}</li>"
        for item in summary['related_work']
    )
    html_text = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(summary['title'])}</title>
<style>
*{{box-sizing:border-box;letter-spacing:0}}body{{margin:0;background:#f6f7f9;color:#202124;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}}main,nav{{max-width:1040px;margin:auto;padding:22px 28px}}nav{{display:flex;gap:18px;flex-wrap:wrap;border-bottom:1px solid #d9dee1;font-size:14px}}a{{color:#155e75;text-underline-offset:3px}}a:focus-visible,summary:focus-visible{{outline:3px solid #155e75;outline-offset:4px}}[aria-current="page"]{{font-weight:700}}.skip{{position:absolute;left:12px;top:-100px;background:white;padding:10px;z-index:5}}.skip:focus{{top:10px}}h1{{font-size:29px;line-height:1.2;margin:7px 0 12px;max-width:900px}}h2{{font-size:17px;margin:15px 0 7px}}p{{margin:7px 0}}section{{padding:4px 0 12px;border-bottom:1px solid #d9dee1}}.eyebrow,.muted{{color:#58616a}}.eyebrow{{font-size:12px;text-transform:uppercase;letter-spacing:.05em}}.grid{{display:grid;grid-template-columns:1.08fr 1fr;gap:28px}}.grid>div{{min-width:0}}.case{{border-left:3px solid #1a7560;padding:2px 14px;margin:14px 0 4px}}.question{{font-weight:650}}table{{width:100%;border-collapse:collapse;font-size:13px}}td,th{{border-bottom:1px solid #d9dee1;padding:7px;text-align:left}}caption{{text-align:left;color:#58616a;font-size:12px;margin:8px 0}}ul{{padding-left:18px}}li{{margin:7px 0}}.related{{font-size:13px;line-height:1.45}}h1,h2,p,li,td,th,a{{overflow-wrap:anywhere}}footer{{margin-top:14px;font-size:12px;color:#58616a}}.print-url{{display:none}}@media(max-width:700px){{.grid{{grid-template-columns:1fr;gap:0}}main,nav{{padding:16px}}h1{{font-size:25px}}}}@page{{size:A4;margin:11mm}}@media print{{body{{background:white;font-size:9pt;line-height:1.27}}nav,.skip{{display:none}}main{{max-width:none;padding:0}}h1{{font-size:18pt;margin:4px 0 7px}}h2{{font-size:11pt;margin:7px 0 4px}}p{{margin:5px 0}}.eyebrow{{font-size:8pt}}.grid{{gap:18px;grid-template-columns:1.08fr 1fr}}section{{padding:2px 0 5px;break-inside:avoid}}.case{{margin:9px 0 2px;padding-left:10px}}table{{font-size:8.5pt}}td,th{{padding:4px}}caption{{font-size:8pt}}.related{{font-size:8.5pt;line-height:1.25}}li{{margin:5px 0}}footer{{font-size:8pt;margin-top:9px}}a{{color:inherit}}.print-url{{display:inline}}}}
</style></head>
<body>
<a class="skip" href="#main">Skip to content</a>
<nav aria-label="Primary"><a href="./index.html">Home</a><a href="./portfolio_demo_v2.html">Cases</a><a href="./detector_interpretation.html">Methods</a><a href="./research_one_pager.html" aria-current="page">Research</a><a href="./assets/bizhallu_research_brief.pdf" download>Download PDF</a><a href="https://github.com/Yuchi-Wang02/bizhallu">GitHub</a></nav>
<main id="main">
<p class="eyebrow">Research brief · Exploratory project</p>
<h1>{esc(summary['title'])}</h1>
<p><a href="https://github.com/Yuchi-Wang02">Yuchi Wang</a> · MS student, Business Analytics and Artificial Intelligence<br>Johns Hopkins Carey Business School · Accounting and supply-management background</p>
<section><h2>Research problem</h2>
<p>Can we distinguish correctly copied data from a correct business relationship? BizHallu audits generated retail claims against transaction evidence. The current contribution is an inspectable workflow and a retrospective evaluation audit; an independent relation verifier remains proposed.</p>
<div class="case"><strong>A concrete example: April 2011</strong>
<p>Qwen assigns {esc(example['product_name'])} to rank {example['stated_rank']} at GBP {esc(example['amount_lexical'])}. The product and amount match source row {example['source_row']}, but the product ranks {example['rank_in_shown_evidence']} in the eight shown rows. Rank 3 belongs to {esc(example['expected_product_at_stated_rank'])} at GBP {esc(example['expected_amount_at_stated_rank'])}. <a href="./portfolio_demo_v2.html?case=q_0064">Inspect q_0064</a>.</p><p class="muted">Curated evidence check; not an independent verifier prediction or a population error rate.</p></div>
</section>
<div class="grid"><div>
<section><h2>Dataset and method</h2>
<p>UCI Online Retail; 100 questions across seven types; local Qwen3-0.6B answers; 205 AI-assisted provisional spans from 35 of 36 dev/test answers. Fifteen selected spans received additional assistant review. Independent human annotation and agreement remain pending.</p>
<p>Transaction evidence → questions → answers → pre-identified spans → token alignment → detector scores. Automatic extraction from new responses and whole-answer accuracy are outside the current evaluation.</p>
<p><strong>Evidence status.</strong> Labels come from an outcome-informed, error-enriched queue. Dev/test share periods and exact evidence-row payloads. Thresholds were fitted on dev, but headline signals were selected after test comparison: exploratory, not confirmatory.</p>
</section>
<section><h2>Research question and immediate pilot</h2>
<p class="question">{esc(research_questions[0])}</p>
<p><strong>Specific request:</strong> feedback on one relation schema and one worked case, to define a small calibration exercise with a second reviewer. No independent review is yet complete.</p>
<p>A proposed evidence-aware verifier would use the question, answer, metric contract and evidence, excluding gold answers and evaluation labels from prediction. Report extraction coverage, abstention and errors separately. The current review schema is label-derived, not that verifier.</p>
<p>The design must account for shared contexts and different information available to token-time uncertainty and completed-answer checks. Early list-marker scores do not establish confidence in the later relationship.</p>
</section>
<section><h2>Longer-term study design</h2>
<p>The 48-context / 96-question plan is estimation-focused, design-only and not execution-ready. Three of seven execution gates are complete. Confirmation remains sealed. <a href="./confirmation_set_v1_design.html">Protocol and remaining gates</a>.</p>
</section>
</div><div>
<section><h2>Historical B1 results</h2>
<table><caption>103 pre-identified test spans from 18 questions; provisional labels.</caption><thead><tr><th scope="col">Reference / signal</th><th scope="col">Test AP</th><th scope="col">Test F1</th></tr></thead><tbody>
<tr><td>Top-2 margin</td><td>{by_signal['one_minus_min_top2_margin']['average_precision']:.3f}</td><td>{by_signal['one_minus_min_top2_margin']['f1']:.3f}</td></tr>
<tr><td>Token entropy</td><td>{by_signal['mean_token_entropy']['average_precision']:.3f}</td><td>{by_signal['mean_token_entropy']['f1']:.3f}</td></tr>
<tr><td>Flag every span</td><td>{by_signal['all_positive']['average_precision']:.3f}</td><td>{by_signal['all_positive']['f1']:.3f}</td></tr>
</tbody></table>
<p>Entropy minus flag-every-span F1: {interval['point_difference']:+.4f}; exploratory paired question-bootstrap 95% interval [{interval['lower_95']:.4f}, {interval['upper_95']:.4f}] crosses zero. Shared periods and test-based selection limit inference.</p>
<p>AP is tied-score-aware. AP/F1 maxima come from different signals. The dev fact-type prior (F1 {by_signal['dev_fact_type_prior']['f1']:.3f}) is a composition control: supplied categories can reveal correctness.</p>
{b2_note_html()}
<p><a href="./detector_interpretation.html">Full methods, controls and source replay</a></p>
</section>
<section id="related-work"><h2>Related work and intended distinction</h2>
<ul class="related">{related_work_html}</ul>
<p class="muted">Related work only; none is an evaluated BizHallu baseline.</p>
</section>
</div></div>
<footer><p><strong>Contribution and provenance.</strong> Yuchi Wang directed the project with AI-assisted implementation and review across the workflow, provisional annotation, analysis and presentation. Independent human validation remains pending.</p><p><strong>Business scope.</strong> Negative transaction value is not verified physical returns; merchandise uses a code-based heuristic. No production readiness, realized savings or inventory optimization is established.</p><p>Research brief revised September 6, 2026 · <a href="https://github.com/Yuchi-Wang02">Author profile</a> · <a href="https://github.com/Yuchi-Wang02/bizhallu/blob/main/docs/reproducibility.md">Reproducibility guide</a><span class="print-url"> · yuchi-wang02.github.io/bizhallu</span></p></footer>
</main></body></html>
"""

    HTML_PATH.write_text(html_text, encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "html": repo_path(HTML_PATH)}, indent=2))


if __name__ == "__main__":
    main()
