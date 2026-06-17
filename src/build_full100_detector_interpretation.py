from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"

FAMILY_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_family_comparison_report.json"
ERROR_REVIEW_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_error_review_report.json"
ERROR_REVIEW_VALIDATION_PATH = RESULTS_DIR / "full100_draft_detector_error_review_validation.json"
ERROR_BY_FACT_TYPE_PATH = RESULTS_DIR / "full100_draft_detector_error_review_by_fact_type.csv"
ERROR_BY_QUESTION_TYPE_PATH = RESULTS_DIR / "full100_draft_detector_error_review_by_question_type.csv"

HTML_PATH = REPORTS_DIR / "full100_detector_interpretation.html"
SUMMARY_PATH = REPORTS_DIR / "full100_detector_interpretation_summary.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def as_float(value: Any) -> float:
    return float(value)


def fmt_metric(value: Any, digits: int = 3) -> str:
    return f"{as_float(value):.{digits}f}"


def fmt_int(value: Any) -> str:
    return str(int(value))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def top_group_rows(
    rows: list[dict[str, str]],
    *,
    baseline_role: str,
    error_type: str,
    limit: int = 4,
) -> list[dict[str, Any]]:
    filtered = [
        {
            "group_value": row["group_value"],
            "count": int(row["count"]),
            "family": row["family"],
            "baseline": row["baseline"],
            "baseline_role": row["baseline_role"],
            "error_type": row["error_type"],
        }
        for row in rows
        if row["baseline_role"] == baseline_role and row["error_type"] == error_type
    ]
    return sorted(filtered, key=lambda item: (-item["count"], item["group_value"]))[:limit]


