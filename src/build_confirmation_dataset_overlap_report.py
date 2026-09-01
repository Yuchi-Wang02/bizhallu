from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_overlap_report.json"
HTML_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_overlap.html"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def integer(value: Any) -> str:
    return f"{int(value):,}"


def percent(value: Any) -> str:
    return f"{float(value) * 100:.2f}%"


def main() -> None:
    if not REPORT_PATH.exists():
        raise FileNotFoundError(f"Missing overlap report: {REPORT_PATH}")
    report = load_json(REPORT_PATH)
    profiles = report["dataset_profiles"]
    canonical = report["record_overlap"]["canonical_eight_field"]
    date_blind = report["record_overlap"]["date_blind_seven_field_sensitivity"]
    business_pattern = report["descriptive_similarity"]["business_pattern_five_field"]
    entities = report["descriptive_similarity"]["entity_overlap"]
    lineage = report["lineage_calibration"]["comparison"]

    comparison_rows = "\n".join(
        "<tr>"
        f"<td>{esc(label)}</td>"
        f"<td><code>{esc(fields)}</code></td>"
        f"<td class=\"num\">{integer(values['unique_fingerprint_overlap_count'])}</td>"
        f"<td class=\"num\">{integer(values['multiset_overlap_row_count'])}</td>"
        f"<td class=\"num\">{percent(values['left_multiset_overlap_rate'])}</td>"
        f"<td class=\"num\">{percent(values['right_multiset_overlap_rate'])}</td>"
        f"<td>{esc(meaning)}</td>"
        "</tr>"
        for label, fields, values, meaning in [
            (
                "Canonical record",
                "8 fields, including date",
                canonical,
                "Primary historical record-overlap gate",
            ),
            (
                "Date-blind record",
                "7 fields, excluding date",
                date_blind,
                "Sensitivity check against a date-only separation result",
            ),
            (
                "Business pattern",
                "product, description, quantity, price, country",
                business_pattern,
                "Descriptive continuity only; not record leakage",
            ),
        ]
    )

    entity_rows = "\n".join(
        "<tr>"
        f"<td><code>{esc(field)}</code></td>"
        f"<td class=\"num\">{integer(values['prior_distinct_count'])}</td>"
        f"<td class=\"num\">{integer(values['current_distinct_count'])}</td>"
        f"<td class=\"num\">{integer(values['shared_distinct_count'])}</td>"
        f"<td class=\"num\">{percent(values['prior_entity_coverage_rate'])}</td>"
        f"<td class=\"num\">{percent(values['current_entity_coverage_rate'])}</td>"
        "</tr>"
        for field, values in entities.items()
    )

    profile_rows = "\n".join(
        "<tr>"
        f"<td>{esc(label)}</td>"
        f"<td class=\"num\">{integer(values['row_count'])}</td>"
        f"<td class=\"num\">{integer(values['unique_fingerprint_count'])}</td>"
        f"<td class=\"num\">{integer(values['duplicate_extra_row_count'])}</td>"
        f"<td><code class=\"nowrap\">{esc(values['date_min'])}</code></td>"
        f"<td><code class=\"nowrap\">{esc(values['date_max'])}</code></td>"
        "</tr>"
        for label, values in [
            ("Strict prior window", profiles["strict_prior_window"]),
            ("Current Online Retail", profiles["current_online_retail"]),
            ("Online Retail II 2010-2011 sheet", profiles["online_retail_ii_2010_2011_sheet"]),
        ]
    )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BizHallu Historical Record-Overlap Proof</title>
  <style>
    :root {{ --ink:#191b1f; --muted:#626a73; --line:#d8dde3; --soft:#f4f6f8; --paper:#fff; --green:#14633f; --green-bg:#eef8f2; --amber:#825006; --amber-bg:#fff8e7; --blue:#075ea8; }}
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
    .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin-top:20px; }}
    .panel {{ min-width:0; padding:18px; border:1px solid var(--line); border-radius:7px; }}
    .panel p {{ color:var(--muted); }}
    .table-wrap {{ margin-top:18px; overflow-x:auto; border:1px solid var(--line); border-radius:7px; }}
    table {{ width:100%; min-width:820px; border-collapse:collapse; }}
    th,td {{ padding:11px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:13px; overflow-wrap:anywhere; }}
    th {{ color:#3e454d; background:var(--soft); font-size:11px; text-transform:uppercase; white-space:nowrap; overflow-wrap:normal; }}
    tr:last-child td {{ border-bottom:0; }}
    td.num {{ white-space:nowrap; font-variant-numeric:tabular-nums; }}
    code {{ padding:2px 5px; border-radius:4px; background:#eef1f4; font-family:"SFMono-Regular",Consolas,monospace; overflow-wrap:anywhere; word-break:break-word; }}
    code.nowrap {{ white-space:nowrap; overflow-wrap:normal; word-break:normal; }}
    ul {{ display:grid; gap:8px; padding-left:20px; }}
    footer {{ padding:34px 0 50px; color:var(--muted); font-size:13px; }}
    @media (max-width:860px) {{ nav div {{ display:none; }} .metrics,.grid {{ grid-template-columns:1fr 1fr; }} .metrics div {{ border-bottom:1px solid var(--line); }} }}
    @media (max-width:560px) {{ main,nav {{ width:min(100% - 24px,1180px); }} h1 {{ font-size:38px; }} h2 {{ font-size:26px; }} .metrics,.grid {{ grid-template-columns:1fr; }} .metrics div {{ border-right:0; }} }}
  </style>
</head>
<body>
  <header><nav><a href="./bizhallu_confirmation_set_v1_design.html"><strong>BizHallu</strong></a><div><a href="./bizhallu_confirmation_dataset_source_audit.html">Source audit</a><a href="./bizhallu_confirmation_dataset_quality.html">Quality profile</a><a href="./bizhallu_confirmation_set_v1_design.html">Study design</a></div></nav></header>
  <main>
    <section class="hero">
      <p class="eyebrow">Confirmation Set v1 · Historical overlap gate</p>
      <h1>The strict prior-period window contains zero repeated current-source records.</h1>
      <p class="lede">All 502,938 prior-period rows were normalized on eight canonical business fields and compared with all 541,909 current Online Retail rows as both unique fingerprints and multiplicity-aware multisets. A second, date-blind sensitivity test also found zero overlap.</p>
      <div class="metrics">
        <div><span>Canonical overlap rows</span><strong>{integer(canonical['multiset_overlap_row_count'])}</strong></div>
        <div><span>Date-blind overlap rows</span><strong>{integer(date_blind['multiset_overlap_row_count'])}</strong></div>
        <div><span>Boundary gap</span><strong>{esc(report['temporal_boundary']['boundary_gap_human'])}</strong></div>
        <div><span>Lineage positive control</span><strong>{integer(lineage['multiset_overlap_row_count'])} / {integer(profiles['current_online_retail']['row_count'])}</strong></div>
      </div>
      <div class="callout good"><strong>Historical overlap check complete.</strong> The strict window is unseen at the normalized record level under the frozen canonicalization.</div>
      <div class="callout"><strong>The dataset gate is still pending.</strong> This step does not prove 36-context feasibility, external independence, or confirmation performance.</div>
    </section>

    <section>
      <p class="eyebrow">Dataset and boundary</p>
      <h2>Two disjoint business periods, checked at source-row multiplicity.</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Dataset</th><th>Rows</th><th>Unique fingerprints</th><th>Duplicate extras</th><th>Minimum date</th><th>Maximum date</th></tr></thead>
        <tbody>{profile_rows}</tbody>
      </table></div>
      <p>The final prior transaction occurs at <code>{esc(report['temporal_boundary']['strict_prior_max'])}</code>; the current source begins at <code>{esc(report['temporal_boundary']['current_min'])}</code>. The gap is {esc(report['temporal_boundary']['boundary_gap_human'])}.</p>
    </section>

    <section>
      <p class="eyebrow">Three deliberately separate comparisons</p>
      <h2>Record identity is not the same as business similarity.</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Comparison</th><th>Fields</th><th>Shared unique</th><th>Shared rows</th><th>Prior row rate</th><th>Current row rate</th><th>Interpretation</th></tr></thead>
        <tbody>{comparison_rows}</tbody>
      </table></div>
      <div class="callout"><strong>Why report the 195,814 shared business patterns?</strong> The same retailer naturally repeats products, quantities, prices, and countries across years. Publishing this continuity prevents a zero-record-overlap result from being misread as company, entity, or domain independence.</div>
    </section>

    <section>
      <p class="eyebrow">Normalization and fingerprinting</p>
      <h2>The primary result does not depend on raw spreadsheet formatting.</h2>
      <div class="grid">
        <article class="panel"><h3>Canonical record</h3><p>Invoice, stock code, normalized description, quantity, timestamp, six-place unit price, nullable customer ID, and country.</p></article>
        <article class="panel"><h3>Date-blind sensitivity</h3><p>The same comparison without timestamp. Its zero overlap shows the primary finding is not produced only by the frozen date cutoff.</p></article>
        <article class="panel"><h3>Multiplicity-aware</h3><p>Overlap rows use the minimum count of each fingerprint in both sources. Duplicate copies cannot disappear behind a set comparison.</p></article>
        <article class="panel"><h3>Private row evidence</h3><p>Length-prefixed, domain-separated SHA-256 fingerprints are recomputed locally. Public artifacts expose only aggregate counts and whole-inventory manifest hashes.</p></article>
      </div>
    </section>

    <section>
      <p class="eyebrow">Lineage positive control</p>
      <h2>The method recovers the known current-source lineage.</h2>
      <p>The current 541,909-row workbook is a complete multiset subset of the 541,910-row Online Retail II 2010-2011 sheet. The sheet has exactly one additional source row; duplicate-extra counts are identical at 5,268.</p>
      <div class="metrics">
        <div><span>Current rows recovered</span><strong>{integer(lineage['multiset_overlap_row_count'])}</strong></div>
        <div><span>Current-only rows</span><strong>{integer(lineage['left_only_row_count'])}</strong></div>
        <div><span>II sheet-only rows</span><strong>{integer(lineage['right_only_row_count'])}</strong></div>
        <div><span>II coverage</span><strong>{percent(lineage['right_multiset_overlap_rate'])}</strong></div>
      </div>
      <p>This is a calibration check for normalization, not evidence of external replication.</p>
    </section>

    <section>
      <p class="eyebrow">Same-retailer continuity</p>
      <h2>Products, customers, and countries overlap even though source records do not.</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Entity field</th><th>Prior distinct</th><th>Current distinct</th><th>Shared distinct</th><th>Prior coverage</th><th>Current coverage</th></tr></thead>
        <tbody>{entity_rows}</tbody>
      </table></div>
      <div class="callout"><strong>Claim limit:</strong> zero record overlap supports a temporal internal replication only. It does not establish a new retailer, independent entity population, different source lineage, or unseen business domain.</div>
    </section>

    <section>
      <p class="eyebrow">Research boundary</p>
      <h2>This proof advances one gate and creates no experiment result.</h2>
      <ul>
        <li>No evidence contexts, questions, split assignments, prompts, or model outputs were generated.</li>
        <li>No annotation, verifier, detector, AUPRC, F1, or other confirmation metric was created or changed.</li>
        <li>Public artifacts contain no invoice values, customer values, or row fingerprint values.</li>
        <li>The next authorized step is only the outcome-blind feasibility check for at least 36 disjoint evidence contexts.</li>
      </ul>
    </section>

    <footer>BizHallu Historical Record-Overlap Proof · Aggregate-only public evidence · Confirmation Set v1 remains design-only and not execution-ready.</footer>
  </main>
</body>
</html>
"""
    HTML_PATH.write_text(html_text, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "confirmation_dataset_overlap_html_built",
                "report_status": report["status"],
                "html_path": repo_path(HTML_PATH),
            },
            indent=2,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
