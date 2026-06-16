from __future__ import annotations

import csv
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
ANNOTATION_DIR = DATA_DIR / "annotations"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RESULTS_DIR = PROJECT_ROOT / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"

LOCK_DECISIONS_PATH = REPORTS_DIR / "full100_label_lock_decisions.jsonl"
LOCK_SUMMARY_PATH = REPORTS_DIR / "full100_label_lock_summary.json"
REVIEW_PATH = OUTPUT_DIR / "full100_review.jsonl"
ANNOTATION_PATH = ANNOTATION_DIR / "span_annotations_full100_draft.jsonl"
DETECTOR_SCORES_PATH = RESULTS_DIR / "full100_draft_detector_scores.csv"
DEMO_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_summary.json"
INTERPRETATION_SUMMARY_PATH = REPORTS_DIR / "full100_detector_interpretation_summary.json"

DEMO_V2_HTML_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_v2.html"
DEMO_V2_DATA_PATH = REPORTS_DIR / "bizhallu_demo_v2_data.json"
DEMO_V2_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_v2_summary.json"

PRIMARY_QUESTION_IDS = ["q_0064", "q_0069"]
SIMPLE_FIELD = "one_minus_min_top2_margin"
ENTROPY_FIELD = "mean_token_entropy"
ENERGY_FIELD = "mean_spilled_probability_mass_after_top2"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def as_float(value: Any) -> float:
    return float(value)


def detector_outcome(label: str, predicted_positive: bool) -> str:
    actual_positive = label != "correct_key_fact"
    if actual_positive and predicted_positive:
        return "caught"
    if actual_positive and not predicted_positive:
        return "missed"
    if not actual_positive and predicted_positive:
        return "false alarm"
    return "cleared"


def case_takeaway(question_id: str, spans: list[dict[str, Any]]) -> str:
    if question_id == "q_0064":
        return (
            "Best paired contrast: Qwen states correct rank-1 and rank-2 facts, then binds rank 3 to the wrong product and amount."
        )
    if question_id == "q_0069":
        return (
            "Best confident-miss case: plausible product and revenue statements stay below detector thresholds while the rank binding is wrong."
        )
    outcomes = Counter(span["simple_outcome"] for span in spans)
    if outcomes.get("false alarm"):
        return "Useful caveat case: a supported span is over-flagged because nearby answer context contains difficult numeric reasoning."
    if outcomes.get("missed"):
        return "Useful false-negative case: the generated span is wrong, but the internal uncertainty signal is low."
    return "Locked support case for explaining span-level labeling and detector readouts."


def evidence_columns(rows: list[dict[str, Any]]) -> list[str]:
    preferred = [
        "stock_code",
        "description",
        "product_name",
        "country",
        "month_label",
        "net_revenue",
        "merchandise_net_revenue",
        "gross_positive_revenue",
        "cancellation_revenue",
        "return_impact",
        "invoice_count",
    ]
    present = []
    all_keys = set().union(*(row.keys() for row in rows)) if rows else set()
    for key in preferred:
        if key in all_keys:
            present.append(key)
    for key in sorted(all_keys):
        if key not in present and len(present) < 7:
            present.append(key)
    return present[:7]


