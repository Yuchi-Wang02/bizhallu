from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REVIEW_CONFIG_PATH = PROJECT_ROOT / "configs" / "confirmation_precision_review_v1.json"
REVIEW_REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_precision_review_report.json"
AMENDMENT_PATH = PROJECT_ROOT / "configs" / "confirmation_precision_scope_amendment_v1.json"
CAPACITY_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_context_feasibility_report.json"
HTML_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_precision_review.html"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def integer(value: Any) -> str:
    return f"{int(value):,}"


def decimal(value: Any, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"


def main() -> None:
    required = [REVIEW_CONFIG_PATH, REVIEW_REPORT_PATH, AMENDMENT_PATH, CAPACITY_PATH]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing precision-review artifacts: {missing}")

    config = load_json(REVIEW_CONFIG_PATH)
    report = load_json(REVIEW_REPORT_PATH)
    amendment = load_json(AMENDMENT_PATH)
    capacity = load_json(CAPACITY_PATH)
    summaries = report["candidate_summaries"]
    selected = amendment["revised_planning_counts"]
    decision = config["decision_policy"]

    candidate_rows = []
    for row in summaries:
        candidate_rows.append(
            "<tr>"
            f"<td class=\"num\">{integer(row['confirmation_context_count'])}</td>"
            f"<td class=\"num\">{integer(row['confirmation_contexts_per_family'])}</td>"
            f"<td class=\"num\">{integer(row['source_period_reserve'])}</td>"
            f"<td class=\"num\">{integer(row['central_preferred_scenario_count'])}/{integer(row['central_scenario_count'])}</td>"
            f"<td class=\"num\">{decimal(row['central_median_of_median_auprc_half_widths'])}</td>"
            f"<td class=\"num\">{decimal(row['central_worst_median_auprc_half_width'])}</td>"
            f"<td class=\"num\">{decimal(row['central_worst_median_paired_difference_half_width'])}</td>"
            f"<td><span class=\"badge {'pass' if row['candidate_pass'] else 'blocked'}\">{'pass' if row['candidate_pass'] else 'did not pass'}</span></td>"
            "</tr>"
        )

    literature_rows = []
    for source in config["literature_context"]:
        literature_rows.append(
            "<li>"
            f"<a href=\"{esc(source['url'])}\"><strong>{esc(source['title'])}</strong></a>: "
            f"{esc(source['relevance'])}"
            "</li>"
        )

    capacity_proof = capacity["capacity_proof"]
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BizHallu Outcome-Blind Precision Review</title>
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
    h1 {{ max-width:1020px; margin:0; font-size:48px; line-height:1.08; letter-spacing:0; }}
    h2 {{ margin:0 0 12px; font-size:30px; line-height:1.2; letter-spacing:0; }}
    h3 {{ margin:0 0 8px; font-size:18px; letter-spacing:0; }}
    p {{ margin:7px 0; }}
    .lede {{ max-width:940px; margin-top:18px; color:var(--muted); font-size:19px; }}
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
    table {{ width:100%; min-width:940px; border-collapse:collapse; }}
    th,td {{ padding:11px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:13px; overflow-wrap:anywhere; }}
    th {{ color:#3e454d; background:var(--soft); font-size:11px; text-transform:uppercase; white-space:nowrap; overflow-wrap:normal; }}
    tr:last-child td {{ border-bottom:0; }}
    td.num {{ white-space:nowrap; font-variant-numeric:tabular-nums; }}
    code {{ padding:2px 5px; border-radius:4px; background:#eef1f4; font-family:"SFMono-Regular",Consolas,monospace; overflow-wrap:anywhere; word-break:break-word; }}
    .badge {{ display:inline-block; padding:3px 7px; border-radius:4px; font-size:11px; font-weight:800; text-transform:uppercase; white-space:nowrap; }}
    .badge.pass {{ color:var(--green); background:var(--green-bg); }}
    .badge.blocked {{ color:var(--red); background:var(--red-bg); }}
    ul,ol {{ display:grid; gap:8px; padding-left:20px; }}
    footer {{ padding:34px 0 50px; color:var(--muted); font-size:13px; }}
    @media (max-width:860px) {{ nav div {{ display:none; }} .metrics {{ grid-template-columns:1fr 1fr; }} .grid {{ grid-template-columns:1fr; }} .metrics div {{ border-bottom:1px solid var(--line); }} }}
    @media (max-width:560px) {{ main,nav {{ width:min(100% - 24px,1180px); }} h1 {{ font-size:38px; }} h2 {{ font-size:26px; }} .metrics {{ grid-template-columns:1fr; }} .metrics div {{ border-right:0; }} }}
  </style>
</head>
<body>
  <header><nav><a href="./bizhallu_confirmation_set_v1_design.html"><strong>BizHallu</strong></a><div><a href="./bizhallu_confirmation_context_feasibility.html">Capacity proof</a><a href="./bizhallu_confirmation_set_v1_design.html">Study design</a><a href="../README.md">Repository guide</a></div></nav></header>
  <main>
    <section class="hero">
      <p class="eyebrow">Confirmation Set v1 · Outcome-blind precision review</p>
      <h1>The 15-context comparison plan was too fragile, so the claim was narrowed instead of the thresholds.</h1>
      <p class="lede">Synthetic clustered scenarios were fixed before the formal run. No candidate met every strong-comparison rule. BizHallu therefore preserves the failed review, increases the sealed confirmation plan to 27 balanced contexts, and limits the study to estimation with uncertainty rather than a detector-superiority claim.</p>
      <div class="metrics">
        <div><span>Strong-design candidates passed</span><strong>0 of {integer(len(summaries))}</strong></div>
        <div><span>Revised confirmation contexts</span><strong>{integer(selected['confirmation_context_count'])}</strong></div>
        <div><span>Total period-disjoint contexts</span><strong>{integer(selected['total_context_count'])}</strong></div>
        <div><span>Unassigned source periods</span><strong>{integer(selected['unassigned_source_period_reserve'])}</strong></div>
      </div>
      <div class="callout blocked"><strong>The original precision gate did not pass.</strong> Its thresholds were not relaxed, its random seed was not replaced, and the result was not rewritten as a success.</div>
      <div class="callout good"><strong>A narrower study remains feasible.</strong> The revised 6/15/27 plan has an independently recomputed {integer(capacity_proof['maximum_slot_matching_count'])}/{integer(capacity_proof['required_slot_count'])} aggregate matching, with no period assignment retained.</div>
    </section>

    <section>
      <p class="eyebrow">What was simulated</p>
      <h2>Design sensitivity, not detector performance.</h2>
      <div class="grid">
        <article class="panel"><h3>Outcome-blind inputs</h3><p>Only synthetic prevalence, spans per context, label ICC, score separation, and aggregate source capacity were used. Confirmation periods, labels, answers, and detector outcomes do not exist.</p></article>
        <article class="panel"><h3>Independent unit</h3><p>Whole synthetic evidence contexts were resampled together. Both detector scores used the same resampled context indices for the paired comparison.</p></article>
        <article class="panel"><h3>Unequal cluster sizes</h3><p>Each scenario used a fixed multiplier pattern around 8 or 12 mean spans per context. Stress scenarios lowered density and increased within-context label correlation.</p></article>
      </div>
      <div class="callout"><strong>Interpretation boundary.</strong> Interval half-widths below are Monte Carlo planning summaries. They are not observed AUPRC, F1, prevalence, power, or model-quality results.</div>
    </section>

    <section>
      <p class="eyebrow">Frozen decision rules</p>
      <h2>No candidate satisfied the complete strong-comparison gate.</h2>
      <p>A preferred central scenario required median AUPRC half-width at most {decimal(decision['preferred_scenario_max_median_auprc_half_width'],2)} and median paired-difference half-width at most {decimal(decision['preferred_scenario_max_median_paired_difference_half_width'],2)}. A design needed at least {decimal(decision['minimum_preferred_central_scenario_share'] * 100,0)}% preferred central scenarios plus the frozen worst-case central limits.</p>
      <div class="table-wrap"><table>
        <thead><tr><th>Confirmation contexts</th><th>Per family</th><th>Source reserve</th><th>Preferred central</th><th>Median AUPRC half-width</th><th>Worst central AUPRC half-width</th><th>Worst paired half-width</th><th>Strong gate</th></tr></thead>
        <tbody>{''.join(candidate_rows)}</tbody>
      </table></div>
      <p>The 27-context candidate came closest, but passed only 10 of 16 preferred central scenarios and had a worst central median AUPRC half-width of {decimal(amendment['failed_strong_comparison_design']['best_capacity_feasible_candidate']['central_worst_median_auprc_half_width'],6)}, just above the frozen 0.12 limit.</p>
    </section>

    <section>
      <p class="eyebrow">Scope amendment</p>
      <h2>Estimate transparently; do not declare a winner.</h2>
      <div class="grid">
        <article class="panel"><h3>Primary objective</h3><p>{esc(amendment['scope_amendment']['primary_objective'])}</p></article>
        <article class="panel"><h3>Paired comparison</h3><p>{esc(amendment['scope_amendment']['paired_difference_role'])}</p></article>
        <article class="panel"><h3>Subgroups</h3><p>{esc(amendment['scope_amendment']['subgroup_policy'])}</p></article>
      </div>
      <div class="callout blocked"><strong>Prohibited claim.</strong> {esc(amendment['scope_amendment']['prohibited_primary_claim'])}</div>
      <ul>
        <li>Protocol pilot: {integer(selected['protocol_pilot_context_count'])} contexts / {integer(selected['protocol_pilot_question_count'])} questions.</li>
        <li>Development: {integer(selected['development_context_count'])} contexts / {integer(selected['development_question_count'])} questions.</li>
        <li>Sealed confirmation: {integer(selected['confirmation_context_count'])} contexts / {integer(selected['confirmation_question_count'])} questions.</li>
        <li>Total: {integer(selected['total_context_count'])} contexts / {integer(selected['total_question_count'])} questions, with {integer(selected['confirmation_contexts_per_family'])} confirmation contexts per allowed family.</li>
      </ul>
    </section>

    <section>
      <p class="eyebrow">Statistical caution</p>
      <h2>Twenty-seven clusters improve precision, but do not make this publication-grade.</h2>
      <p>{esc(config['future_interval_policy']['small_cluster_caveat'])}</p>
      <p>The future sealed analysis plans {integer(config['future_interval_policy']['planned_bootstrap_replicates'])} context-level bootstrap replicates, a BCa interval when leave-one-context-out estimates are defined, and a paired percentile interval as sensitivity analysis. This method still requires implementation and validation on non-confirmation data.</p>
      <ul>{''.join(literature_rows)}</ul>
    </section>

    <section>
      <p class="eyebrow">Next gate</p>
      <h2>Only the context manifest and seeded split may come next.</h2>
      <ol>
        <li>Freeze a deterministic, auditable context-selection procedure before retaining any period.</li>
        <li>Create the 6/15/27 manifest and seeded split once, then verify period and evidence-fingerprint disjointness.</li>
        <li>Keep product, country, invoice, customer, and period details local; publish only aggregate proof.</li>
        <li>Do not generate questions, prompts, Qwen outputs, annotations, detector scores, or confirmation metrics in that step.</li>
      </ol>
      <div class="callout"><strong>Current boundary.</strong> No context manifest, split assignment, question, prompt, model output, label, detector score, or new empirical metric exists.</div>
    </section>
    <footer>BizHallu Confirmation Set v1 · Outcome-blind precision review and scope amendment · Generated from committed machine-readable artifacts.</footer>
  </main>
</body>
</html>
"""
    HTML_PATH.write_text(html_text, encoding="utf-8")
    print(f"Wrote {HTML_PATH}")


if __name__ == "__main__":
    main()
