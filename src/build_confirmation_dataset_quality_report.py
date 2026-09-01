from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUALITY_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_quality_report.json"
HTML_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_quality.html"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def integer(value: Any) -> str:
    return f"{int(value):,}"


def money(value: Any) -> str:
    return f"GBP {float(value):,.2f}"


def percent(rate: Any) -> str:
    return f"{float(rate) * 100:.2f}%"


def main() -> None:
    if not QUALITY_PATH.exists():
        raise FileNotFoundError(f"Missing quality report: {QUALITY_PATH}")
    report = load_json(QUALITY_PATH)
    completeness = report["completeness"]["by_column"]
    duplicates = report["duplicates_and_grain"]
    business = report["business_rules"]
    reconciliation = report["analysis_policy_reconciliation"]
    monthly = report["monthly_coverage"]["months"]

    completeness_rows = "\n".join(
        "<tr>"
        f"<td><code>{esc(column)}</code></td>"
        f"<td>{integer(values['null_count'])}</td>"
        f"<td>{integer(values['blank_count'])}</td>"
        f"<td>{integer(values['missing_or_blank_count'])}</td>"
        f"<td>{percent(values['missing_or_blank_rate'])}</td>"
        "</tr>"
        for column, values in completeness.items()
    )

    duplicate_rows = "\n".join(
        "<tr>"
        f"<td>{esc(label)}</td>"
        f"<td>{integer(values['duplicate_extra_rows'])}</td>"
        f"<td>{percent(values['duplicate_extra_row_rate'])}</td>"
        f"<td>{integer(values['duplicate_affected_rows'])}</td>"
        f"<td>{integer(values['duplicated_group_count'])}</td>"
        f"<td>{integer(values['max_rows_per_duplicated_group'])}</td>"
        "</tr>"
        for label, values in [
            ("Raw exact row", duplicates["raw_exact_row_profile"]),
            ("Normalized exact row", duplicates["normalized_exact_row_profile"]),
            ("InvoiceNo + StockCode candidate key", duplicates["invoice_stock_candidate_key_profile"]),
        ]
    )

    monthly_rows = "\n".join(
        "<tr>"
        f"<td><code>{esc(item['year_month'])}</code></td>"
        f"<td>{integer(item['row_count'])}</td>"
        f"<td>{integer(item['invoice_count'])}</td>"
        f"<td>{integer(item['customer_count'])}</td>"
        f"<td>{integer(item['stock_code_count'])}</td>"
        f"<td>{integer(item['country_count'])}</td>"
        f"<td>{integer(item['negative_quantity_row_count'])}</td>"
        f"<td>{integer(item['exact_duplicate_extra_row_count'])}</td>"
        f"<td>{money(item['net_revenue'])}</td>"
        "</tr>"
        for item in monthly
    )

    finding_rows = "\n".join(
        "<article class=\"finding\">"
        f"<div><span class=\"badge {esc(item['severity'])}\">{esc(item['severity'])}</span>"
        f"<span class=\"confidence\">{esc(item['confidence'])} confidence</span></div>"
        f"<h3>{esc(item['finding_id'].replace('_', ' ').title())}</h3>"
        f"<p><strong>Risk:</strong> {esc(item['analytical_risk'])}</p>"
        f"<p><strong>Control:</strong> {esc(item['control'])}</p>"
        "</article>"
        for item in report["quality_findings"]
    )

    policy_rows = "\n".join(
        f"<tr><td>{esc(name.replace('_', ' ').title())}</td><td>{esc(value)}</td></tr>"
        for name, value in reconciliation["policy"].items()
    )

    cancellation = business["cancellation_prefix_crosscheck"]
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BizHallu Confirmation Dataset Quality Profile</title>
  <style>
    :root {{ --ink:#17191c; --muted:#626a73; --line:#d8dde3; --soft:#f5f6f8; --paper:#ffffff; --green:#166534; --green-bg:#f0f8f3; --amber:#8a4b08; --amber-bg:#fff8e8; --red:#9f2d20; --red-bg:#fff3f1; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:var(--paper); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; line-height:1.55; letter-spacing:0; }}
    header {{ border-bottom:1px solid var(--line); background:#fbfbfc; }}
    nav {{ width:min(1180px,calc(100% - 40px)); margin:0 auto; min-height:58px; display:flex; align-items:center; justify-content:space-between; gap:20px; }}
    nav strong {{ font-size:15px; }}
    nav span {{ color:var(--muted); font-size:13px; }}
    main {{ width:min(1180px,calc(100% - 40px)); margin:0 auto; }}
    section {{ padding:42px 0; border-bottom:1px solid var(--line); }}
    .hero {{ padding:62px 0 46px; }}
    .eyebrow {{ margin:0 0 10px; color:var(--green); font-size:12px; font-weight:800; text-transform:uppercase; }}
    h1 {{ max-width:920px; margin:0; font-size:48px; line-height:1.08; letter-spacing:0; }}
    h2 {{ margin:0 0 12px; font-size:30px; line-height:1.2; letter-spacing:0; }}
    h3 {{ margin:8px 0 6px; font-size:17px; letter-spacing:0; }}
    p {{ margin:7px 0; }}
    .lede {{ max-width:900px; margin-top:18px; color:var(--muted); font-size:19px; }}
    .metrics {{ margin-top:28px; display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); border:1px solid var(--line); border-radius:7px; overflow:hidden; }}
    .metrics div {{ min-width:0; padding:15px; border-right:1px solid var(--line); background:#fff; }}
    .metrics div:last-child {{ border-right:0; }}
    .metrics span {{ display:block; color:var(--muted); font-size:11px; font-weight:700; text-transform:uppercase; }}
    .metrics strong {{ display:block; margin-top:5px; font-size:20px; overflow-wrap:anywhere; }}
    .callout {{ margin-top:20px; padding:15px 17px; border-left:4px solid var(--amber); background:var(--amber-bg); }}
    .callout.good {{ border-color:var(--green); background:var(--green-bg); }}
    .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; margin-top:20px; }}
    .finding {{ min-width:0; padding:17px; border:1px solid var(--line); border-radius:7px; background:#fff; }}
    .badge {{ display:inline-block; padding:2px 7px; border-radius:5px; font-size:11px; font-weight:800; text-transform:uppercase; }}
    .badge.medium {{ color:var(--amber); background:var(--amber-bg); }}
    .badge.low {{ color:var(--green); background:var(--green-bg); }}
    .badge.high, .badge.critical {{ color:var(--red); background:var(--red-bg); }}
    .confidence {{ margin-left:8px; color:var(--muted); font-size:12px; }}
    .table-wrap {{ margin-top:18px; overflow-x:auto; border:1px solid var(--line); border-radius:7px; }}
    table {{ width:100%; border-collapse:collapse; min-width:760px; }}
    th,td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; font-size:13px; }}
    th {{ color:#3e454d; background:var(--soft); font-size:11px; text-transform:uppercase; }}
    tr:last-child td {{ border-bottom:0; }}
    code {{ padding:2px 5px; border-radius:4px; background:#eef1f4; font-family:"SFMono-Regular",Consolas,monospace; overflow-wrap:anywhere; word-break:break-word; }}
    ul {{ display:grid; gap:8px; padding-left:20px; }}
    footer {{ padding:34px 0 50px; color:var(--muted); font-size:13px; }}
    @media (max-width:900px) {{ .metrics {{ grid-template-columns:repeat(2,minmax(0,1fr)); }} .metrics div {{ border-bottom:1px solid var(--line); }} .grid {{ grid-template-columns:1fr; }} }}
    @media (max-width:560px) {{ nav span {{ display:none; }} main,nav {{ width:min(100% - 24px,1180px); }} h1 {{ font-size:38px; }} h2 {{ font-size:26px; }} .metrics {{ grid-template-columns:1fr; }} .metrics div {{ border-right:0; }} }}
  </style>
</head>
<body>
  <header><nav><strong>BizHallu</strong><span>Confirmation Dataset Quality Profile</span></nav></header>
  <main>
    <section class="hero">
      <p class="eyebrow">Confirmation Set v1 · Source QA</p>
      <h1>The prior-period window is usable only after explicit controls.</h1>
      <p class="lede">The 502,938-row strict historical window passes core schema, date, type, monthly coverage, and revenue reconciliation checks. Missing descriptions, optional customer IDs, exact duplicates, nonpositive prices, and cancellation encoding still require frozen analytical controls.</p>
      <div class="metrics">
        <div><span>Strict rows</span><strong>{integer(report['source']['strict_window_row_count'])}</strong></div>
        <div><span>Months present</span><strong>{integer(report['source']['month_count'])} / 12</strong></div>
        <div><span>Missing CustomerID</span><strong>{percent(completeness['CustomerID']['missing_or_blank_rate'])}</strong></div>
        <div><span>Duplicate extra rows</span><strong>{percent(duplicates['normalized_exact_row_profile']['duplicate_extra_row_rate'])}</strong></div>
        <div><span>Controlled net revenue</span><strong>{money(reconciliation['net_revenue'])}</strong></div>
      </div>
      <div class="callout good"><strong>Quality decision:</strong> conditionally suitable for aggregate business analysis after documented controls.</div>
      <div class="callout"><strong>The dataset gate is still pending.</strong> This profile does not prove historical non-overlap, 36-context feasibility, split independence, or confirmation performance.</div>
    </section>

    <section>
      <p class="eyebrow">Dataset and grain</p>
      <h2>A complete twelve-month transaction window, without a stable source primary key.</h2>
      <p>The intended analytical grain is one normalized source invoice-line row before exact-row deduplication. <code>InvoiceNo + StockCode</code> is not unique; the local-only lineage key is <code>source_sheet + source_row_number</code>.</p>
      <div class="metrics">
        <div><span>Invoices</span><strong>{integer(report['cardinality']['invoice_count'])}</strong></div>
        <div><span>Stock codes</span><strong>{integer(report['cardinality']['stock_code_count'])}</strong></div>
        <div><span>Descriptions</span><strong>{integer(report['cardinality']['description_count'])}</strong></div>
        <div><span>Customers observed</span><strong>{integer(report['cardinality']['customer_count'])}</strong></div>
        <div><span>Countries</span><strong>{integer(report['cardinality']['country_count'])}</strong></div>
      </div>
    </section>

    <section>
      <p class="eyebrow">Completeness</p>
      <h2>Core transaction fields are complete; two analytical fields are not.</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Canonical field</th><th>Null</th><th>Blank</th><th>Missing total</th><th>Missing rate</th></tr></thead>
        <tbody>{completeness_rows}</tbody>
      </table></div>
      <div class="callout"><strong>Control:</strong> CustomerID remains optional for month, country, product, and cancellation questions. Description is mandatory for product-name and valid-net evidence.</div>
    </section>

    <section>
      <p class="eyebrow">Duplicates and grain</p>
      <h2>Only normalized exact rows are removed before aggregation.</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Candidate grain</th><th>Extra rows</th><th>Extra rate</th><th>Affected rows</th><th>Groups</th><th>Max group</th></tr></thead>
        <tbody>{duplicate_rows}</tbody>
      </table></div>
      <p>{esc(duplicates['grain_decision'])}</p>
    </section>

    <section>
      <p class="eyebrow">Cancellation and value controls</p>
      <h2>Negative quantity is broader than the invoice-prefix signal.</h2>
      <div class="metrics">
        <div><span>Cancel-prefix rows</span><strong>{integer(business['cancel_invoice_row_count'])}</strong></div>
        <div><span>Negative-quantity rows</span><strong>{integer(business['negative_quantity_row_count'])}</strong></div>
        <div><span>Negative without C</span><strong>{integer(cancellation['no_cancel_prefix_and_negative_quantity'])}</strong></div>
        <div><span>C without negative qty</span><strong>{integer(cancellation['cancel_prefix_and_nonnegative_quantity'])}</strong></div>
        <div><span>Return/cancel rows after dedup</span><strong>{integer(business['cancellation_or_return_rows_after_exact_dedup'])}</strong></div>
      </div>
      <div class="table-wrap"><table>
        <thead><tr><th>Metric</th><th>Value</th></tr></thead>
        <tbody>
          <tr><td>Gross positive revenue</td><td>{money(reconciliation['gross_positive_revenue'])}</td></tr>
          <tr><td>Negative revenue</td><td>{money(reconciliation['negative_revenue'])}</td></tr>
          <tr><td>Net revenue</td><td>{money(reconciliation['net_revenue'])}</td></tr>
          <tr><td>Gross + negative - net</td><td>{money(reconciliation['gross_plus_negative_minus_net'])}</td></tr>
          <tr><td>Merchandise net revenue</td><td>{money(reconciliation['merchandise_net_revenue'])}</td></tr>
        </tbody>
      </table></div>
    </section>

    <section>
      <p class="eyebrow">Frozen analytical policy</p>
      <h2>Cleaning rules are explicit and auditable.</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Layer</th><th>Rule</th></tr></thead><tbody>{policy_rows}</tbody>
      </table></div>
      <div class="callout"><strong>Tail policy:</strong> IQR and percentile flags are diagnostic only. Large quantities, prices, or adjustments are not deleted automatically because that would introduce outcome-dependent filtering.</div>
    </section>

    <section>
      <p class="eyebrow">Monthly coverage</p>
      <h2>Every frozen month is present and reconciled.</h2>
      <div class="table-wrap"><table>
        <thead><tr><th>Month</th><th>Rows</th><th>Invoices</th><th>Customers</th><th>Stock codes</th><th>Countries</th><th>Negative qty</th><th>Duplicate extras</th><th>Net revenue</th></tr></thead>
        <tbody>{monthly_rows}</tbody>
      </table></div>
    </section>

    <section>
      <p class="eyebrow">Findings and controls</p>
      <h2>Known data issues are documented rather than hidden.</h2>
      <div class="grid">{finding_rows}</div>
    </section>

    <section>
      <p class="eyebrow">Research boundary</p>
      <h2>Quality profiling does not authorize model execution.</h2>
      <ul>
        <li>No current-source overlap comparison was performed in this step.</li>
        <li>No candidate contexts or split assignments were generated.</li>
        <li>No prompt, Qwen answer, annotation target, verifier output, or detector metric was created.</li>
        <li>The next authorized action is only the normalized record-overlap proof.</li>
      </ul>
    </section>

    <footer>BizHallu Confirmation Dataset Quality Profile · Public report contains aggregate evidence only; the normalized line table remains local and Git-ignored.</footer>
  </main>
</body>
</html>
"""
    HTML_PATH.write_text(html_text, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "confirmation_dataset_quality_html_built",
                "quality_status": report["status"],
                "strict_window_row_count": report["source"]["strict_window_row_count"],
                "html_path": repo_path(HTML_PATH),
            },
            indent=2,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