def build_demo_data() -> dict[str, Any]:
    lock_summary = load_json(LOCK_SUMMARY_PATH)
    demo_summary = load_json(DEMO_SUMMARY_PATH)
    interpretation_summary = load_json(INTERPRETATION_SUMMARY_PATH)
    lock_rows = load_jsonl(LOCK_DECISIONS_PATH)
    annotations = {row["annotation_id"]: row for row in load_jsonl(ANNOTATION_PATH)}
    reviews = {row["question_id"]: row for row in load_jsonl(REVIEW_PATH)}
    scores = {row["annotation_id"]: row for row in load_csv(DETECTOR_SCORES_PATH)}

    simple_threshold = as_float(demo_summary["simple_threshold"])
    entropy_threshold = as_float(demo_summary["entropy_threshold"])
    energy_threshold = as_float(demo_summary["energy_threshold"])

    spans_by_question: dict[str, list[dict[str, Any]]] = {}
    for lock in lock_rows:
        annotation = annotations[lock["annotation_id"]]
        score = scores.get(lock["annotation_id"], {})
        simple_score = as_float(score.get(SIMPLE_FIELD, 0))
        entropy_score = as_float(score.get(ENTROPY_FIELD, 0))
        energy_score = as_float(score.get(ENERGY_FIELD, 0))
        simple_pred = simple_score >= simple_threshold
        entropy_pred = entropy_score >= entropy_threshold
        energy_pred = energy_score >= energy_threshold
        span = {
            "annotation_id": lock["annotation_id"],
            "confirmation_item_id": lock["confirmation_item_id"],
            "question_id": lock["question_id"],
            "span_text": lock["span_text"],
            "span_start_char": int(annotation["span_start_char"]),
            "span_end_char": int(annotation["span_end_char"]),
            "fact_type": lock["fact_type"],
            "label": lock["label"],
            "publish_use": lock["publish_use"],
            "presentation_use": lock["presentation_use"],
            "demo_priority": lock["demo_priority"],
            "review_note": lock["review_note"],
            "detector_role_text": lock["detector_role_text"],
            "simple_score": simple_score,
            "entropy_score": entropy_score,
            "energy_score": energy_score,
            "simple_outcome": detector_outcome(lock["label"], simple_pred),
            "entropy_outcome": detector_outcome(lock["label"], entropy_pred),
            "energy_outcome": detector_outcome(lock["label"], energy_pred),
            "gold_short_answer": lock["gold_short_answer"],
        }
        spans_by_question.setdefault(lock["question_id"], []).append(span)

    ordered_question_ids = PRIMARY_QUESTION_IDS + [
        qid for qid in sorted(spans_by_question) if qid not in PRIMARY_QUESTION_IDS
    ]
    cases = []
    for question_id in ordered_question_ids:
        review = reviews[question_id]
        spans = sorted(spans_by_question[question_id], key=lambda item: item["span_start_char"])
        evidence_rows = review.get("prompt_evidence_rows", [])
        cases.append(
            {
                "question_id": question_id,
                "is_primary": question_id in PRIMARY_QUESTION_IDS,
                "split": review["split"],
                "question_type": review["question_type"],
                "difficulty": review["difficulty"],
                "question": review["question"],
                "gold_short_answer": review["gold_short_answer"],
                "generated_text": review["generation"]["generated_text"],
                "evidence_columns": evidence_columns(evidence_rows),
                "prompt_evidence_rows": evidence_rows,
                "takeaway": case_takeaway(question_id, spans),
                "spans": spans,
                "span_count": len(spans),
            }
        )

    all_spans = [span for spans in spans_by_question.values() for span in spans]
    data = {
        "meta": {
            "status": "portfolio_demo_v2_ready",
            "title": "BizHallu Interactive Demo V2",
            "case_count": len(cases),
            "span_count": len(all_spans),
            "primary_question_ids": PRIMARY_QUESTION_IDS,
            "label_lock_basis": lock_summary["lock_basis"],
            "label_lock_status": lock_summary["status"],
            "simple_threshold": simple_threshold,
            "entropy_threshold": entropy_threshold,
            "energy_threshold": energy_threshold,
            "best_test_auprc": interpretation_summary["best_overall_by_test_auprc"]["test_auprc"],
            "best_test_f1": interpretation_summary["best_overall_by_test_f1"]["test_f1"],
            "guardrail": "Assistant-reviewed presentation labels; span-level demo, not a human benchmark or production detector.",
        },
        "filters": {
            "fact_types": sorted({span["fact_type"] for span in all_spans}),
            "labels": sorted({span["label"] for span in all_spans}),
            "outcomes": ["caught", "missed", "false alarm", "cleared"],
            "detectors": [
                {"id": "simple", "label": "Top-2 margin", "score_field": SIMPLE_FIELD},
                {"id": "entropy", "label": "Entropy", "score_field": ENTROPY_FIELD},
                {"id": "energy", "label": "Energy-family", "score_field": ENERGY_FIELD},
            ],
        },
        "cases": cases,
    }
    return data


