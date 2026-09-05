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
        "How should amount fidelity and entity-rank-value correctness be annotated without repeated counting?",
        "How should token-time uncertainty and completed-answer verification be compared under different information budgets?",
        "What sample and independent-review design supports uncertainty estimates under shared evidence contexts?",
    ]

    method_steps = [
        "Clean UCI Online Retail transactions into auditable business evidence tables.",
        "Generate deterministic business questions and gold answers across seven retail analytics question types.",
        "Run local Qwen3-0.6B generations and preserve token-level probability, entropy, margin, and energy-style traces.",
        "Build AI-assisted provisional business-fact span labels and align pre-identified spans to generated tokens.",
        "Select thresholds on dev spans, then compare candidate-signal metrics on the test spans as an exploratory analysis.",
    ]

    key_findings = [
        f"The exploratory maximum test AUPRC is {metric(best_auprc['test_auprc'])} from {best_auprc['baseline']}.",
        f"The exploratory maximum test F1 is {metric(best_f1['test_f1'])} from {best_f1['baseline']}; it is a different signal.",
        "Top-3 product questions expose the most presentation-friendly failure mode: the model can use real values while assigning them to the wrong rank or product.",
        "Internal uncertainty has signal, but confident wrong evidence binding remains hard; this motivates a comparison with explicit evidence-aware verification.",
    ]

    jhu_extensions = [
        "Healthcare analytics: audit whether AI-generated utilization, cost, or quality summaries are grounded in source tables.",
        "Operations analytics: verify product-performance, return-impact, and revenue-exposure claims before they influence prioritization decisions.",
        "Responsible AI governance: turn evidence-grounding checks into an audit layer for business decision-support tools.",
        "Capstone direction: compare internal-state signals, literature-grounded baselines, and evidence-aware verifiers on business claims.",
    ]

    research_tracks = [
        "Internal uncertainty: entropy, top-2 margin, and energy-style probability-mass signals already used in this project.",
        "Literature-grounded baselines: Semantic Entropy, TOHA, and entity-level hallucination detection as future comparison candidates.",
        "Evidence-aware verification: future independent claim-evidence decisions against structured source rows and deterministic gold answers; the current v0 is only a label-derived review schema.",
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
        "next_stage_scope": "English evidence-grounded presentation and assistant review; independent human review deferred, not claimed; no model execution or confirmation evaluation",
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

    from presentation_evidence import statistical_context, walkthrough, METRIC_NOTE, b2_context, b2_note_html
    stats = statistical_context()
    by_signal = {row['signal']: row for row in stats['test_rows']}
    interval = stats['entropy_minus_all_positive']
    demo_data = load_json(REPORTS_DIR / 'bizhallu_demo_v2_data.json')
    example = walkthrough(next(c for c in demo_data['cases'] if c['question_id']=='q_0064'))['claims'][2]
    summary['presentation_revision'] = 'english_evidence_review_2026_09_05'
    summary['statistical_review'] = stats
    summary['b2_sensitivity'] = b2_context()
    summary['independent_human_annotation'] = False
    summary['share_status'] = 'exploratory_project_for_method_feedback'
    html_text = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(summary['title'])}</title>
