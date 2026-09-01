from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = PROJECT_ROOT / "configs" / "confirmation_dataset_source_audit_v1.json"
PROTOCOL_PATH = PROJECT_ROOT / "configs" / "confirmation_set_v1_protocol.json"
ACQUISITION_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_acquisition_report.json"
STRUCTURE_PATH = PROJECT_ROOT / "reports" / "bizhallu_confirmation_dataset_structure_report.json"
REPORTS_DIR = PROJECT_ROOT / "reports"
HTML_PATH = REPORTS_DIR / "bizhallu_confirmation_dataset_source_audit.html"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_confirmation_dataset_source_audit_summary.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_list(items: list[Any]) -> str:
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def render_source_link(url: str | None, label: str) -> str:
    if not url:
        return f"<span>{esc(label)}</span>"
    if url.startswith("https://"):
        return f'<a href="{esc(url)}" target="_blank" rel="noreferrer">{esc(label)}</a>'
    return f"<code>{esc(url)}</code>"


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    audit = load_json(AUDIT_PATH)
    protocol = load_json(PROTOCOL_PATH)
    acquisition = load_json(ACQUISITION_PATH)
    structure = load_json(STRUCTURE_PATH)

    decision = audit["decision"]
    candidates = audit["candidates"]
    criteria = audit["source_acceptance_criteria"]
    checks = audit["required_local_profile_checks"]
    references = audit["source_references"]
    selected = next(
        item for item in candidates if item["candidate_id"] == decision["selected_candidate_id"]
    )
    criterion_counts = dict(
        sorted(Counter(item["selected_candidate_status"] for item in criteria).items())
    )

    external_shortlist = [
        item
        for item in candidates
        if item["role"] in {"external_replication_shortlist", "external_relational_alternative"}
    ]
    pending_criteria = [
        item["criterion_id"]
        for item in criteria
        if item["selected_candidate_status"] == "pending_local_profile"
    ]

    summary = {
        "status": "confirmation_dataset_source_audit_v1_ready",
        "audit_path": repo_path(AUDIT_PATH),
        "protocol_path": repo_path(PROTOCOL_PATH),
        "html_path": repo_path(HTML_PATH),
        "audit_date": audit["audit_date"],
        "desk_audit_complete": True,
        "download_performed": audit["download_performed"],
        "acquisition_verified": audit["acquisition_verified"],
        "structure_profile_complete": audit["structure_profile_complete"],
        "local_profile_complete": audit["local_profile_complete"],
        "execution_ready": audit["execution_ready"],
        "no_new_results": audit["no_new_results"],
        "selection_status": decision["selection_status"],
        "selected_candidate_id": selected["candidate_id"],
        "selected_candidate_name": selected["name"],
        "selected_candidate_role": selected["role"],
        "selected_source_url": selected["official_source_url"],
        "selected_window": selected["selected_window"],
        "dataset_gate_status": decision["dataset_gate_status"],
        "zip_sha256": acquisition["raw_artifacts"]["zip"]["sha256"],
        "xlsx_sha256": acquisition["raw_artifacts"]["xlsx"]["sha256"],
        "workbook_total_data_rows": structure["workbook_total_data_rows"],
        "strict_window_row_count": structure["date_scan"]["strict_window_row_count"],
        "strict_window_date_min": structure["date_scan"]["strict_window_date_min"],
        "strict_window_date_max": structure["date_scan"]["strict_window_date_max"],
        "metadata_header_drift_detected": structure["metadata_header_drift_detected"],
        "required_header_aliases": structure["metadata_header_drift"]["actual_to_canonical_changes"],
        "candidate_count": len(candidates),
        "external_shortlist_count": len(external_shortlist),
        "source_reference_count": len(references),
        "selected_criterion_status_counts": criterion_counts,
        "pending_criterion_ids": pending_criteria,
        "local_profile_check_count": len(checks),
        "next_authorized_action": (
            "Run the full strict-window field-quality, duplicate/grain, cancellation, monthly-coverage, "
            "current-source overlap, and outcome-blind context-feasibility profile without creating prompts."
        ),
        "num_failures": 0,
        "failures": [],
    }

    criterion_rows = "\n".join(
        f"""
        <tr>
          <td><code>{esc(item['criterion_id'])}</code></td>
          <td><span class="badge {esc(item['selected_candidate_status'])}">{esc(item['selected_candidate_status'])}</span></td>
          <td>{esc(item['description'])}</td>
          <td>{esc(item['evidence'])}</td>
        </tr>
        """.strip()
        for item in criteria
    )

    candidate_rows = "\n".join(
        f"""
        <tr>
          <td><strong>{esc(item['name'])}</strong><code>{esc(item['candidate_id'])}</code></td>
          <td>{esc(item['role'])}<span class="badge decision">{esc(item['decision_status'])}</span></td>
          <td>{render_list([f"{key}: {value}" for key, value in item['field_fit'].items()])}</td>
          <td>{render_list(item['known_strengths'])}</td>
          <td>{render_list(item['known_risks'])}</td>
          <td>{esc(item['recommended_use'])}</td>
        </tr>
        """.strip()
        for item in candidates
    )

    check_rows = "\n".join(
        f"<tr><td>{index}</td><td><code>{esc(item['check_id'])}</code></td><td><span class=\"badge {esc(item['status'])}\">{esc(item['status'])}</span></td><td>{esc(item['requirement'])}</td></tr>"
        for index, item in enumerate(checks, start=1)
    )

    source_rows = "\n".join(
        f"""
        <tr>
          <td>{render_source_link(item.get('url'), item['title'])}</td>
          <td>{esc(item['source_type'])}</td>
          <td>{esc(item['accessed_on'])}</td>
        </tr>
        """.strip()
        for item in references
    )

    html_text = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BizHallu Confirmation Dataset Source Audit v1</title>
    <style>
      :root {{ --bg:#f5f6f8; --surface:#fff; --ink:#1d1d1f; --muted:#5f6368; --line:#d7dce2; --blue:#075ea8; --green:#11694d; --amber:#8a5700; --red:#a23b32; }}
      * {{ box-sizing:border-box; }}
      body {{ margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif; line-height:1.55; }}
      a {{ color:var(--blue); text-decoration:none; }}
      .topbar {{ min-height:60px; padding:0 28px; display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid var(--line); background:rgba(255,255,255,.96); position:sticky; top:0; z-index:5; }}
      .brand {{ color:var(--ink); font-weight:850; }}
      nav {{ display:flex; gap:16px; font-size:14px; font-weight:750; }}
      main {{ width:min(1180px,calc(100% - 36px)); margin:0 auto; }}
      section {{ padding:46px 0; border-bottom:1px solid var(--line); }}
      .hero {{ padding-top:66px; }}
      .eyebrow {{ margin:0 0 10px; color:var(--blue); font-size:12px; font-weight:850; text-transform:uppercase; }}
      h1 {{ max-width:1000px; margin:0; font-size:68px; line-height:1.02; letter-spacing:0; }}
      h2 {{ margin:0; font-size:40px; line-height:1.12; letter-spacing:0; }}
      h3 {{ margin:0; font-size:19px; line-height:1.25; letter-spacing:0; }}
      p, li, th, td {{ overflow-wrap:anywhere; }}
      .lede {{ max-width:940px; margin:20px 0 0; color:var(--muted); font-size:20px; }}
      .status {{ margin-top:28px; padding:18px 0; border-top:1px solid var(--line); border-bottom:1px solid var(--line); display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:18px; }}
      .status span {{ display:block; color:var(--muted); font-size:12px; font-weight:850; text-transform:uppercase; }}
      .status strong {{ display:block; margin-top:6px; font-size:23px; overflow-wrap:anywhere; }}
      .callout {{ margin-top:22px; padding:20px; border-left:4px solid var(--amber); background:#fff9ed; }}
      .callout.good {{ border-left-color:var(--green); background:#f3fbf7; }}
      .callout.danger {{ border-left-color:var(--red); background:#fff6f5; }}
      .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin-top:22px; }}
      .panel {{ min-width:0; padding:22px; border:1px solid var(--line); border-radius:8px; background:var(--surface); }}
      .panel p, .panel li {{ color:var(--muted); }}
      .table-wrap {{ width:100%; margin-top:22px; overflow-x:auto; border:1px solid var(--line); background:var(--surface); }}
      table {{ width:100%; min-width:900px; border-collapse:collapse; font-size:14px; }}
      .wide table {{ min-width:1380px; }}
      th, td {{ padding:14px; text-align:left; vertical-align:top; border-right:1px solid var(--line); border-bottom:1px solid var(--line); }}
      th {{ background:#eef1f4; font-size:12px; text-transform:uppercase; }}
      th:last-child, td:last-child {{ border-right:0; }}
      tr:last-child td {{ border-bottom:0; }}
      td strong, td code {{ display:block; margin-bottom:7px; }}
      ul, ol {{ display:grid; gap:8px; padding-left:21px; margin:8px 0; }}
      code {{ padding:2px 5px; border-radius:4px; background:#eef1f4; font-family:"SFMono-Regular",Consolas,monospace; overflow-wrap:anywhere; word-break:break-word; }}
      .badge {{ display:inline-block; margin-top:5px; padding:3px 7px; border:1px solid var(--line); border-radius:5px; color:var(--muted); font-size:11px; font-weight:800; text-transform:uppercase; }}
      .badge.pass_metadata, .badge.completed {{ color:var(--green); border-color:#93c8b4; background:#f3fbf7; }}
      .badge.conditional_pass, .badge.pending_local_profile, .badge.pending, .badge.active {{ color:var(--amber); border-color:#d7bd88; background:#fff9ed; }}
      footer {{ padding:32px 0 48px; color:var(--muted); }}
      @media (max-width:820px) {{ nav {{ display:none; }} h1 {{ font-size:40px; }} h2 {{ font-size:28px; }} .status,.grid {{ grid-template-columns:1fr; }} main {{ width:min(100% - 24px,1180px); }} }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <a class="brand" href="./bizhallu_confirmation_set_v1_design.html">BizHallu</a>
      <nav><a href="./bizhallu_confirmation_set_v1_design.html">Confirmation design</a><a href="./bizhallu_methodology_hardening.html">Current audit</a></nav>
    </header>
    <main>
      <section class="hero">
        <p class="eyebrow">Confirmation Dataset Source Audit v1</p>
        <h1>The official source is verified; execution remains blocked.</h1>
        <p class="lede">UCI Online Retail II is now acquired, hashed, and structurally inspected. The strict prior-period boundary retains 502,938 date-valid rows, but the dataset gate stays pending until full quality, overlap, and context-feasibility checks pass.</p>
        <div class="status">
          <div><span>Decision</span><strong>Provisional</strong></div>
          <div><span>Source</span><strong>Verified</strong></div>
          <div><span>Strict rows</span><strong>502,938</strong></div>
          <div><span>New results</span><strong>None</strong></div>
        </div>
        <div class="callout"><strong>Execution remains blocked.</strong> The raw files remain local and Git-ignored. No context manifest, prompt, model output, annotation target, detector decision, or Confirmation Set result was created.</div>
      </section>

      <section>
        <p class="eyebrow">Decision</p>
        <h2>Prefer unseen prior-period transactions before changing domains.</h2>
        <div class="grid">
          <article class="panel"><h3>Selected window</h3><p><code>{esc(decision['allowed_time_window']['start_inclusive'])}</code> inclusive through <code>{esc(decision['allowed_time_window']['end_exclusive'])}</code> exclusive.</p></article>
          <article class="panel"><h3>Research role</h3><p>{esc(decision['selected_role'])}. This is not an independent company or cross-domain replication.</p></article>
          <article class="panel"><h3>Why it fits</h3><p>{esc(decision['decision_summary'])}</p></article>
          <article class="panel"><h3>Why the gate stays pending</h3><p>{esc(decision['gate_completion_rule'])}</p></article>
        </div>
        <div class="callout good"><strong>External path remains open.</strong> Complete Journey is the preferred external-replication shortlist candidate after the corrected protocol is tested on the lower-risk prior-period source.</div>
      </section>

      <section>
        <p class="eyebrow">Acquisition evidence</p>
        <h2>The immutable file and strict date boundary now reconcile.</h2>
        <div class="grid">
          <article class="panel"><h3>Official ZIP</h3><p>{esc(acquisition['raw_artifacts']['zip']['size_bytes'])} bytes</p><code>{esc(acquisition['raw_artifacts']['zip']['sha256'])}</code></article>
          <article class="panel"><h3>Extracted workbook</h3><p>{esc(acquisition['raw_artifacts']['xlsx']['size_bytes'])} bytes</p><code>{esc(acquisition['raw_artifacts']['xlsx']['sha256'])}</code></article>
          <article class="panel"><h3>Workbook reconciliation</h3><p>{esc(structure['workbook_total_data_rows'])} data rows across {esc(structure['workbook_sheet_count'])} sheets; documented instance delta: {esc(structure['documented_instance_delta'])}.</p></article>
          <article class="panel"><h3>Strict window</h3><p>{esc(structure['date_scan']['strict_window_row_count'])} rows from {esc(structure['date_scan']['strict_window_date_min'])} through {esc(structure['date_scan']['strict_window_date_max'])}.</p></article>
        </div>
        <div class="callout"><strong>Schema drift recorded.</strong> The workbook uses <code>Invoice</code>, <code>Price</code>, and <code>Customer ID</code>; ingestion must map them to <code>InvoiceNo</code>, <code>UnitPrice</code>, and <code>CustomerID</code> before shared business rules run.</div>
      </section>

      <section>
        <p class="eyebrow">Acceptance criteria</p>
        <h2>Metadata and structure are verified; analytical fitness is not.</h2>
        <p>Local evidence now confirms file integrity, workbook shape, date coverage, and deterministic header aliases. Completeness, duplicate behavior, business-rule validity, record independence, and context capacity still require the next profile.</p>
        <div class="table-wrap"><table>
          <thead><tr><th>Criterion</th><th>Status</th><th>Requirement</th><th>Current evidence</th></tr></thead>
          <tbody>{criterion_rows}</tbody>
        </table></div>
      </section>

      <section>
        <p class="eyebrow">Candidate matrix</p>
        <h2>Keep internal replication, external replication, and domain transfer separate.</h2>
        <div class="table-wrap wide"><table>
          <thead><tr><th>Candidate</th><th>Role and decision</th><th>Field fit</th><th>Strengths</th><th>Risks</th><th>Recommended use</th></tr></thead>
          <tbody>{candidate_rows}</tbody>
        </table></div>
        <div class="callout danger"><strong>Metadata conflict matters.</strong> The UCI Online Retail page reports no missing values, but BizHallu's local source audit found 1,454 missing descriptions, 135,080 missing customer IDs, and 5,268 duplicate rows. Online metadata alone is therefore not sufficient to clear the new source.</div>
      </section>

      <section>
        <p class="eyebrow">Local acquisition gate</p>
        <h2>Three checks are complete; six remain pending and privacy stays active.</h2>
        <div class="table-wrap"><table>
          <thead><tr><th>#</th><th>Check</th><th>Status</th><th>Requirement</th></tr></thead>
          <tbody>{check_rows}</tbody>
        </table></div>
      </section>

      <section>
        <p class="eyebrow">Decision rules</p>
        <h2>Reject the source if independence or deterministic evidence fails.</h2>
        <div class="grid">
          <article class="panel"><h3>Accept only if</h3>{render_list(audit['post_profile_decision_rules']['accept_selected_source_if'])}</article>
          <article class="panel"><h3>Reject or redesign if</h3>{render_list(audit['post_profile_decision_rules']['reject_or_redesign_if'])}</article>
        </div>
      </section>

      <section>
        <p class="eyebrow">Source register</p>
        <h2>Every desk-audit claim points to a primary or maintainer source.</h2>
        <div class="table-wrap"><table>
          <thead><tr><th>Source</th><th>Type</th><th>Checked</th></tr></thead>
          <tbody>{source_rows}</tbody>
        </table></div>
      </section>

      <section>
        <p class="eyebrow">Next authorized action</p>
        <h2>Profile the verified window; do not generate.</h2>
        <p>{esc(summary['next_authorized_action'])}</p>
        <div class="callout"><strong>Still prohibited:</strong> creating confirmation prompts, running Qwen, viewing answer correctness, selecting annotation targets, tuning detectors, or reporting Confirmation Set v1 performance.</div>
      </section>

      <footer>BizHallu Confirmation Dataset Source Audit v1. Acquisition and structure verified {esc(audit['audit_date'])}; analytical source QA remains pending.</footer>
    </main>
  </body>
</html>
"""

    HTML_PATH.write_text(html_text, encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "selected_candidate_id": summary["selected_candidate_id"],
                "selection_status": summary["selection_status"],
                "dataset_gate_status": summary["dataset_gate_status"],
                "html_path": summary["html_path"],
                "summary_path": repo_path(SUMMARY_PATH),
            },
            indent=2,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
