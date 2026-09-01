from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = PROJECT_ROOT / "configs" / "confirmation_set_v1_protocol.json"
METHODOLOGY_SUMMARY_PATH = PROJECT_ROOT / "reports" / "bizhallu_methodology_hardening_summary.json"
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

    sampling = protocol["sampling_plan"]
    gates = protocol["execution_gates"]
    pending_gates = [item["gate"] for item in gates if item["status"] != "complete"]
    options = protocol["dataset_strategy"]["options"]
    families = protocol["question_design"]["candidate_families"]

    summary = {
        "status": "confirmation_set_v1_design_ready",
        "execution_ready": protocol["execution_ready"],
        "no_new_results": protocol["no_new_results"],
        "protocol_path": repo_path(PROTOCOL_PATH),
        "html_path": repo_path(HTML_PATH),
        "study_role": protocol["study_role"],
        "dataset_selection_status": protocol["dataset_strategy"]["selection_status"],
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
        "recommended_next_decision": "Select and audit the dataset source before creating any new prompt or generation file.",
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
        f"<article class=\"panel\"><h3>{esc(item['family'])}</h3><p>{esc(item['business_value'])}</p></article>"
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
      h1 {{ max-width:920px; margin:0; font-size:clamp(40px,6vw,68px); line-height:1.02; letter-spacing:0; }}
      h2 {{ margin:0; font-size:clamp(28px,4vw,40px); line-height:1.12; letter-spacing:0; }}
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
      @media (max-width:820px) {{ nav {{ display:none; }} .status,.grid {{ grid-template-columns:1fr; }} }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <a class="brand" href="./bizhallu_methodology_hardening.html">BizHallu</a>
      <nav><a href="./bizhallu_methodology_hardening.html">Current audit</a><a href="./bizhallu_research_one_pager.html">Research one-pager</a></nav>
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
        <div class="callout"><strong>Not execution-ready.</strong> No dataset option has been selected, no context manifest has been frozen, no new model output has been generated, and no Confirmation Set v1 performance result exists.</div>
      </section>

      <section>
        <p class="eyebrow">Why this exists</p>
        <h2>Correct the current study's selection and split limits prospectively.</h2>
        <div class="grid">
          <article class="panel"><h3>Outcome-blind sampling</h3><p>All contexts and question IDs are selected before generation. Answers are never retained, dropped, or rebalanced because they look correct, incorrect, easy, or difficult.</p></article>
          <article class="panel"><h3>Context-separated evaluation</h3><p>Every new-study split uses disjoint periods and evidence fingerprints, and exact historical full100 evidence fingerprints are excluded. Assignment happens at <code>evidence_context_id</code>, not row position.</p></article>
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
        <div class="callout good"><strong>Recommended near-term decision.</strong> Use the existing Online Retail lineage only for a prospectively sampled internal replication. A broader generalization claim still requires the second-public-dataset arm.</div>
      </section>

      <section>
        <p class="eyebrow">Sampling architecture</p>
        <h2>72 generations, but only 60 enter the main study.</h2>
        <div class="status">
          <div><span>Protocol pilot</span><strong>12</strong></div>
          <div><span>Development</span><strong>30</strong></div>
          <div><span>Confirmation</span><strong>30</strong></div>
          <div><span>Main total</span><strong>60</strong></div>
        </div>
        <ul>
          <li>The 12-question protocol pilot validates schemas and runtime and is permanently excluded from confirmation metrics.</li>
          <li>Development data freezes thresholds, extraction settings, verifier rules, and any hybrid combination.</li>
          <li>The 30-question confirmation split is evaluated once after all decisions are frozen.</li>
          <li>Natural correct/error prevalence is reported; no 50/50 balancing is imposed after generation.</li>
          <li>The 15 development and 15 confirmation contexts are minimum planning targets. An outcome-blind precision review may increase them before generation.</li>
        </ul>
      </section>

      <section>
        <p class="eyebrow">Candidate business tasks</p>
        <h2>Keep accounting and supply-management relevance visible.</h2>
        <div class="grid">{family_panels}</div>
        <p>These are candidate families, not frozen templates. Source feasibility, deterministic gold calculations, and evidence-table construction must pass before they become part of the context manifest.</p>
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
          <li>Uncertainty intervals use a cluster bootstrap by <code>evidence_context_id</code>, not an independent-span bootstrap.</li>
          <li><code>contradicted</code> and <code>unmatched</code> are positive unsupported claims; unresolved <code>needs_review</code> items are counted and excluded only after an adjudication attempt.</li>
          <li>Context counts must pass the pending outcome-blind precision review before the context manifest is frozen.</li>
          <li><code>one_minus_min_top2_margin</code> is a frozen candidate because of the exploratory study, not because it is already confirmed.</li>
          <li>Semantic Entropy, TOHA, and entity-level detection remain academic candidates, but inclusion and implementation must be frozen before the pilot.</li>
        </ul>
      </section>

      <section>
        <p class="eyebrow">Execution gates</p>
        <h2>Every gate is intentionally pending.</h2>
        <div class="table-wrap"><table>
          <thead><tr><th>#</th><th>Gate</th><th>Status</th></tr></thead>
          <tbody>{gate_rows}</tbody>
        </table></div>
        <div class="callout"><strong>Next authorized action.</strong> Select and audit the dataset source, then complete the outcome-blind precision review before freezing the context manifest. Do not create prompts, run Qwen, annotate outputs, or implement confirmation metrics before those decisions are recorded.</div>
      </section>

      <section>
        <p class="eyebrow">Historical boundary</p>
        <h2>The current 0.835 / 0.779 values remain exploratory context.</h2>
        <p>The existing numbers are not Confirmation Set v1 baselines or targets. This design introduces no new detector metric and does not retroactively upgrade the current evidence level.</p>
      </section>
    </main>
    <footer><main>Generated from <code>configs/confirmation_set_v1_protocol.json</code>. Status: design ready, execution blocked by seven explicit gates.</main></footer>
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