def build_html(data: dict[str, Any]) -> str:
    data_json = json.dumps(data, ensure_ascii=True)
    escaped_title = html.escape(data["meta"]["title"], quote=True)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escaped_title}</title>
    <style>
      :root {{
        --bg: #f6f7f9;
        --surface: #ffffff;
        --ink: #1d1d1f;
        --muted: #5f6368;
        --line: rgba(29, 29, 31, 0.13);
        --blue: #0066cc;
        --green: #0f766e;
        --red: #b3261e;
        --amber: #9a6700;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: linear-gradient(180deg, #ffffff 0%, var(--bg) 48%, #eef2f5 100%);
        color: var(--ink);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
        line-height: 1.5;
      }}
      a {{ color: inherit; text-decoration: none; }}
      button, select {{ font: inherit; }}
      .topbar {{
        position: sticky;
        top: 0;
        z-index: 20;
        min-height: 62px;
        padding: 0 34px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid var(--line);
        background: rgba(246, 247, 249, 0.88);
        backdrop-filter: blur(16px);
      }}
      .brand {{ display: flex; align-items: center; gap: 10px; font-weight: 850; }}
      .brand span {{
        display: grid;
        place-items: center;
        width: 32px;
        height: 32px;
        border-radius: 8px;
        background: var(--ink);
        color: white;
        font-size: 12px;
      }}
      .nav {{ display: flex; gap: 14px; color: var(--muted); font-size: 14px; font-weight: 750; }}
      main {{ width: min(1240px, calc(100% - 40px)); margin: 0 auto; }}
      .hero {{ padding: 56px 0 34px; }}
      .eyebrow {{
        margin: 0 0 12px;
        color: var(--blue);
        font-size: 12px;
        font-weight: 850;
        letter-spacing: 0;
        text-transform: uppercase;
      }}
      h1, h2, h3, p, td, th, li, button, select {{ overflow-wrap: anywhere; }}
      h1 {{ margin: 0; max-width: 960px; font-size: clamp(42px, 6vw, 70px); line-height: 1; letter-spacing: 0; }}
      h2 {{ margin: 0; font-size: 30px; line-height: 1.1; letter-spacing: 0; }}
      h3 {{ margin: 0; font-size: 18px; line-height: 1.22; letter-spacing: 0; }}
      .lede {{ margin: 20px 0 0; max-width: 920px; color: var(--muted); font-size: 21px; }}
      .layout {{
        display: grid;
        grid-template-columns: 300px minmax(0, 1fr);
        gap: 18px;
        align-items: start;
        padding: 22px 0 64px;
      }}
      .sidebar, .panel, .toolbar, .metric {{
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
      }}
      .sidebar {{
        position: sticky;
        top: 82px;
        display: grid;
        gap: 8px;
        padding: 12px;
      }}
      .case-button {{
        display: grid;
        gap: 4px;
        width: 100%;
        min-height: 62px;
        padding: 10px 12px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: white;
        color: var(--ink);
        text-align: left;
        cursor: pointer;
      }}
      .case-button.active {{
        border-color: rgba(0, 102, 204, 0.5);
        background: rgba(0, 102, 204, 0.08);
      }}
      .case-button strong {{ font-size: 14px; }}
      .case-button span {{ color: var(--muted); font-size: 12px; }}
      .content {{ display: grid; gap: 14px; }}
      .toolbar {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
        padding: 14px;
      }}
      label {{ display: grid; gap: 6px; color: var(--muted); font-size: 12px; font-weight: 850; text-transform: uppercase; }}
      select {{
        min-height: 40px;
        padding: 8px 10px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: white;
        color: var(--ink);
      }}
      .panel {{ padding: 22px; }}
      .metric-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }}
      .metric {{ padding: 16px; }}
      .metric span {{ color: var(--muted); font-size: 12px; font-weight: 850; text-transform: uppercase; }}
      .metric strong {{ display: block; margin-top: 6px; font-size: 26px; line-height: 1; }}
      .case-head {{ display: grid; gap: 8px; }}
      .case-head p, .panel p {{ color: var(--muted); }}
      .answer-grid {{ display: grid; grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr); gap: 12px; }}
      pre {{
        white-space: pre-wrap;
        margin: 0;
        padding: 16px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: #fbfbfd;
        color: var(--ink);
        font-family: "SFMono-Regular", Consolas, monospace;
        font-size: 13px;
      }}
      mark {{
        padding: 2px 4px;
        border-radius: 5px;
        color: inherit;
      }}
      mark.ok {{ background: rgba(15, 118, 110, 0.18); outline: 1px solid rgba(15, 118, 110, 0.35); }}
      mark.bad {{ background: rgba(179, 38, 30, 0.16); outline: 1px solid rgba(179, 38, 30, 0.35); }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }}
      th, td {{ padding: 10px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }}
      th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
      .pill {{
        display: inline-flex;
        align-items: center;
        min-height: 26px;
        padding: 4px 8px;
        border-radius: 8px;
        font-size: 12px;
        font-weight: 850;
      }}
      .pill.ok {{ color: var(--green); background: rgba(15, 118, 110, 0.10); }}
      .pill.bad {{ color: var(--red); background: rgba(179, 38, 30, 0.10); }}
      .pill.warn {{ color: var(--amber); background: rgba(154, 103, 0, 0.10); }}
      .small {{ display: block; margin-top: 4px; color: var(--muted); font-size: 12px; }}
      .links {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 16px; }}
      .links a {{
        display: inline-flex;
        align-items: center;
        min-height: 40px;
        padding: 9px 13px;
        border-radius: 8px;
        color: var(--blue);
        border: 1px solid rgba(0, 102, 204, 0.22);
        background: rgba(0, 102, 204, 0.07);
        font-weight: 800;
      }}
      @media (max-width: 980px) {{
        .topbar {{ padding: 0 20px; }}
        .nav {{ display: none; }}
        main {{ width: min(100% - 28px, 760px); }}
        .layout, .answer-grid, .toolbar, .metric-grid {{ grid-template-columns: 1fr; }}
        .sidebar {{ position: static; }}
      }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <a class="brand" href="./index.html"><span>BH</span>BizHallu</a>
      <nav class="nav">
        <a href="./career_package.html">Career package</a>
        <a href="./portfolio_demo.html">Original demo</a>
        <a href="./detector_interpretation.html">Metrics</a>
      </nav>
    </header>

    <main>
      <section class="hero">
        <p class="eyebrow">Interactive demo v2</p>
        <h1>Filter hallucinated business facts by case, label, fact type, and detector outcome.</h1>
        <p class="lede">This page uses only public, assistant-reviewed presentation labels and presentation-locked artifacts. It shows why evidence-aware checking matters when internal uncertainty misses confident wrong business bindings.</p>
        <div class="links">
          <a href="./assets/bizhallu_demo_v2_data.json">Open JSON data bundle</a>
          <a href="./portfolio_narrative.html">Read project narrative</a>
        </div>
      </section>

      <section class="metric-grid" id="metrics"></section>
      <section class="layout">
        <aside class="sidebar" id="caseList"></aside>
        <div class="content">
          <div class="toolbar">
            <label>Detector<select id="detectorFilter"></select></label>
            <label>Fact type<select id="factTypeFilter"></select></label>
            <label>Label<select id="labelFilter"></select></label>
            <label>Outcome<select id="outcomeFilter"></select></label>
          </div>
          <article class="panel" id="casePanel"></article>
          <article class="panel" id="spanPanel"></article>
          <article class="panel" id="evidencePanel"></article>
        </div>
      </section>
    </main>

    <script>
      const DEMO_DATA = {data_json};
      let currentCaseId = DEMO_DATA.cases[0].question_id;

      function escapeHtml(value) {{
        return String(value ?? "").replace(/[&<>"']/g, (char) => ({{
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;"
        }}[char]));
      }}

      function scoreText(value) {{
        const number = Number(value);
        if (!Number.isFinite(number)) return "n/a";
        if (number === 0) return "0";
        if (Math.abs(number) < 0.001) return number.toExponential(2);
        return number.toFixed(3);
      }}

      function activeDetector() {{
        return document.getElementById("detectorFilter").value || "simple";
      }}

      function detectorOutcome(span) {{
        return span[`${{activeDetector()}}_outcome`];
      }}

      function detectorScore(span) {{
        return span[`${{activeDetector()}}_score`];
      }}

      function filteredSpans(caseRow) {{
        const factType = document.getElementById("factTypeFilter").value;
        const label = document.getElementById("labelFilter").value;
        const outcome = document.getElementById("outcomeFilter").value;
        return caseRow.spans.filter((span) => {{
          if (factType !== "all" && span.fact_type !== factType) return false;
          if (label !== "all" && span.label !== label) return false;
          if (outcome !== "all" && detectorOutcome(span) !== outcome) return false;
          return true;
        }});
      }}

      function highlightAnswer(text, spans) {{
        const sorted = [...spans].sort((a, b) => a.span_start_char - b.span_start_char);
        let cursor = 0;
        let html = "";
        for (const span of sorted) {{
          if (span.span_start_char < cursor) continue;
          html += escapeHtml(text.slice(cursor, span.span_start_char));
          const cls = span.label === "correct_key_fact" ? "ok" : "bad";
          html += `<mark class="${{cls}}" title="${{escapeHtml(span.fact_type)}} / ${{escapeHtml(span.label)}}">${{escapeHtml(text.slice(span.span_start_char, span.span_end_char))}}</mark>`;
          cursor = span.span_end_char;
        }}
        html += escapeHtml(text.slice(cursor));
        return html;
      }}

      function renderFilters() {{
        const detector = document.getElementById("detectorFilter");
        detector.innerHTML = DEMO_DATA.filters.detectors.map((item) => `<option value="${{item.id}}">${{escapeHtml(item.label)}}</option>`).join("");
        document.getElementById("factTypeFilter").innerHTML = `<option value="all">All fact types</option>` + DEMO_DATA.filters.fact_types.map((item) => `<option value="${{escapeHtml(item)}}">${{escapeHtml(item)}}</option>`).join("");
        document.getElementById("labelFilter").innerHTML = `<option value="all">All labels</option>` + DEMO_DATA.filters.labels.map((item) => `<option value="${{escapeHtml(item)}}">${{escapeHtml(item)}}</option>`).join("");
        document.getElementById("outcomeFilter").innerHTML = `<option value="all">All outcomes</option>` + DEMO_DATA.filters.outcomes.map((item) => `<option value="${{escapeHtml(item)}}">${{escapeHtml(item)}}</option>`).join("");
        for (const id of ["detectorFilter", "factTypeFilter", "labelFilter", "outcomeFilter"]) {{
          document.getElementById(id).addEventListener("change", render);
        }}
      }}

      function renderMetrics() {{
        const meta = DEMO_DATA.meta;
        const items = [
          ["Cases", meta.case_count, "Locked questions in the demo bundle."],
          ["Locked spans", meta.span_count, "Presentation-selected fact spans."],
          ["Best test AUPRC", Number(meta.best_test_auprc).toFixed(3), "Split-safe detector ranking result."],
          ["Best test F1", Number(meta.best_test_f1).toFixed(3), "Dev-thresholded held-out result."]
        ];
        document.getElementById("metrics").innerHTML = items.map(([label, value, text]) => `
          <article class="metric"><span>${{escapeHtml(label)}}</span><strong>${{escapeHtml(value)}}</strong><p>${{escapeHtml(text)}}</p></article>
        `).join("");
      }}

      function renderCaseList() {{
        document.getElementById("caseList").innerHTML = DEMO_DATA.cases.map((caseRow) => `
          <button class="case-button ${{caseRow.question_id === currentCaseId ? "active" : ""}}" data-case="${{escapeHtml(caseRow.question_id)}}">
            <strong>${{escapeHtml(caseRow.question_id)}}${{caseRow.is_primary ? " / primary" : ""}}</strong>
            <span>${{escapeHtml(caseRow.question_type)}} / ${{caseRow.span_count}} spans</span>
          </button>
        `).join("");
        document.querySelectorAll(".case-button").forEach((button) => {{
          button.addEventListener("click", () => {{
            currentCaseId = button.dataset.case;
            render();
          }});
        }});
      }}

      function renderCase(caseRow, spans) {{
        document.getElementById("casePanel").innerHTML = `
          <div class="case-head">
            <p class="eyebrow">${{escapeHtml(caseRow.question_id)}} / ${{escapeHtml(caseRow.split)}} / ${{escapeHtml(caseRow.question_type)}}</p>
            <h2>${{escapeHtml(caseRow.question)}}</h2>
            <p>${{escapeHtml(caseRow.takeaway)}}</p>
          </div>
          <div class="answer-grid">
            <div>
              <h3>Gold answer</h3>
              <p>${{escapeHtml(caseRow.gold_short_answer)}}</p>
            </div>
            <div>
              <h3>Qwen answer</h3>
              <pre>${{highlightAnswer(caseRow.generated_text, spans)}}</pre>
            </div>
          </div>
        `;
      }}

      function renderSpans(spans) {{
        const rows = spans.map((span) => {{
          const isCorrect = span.label === "correct_key_fact";
          const labelClass = isCorrect ? "ok" : "bad";
          const outcome = detectorOutcome(span);
          const outcomeClass = outcome === "caught" || outcome === "cleared" ? "ok" : outcome === "missed" ? "bad" : "warn";
          return `
            <tr>
              <td><span class="pill ${{labelClass}}">${{escapeHtml(span.label)}}</span><span class="small">${{escapeHtml(span.fact_type)}}</span></td>
              <td>${{escapeHtml(span.span_text)}}<span class="small">${{escapeHtml(span.annotation_id)}}</span></td>
              <td><span class="pill ${{outcomeClass}}">${{escapeHtml(outcome)}}</span><span class="small">score ${{scoreText(detectorScore(span))}}</span></td>
              <td>${{escapeHtml(span.detector_role_text)}}<span class="small">${{escapeHtml(span.publish_use)}} / ${{escapeHtml(span.presentation_use)}}</span></td>
              <td>${{escapeHtml(span.review_note)}}</td>
            </tr>
          `;
        }}).join("");
        document.getElementById("spanPanel").innerHTML = `
          <h3>Filtered locked spans</h3>
          <p>${{spans.length}} span(s) match the current filters. Outcomes use the selected detector in the toolbar.</p>
          <table>
            <thead><tr><th>Label</th><th>Span</th><th>Detector outcome</th><th>Role</th><th>Review note</th></tr></thead>
            <tbody>${{rows || '<tr><td colspan="5">No spans match these filters.</td></tr>'}}</tbody>
          </table>
        `;
      }}

      function renderEvidence(caseRow) {{
        const cols = caseRow.evidence_columns;
        const header = cols.map((col) => `<th>${{escapeHtml(col)}}</th>`).join("");
        const body = caseRow.prompt_evidence_rows.map((row) => `
          <tr>${{cols.map((col) => `<td>${{escapeHtml(row[col])}}</td>`).join("")}}</tr>
        `).join("");
        document.getElementById("evidencePanel").innerHTML = `
          <h3>Evidence rows shown to Qwen</h3>
          <p>The page includes only compact public evidence fields, not raw line-level transaction data or token traces.</p>
          <table><thead><tr>${{header}}</tr></thead><tbody>${{body}}</tbody></table>
        `;
      }}

      function render() {{
        renderCaseList();
        const caseRow = DEMO_DATA.cases.find((item) => item.question_id === currentCaseId) || DEMO_DATA.cases[0];
        const spans = filteredSpans(caseRow);
        renderCase(caseRow, spans.length ? spans : caseRow.spans);
        renderSpans(spans);
        renderEvidence(caseRow);
      }}

      renderFilters();
      renderMetrics();
      render();
    </script>
  </body>