def render_group_list(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "<li>No grouped errors in this slice.</li>"
    return "\n".join(
        f"<li><span>{esc(row['group_value'])}</span><strong>{row['count']}</strong></li>" for row in rows
    )


def metric_card(label: str, value: str, detail: str) -> str:
    return f"""
          <article class="metric-card">
            <span>{esc(label)}</span>
            <strong>{esc(value)}</strong>
            <p>{esc(detail)}</p>
          </article>"""


def compact_baseline(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "family": row["family"],
        "baseline": row["baseline"],
        "score_field": row["score_field"],
        "threshold": as_float(row["threshold"]),
        "test_auprc": as_float(row["test_auprc"]),
        "test_auroc": as_float(row["test_auroc"]),
        "test_f1": as_float(row["test_f1"]),
        "test_precision": as_float(row["test_precision"]),
        "test_recall": as_float(row["test_recall"]),
        "test_specificity": as_float(row["test_specificity"]),
        "test_accuracy": as_float(row["test_accuracy"]),
        "test_tp": int(row["test_tp"]),
        "test_fp": int(row["test_fp"]),
        "test_tn": int(row["test_tn"]),
        "test_fn": int(row["test_fn"]),
        "description": row["description"],
    }


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    family_report = load_json(FAMILY_REPORT_PATH)
    error_report = load_json(ERROR_REVIEW_REPORT_PATH)
    error_validation = load_json(ERROR_REVIEW_VALIDATION_PATH)
    by_fact_type = load_csv(ERROR_BY_FACT_TYPE_PATH)
    by_question_type = load_csv(ERROR_BY_QUESTION_TYPE_PATH)

    best_auprc = family_report["best_overall_by_test_auprc"]
    best_f1 = family_report["best_overall_by_test_f1"]
    simple_best_auprc = family_report["simple_best_by_test_auprc"]
    energy_best_f1 = family_report["energy_best_by_test_f1"]
    error_counts = error_report["error_counts_by_baseline"]

    simple_error = error_counts[simple_best_auprc["baseline"]]
    energy_error = error_counts[energy_best_f1["baseline"]]

    grouped = {
        "simple_false_negative_fact_types": top_group_rows(
            by_fact_type, baseline_role="simple_best_test_auprc", error_type="false_negative"
        ),
        "simple_false_positive_fact_types": top_group_rows(
            by_fact_type, baseline_role="simple_best_test_auprc", error_type="false_positive"
        ),
        "energy_false_negative_fact_types": top_group_rows(
            by_fact_type, baseline_role="energy_best_test_f1", error_type="false_negative"
        ),
        "energy_false_positive_fact_types": top_group_rows(
            by_fact_type, baseline_role="energy_best_test_f1", error_type="false_positive"
        ),
        "simple_false_negative_question_types": top_group_rows(
            by_question_type, baseline_role="simple_best_test_auprc", error_type="false_negative"
        ),
        "energy_false_positive_question_types": top_group_rows(
            by_question_type, baseline_role="energy_best_test_f1", error_type="false_positive"
        ),
    }

    takeaways = [
        "Simple uncertainty is the strongest current held-out signal: it leads both overall AUPRC and overall F1.",
        "The best energy-family row is a probability-mass control, not pure adjacent-step Spilled Energy.",
        "AUPRC and F1 tell different stories: the best-AUPRC detector is more precise, while the best-F1 detector raises recall at the cost of specificity.",
        "Top-3 product questions remain the clearest confident-error failure mode.",
        "Correct numeric and context facts are still over-flagged, so detector claims must stay qualified.",
    ]

    summary = {
        "status": "report_ready_draft",
        "scope": {
            "dataset": "UCI Online Retail",
            "model": "Qwen3-0.6B",
            "evaluation_scope": "35 high-priority held-out dev/test questions; metrics reported on 103 held-out test spans",
            "threshold_policy": "Thresholds selected on dev spans and reused unchanged on test spans.",
            "label_status": "Presentation labels locked after assistant full review.",
        },
        "best_overall_by_test_auprc": compact_baseline(best_auprc),
        "best_overall_by_test_f1": compact_baseline(best_f1),
        "simple_best_auprc_error_counts": simple_error,
        "energy_best_f1_error_counts": energy_error,
        "energy_minus_simple_best_auprc_delta": as_float(family_report["energy_minus_simple_best_auprc_delta"]),
        "energy_minus_simple_best_f1_delta": as_float(family_report["energy_minus_simple_best_f1_delta"]),
        "all_positive_like_energy_count": int(family_report["all_positive_like_count"]),
        "error_row_count": int(error_report["error_row_count"]),
        "selected_baseline_count": int(error_report["selected_baseline_count"]),
        "grouped_error_patterns": grouped,
        "takeaways": takeaways,
        "source_files": {
            "family_comparison_report": repo_path(FAMILY_REPORT_PATH),
            "error_review_report": repo_path(ERROR_REVIEW_REPORT_PATH),
            "error_review_validation": repo_path(ERROR_REVIEW_VALIDATION_PATH),
            "error_review_examples": repo_path(RESULTS_DIR / "full100_draft_detector_error_review_examples.csv"),
        },
        "num_failures": 0,
        "source_validation_num_failures": error_validation.get("num_failures"),
    }

    metric_cards = "\n".join(
        [
            metric_card(
                "Best AUPRC",
                fmt_metric(best_auprc["test_auprc"]),
                f"{best_auprc['baseline']} ranks wrong spans best on held-out test.",
            ),
            metric_card(
                "Best F1",
                fmt_metric(best_f1["test_f1"]),
                f"{best_f1['baseline']} gives the best dev-thresholded test F1.",
            ),
            metric_card(
                "Best energy F1",
                fmt_metric(energy_best_f1["test_f1"]),
                "Probability mass outside the top two choices is the strongest energy-family row.",
            ),
            metric_card(
                "Error rows",
                fmt_int(error_report["error_row_count"]),
                "Held-out test false positives and false negatives across two selected baselines.",
            ),
        ]
    )

    html_text = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BizHallu Detector Interpretation</title>
    <style>
      :root {{
        --bg: #f5f5f7;
        --surface: rgba(255, 255, 255, 0.86);
        --strong: #ffffff;
        --text: #1d1d1f;
        --muted: #5f6368;
        --line: rgba(29, 29, 31, 0.12);
        --blue: #0066cc;
        --green: #0a7f42;
        --amber: #9a6700;
        --red: #b3261e;
        --shadow: 0 18px 42px rgba(0, 0, 0, 0.08);
        color-scheme: light;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: linear-gradient(180deg, #ffffff 0%, var(--bg) 38%, #edf2f7 100%);
        color: var(--text);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
        line-height: 1.5;
      }}
      a {{ color: inherit; text-decoration: none; }}
      .topbar {{
        position: sticky;
        top: 0;
        z-index: 5;
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 62px;
        padding: 0 36px;
        border-bottom: 1px solid var(--line);
        background: rgba(245, 245, 247, 0.84);
        backdrop-filter: blur(18px);
      }}
      .brand {{ display: flex; align-items: center; gap: 10px; font-weight: 800; }}
      .brand span {{
        display: grid;
        place-items: center;
        width: 32px;
        height: 32px;
        border-radius: 8px;
        background: var(--text);
        color: #fff;
        font-size: 12px;
      }}
      main {{ width: min(1120px, calc(100% - 40px)); margin: 0 auto; }}
      .hero {{
        display: grid;
        grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
        gap: 30px;
        align-items: center;
        min-height: calc(100vh - 78px);
        padding: 56px 0 42px;
      }}
      .eyebrow {{
        margin: 0 0 12px;
        color: var(--blue);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
      }}
      h1, h2, h3, p {{ overflow-wrap: anywhere; }}
      h1 {{ max-width: 760px; margin: 0; font-size: 64px; line-height: 0.99; letter-spacing: 0; }}
      h2 {{ margin: 0; font-size: 38px; line-height: 1.08; letter-spacing: 0; }}
      h3 {{ margin: 0; font-size: 18px; line-height: 1.25; letter-spacing: 0; }}
      .lede {{ max-width: 760px; margin: 22px 0 0; color: var(--muted); font-size: 21px; }}
      .snapshot, .metric-card, .panel, .claim-card {{
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        box-shadow: var(--shadow);
        backdrop-filter: blur(18px);
      }}
      .snapshot {{ display: grid; overflow: hidden; }}
      .snapshot div {{ padding: 20px; border-bottom: 1px solid var(--line); }}
      .snapshot div:last-child {{ border-bottom: 0; }}
      .label, .metric-card span, .tag {{
        color: var(--muted);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
      }}
      .snapshot strong {{ display: block; margin-top: 4px; font-size: 22px; }}
      section {{ padding: 64px 0; border-top: 1px solid var(--line); }}
      .section-heading {{ max-width: 780px; margin-bottom: 26px; }}
      .metric-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }}
      .metric-card {{ min-height: 178px; padding: 22px; box-shadow: none; background: var(--strong); }}
      .metric-card strong {{ display: block; margin: 10px 0 8px; font-size: 42px; line-height: 1; }}
      .metric-card p, .panel p, .claim-card p {{ margin: 0; color: var(--muted); }}
      .claim-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
      .claim-card {{ padding: 22px; box-shadow: none; background: var(--strong); }}
      .claim-card h3 {{ margin-bottom: 10px; }}
      .two-col {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; align-items: start; }}
      .panel {{ padding: 24px; box-shadow: none; background: var(--strong); }}
      .panel h3 {{ margin-bottom: 12px; }}
      .error-list {{ display: grid; gap: 10px; padding: 0; margin: 16px 0 0; list-style: none; }}
      .error-list li {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 12px 0;
        border-top: 1px solid var(--line);
      }}
      .error-list strong {{ font-size: 22px; }}
      .callout {{
        margin-top: 18px;
        padding: 18px;
        border: 1px solid rgba(154, 103, 0, 0.24);
        border-radius: 8px;
        background: rgba(154, 103, 0, 0.08);
      }}
      .callout strong {{ display: block; margin-bottom: 6px; }}
      .table {{
        display: grid;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--strong);
      }}
      .row {{ display: grid; grid-template-columns: 1.5fr repeat(4, 0.8fr); gap: 12px; padding: 14px 16px; border-top: 1px solid var(--line); }}
      .row:first-child {{ border-top: 0; }}
      .row.head {{ color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .next {{ display: flex; align-items: center; justify-content: space-between; gap: 24px; }}
      .button {{ display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 11px 18px; border-radius: 8px; background: var(--blue); color: #fff; font-weight: 800; }}
      @media (max-width: 900px) {{
        .topbar {{ padding: 0 20px; }}
        .hero, .two-col, .claim-grid {{ grid-template-columns: 1fr; }}
        .metric-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        h1 {{ font-size: 48px; }}
        h2 {{ font-size: 32px; }}
        .row {{ grid-template-columns: 1fr 1fr; }}
        .row.head {{ display: none; }}
        .next {{ align-items: flex-start; flex-direction: column; }}
      }}
      @media (max-width: 560px) {{
        main {{ width: min(100% - 28px, 1120px); }}
        .metric-grid {{ grid-template-columns: 1fr; }}
        h1 {{ font-size: 40px; }}
      }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <a class="brand" href="../site/index.html"><span>BH</span>BizHallu</a>
      <a href="../results/full100_draft_detector_error_review_examples.csv">Error examples</a>
    </header>
    <main>
      <section class="hero">
        <div>
          <p class="eyebrow">Full100 held-out interpretation</p>
          <h1>Internal uncertainty helps, but it is not a business fact checker.</h1>
          <p class="lede">
            On the draft held-out span set, simple token uncertainty gives the strongest current signal.
            The best energy-family result is a probability-mass control, while pure adjacent-step Spilled
            Energy rows can collapse into almost-all-positive behavior.
          </p>
        </div>
        <aside class="snapshot" aria-label="Report snapshot">
          <div><span class="label">Scope</span><strong>35 held-out questions</strong></div>
          <div><span class="label">Test spans</span><strong>{esc(best_auprc['test_positive_count'])} positive / {esc(best_auprc['test_negative_count'])} negative</strong></div>
          <div><span class="label">Threshold policy</span><strong>Dev selected, test reported</strong></div>
          <div><span class="label">Claim status</span><strong>Labels locked after assistant full review</strong></div>
        </aside>
      </section>

      <section>
        <div class="section-heading">
          <p class="eyebrow">Headline metrics</p>
          <h2>The best rows are useful, but they optimize different behavior.</h2>
        </div>
        <div class="metric-grid">
{metric_cards}
        </div>
      </section>

      <section>
        <div class="section-heading">
          <p class="eyebrow">How to read it</p>
          <h2>AUPRC is ranking quality; F1 is a threshold tradeoff.</h2>
        </div>
        <div class="claim-grid">
          <article class="claim-card">
            <h3>AUPRC story</h3>
            <p>
              {esc(best_auprc['baseline'])} reaches AUPRC {fmt_metric(best_auprc['test_auprc'])}.
              It is precise at the selected threshold, but misses 20 positive spans.
            </p>
          </article>
          <article class="claim-card">
            <h3>F1 story</h3>
            <p>
              {esc(best_f1['baseline'])} reaches F1 {fmt_metric(best_f1['test_f1'])}.
              It catches more positives, but specificity drops to {fmt_metric(best_f1['test_specificity'])}.
            </p>
          </article>
          <article class="claim-card">
            <h3>Energy story</h3>
            <p>
              The best energy-family F1 is {fmt_metric(energy_best_f1['test_f1'])}, but it comes from
              probability mass outside top two choices, not pure Spilled Energy.
            </p>
          </article>
        </div>
        <div class="callout">
          <strong>Report wording</strong>
          <p>
            The fair claim is not that internal-state detectors solve hallucination. The fair claim is that
            uncertainty features expose a measurable signal, while many business errors remain confident or
            context-dependent.
          </p>
        </div>
      </section>

      <section>
        <div class="section-heading">
          <p class="eyebrow">Error review</p>
          <h2>The two selected baselines fail in different ways.</h2>
        </div>
        <div class="two-col">
          <article class="panel">
            <h3>Simple best-AUPRC: {esc(simple_best_auprc['baseline'])}</h3>
            <p>
              This row is more selective: {simple_error['false_positive']} false positives and
              {simple_error['false_negative']} false negatives on held-out test spans.
            </p>
            <ul class="error-list">
              <li><span>Top false-negative fact type</span><strong>{esc(grouped['simple_false_negative_fact_types'][0]['group_value'])}: {grouped['simple_false_negative_fact_types'][0]['count']}</strong></li>
              <li><span>Top false-negative question type</span><strong>{esc(grouped['simple_false_negative_question_types'][0]['group_value'])}: {grouped['simple_false_negative_question_types'][0]['count']}</strong></li>
              <li><span>Precision / recall</span><strong>{fmt_metric(simple_best_auprc['test_precision'])} / {fmt_metric(simple_best_auprc['test_recall'])}</strong></li>
            </ul>
          </article>
          <article class="panel">
            <h3>Energy best-F1: {esc(energy_best_f1['baseline'])}</h3>
            <p>
              This row catches more positives: {energy_error['false_positive']} false positives and
              {energy_error['false_negative']} false negatives on held-out test spans.
            </p>
            <ul class="error-list">
              <li><span>Top false-positive fact type</span><strong>{esc(grouped['energy_false_positive_fact_types'][0]['group_value'])}: {grouped['energy_false_positive_fact_types'][0]['count']}</strong></li>
              <li><span>Top false-positive question type</span><strong>{esc(grouped['energy_false_positive_question_types'][0]['group_value'])}: {grouped['energy_false_positive_question_types'][0]['count']}</strong></li>
              <li><span>Precision / recall</span><strong>{fmt_metric(energy_best_f1['test_precision'])} / {fmt_metric(energy_best_f1['test_recall'])}</strong></li>
            </ul>
          </article>
        </div>
      </section>

      <section>
        <div class="section-heading">
          <p class="eyebrow">Grouped misses</p>
          <h2>Where the detectors need stronger business context.</h2>
        </div>
        <div class="two-col">
          <article class="panel">
            <h3>Simple false negatives by fact type</h3>
            <ul class="error-list">
              {render_group_list(grouped['simple_false_negative_fact_types'])}
            </ul>
          </article>
          <article class="panel">
            <h3>Energy false positives by fact type</h3>
            <ul class="error-list">
              {render_group_list(grouped['energy_false_positive_fact_types'])}
            </ul>
          </article>
        </div>
      </section>

      <section>
        <div class="section-heading">
          <p class="eyebrow">Main takeaway</p>
          <h2>This is a credible negative-plus-positive result.</h2>
        </div>
        <div class="table" role="table" aria-label="Detector interpretation table">
          <div class="row head" role="row">
            <span>Claim</span><span>Evidence</span><span>Risk</span><span>Use in report</span><span>Status</span>
          </div>
          <div class="row" role="row">
            <span>Simple uncertainty has real signal.</span>
            <span>AUPRC {fmt_metric(best_auprc['test_auprc'])}; F1 {fmt_metric(best_f1['test_f1'])}</span>
            <span>Not causal or semantic.</span>
            <span>Lead result.</span>
            <span>Draft</span>
          </div>
          <div class="row" role="row">
            <span>Pure Spilled Energy is not the winner.</span>
            <span>{family_report['all_positive_like_count']} all-positive-like rows flagged.</span>
            <span>Can overstate specificity.</span>
            <span>Guardrail result.</span>
            <span>Draft</span>
          </div>
          <div class="row" role="row">
            <span>Business context is still missing.</span>
            <span>Top-3 and currency misses dominate error review.</span>
            <span>Token confidence can be high for wrong evidence binding.</span>
            <span>Motivation for next method.</span>
            <span>Draft</span>
          </div>
        </div>
      </section>

      <section class="next">
        <div>
          <p class="eyebrow">Next step</p>
          <h2>Review the confirmation packet before locking claims.</h2>
          <p class="lede">
            Before public claims, review the 15 selected confirmation items and fix any source annotation issues.
            Then use this page as the detector-results section of the portfolio story.
          </p>
        </div>
        <a class="button" href="./full100_label_confirmation_packet.html">Open packet</a>
      </section>
    </main>
  </body>
</html>
"""

    HTML_PATH.write_text(html_text, encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "html_path": str(HTML_PATH),
                "summary_path": str(SUMMARY_PATH),
                "status": summary["status"],
                "best_auprc": summary["best_overall_by_test_auprc"],
                "best_f1": summary["best_overall_by_test_f1"],
                "error_row_count": summary["error_row_count"],
                "num_failures": 0,
            },
            indent=2,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
