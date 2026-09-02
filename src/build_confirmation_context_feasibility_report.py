from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility_report.json"
CONFIG_PATH = PROJECT_ROOT / "configs" / "confirmation_context_feasibility_v1.json"
MANIFEST_REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_manifest_report.json"
HTML_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility.html"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def integer(value: Any) -> str:
    return f"{int(value):,}"


def number(value: Any) -> str:
    value = float(value)
    return f"{value:,.1f}" if not value.is_integer() else f"{int(value):,}"


def main() -> None:
    for path in [REPORT_PATH, CONFIG_PATH, MANIFEST_REPORT_PATH]:
        if not path.exists():
            raise FileNotFoundError(f"Missing context-feasibility artifact: {path}")
    report = load_json(REPORT_PATH)
    config = load_json(CONFIG_PATH)
    manifest = load_json(MANIFEST_REPORT_PATH)

    source = report["source_capacity"]
    capacity = report["capacity_proof"]
    frozen_inventory = manifest["frozen_inventory"]
    family_capacity = report["family_capacity"]
    support = source["support_distributions"]
    family_configs = {item["family"]: item for item in config["family_eligibility"]}

    family_labels = {
        "net_revenue_reconciliation_by_period": "Net-revenue reconciliation",
        "product_return_rate_comparison": "Product return comparison",
        "country_product_exposure": "Country-product exposure",
        "customer_revenue_concentration": "Customer concentration",
    }
    family_rows = []
    for family, values in family_capacity.items():
        family_config = family_configs[family]
        if family == "customer_revenue_concentration":
            family_rows.append(
                "<tr>"
                f"<td><strong>{esc(family_labels[family])}</strong><code>{esc(family)}</code></td>"
                "<td><span class=\"badge blocked\">blocked</span></td>"
                "<td class=\"num\">0</td><td class=\"num\">0</td><td class=\"num\">0</td>"
                f"<td>{esc(family_config['reason'])}</td>"
                "</tr>"
            )
            continue
        family_rows.append(
            "<tr>"
            f"<td><strong>{esc(family_labels[family])}</strong><code>{esc(family)}</code></td>"
            "<td><span class=\"badge pass\">source-feasible</span></td>"
            f"<td class=\"num\">{integer(values['eligible_period_count'])}</td>"
            f"<td class=\"num\">{integer(values['required_period_count'])}</td>"
            f"<td class=\"num\">+{integer(values['capacity_slack'])}</td>"
            f"<td>{esc(family_config.get('claim_limit', family_config.get('interpretation', '')))}</td>"
            "</tr>"
        )

    hall_rows = []
    for check in capacity["generalized_hall_checks"]:
        labels = " + ".join(family_labels[family] for family in check["family_subset"])
        hall_rows.append(
            "<tr>"
            f"<td>{esc(labels)}</td>"
            f"<td class=\"num\">{integer(check['available_unique_period_count'])}</td>"
            f"<td class=\"num\">{integer(check['required_unique_period_count'])}</td>"
            f"<td class=\"num\">+{integer(check['capacity_slack'])}</td>"
            "<td><span class=\"badge pass\">pass</span></td>"
            "</tr>"
        )

    support_rows = []
    support_labels = {
        "source_rows_per_observed_complete_period": "Source rows",
        "valid_net_revenue_lines_per_observed_complete_period": "Valid net-revenue lines",
        "cancellation_or_return_rows_per_observed_complete_period": "Cancellation or return rows",
        "eligible_products_per_observed_complete_period": "Eligible products",
        "eligible_countries_per_observed_complete_period": "Eligible countries",
    }
    for key, label in support_labels.items():
        values = support[key]
        support_rows.append(
            "<tr>"
            f"<td>{esc(label)}</td>"
            f"<td class=\"num\">{number(values['minimum'])}</td>"
            f"<td class=\"num\">{number(values['median'])}</td>"
            f"<td class=\"num\">{number(values['maximum'])}</td>"
            "</tr>"
        )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BizHallu Outcome-Blind Context Capacity Proof</title>
  <style>
    :root {{ --ink:#191b1f; --muted:#626a73; --line:#d8dde3; --soft:#f4f6f8; --paper:#fff; --green:#14633f; --green-bg:#eef8f2; --amber:#825006; --amber-bg:#fff8e7; --red:#8a2f2a; --red-bg:#fff1ef; --blue:#075ea8; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--paper); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; line-height:1.55; letter-spacing:0; }}
    a {{ color:var(--blue); text-decoration:none; }}
    header {{ border-bottom:1px solid var(--line); background:#fbfbfc; }}
    nav {{ width:min(1180px,calc(100% - 40px)); min-height:60px; margin:0 auto; display:flex; align-items:center; justify-content:space-between; gap:24px; }}
    nav strong {{ color:var(--ink); font-size:15px; }}
    nav div {{ display:flex; gap:17px; font-size:13px; font-weight:700; }}
    main {{ width:min(1180px,calc(100% - 40px)); margin:0 auto; }}
    section {{ padding:44px 0; border-bottom:1px solid var(--line); }}
    .hero {{ padding:64px 0 48px; }}
    .eyebrow {{ margin:0 0 10px; color:var(--green); font-size:12px; font-weight:800; text-transform:uppercase; }}
    h1 {{ max-width:980px; margin:0; font-size:48px; line-height:1.08; letter-spacing:0; }}
    h2 {{ margin:0 0 12px; font-size:30px; line-height:1.2; letter-spacing:0; }}
    h3 {{ margin:0 0 8px; font-size:18px; letter-spacing:0; }}
    p {{ margin:7px 0; }}
    .lede {{ max-width:920px; margin-top:18px; color:var(--muted); font-size:19px; }}
    .metrics {{ margin-top:28px; display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); border:1px solid var(--line); border-radius:7px; overflow:hidden; }}
    .metrics div {{ min-width:0; padding:16px; border-right:1px solid var(--line); background:#fff; }}
    .metrics div:last-child {{ border-right:0; }}
    .metrics span {{ display:block; color:var(--muted); font-size:11px; font-weight:800; text-transform:uppercase; }}
    .metrics strong {{ display:block; margin-top:5px; font-size:22px; overflow-wrap:anywhere; }}
    .callout {{ margin-top:20px; padding:16px 18px; border-left:4px solid var(--amber); background:var(--amber-bg); }}
    .callout.good {{ border-color:var(--green); background:var(--green-bg); }}
    .callout.blocked {{ border-color:var(--red); background:var(--red-bg); }}
    .grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; margin-top:20px; }}
    .panel {{ min-width:0; padding:18px; border:1px solid var(--line); border-radius:7px; }}
    .panel p {{ color:var(--muted); }}
    .table-wrap {{ margin-top:18px; overflow-x:auto; border:1px solid var(--line); border-radius:7px; }}
    table {{ width:100%; min-width:820px; border-collapse:collapse; }}
    th,td {{ padding:11px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:13px; overflow-wrap:anywhere; }}
    th {{ color:#3e454d; background:var(--soft); font-size:11px; text-transform:uppercase; white-space:nowrap; overflow-wrap:normal; }}
    tr:last-child td {{ border-bottom:0; }}
    td.num {{ white-space:nowrap; font-variant-numeric:tabular-nums; }}
    td code {{ display:block; margin-top:4px; }}
    code {{ padding:2px 5px; border-radius:4px; background:#eef1f4; font-family:"SFMono-Regular",Consolas,monospace; overflow-wrap:anywhere; word-break:break-word; }}
    .badge {{ display:inline-block; padding:3px 7px; border-radius:4px; font-size:11px; font-weight:800; text-transform:uppercase; white-space:nowrap; }}
    .badge.pass {{ color:var(--green); background:var(--green-bg); }}
    .badge.blocked {{ color:var(--red); background:var(--red-bg); }}
    ul {{ display:grid; gap:8px; padding-left:20px; }}
    footer {{ padding:34px 0 50px; color:var(--muted); font-size:13px; }}
    @media (max-width:860px) {{ nav div {{ display:none; }} .metrics {{ grid-template-columns:1fr 1fr; }} .grid {{ grid-template-columns:1fr; }} .metrics div {{ border-bottom:1px solid var(--line); }} }}
    @media (max-width:560px) {{ main,nav {{ width:min(100% - 24px,1180px); }} h1 {{ font-size:38px; }} h2 {{ font-size:26px; }} .metrics {{ grid-template-columns:1fr; }} .metrics div {{ border-right:0; }} }}
  </style>
</head>
<body>
  <header><nav><a href="./bizhallu_confirmation_set_v1_design.html"><strong>BizHallu</strong></a><div><a href="./bizhallu_confirmation_dataset_quality.html">Quality profile</a><a href="./bizhallu_confirmation_dataset_overlap.html">Overlap proof</a><a href="./bizhallu_confirmation_precision_review.html">Precision review</a><a href="./bizhallu_confirmation_context_manifest.html">Context manifest</a><a href="./bizhallu_confirmation_set_v1_design.html">Study design</a></div></nav></header>
  <main>
    <section class="hero">
      <p class="eyebrow">Confirmation Set v1 · Outcome-blind source capacity</p>
      <h1>The source can support {integer(capacity['required_total_context_count'])} period-disjoint contexts without looking at model outcomes.</h1>
      <p class="lede">Complete Monday-through-Sunday weeks were evaluated under frozen data-quality and business-support rules. At this historical capacity checkpoint, no week was selected, no split was assigned, and no context manifest was created.</p>
      <div class="metrics">
        <div><span>Observed complete weeks</span><strong>{integer(source['observed_complete_period_count'])}</strong></div>
        <div><span>Required context slots</span><strong>{integer(capacity['required_slot_count'])}</strong></div>
        <div><span>Maximum matching</span><strong>{integer(capacity['maximum_slot_matching_count'])}/{integer(capacity['required_slot_count'])}</strong></div>
        <div><span>Eligible families</span><strong>3 of 4</strong></div>
      </div>
      <div class="callout good"><strong>Capacity proof complete.</strong> Three allowed families each have 50 eligible periods for {integer(capacity['required_contexts_per_eligible_family'])} required slots, and the minimum Hall-capacity slack is +{integer(capacity['minimum_hall_capacity_slack'])}.</div>
      <div class="callout"><strong>Checkpoint versus current state.</strong> The capacity proof and precision review preceded selection. A subsequent outcome-blind freeze now fixes {integer(frozen_inventory['selected_context_count'])} contexts and the {integer(frozen_inventory['split_counts']['protocol_pilot'])}/{integer(frozen_inventory['split_counts']['development'])}/{integer(frozen_inventory['split_counts']['confirmation'])} split. Question templates, prompts, model outputs, new labels, detector scores, and confirmation results still do not exist.</div>
    </section>

    <section>
      <p class="eyebrow">Frozen context grain</p>
      <h2>One complete calendar week can serve at most one final family.</h2>
      <div class="grid">
        <article class="panel"><h3>Calendar-defined periods</h3><p>Only complete Monday-through-Sunday weeks inside the strict prior window are counted. Partial boundary weeks are excluded before eligibility is measured.</p></article>
        <article class="panel"><h3>Stronger separation</h3><p>A final period may be assigned to one family only. Context periods would therefore be disjoint across all contexts, not merely across development and confirmation.</p></article>
        <article class="panel"><h3>No assignment at this checkpoint</h3><p>The capacity calculation discarded its period-to-slot matching. A later, separately committed procedure performed the one-time manifest freeze.</p></article>
      </div>
      <div class="metrics">
        <div><span>Complete calendar weeks</span><strong>{integer(source['complete_calendar_period_count'])}</strong></div>
        <div><span>Weeks with source rows</span><strong>{integer(source['observed_complete_period_count'])}</strong></div>
        <div><span>Empty complete weeks</span><strong>{integer(source['empty_complete_period_count'])}</strong></div>
        <div><span>Boundary rows excluded</span><strong>{integer(source['excluded_boundary_source_row_count'])}</strong></div>
      </div>
      <p>{integer(source['complete_period_source_row_count'])} complete-period rows plus {integer(source['excluded_boundary_source_row_count'])} excluded boundary rows reconcile to the 502,938-row strict source.</p>
    </section>

    <section>
      <p class="eyebrow">Source support</p>
      <h2>Even the least-supported observed week clears the frozen family rules.</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Weekly support measure</th><th>Minimum</th><th>Median</th><th>Maximum</th></tr></thead>
        <tbody>{''.join(support_rows)}</tbody>
      </table></div>
      <p>Support statistics describe source capacity, not answer difficulty, correctness prevalence, or detector performance.</p>
    </section>

    <section>
      <p class="eyebrow">Family decision</p>
      <h2>Three families advance; customer concentration stays blocked.</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Question family</th><th>Status</th><th>Eligible periods</th><th>Required</th><th>Slack</th><th>Interpretation or block reason</th></tr></thead>
        <tbody>{''.join(family_rows)}</tbody>
      </table></div>
      <div class="callout blocked"><strong>No complete-case shortcut.</strong> The source has {integer(family_capacity['customer_revenue_concentration']['missing_customer_id_rows'])} rows without Customer ID. The pre-existing source audit blocks customer-level questions, so this profile does not invent a denominator after seeing capacity.</div>
      <div class="callout"><strong>Return metric limit.</strong> Product support uses a recorded return-to-positive-sales unit ratio within the same week. It is not an original-sale-linked or causal customer return rate; question wording and metric precision still require the pending review.</div>
    </section>

    <section>
      <p class="eyebrow">Capacity proof</p>
      <h2>Every family subset has enough unique periods.</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Family subset</th><th>Available unique periods</th><th>Required unique periods</th><th>Slack</th><th>Result</th></tr></thead>
        <tbody>{''.join(hall_rows)}</tbody>
      </table></div>
      <p>The independent maximum matching fills all {integer(capacity['required_slot_count'])} slots: 2 pilot, 5 development, and 9 confirmation contexts per eligible family. At this capacity checkpoint, the assignment itself was neither retained nor published.</p>
    </section>

    <section>
      <p class="eyebrow">Evidence and privacy boundary</p>
      <h2>The capacity checkpoint exposed no candidate or selected period.</h2>
      <ul>
        <li>Exact-duplicate copies are excluded by the frozen analytical evidence flags.</li>
        <li>Complete calendar periods are row-disjoint; a source row belongs to only one period.</li>
        <li>Historical canonical and date-blind overlap with the exploratory source remain zero.</li>
        <li>The public report contains no candidate period list, invoice, customer, product, country candidate, row fingerprint, selected context ID, or split assignment.</li>
        <li>The local period profile remains Git-ignored and contains no matching assignment from this capacity calculation.</li>
      </ul>
      <div class="callout"><strong>Claim limit:</strong> this proves source capacity for a same-retailer temporal internal replication. It does not validate question wording, establish independent labels, estimate confirmation performance, or support external-generalization claims.</div>
    </section>

    <section>
      <p class="eyebrow">Subsequent gate</p>
      <h2>The authorized manifest freeze is complete.</h2>
      <p>The <a href="./bizhallu_confirmation_precision_review.html">outcome-blind precision review</a> rejected the stronger comparison design and revised the plan to 6 pilot, 15 development, and 27 confirmation contexts. The later <a href="./bizhallu_confirmation_context_manifest.html">manifest gate</a> froze exactly that allocation without inspecting model outcomes.</p>
      <ul>
        <li>No question, prompt, Qwen output, annotation target, verifier prediction, detector score, AUPRC, or F1 was created by either checkpoint.</li>
        <li>Two protocol gates are complete and the five downstream execution gates remain pending.</li>
        <li>The next gate is limited to deterministic question templates, gold calculations, and question-level evidence fingerprints.</li>
        <li>A later external dataset is still required for cross-company or cross-domain claims.</li>
      </ul>
    </section>
    <footer>BizHallu Outcome-Blind Context Capacity Proof · Historical capacity checkpoint with a linked current manifest state · No experiment result.</footer>
  </main>
</body>
</html>
"""
    HTML_PATH.write_text(html_text, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "confirmation_context_feasibility_html_built",
                "report_status": report["status"],
                "html_path": "reports/bizhallu_confirmation_context_feasibility.html",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