</html>
"""


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    data = build_demo_data()
    DEMO_V2_DATA_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=True), encoding="utf-8")
    DEMO_V2_HTML_PATH.write_text(build_html(data), encoding="utf-8")

    all_spans = [span for case in data["cases"] for span in case["spans"]]
    summary = {
        "status": "portfolio_demo_v2_ready",
        "portfolio_demo_v2_html_path": str(DEMO_V2_HTML_PATH),
        "portfolio_demo_v2_data_path": str(DEMO_V2_DATA_PATH),
        "case_count": len(data["cases"]),
        "locked_span_count": len(all_spans),
        "primary_question_ids": PRIMARY_QUESTION_IDS,
        "primary_case_count": sum(1 for case in data["cases"] if case["is_primary"]),
        "fact_type_count": len(data["filters"]["fact_types"]),
        "label_count": len(data["filters"]["labels"]),
        "detector_count": len(data["filters"]["detectors"]),
        "by_label": dict(Counter(span["label"] for span in all_spans)),
        "by_simple_outcome": dict(Counter(span["simple_outcome"] for span in all_spans)),
        "by_entropy_outcome": dict(Counter(span["entropy_outcome"] for span in all_spans)),
        "by_energy_outcome": dict(Counter(span["energy_outcome"] for span in all_spans)),
        "label_lock_basis": data["meta"]["label_lock_basis"],
        "num_failures": 0,
        "failures": [],
    }
    DEMO_V2_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "html": str(DEMO_V2_HTML_PATH)}, indent=2))


if __name__ == "__main__":
    main()
