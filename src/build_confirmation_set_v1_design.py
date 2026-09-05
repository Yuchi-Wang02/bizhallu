from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = PROJECT_ROOT / "configs" / "confirmation_set_v1_protocol.json"
METHODOLOGY_SUMMARY_PATH = PROJECT_ROOT / "reports" / "bizhallu_methodology_hardening_summary.json"
DATASET_AUDIT_SUMMARY_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_source_audit_summary.json"
CONTEXT_FEASIBILITY_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility_report.json"
PRECISION_REVIEW_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_precision_review_report.json"
CONTEXT_MANIFEST_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_manifest_report.json"
QUESTION_DESIGN_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_question_design_report.json"
REPORTS_DIR = PROJECT_ROOT / "reports"
HTML_PATH = REPORTS_DIR / "bizhallu_confirmation_set_v1_design.html"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_confirmation_set_v1_design_summary.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_list(items: list[Any]) -> str:
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    protocol = load_json(PROTOCOL_PATH)
    methodology = load_json(METHODOLOGY_SUMMARY_PATH)
    dataset_audit = load_json(DATASET_AUDIT_SUMMARY_PATH)
    feasibility = load_json(CONTEXT_FEASIBILITY_PATH)
    precision_review = load_json(PRECISION_REVIEW_PATH)
    context_manifest = load_json(CONTEXT_MANIFEST_PATH)
    question_design = load_json(QUESTION_DESIGN_PATH)
    active_definition = protocol.get("active_business_definition", {})
    amendment_notice = ""
    if active_definition:
        amendment_notice = (
            '<div class="callout"><strong>Active business-definition amendment: v1.1.</strong> '
            'Positive and negative transaction value include eligible non-merchandise lines; '
            'negative value is not a measure of confirmed physical returns. The same 48 contexts, '
            'split and 96 numeric/entity gold answers are preserved. Legacy v1 fields below are '
            'historical provenance; future inputs must follow active_business_definition in the protocol. '
            'Gate 3 has been revalidated; no model run is authorized.</div>'
        )

    sampling = protocol["sampling_plan"]
    gates = protocol["execution_gates"]
    pending_gates = [item["gate"] for item in gates if item["status"] != "complete"]
    options = protocol["dataset_strategy"]["options"]
    families = protocol["question_design"]["candidate_families"]

    summary = {
        "status": "confirmation_set_v1_design_ready",
        "execution_ready": protocol["execution_ready"],
        "no_new_results": protocol["no_new_results"],
        "active_business_definition": active_definition,
        "protocol_path": repo_path(PROTOCOL_PATH),
        "html_path": repo_path(HTML_PATH),
        "study_role": protocol["study_role"],
        "dataset_selection_status": protocol["dataset_strategy"]["selection_status"],
        "dataset_source_audit_path": repo_path(DATASET_AUDIT_SUMMARY_PATH),
        "selected_candidate_id": dataset_audit["selected_candidate_id"],
        "selected_candidate_role": dataset_audit["selected_candidate_role"],
        "dataset_gate_status": dataset_audit["dataset_gate_status"],
        "dataset_acquisition_verified": dataset_audit["acquisition_verified"],
        "dataset_structure_profile_complete": dataset_audit["structure_profile_complete"],
        "dataset_quality_profile_complete": dataset_audit["quality_profile_complete"],
        "dataset_historical_overlap_check_complete": dataset_audit["historical_overlap_check_complete"],
        "dataset_context_feasibility_check_complete": dataset_audit["context_feasibility_check_complete"],
        "dataset_local_profile_complete": dataset_audit["local_profile_complete"],
        "strict_window_row_count": dataset_audit["strict_window_row_count"],
        "metadata_header_drift_detected": dataset_audit["metadata_header_drift_detected"],
        "dataset_quality_decision": dataset_audit["quality_decision"],
        "strict_window_missing_description_rows": dataset_audit["missing_description_rows"],
        "strict_window_missing_customer_id_rows": dataset_audit["missing_customer_id_rows"],
        "strict_window_normalized_exact_duplicate_extra_rows": dataset_audit["normalized_exact_duplicate_extra_rows"],
        "strict_window_valid_net_revenue_line_count": dataset_audit["valid_net_revenue_line_count"],
        "strict_window_net_revenue_gbp": dataset_audit["net_revenue_gbp"],
        "canonical_record_overlap_row_count": dataset_audit["canonical_record_overlap_row_count"],
        "date_blind_record_overlap_row_count": dataset_audit["date_blind_record_overlap_row_count"],
        "business_pattern_overlap_row_count": dataset_audit["business_pattern_overlap_row_count"],
        "context_feasibility_report_path": repo_path(CONTEXT_FEASIBILITY_PATH),
        "complete_calendar_week_count": feasibility["source_capacity"]["complete_calendar_period_count"],
        "observed_complete_week_count": feasibility["source_capacity"]["observed_complete_period_count"],
        "required_context_count": feasibility["capacity_proof"]["required_total_context_count"],
        "maximum_slot_matching_count": feasibility["capacity_proof"]["maximum_slot_matching_count"],
        "minimum_hall_capacity_slack": feasibility["capacity_proof"]["minimum_hall_capacity_slack"],
        "precision_review_report_path": repo_path(PRECISION_REVIEW_PATH),
        "precision_review_original_status": precision_review["status"],
        "precision_scope_amendment_status": "complete_with_scope_downgrade",
        "context_manifest_report_path": repo_path(CONTEXT_MANIFEST_PATH),
        "context_manifest_status": context_manifest["status"],
        "context_manifest_created": context_manifest["execution_boundary"]["context_manifest_created"],
        "split_assignment_created": context_manifest["execution_boundary"]["split_assignment_created"],
        "context_manifest_commitment_sha256": context_manifest["private_manifest_commitment"]["canonical_sha256"],
        "selected_context_count": context_manifest["frozen_inventory"]["selected_context_count"],
        "reserve_period_count": context_manifest["frozen_inventory"]["reserve_period_count"],
        "question_design_report_path": repo_path(QUESTION_DESIGN_PATH),
        "question_design_status": question_design["status"],
        "question_design_config_path": question_design["config"]["path"],
        "question_design_commitment_sha256": question_design["private_question_manifest_commitment"]["canonical_sha256"],
        "question_count_frozen": question_design["frozen_inventory"]["question_count"],
        "question_template_count": len(question_design["frozen_inventory"]["template_counts"]),
        "question_payload_fingerprint_check_pending": False,
        "question_payload_fingerprint_check_complete": question_design["evidence_payload_integrity"]["question_level_evidence_payload_fingerprint_check"] == "complete",
        "question_payload_cross_split_overlap_count": question_design["evidence_payload_integrity"]["cross_split_fingerprint_count"],
        "question_evidence_content_fingerprint_count": question_design["evidence_payload_integrity"]["unique_content_fingerprint_count"],
        "question_evidence_content_cross_split_overlap_count": question_design["evidence_payload_integrity"]["content_cross_split_fingerprint_count"],
        "historical_unique_evidence_content_fingerprint_count": question_design["evidence_payload_integrity"]["historical_full100_content_fingerprint_count"],
        "question_evidence_content_historical_overlap_count": question_design["evidence_payload_integrity"]["historical_full100_content_fingerprint_overlap_count"],
        "selected_reconciliation_positive_cancel_flagged_row_count": question_design["gold_calculation_integrity"]["selected_reconciliation_positive_cancel_flagged_row_count"],
        "selected_product_return_ratio_percentage_range": question_design["gold_calculation_integrity"]["selected_product_return_ratio_percentage_range"],
        "selected_product_return_ratio_over_100_count": question_design["gold_calculation_integrity"]["selected_product_return_ratio_over_100_count"],
        "country_gold_position_counts": question_design["selection_integrity"]["country_gold_position_counts"],
        "country_candidate_tables_accidentally_fully_descending": question_design["selection_integrity"]["country_candidate_tables_accidentally_fully_descending"],
        "dataset_option_count": len(options),
        "candidate_question_family_count": len(families),
        "protocol_pilot_question_count": sampling["protocol_pilot"]["question_count"],
        "development_question_count": sampling["development"]["question_count"],
        "confirmation_question_count": sampling["confirmation"]["question_count"],
        "main_question_count": sampling["main_question_count"],
        "total_generation_target_including_pilot": sampling["total_generation_target_including_pilot"],
        "counts_are_minimum_targets_pending_precision_review": sampling["counts_are_minimum_targets_pending_precision_review"],
        "precision_review_status": protocol["precision_review"]["status"],
        "historical_evidence_fingerprint_exclusion": protocol["context_split_policy"]["historical_exploratory_evidence_fingerprint_exclusion"],
        "primary_metric": protocol["metric_policy"]["primary_metric"],
        "bootstrap_unit": "evidence_context_id",
        "reviewer_count": protocol["annotation_protocol"]["reviewer_count"],
        "claim_inventory_policy": "exhaustive_business_fact_claim_inventory",
        "binary_positive_statuses": ["contradicted", "unmatched"],
        "evaluation_track_count": len(protocol["evaluation_tracks"]),
        "pending_gate_count": len(pending_gates),
        "pending_gates": pending_gates,
        "current_study_classification": methodology["study_classification"],
        "current_share_status": methodology["share_status"],
        "historical_exploratory_max_test_auprc": methodology["locked_public_results"]["exploratory_max_test_auprc"],
        "historical_exploratory_max_test_f1": methodology["locked_public_results"]["exploratory_max_test_f1"],
        "recommended_next_decision": "Freeze the model revision, tokenizer revision, prompt template, decoding settings, detector-family inclusion decisions, and metric implementations before protocol-pilot generation. The 48 contexts and 96 deterministic question/gold payloads are frozen; four later gates remain pending.",
        "num_failures": 0,
        "failures": [],
    }

    dataset_rows = "\n".join(
        f"""
        <tr>
          <td><strong>{esc(option['option_id'])}</strong><span>{esc(option['role'])}</span></td>
          <td>{esc(option['source'])}</td>
          <td>{render_list(option['advantages'])}</td>
          <td>{render_list(option['limitations'])}</td>
        </tr>
        """.strip()
        for option in options
    )
    gate_rows = "".join(
        f"<tr><td>{index}</td><td><code>{esc(item['gate'])}</code></td><td>{esc(item['status'])}</td></tr>"
        for index, item in enumerate(gates, start=1)
    )
    family_panels = "".join(
        f"<article class=\"panel\"><h3>{esc(item['family'])}</h3>"
        f"<p><strong>{esc(item['source_feasibility_status'])}</strong></p>"
        f"<p>{esc(item['business_value'])}</p>"
        + (f"<p>{esc(item['reason'])}</p>" if item.get("reason") else "")
        + "</article>"
        for item in families
    )

    html_text = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BizHallu Confirmation Set v1 Design</title>
    <style>
      :root {{ --bg:#f5f6f8; --surface:#fff; --ink:#1d1d1f; --muted:#5f6368; --line:#d7dce2; --blue:#075ea8; --green:#11694d; --amber:#8a5700; }}
      * {{ box-sizing:border-box; }}
      body {{ margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif; line-height:1.55; }}
      a {{ color:var(--blue); text-decoration:none; }}
      .topbar {{ min-height:60px; padding:0 28px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid var(--line); background:rgba(255,255,255,.95); position:sticky; top:0; z-index:5; }}
      .brand {{ color:var(--ink); font-weight:850; }}
      nav {{ display:flex; gap:16px; font-size:14px; font-weight:750; }}
      main {{ width:min(1120px,calc(100% - 36px)); margin:0 auto; }}
      section {{ padding:46px 0; border-bottom:1px solid var(--line); }}
      .hero {{ padding-top:66px; }}
      .eyebrow {{ margin:0 0 10px; color:var(--blue); font-size:12px; font-weight:850; text-transform:uppercase; }}
      h1 {{ max-width:920px; margin:0; font-size:56px; line-height:1.02; letter-spacing:0; }}
      h2 {{ margin:0; font-size:38px; line-height:1.12; letter-spacing:0; }}
      h3 {{ margin:0; font-size:19px; line-height:1.25; letter-spacing:0; }}
      p, li, th, td {{ overflow-wrap:anywhere; }}
      .lede {{ max-width:900px; margin:20px 0 0; color:var(--muted); font-size:20px; }}
      .status {{ margin-top:28px; padding:18px 0; border-top:1px solid var(--line); border-bottom:1px solid var(--line); display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:18px; }}
      .status span {{ display:block; color:var(--muted); font-size:12px; font-weight:850; text-transform:uppercase; }}
      .status strong {{ display:block; margin-top:6px; font-size:24px; }}
      .callout {{ margin-top:22px; padding:20px; border-left:4px solid var(--amber); background:#fff9ed; }}
      .callout.good {{ border-left-color:var(--green); background:#f3fbf7; }}
      .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin-top:22px; }}
      .panel {{ min-width:0; padding:22px; border:1px solid var(--line); border-radius:8px; background:var(--surface); }}
      .panel h3 {{ overflow-wrap:anywhere; }}
      .panel p, li, td span {{ color:var(--muted); }}
      .table-wrap {{ width:100%; margin-top:22px; overflow-x:auto; border:1px solid var(--line); background:var(--surface); }}
      table {{ width:100%; min-width:820px; border-collapse:collapse; font-size:14px; }}
      th, td {{ padding:14px; text-align:left; vertical-align:top; border-right:1px solid var(--line); border-bottom:1px solid var(--line); }}
      th {{ background:#eef1f4; font-size:12px; text-transform:uppercase; }}
      th:last-child, td:last-child {{ border-right:0; }}
      tr:last-child td {{ border-bottom:0; }}
      td span {{ display:block; margin-top:5px; font-size:12px; }}
      ul, ol {{ display:grid; gap:9px; padding-left:22px; }}
      code {{ padding:2px 5px; border-radius:4px; background:#eef1f4; font-family:"SFMono-Regular",Consolas,monospace; overflow-wrap:anywhere; word-break:break-word; }}
      footer {{ padding:32px 0 48px; color:var(--muted); }}
      @media (max-width:820px) {{ nav {{ display:none; }} .status,.grid {{ grid-template-columns:1fr; }} h1 {{ font-size:40px; }} h2 {{ font-size:30px; }} }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <a class="brand" href="./bizhallu_methodology_hardening.html">BizHallu</a>
      <nav><a href="./bizhallu_methodology_hardening.html">Current audit</a><a href="./bizhallu_confirmation_dataset_source_audit.html">Source audit</a><a href="./bizhallu_confirmation_dataset_quality.html">Quality profile</a><a href="./bizhallu_confirmation_dataset_overlap.html">Overlap proof</a><a href="./bizhallu_confirmation_context_feasibility.html">Capacity proof</a><a href="./bizhallu_confirmation_precision_review.html">Precision review</a><a href="./bizhallu_confirmation_context_manifest.html">Manifest freeze</a><a href="./bizhallu_research_one_pager.html">Research one-pager</a></nav>
    </header>
    <main>
      <section class="hero">
        <p class="eyebrow">Prospective protocol design</p>
        <h1>Confirmation Set v1 starts before the model answers.</h1>
        <p class="lede">This design replaces answer-driven sampling with a frozen context manifest, independent human review, sealed confirmation labels, and separate evaluations for claim extraction and evidence verification.</p>
        <div class="status">
          <div><span>Current state</span><strong>Design only</strong></div>
          <div><span>Main questions</span><strong>{sampling['main_question_count']}</strong></div>
          <div><span>Human reviewers</span><strong>{protocol['annotation_protocol']['reviewer_count']}</strong></div>
          <div><span>Execution gates</span><strong>{len(pending_gates)} pending</strong></div>
        </div>
        <div class="callout"><strong>Not execution-ready.</strong> The source, context-manifest, and question-design gates are complete. Private, Git-ignored manifests now fix 48 complete-week contexts, the 6/15/27 split, and 96 deterministic questions with gold answers and evidence payloads. Prompts, model outputs, labels, detector scores, and Confirmation Set v1 metrics do not exist yet.</div>
        {amendment_notice}
      </section>

      <section>
        <p class="eyebrow">Why this exists</p>
        <h2>Correct the current study's selection and split limits prospectively.</h2>
        <div class="grid">
          <article class="panel"><h3>Outcome-blind sampling</h3><p>All contexts and question IDs are selected before generation. Answers are never retained, dropped, or rebalanced because they look correct, incorrect, easy, or difficult.</p></article>
          <article class="panel"><h3>Context-separated evaluation</h3><p>The frozen manifest uses one unique complete week per context across every family and split. All 96 full payloads and all 96 normalized evidence-table contents have unique fingerprints, with zero cross-split overlap. The wrapper-independent content comparison matches 0 of 66 unique historical full100 evidence contents.</p></article>
          <article class="panel"><h3>Independent labels</h3><p>Two human reviewers annotate every in-scope business-fact claim without detector scores or each other's labels. Agreement is reported before adjudication.</p></article>
          <article class="panel"><h3>Sealed research decisions</h3><p>Detector families, thresholds, extraction logic, verifier rules, prompts, and analysis code are frozen before confirmation-label access.</p></article>
        </div>
      </section>

      <section>
        <p class="eyebrow">Dataset decision</p>
        <h2>Use a staged path instead of overstating one dataset.</h2>
        <p>{esc(protocol['dataset_strategy']['recommended_sequence'])}</p>
        <div class="table-wrap"><table>
          <thead><tr><th>Option</th><th>Source and role</th><th>Advantages</th><th>Limitations</th></tr></thead>
          <tbody>{dataset_rows}</tbody>
        </table></div>
        <div class="callout good"><strong>Near-term source decision.</strong> The strict window is conditionally suitable for aggregate business analysis after exact-duplicate, description, customer-coverage, cancellation, and value controls. Zero historical record overlap and 48-slot aggregate capacity are verified across three allowed families. The precision review rejected a superiority design and retained an estimation-only scope. The 48-context manifest and 6/15/27 split are now frozen. Customer concentration remains blocked, and a broader claim still requires the second-public-dataset arm. <a href="./bizhallu_confirmation_dataset_source_audit.html">Read the source audit.</a> <a href="./bizhallu_confirmation_dataset_quality.html">Read the quality profile.</a> <a href="./bizhallu_confirmation_dataset_overlap.html">Read the overlap proof.</a> <a href="./bizhallu_confirmation_context_feasibility.html">Read the capacity proof.</a> <a href="./bizhallu_confirmation_precision_review.html">Read the precision review.</a> <a href="./bizhallu_confirmation_context_manifest.html">Read the manifest commitment.</a></div>
      </section>

      <section>
        <p class="eyebrow">Sampling architecture</p>
        <h2>{sampling['total_generation_target_including_pilot']} generations, but only {sampling['main_question_count']} enter the main study.</h2>
        <div class="status">
          <div><span>Protocol pilot</span><strong>{sampling['protocol_pilot']['question_count']}</strong></div>
          <div><span>Development</span><strong>{sampling['development']['question_count']}</strong></div>
          <div><span>Confirmation</span><strong>{sampling['confirmation']['question_count']}</strong></div>
          <div><span>Main total</span><strong>{sampling['main_question_count']}</strong></div>
        </div>
        <ul>
          <li>The 12-question protocol pilot validates schemas and runtime and is permanently excluded from confirmation metrics.</li>
          <li>Development data freezes thresholds, extraction settings, verifier rules, and any hybrid combination.</li>
          <li>The {sampling['confirmation']['question_count']}-question confirmation split is evaluated once after all decisions are frozen.</li>
          <li>Natural correct/error prevalence is reported; no 50/50 balancing is imposed after generation.</li>
          <li>The outcome-blind review increased sealed confirmation from 15 to 27 contexts. The study estimates detector performance with intervals and does not preregister a superiority claim.</li>
        </ul>
      </section>

      <section>
        <p class="eyebrow">Candidate business tasks</p>
        <h2>Keep accounting and supply-management relevance visible.</h2>
        <div class="grid">{family_panels}</div>
        <p>Three families pass source-capacity checks; customer concentration is blocked by the pre-existing Customer ID coverage rule. Six templates now create two deterministic questions per context: weekly reconciliation and cancellation hotspot, two disjoint product-return comparisons, or two country-product exposure questions. Gold calculations and evidence payload fingerprints are frozen before prompt generation.</p>
        <div class="callout"><strong>Pre-generation diagnostics.</strong> One selected reconciliation row has a cancellation invoice prefix but positive quantity and revenue; the sign-based formula retains it in gross positive line revenue and does not call it a negative reduction. One of 64 selected product evidence rows has a recorded return-to-positive-sales unit ratio above 100% (maximum 156.25%). It is retained because same-week negative units are not linked to their original sales; this metric is a recorded ratio, not a causal return rate. Hash ordering places the correct country-product candidate across positions 1-5, and one of 32 candidate tables happens to be fully revenue-descending by chance. The ordering algorithm never reads the gold rank.</div>
      </section>

      <section>
        <p class="eyebrow">Evaluation architecture</p>
        <h2>Do not hide oracle spans inside an end-to-end claim.</h2>
        <div class="grid">
          <article class="panel"><h3>1. Oracle-span diagnostics</h3><p>Compare frozen internal, literature-grounded, evidence-aware, and optional hybrid families on adjudicated spans.</p></article>
          <article class="panel"><h3>2. Claim extraction</h3><p>Measure exact and overlap span precision, recall, F1, and fact-type classification separately.</p></article>
          <article class="panel"><h3>3. Evidence verification</h3><p>Produce independent statuses, a continuous unsupported-risk score, abstentions, and matched evidence references. Gold labels cannot be used as predictions.</p></article>
          <article class="panel"><h3>4. End-to-end audit</h3><p>Combine extraction and verification, then report missed claims, abstentions, and business-fact errors.</p></article>
        </div>
      </section>

      <section>
        <p class="eyebrow">Metric freeze</p>
        <h2>AUPRC is primary; uncertainty is clustered by context.</h2>
        <ul>
          <li>Primary oracle-span metric: <strong>{esc(protocol['metric_policy']['primary_metric'])}</strong>.</li>
          <li>Secondary F1 reuses a development-frozen threshold; precision, recall, specificity, AUROC, coverage, and abstention are reported.</li>
          <li>Uncertainty uses context-level BCa bootstrap when defined, with a paired percentile context bootstrap as sensitivity; independent-span bootstrap is prohibited.</li>
          <li><code>contradicted</code> and <code>unmatched</code> are positive unsupported claims; unresolved <code>needs_review</code> items are counted and excluded only after an adjudication attempt.</li>
          <li>The precision review is complete with a scope downgrade: report estimates and intervals, but do not declare a detector family statistically superior.</li>
          <li><code>one_minus_min_top2_margin</code> is a frozen candidate because of the exploratory study, not because it is already confirmed.</li>
          <li>Semantic Entropy, TOHA, and entity-level detection remain academic candidates, but inclusion and implementation must be frozen before the pilot.</li>
        </ul>
      </section>

      <section>
        <p class="eyebrow">Execution gates</p>
        <h2>{len(gates) - len(pending_gates)} gates are complete; {len(pending_gates)} remain pending.</h2>
        <div class="table-wrap"><table>
          <thead><tr><th>#</th><th>Gate</th><th>Status</th></tr></thead>
          <tbody>{gate_rows}</tbody>
        </table></div>
        <div class="callout"><strong>Next authorized action.</strong> Freeze the model revision, tokenizer revision, prompt template, decoding settings, detector-family feasibility decisions, and metric implementations. Do not run Qwen, annotate outputs, score detectors, or report new metrics yet.</div>
      </section>

      <section>
        <p class="eyebrow">Historical boundary</p>
        <h2>The current 0.835 / 0.779 values remain exploratory context.</h2>
        <p>The existing numbers are not Confirmation Set v1 baselines or targets. This design introduces no new detector metric and does not retroactively upgrade the current evidence level.</p>
      </section>
    </main>
    <footer><main>Generated from <code>configs/confirmation_set_v1_protocol.json</code>. Status: design ready, {len(gates) - len(pending_gates)} gates complete, execution blocked by {len(pending_gates)} pending gates.</main></footer>
  </body>
</html>
"""

    HTML_PATH.write_text(html_text, encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "execution_ready": summary["execution_ready"],
                "pending_gate_count": summary["pending_gate_count"],
                "html_path": summary["html_path"],
                "summary_path": repo_path(SUMMARY_PATH),
            },
            indent=2,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