<style>
*{{box-sizing:border-box;letter-spacing:0}}body{{margin:0;background:#f6f7f9;color:#202124;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}}main,nav{{max-width:940px;margin:auto;padding:22px 28px}}nav{{display:flex;gap:18px;flex-wrap:wrap;border-bottom:1px solid #d9dee1}}a{{color:#155e75}}h1{{font-size:27px;line-height:1.22;margin:8px 0 12px}}h2{{font-size:17px;margin:17px 0 7px}}p{{margin:7px 0}}section{{padding:5px 0 12px;border-bottom:1px solid #d9dee1}}.eyebrow,.muted{{color:#58616a}}.eyebrow{{font-size:12px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}.case{{border-left:3px solid #1a7560;padding-left:14px}}table{{width:100%;border-collapse:collapse;font-size:13px}}td,th{{border-bottom:1px solid #d9dee1;padding:7px;text-align:left}}li{{margin:5px 0}}h1,p,li,td,th{{overflow-wrap:anywhere}}footer{{margin-top:14px;font-size:12px;color:#58616a}}@media(max-width:650px){{.grid{{grid-template-columns:1fr;gap:0}}main,nav{{padding:16px}}}}@page{{size:A4;margin:12mm}}@media print{{body{{background:white;font-size:10pt;line-height:1.32}}nav{{display:none}}main{{max-width:none;padding:0}}h1{{font-size:20pt}}h2{{font-size:12pt}}section{{break-inside:avoid}}a{{color:inherit}}}}
</style></head>
<body>
<nav aria-label="Project"><a href="./portfolio_demo_v2.html">Cases</a><a href="./detector_interpretation.html">Methods</a><a href="https://github.com/Yuchi-Wang02/bizhallu">GitHub</a></nav>
<main>
<p class="eyebrow">Professor / research advisor one-pager · Exploratory project</p>
<h1>{esc(summary['title'])}</h1>
<p>Yuchi Wang · Accounting and supply-management background · JHU Carey BAAI</p>
<section><h2>Research problem</h2>
<p>Can we distinguish correctly copied data from a correct business relationship? BizHallu studies evidence binding in LLM-generated retail analysis. Its contribution at this stage is an auditable experimental workflow and inspectable failure cases, not a validated production detector.</p>
<div class="case"><strong>A concrete example: April 2011</strong>
<p>Qwen assigns {esc(example['product_name'])} to rank {example['stated_rank']} at GBP {esc(example['amount_lexical'])}. The product and amount match source row {example['source_row']}, but the product ranks {example['rank_in_shown_evidence']} in the eight shown rows. Rank 3 belongs to {esc(example['expected_product_at_stated_rank'])} at GBP {esc(example['expected_amount_at_stated_rank'])}. <a href="./portfolio_demo_v2.html?case=q_0064">Inspect q_0064</a>.</p></div>
</section>
<div class="grid">
<section><h2>Dataset and method</h2>
<p>UCI Online Retail; 100 deterministic questions across seven task types; local Qwen3-0.6B answers; 205 AI-assisted provisional spans across 35 dev/test answers. Fifteen selected spans received additional assistant review. No independent human agreement has been measured.</p>
<p>Transaction evidence → questions → answers → pre-identified spans → token alignment → detector scores. Thresholds were fitted on dev; candidate signals were compared on test. The quoted maxima therefore remain exploratory, not confirmatory.</p>
<p>Negative transaction value is not verified physical returns. Product analysis uses a merchandise-code heuristic; metric scope and historical field meanings are documented separately.</p>
</section>
<section><h2>Historical B1 results</h2>
<table><thead><tr><th>Reference / signal</th><th>Test AP</th><th>Test F1</th></tr></thead><tbody>
<tr><td>Top-2 margin</td><td>{by_signal['one_minus_min_top2_margin']['average_precision']:.3f}</td><td>{by_signal['one_minus_min_top2_margin']['f1']:.3f}</td></tr>
<tr><td>Token entropy</td><td>{by_signal['mean_token_entropy']['average_precision']:.3f}</td><td>{by_signal['mean_token_entropy']['f1']:.3f}</td></tr>
<tr><td>Flag every span</td><td>{by_signal['all_positive']['average_precision']:.3f}</td><td>{by_signal['all_positive']['f1']:.3f}</td></tr>
</tbody></table>
<p>103 test spans from all 18 test questions. Entropy's F1 difference from flag-every-span is {interval['point_difference']:+.4f}; the exploratory paired question-bootstrap interval [{interval['lower_95']:.4f}, {interval['upper_95']:.4f}] crosses zero. No stable superiority claim follows.</p>
<p>AP uses tied-score-aware average precision. A dev fact-type prior has F1 {by_signal['dev_fact_type_prior']['f1']:.3f}, but annotation-derived types can contain correctness hints: this is a composition control, not a fair automatic detector competitor.</p>
{b2_note_html()}
</section></div>
<section><h2>Three questions for collaboration</h2>
<ol><li>How should amount fidelity and full entity-rank-value correctness be annotated without counting one binding error several times?</li><li>How should token-time uncertainty and completed-answer verification be compared when their available information differs?</li><li>What sample and independent review design would support useful uncertainty estimates under shared evidence contexts?</li></ol>
<p><strong>Specific request:</strong> feedback on the relation annotation unit and comparison design, plus a small calibration exercise with a second reviewer. Professor or career-facing discussion need not wait for a publication-scale benchmark.</p>
</section>
<section><h2>Limits and next comparisons</h2>
<p>The historical labels are provisional and the queue was outcome-informed. Dev/test share periods and evidence. q_0048 was absent from original dev labels and is now included only in separate B2 sensitivity. Low uncertainty on an early list marker cannot establish confidence about the following full relationship.</p>
<p>A future evidence-aware verifier must predict without gold or evaluation labels. Semantic Entropy remains a multi-generation consistency candidate; TOHA and entity probes need compatibility review. Adjacent-step Spilled Energy requires a formula/index audit: same-step energy gap is NLL, not an independent method.</p>
<p>A 48-context / 96-question, estimation-focused next study is prepared but not executed. Confirmation remains sealed. <a href="./confirmation_set_v1_design.html">Study design</a> · <a href="./detector_interpretation.html#statistical-review">Statistical review</a>.</p>
</section>
<footer>English presentation revision: September 5, 2026. Assistant-reviewed presentation, not new annotations or model results. Prepared for method feedback and academic discussion.</footer>
</main></body></html>
"""

    HTML_PATH.write_text(html_text, encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "html": repo_path(HTML_PATH)}, indent=2))


if __name__ == "__main__":
    main()
