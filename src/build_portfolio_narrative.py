from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RESULTS_DIR = PROJECT_ROOT / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"

DEMO_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_summary.json"
INTERPRETATION_SUMMARY_PATH = REPORTS_DIR / "full100_detector_interpretation_summary.json"
LABEL_LOCK_SUMMARY_PATH = REPORTS_DIR / "full100_label_lock_summary.json"
QUESTION_REPORT_PATH = DATA_DIR / "business_questions_gold_report.json"
QWEN_FULL100_REPORT_PATH = OUTPUT_DIR / "qwen_full100_report.json"
ANNOTATION_DRAFT_REPORT_PATH = OUTPUT_DIR / "full100_annotation_draft_report.json"
ALIGNMENT_REPORT_PATH = OUTPUT_DIR / "full100_draft_span_token_alignment_report.json"
ERROR_REVIEW_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_error_review_report.json"
PREFLIGHT_VALIDATION_PATH = RESULTS_DIR / "full100_preflight_validation.json"
FULL100_REVIEW_PATH = OUTPUT_DIR / "full100_review.jsonl"

NARRATIVE_HTML_PATH = REPORTS_DIR / "bizhallu_portfolio_narrative.html"
NARRATIVE_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_narrative_summary.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def fmt_float(value: Any, digits: int = 3) -> str:
    return f"{float(value):.{digits}f}"


def fmt_int(value: Any) -> str:
    return f"{int(value):,}"


def fmt_money(value: Any) -> str:
    return f"GBP {float(value):,.2f}"


def render_metric_cards(items: list[tuple[str, str, str]]) -> str:
    return "\n".join(
        f"""
        <article class="metric-card">
          <span>{esc(label)}</span>
          <strong>{esc(value)}</strong>
          <p>{esc(description)}</p>
        </article>"""
        for label, value, description in items
    )


def render_bullets(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def render_numbered(items: list[str]) -> str:
    return "<ol>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ol>"


def render_gold_top3(review: dict[str, Any]) -> str:
    rows = []
    for item in review["gold_answer"]["top_products"]:
        rows.append(
            f"""
            <tr>
              <td>{esc(item['rank'])}</td>
              <td>{esc(item['stock_code'])}</td>
              <td>{esc(item['description'])}</td>
              <td>{fmt_money(item['merchandise_net_revenue'])}</td>
            </tr>"""
        )
    return f"""
      <table class="mini-table">
        <thead>
          <tr><th>Rank</th><th>Stock</th><th>Product</th><th>Gold net revenue</th></tr>
        </thead>
        <tbody>{''.join(rows)}</tbody>
      </table>"""


def case_takeaway(question_id: str) -> str:
    if question_id == "q_0064":
        return (
            "Best paired contrast. The same answer contains supported spans for rank 1 and rank 2, "
            "then a hallucinated rank-3 product and amount. This makes span-level evaluation visible."
        )
    if question_id == "q_0069":
        return (
            "Best confident-miss example. Qwen uses plausible products and real-looking amounts, "
            "but binds them to the wrong ranks while internal signals stay low."
        )
    return "Primary portfolio case."


def render_case_cards(reviews: dict[str, dict[str, Any]], question_ids: list[str]) -> str:
    cards = []
    for question_id in question_ids:
        review = reviews[question_id]
        generated_text = review["generation"]["generated_text"]
        cards.append(
            f"""
            <article class="case-card">
              <div class="case-kicker">{esc(question_id)} / {esc(review['split'])} / {esc(review['question_type'])}</div>
              <h3>{esc(review['question'])}</h3>
              <p>{esc(case_takeaway(question_id))}</p>
              <div class="case-columns">
                <div>
                  <h4>Gold answer</h4>
                  {render_gold_top3(review)}
                </div>
                <div>
                  <h4>Qwen answer</h4>
                  <pre>{esc(generated_text)}</pre>
                </div>
              </div>
              <a class="text-link" href="./bizhallu_portfolio_demo.html#{esc(question_id)}">Open this case in the demo</a>
            </article>"""
        )
    return "\n".join(cards)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    demo = load_json(DEMO_SUMMARY_PATH)
    interpretation = load_json(INTERPRETATION_SUMMARY_PATH)
    label_lock = load_json(LABEL_LOCK_SUMMARY_PATH)
    question_report = load_json(QUESTION_REPORT_PATH)
    qwen_report = load_json(QWEN_FULL100_REPORT_PATH)
    annotation_report = load_json(ANNOTATION_DRAFT_REPORT_PATH)
    alignment_report = load_json(ALIGNMENT_REPORT_PATH)
    error_review = load_json(ERROR_REVIEW_REPORT_PATH)
    preflight = load_json(PREFLIGHT_VALIDATION_PATH)
    reviews = {row["question_id"]: row for row in load_jsonl(FULL100_REVIEW_PATH)}

    primary_question_ids = demo["primary_question_ids"]
    best_auprc = interpretation["best_overall_by_test_auprc"]
    best_f1 = interpretation["best_overall_by_test_f1"]
    energy_f1_baseline = error_review["selected_baselines"][1]

    positioning_statement = (
        "I build business analytics systems that do not just generate answers, "
        "but audit whether the answer is grounded in the underlying transaction evidence."
    )
    one_minute_pitch = [
        "BizHallu is my AI reliability project for business analysis. I used UCI Online Retail data to generate deterministic retail analytics questions with known gold answers.",
        "I ran Qwen3-0.6B locally, captured token-level traces, and labeled exact business fact spans such as product names, ranks, countries, months, currency amounts, and percentages.",
        "The core finding is that the model often sounds analytical while binding evidence incorrectly. It may copy a real amount from the table, but assign it to the wrong rank or product.",
        "Simple internal uncertainty signals help, with held-out test AUPRC 0.835, but they still miss confident ranking and amount-binding errors. That is why business-context validation matters.",
    ]
    resume_bullets = [
        "Built BizHallu, a business-analysis hallucination detection benchmark using UCI Online Retail, Qwen3-0.6B, deterministic gold answers, span labels, and split-safe detector evaluation.",
        "Generated 100 evidence-grounded retail analytics questions across 7 business question types and ran a local CUDA Qwen3-0.6B full100 generation pipeline with 100 saved token traces.",
        "Annotated 205 held-out business fact spans across 35 dev/test questions and aligned all spans to token-level logit and energy-style traces for detector scoring.",
        "Evaluated 12 simple and energy-family detector baselines with dev-selected thresholds and held-out test reporting; best test AUPRC reached 0.835 and best test F1 reached 0.779.",
        "Created a portfolio demo showing how LLMs can copy real values while binding them to the wrong product rank, highlighting why evidence-aware business AI validation is needed.",
    ]
    linkedin_blurb = (
        "I built BizHallu to study hallucinations in business analytics, not as abstract chatbot errors but as concrete mistakes in revenue, ranking, product, and evidence binding. "
        "The project turns retail transactions into deterministic questions, runs Qwen3-0.6B locally, labels exact business fact spans, and evaluates whether internal uncertainty signals catch unsupported claims."
    )
    slide_outline = [
        "Motivation: business users need answers grounded in transaction evidence, not just fluent explanations.",
        "Dataset and task: UCI Online Retail, 100 deterministic questions, 7 business question types.",
        "Model and traces: Qwen3-0.6B local generation with token-level uncertainty and energy-ready fields.",
        "Labels: 205 held-out spans across 35 dev/test questions, including correct and hallucinated key facts.",
        "Results: simple uncertainty leads, energy-family controls are close but not a clean pure Spilled Energy win.",
        "Demo cases: q_0064 and q_0069 show wrong rank/product/amount bindings in top-3 product analysis.",
        "Takeaway: span-level detection is useful, but future methods need stronger evidence-aware checking.",
    ]
    guardrails = [
        "Report this as span-level hallucination detection, not whole-answer correctness.",
        "Say the selected presentation labels are locked with lock_basis=assistant_full_review, not independent human annotation.",
        "Say the strongest energy-family result is a probability-mass control, not pure adjacent-step Spilled Energy.",
        "Use q_0064 and q_0069 as primary examples because they connect business relevance, detector failure, and clear evidence.",
        "Avoid claiming production readiness; the current artifact is a rigorous portfolio-scale benchmark and demo.",
    ]
    next_steps = [
        "Convert the narrative into a concise slide deck for interviews and JHU BAAI networking.",
        "Add a small interactive viewer that lets users switch between gold evidence, Qwen answer, locked spans, and detector scores.",
        "Add an evidence-aware baseline that checks generated claims against structured source rows, then compare it with internal-only signals.",
        "Optionally add hidden-state probes after saving hidden states for the same locked spans.",
    ]

    summary = {
        "status": "portfolio_narrative_ready",
        "narrative_html_path": repo_path(NARRATIVE_HTML_PATH),
        "source_portfolio_demo_summary_path": repo_path(DEMO_SUMMARY_PATH),
        "source_detector_interpretation_summary_path": repo_path(INTERPRETATION_SUMMARY_PATH),
        "source_label_lock_summary_path": repo_path(LABEL_LOCK_SUMMARY_PATH),
        "current_preflight_stage": preflight["current_stage"],
        "ready_for_current_stage": preflight["ready_for_current_stage"],
        "primary_question_ids": primary_question_ids,
        "question_count": question_report["record_count"],
        "question_type_count": len(question_report["question_type_counts"]),
        "qwen_record_count": qwen_report["record_count"],
        "qwen_model_id": qwen_report["model_id"],
        "annotated_question_count": annotation_report["annotated_question_count"],
        "annotated_span_count": annotation_report["total_span_count"],
        "aligned_span_count": alignment_report["aligned_span_count"],
        "best_test_auprc": best_auprc["test_auprc"],
        "best_test_auprc_baseline": best_auprc["baseline"],
        "best_test_f1": best_f1["test_f1"],
        "best_test_f1_baseline": best_f1["baseline"],
        "energy_best_f1": float(energy_f1_baseline["test_f1"]),
        "energy_best_f1_baseline": energy_f1_baseline["baseline"],
        "error_row_count": interpretation["error_row_count"],
        "locked_selected_span_count": label_lock["selected_annotation_count"],
        "locked_primary_span_count": demo["locked_primary_span_count"],
        "positioning_statement": positioning_statement,
        "resume_bullet_count": len(resume_bullets),
        "slide_count": len(slide_outline),
        "guardrail_count": len(guardrails),
        "labels_locked": label_lock["labels_locked"],
        "label_lock_basis": label_lock["lock_basis"],
        "num_failures": 0,
        "failures": [],
    }

    metric_cards = [
        ("Gold questions", fmt_int(summary["question_count"]), "Deterministic retail analytics questions."),
        ("Question types", fmt_int(summary["question_type_count"]), "Top product, top country, top 3, share, returns, comparisons, monthly change."),
        ("Qwen generations", fmt_int(summary["qwen_record_count"]), "Local Qwen3-0.6B answers with saved traces."),
        ("Annotated spans", fmt_int(summary["annotated_span_count"]), "Held-out business fact spans aligned to token traces."),
        ("Best test AUPRC", fmt_float(summary["best_test_auprc"]), f"{summary['best_test_auprc_baseline']} on held-out test spans."),
        ("Best test F1", fmt_float(summary["best_test_f1"]), f"{summary['best_test_f1_baseline']} with dev-selected threshold."),
        ("Error rows", fmt_int(summary["error_row_count"]), "Held-out FP/FN rows used for interpretation."),
        ("Locked demo spans", fmt_int(summary["locked_primary_span_count"]), "Primary presentation spans in q_0064 and q_0069."),
    ]

    html_text = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BizHallu Portfolio Narrative</title>
    <style>
      :root {{
        --bg: #f5f5f7;
        --surface: #ffffff;
        --text: #1d1d1f;
        --muted: #60646c;
        --line: rgba(29, 29, 31, 0.12);
        --blue: #0066cc;
        --green: #0a7f42;
        --red: #b3261e;
        --ink: #111827;
        --soft-blue: rgba(0, 102, 204, 0.08);
        --soft-green: rgba(10, 127, 66, 0.10);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: linear-gradient(180deg, #ffffff 0%, var(--bg) 42%, #eef3f8 100%);
        color: var(--text);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
        line-height: 1.55;
      }}
      a {{ color: inherit; text-decoration: none; }}
      .topbar {{
        position: sticky;
        top: 0;
        z-index: 10;
        min-height: 62px;
        padding: 0 34px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid var(--line);
        background: rgba(245, 245, 247, 0.88);
        backdrop-filter: blur(18px);
      }}
      .brand {{ display: flex; align-items: center; gap: 10px; font-weight: 850; }}
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
      .nav {{ display: flex; gap: 18px; color: var(--muted); font-size: 14px; font-weight: 750; }}
      main {{ width: min(1180px, calc(100% - 40px)); margin: 0 auto; }}
      section {{ padding: 58px 0; border-top: 1px solid var(--line); }}
      .hero {{
        min-height: calc(100vh - 66px);
        display: grid;
        grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
        gap: 36px;
        align-items: center;
        border-top: 0;
      }}
      .eyebrow, .tag {{
        margin: 0 0 12px;
        color: var(--blue);
        font-size: 12px;
        font-weight: 850;
        letter-spacing: 0;
        text-transform: uppercase;
      }}
      h1, h2, h3, h4, p, li, td, th {{ overflow-wrap: anywhere; }}
      h1 {{ margin: 0; max-width: 880px; font-size: 62px; line-height: 1; letter-spacing: 0; }}
      h2 {{ margin: 0; font-size: 38px; line-height: 1.1; letter-spacing: 0; }}
      h3 {{ margin: 0; font-size: 22px; line-height: 1.22; letter-spacing: 0; }}
      h4 {{ margin: 0 0 10px; font-size: 14px; text-transform: uppercase; color: var(--muted); letter-spacing: 0; }}
      .lede {{ margin: 22px 0 0; max-width: 820px; color: var(--muted); font-size: 21px; }}
      .panel, .metric-card, .script-box, .case-card, .artifact-link {{
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
      }}
      .snapshot {{ display: grid; gap: 12px; }}
      .snapshot .panel {{ padding: 22px; }}
      .snapshot strong {{ display: block; margin-top: 4px; font-size: 24px; }}
      .snapshot span, .metric-card span {{ color: var(--muted); font-size: 12px; font-weight: 850; text-transform: uppercase; }}
      .metric-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }}
      .metric-card {{ min-height: 158px; padding: 20px; }}
      .metric-card strong {{ display: block; margin: 10px 0 8px; font-size: 38px; line-height: 1; }}
      .metric-card p, .panel p, .case-card p {{ margin: 0; color: var(--muted); }}
      .section-heading {{ max-width: 860px; margin-bottom: 22px; }}
      .section-heading p:last-child {{ margin: 14px 0 0; color: var(--muted); font-size: 18px; }}
      .two-col {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; }}
      .three-col {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }}
      .panel {{ padding: 24px; }}
      .panel ul, .script-box ul, .script-box ol {{ margin: 12px 0 0; padding-left: 22px; color: var(--muted); }}
      .panel li, .script-box li {{ margin: 8px 0; }}
      .storyline {{ counter-reset: step; display: grid; gap: 12px; }}
      .storyline li {{
        list-style: none;
        display: grid;
        grid-template-columns: 44px minmax(0, 1fr);
        gap: 14px;
        align-items: start;
        padding: 18px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
      }}
      .storyline li::before {{
        counter-increment: step;
        content: counter(step);
        display: grid;
        place-items: center;
        width: 34px;
        height: 34px;
        border-radius: 8px;
        background: var(--ink);
        color: white;
        font-weight: 850;
      }}
      .case-card {{ padding: 24px; margin-bottom: 16px; }}
      .case-kicker {{ color: var(--blue); font-size: 12px; font-weight: 850; text-transform: uppercase; margin-bottom: 10px; }}
      .case-card h3 {{ margin-bottom: 10px; }}
      .case-columns {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; margin-top: 18px; }}
      pre {{
        margin: 0;
        padding: 14px;
        border-radius: 8px;
        background: #f7f8fa;
        white-space: pre-wrap;
        font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
        font-size: 13px;
        line-height: 1.55;
      }}
      .mini-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
      th, td {{ padding: 9px 8px; border-top: 1px solid var(--line); text-align: left; vertical-align: top; }}
      th {{ color: var(--muted); font-size: 11px; text-transform: uppercase; }}
      thead th {{ border-top: 0; }}
      .script-box {{ padding: 22px; background: linear-gradient(180deg, var(--soft-blue), #fff); }}
      .script-box strong {{ display: block; margin-bottom: 8px; }}
      .quote {{ padding: 18px; border-radius: 8px; background: var(--soft-green); font-weight: 750; }}
      .artifact-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
      .artifact-link {{ padding: 18px; display: block; }}
      .artifact-link strong {{ display: block; margin-bottom: 6px; }}
      .artifact-link p {{ margin: 0; color: var(--muted); font-size: 14px; }}
      .text-link {{ display: inline-flex; margin-top: 16px; color: var(--blue); font-weight: 800; }}
      @media (max-width: 960px) {{
        .nav {{ display: none; }}
        .hero, .two-col, .three-col, .case-columns, .artifact-grid {{ grid-template-columns: 1fr; }}
        .metric-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        h1 {{ font-size: 46px; }}
        h2 {{ font-size: 31px; }}
      }}
      @media (max-width: 620px) {{
        main {{ width: min(100% - 28px, 1180px); }}
        .topbar {{ padding: 0 20px; }}
        .metric-grid {{ grid-template-columns: 1fr; }}
        h1 {{ font-size: 38px; }}
      }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <a class="brand" href="../site/index.html"><span>BH</span>BizHallu</a>
      <nav class="nav">
        <a href="#story">Story</a>
        <a href="#method">Method</a>
        <a href="#results">Results</a>
        <a href="#cases">Cases</a>
        <a href="#branding">Branding</a>
        <a href="#artifacts">Artifacts</a>
      </nav>
    </header>
    <main>
      <section class="hero">
        <div>
          <p class="eyebrow">BizHallu Portfolio Narrative</p>
          <h1>Auditing hallucinated business facts in LLM-generated retail analysis.</h1>
          <p class="lede">
            This is the polished project story for a business analytics and AI reliability portfolio:
            an accounting and supply-management background turned into a reproducible benchmark
            for checking whether model-generated business conclusions are actually grounded in evidence.
          </p>
        </div>
        <aside class="snapshot">
          <div class="panel"><span>Positioning</span><strong>{esc(positioning_statement)}</strong></div>
          <div class="panel"><span>Current stage</span><strong>{esc(summary['status'])}</strong></div>
          <div class="panel"><span>Label lock basis</span><strong>{esc(summary['label_lock_basis'])}</strong></div>
          <div class="panel"><span>Primary demo cases</span><strong>{esc(', '.join(primary_question_ids))}</strong></div>
        </aside>
      </section>

      <section id="story">
        <div class="section-heading">
          <p class="eyebrow">Core Story</p>
          <h2>What this project is trying to prove.</h2>
          <p>
            The project is not a generic chatbot demo. It is a business reliability experiment:
            when an LLM writes a sales-analysis answer, can we identify which exact business facts
            are supported by the data and which are hallucinated or mis-bound?
          </p>
        </div>
        <ol class="storyline">
          <li><div><h3>Business problem</h3><p>Analytics users can be harmed by a wrong revenue amount, wrong top product, wrong rank, or wrong comparison direction even when the prose sounds fluent.</p></div></li>
          <li><div><h3>Controlled evidence</h3><p>UCI Online Retail transaction data is cleaned into deterministic gold answers, so every question can be checked against source rows.</p></div></li>
          <li><div><h3>Model behavior</h3><p>Qwen3-0.6B often copies plausible evidence values but binds them to the wrong product, rank, country, or period.</p></div></li>
          <li><div><h3>Detector question</h3><p>Internal uncertainty and energy-style signals provide useful signal, but they miss some confident business-context errors.</p></div></li>
          <li><div><h3>Portfolio claim</h3><p>The strongest takeaway is not that the detector is finished. It is that business AI needs evidence-aware validation beyond token confidence.</p></div></li>
        </ol>
      </section>

      <section id="method">
        <div class="section-heading">
          <p class="eyebrow">Method</p>
          <h2>From raw transactions to span-level detector evaluation.</h2>
        </div>
        <div class="metric-grid">
          {render_metric_cards(metric_cards)}
        </div>
        <div class="two-col" style="margin-top:16px;">
          <article class="panel">
            <h3>Experimental design</h3>
            {render_bullets([
                f"Generated {question_report['record_count']} deterministic questions across {len(question_report['question_type_counts'])} business question types.",
                f"Ran {qwen_report['model_id']} locally on {qwen_report['device']} with seed {qwen_report['base_seed']}.",
                f"Annotated {annotation_report['total_span_count']} held-out spans across {annotation_report['annotated_question_count']} dev/test questions.",
                f"Aligned {alignment_report['aligned_span_count']} spans to token traces with simple uncertainty and energy-ready score fields.",
                "Selected thresholds on dev spans and reported metrics on held-out test spans.",
            ])}
          </article>
          <article class="panel">
            <h3>Why span-level labels matter</h3>
            {render_bullets([
                "Whole-answer labels are too coarse because one answer can mix correct and wrong facts.",
                "Business users often rely on a single rank, amount, or comparison direction.",
                "The label schema separates correct_key_fact, hallucinated_key_fact, and unsupported_claim.",
                "The portfolio demo uses locked spans so the public examples are traceable to source rows.",
            ])}
          </article>
        </div>
      </section>

      <section id="results">
        <div class="section-heading">
          <p class="eyebrow">Results</p>
          <h2>Internal signals help, but confident evidence-binding errors remain.</h2>
          <p>
            The detector result is credible because it is split-safe: thresholds are chosen on dev spans,
            then reused unchanged on held-out test spans. The strongest current signal comes from simple
            token uncertainty, not from a clean pure Spilled Energy win.
          </p>
        </div>
        <div class="three-col">
          <article class="panel">
            <h3>Best ranking signal</h3>
            <p><strong>{fmt_float(best_auprc['test_auprc'])} test AUPRC</strong></p>
            <p>{esc(best_auprc['baseline'])} ranks wrong spans best, with test precision {fmt_float(best_auprc['test_precision'])} and recall {fmt_float(best_auprc['test_recall'])} at the dev-selected threshold.</p>
          </article>
          <article class="panel">
            <h3>Best thresholded F1</h3>
            <p><strong>{fmt_float(best_f1['test_f1'])} test F1</strong></p>
            <p>{esc(best_f1['baseline'])} increases recall to {fmt_float(best_f1['test_recall'])}, but specificity falls to {fmt_float(best_f1['test_specificity'])}.</p>
          </article>
          <article class="panel">
            <h3>Energy nuance</h3>
            <p><strong>{fmt_float(energy_f1_baseline['test_f1'])} best energy F1</strong></p>
            <p>The best energy-family row is {esc(energy_f1_baseline['baseline'])}, a probability-mass control rather than pure adjacent-step Spilled Energy.</p>
          </article>
        </div>
        <div class="two-col" style="margin-top:16px;">
          <article class="panel">
            <h3>Observed failure patterns</h3>
            {render_bullets([
                f"Simple best-AUPRC baseline produced {interpretation['simple_best_auprc_error_counts']['false_negative']} false negatives and {interpretation['simple_best_auprc_error_counts']['false_positive']} false positives on held-out test error review rows.",
                f"Energy best-F1 baseline produced {interpretation['energy_best_f1_error_counts']['false_negative']} false negatives and {interpretation['energy_best_f1_error_counts']['false_positive']} false positives.",
                "Currency amounts and top-3 product rows are the most important miss patterns.",
                "Correct numeric and context spans can be over-flagged, so detector claims must remain qualified.",
            ])}
          </article>
          <article class="panel">
            <h3>Interpretation</h3>
            {render_bullets(interpretation["takeaways"])}
          </article>
        </div>
      </section>

      <section id="cases">
        <div class="section-heading">
          <p class="eyebrow">Primary Demo Cases</p>
          <h2>Two cases make the project easy to understand.</h2>
          <p>
            These are the examples to show in a portfolio, interview, or class presentation.
            They connect business evidence, Qwen output, locked spans, and detector behavior.
          </p>
        </div>
        {render_case_cards(reviews, primary_question_ids)}
      </section>

      <section id="branding">
        <div class="section-heading">
          <p class="eyebrow">Personal Branding</p>
          <h2>How to present this as your project.</h2>
          <p>
            The strongest positioning is not "I made another AI demo." It is:
            I can translate business data problems into rigorous AI evaluation workflows.
          </p>
        </div>
        <div class="two-col">
          <article class="script-box">
            <strong>One-minute pitch</strong>
            {render_numbered(one_minute_pitch)}
          </article>
          <article class="script-box">
            <strong>LinkedIn / portfolio blurb</strong>
            <p>{esc(linkedin_blurb)}</p>
          </article>
        </div>
        <div class="two-col" style="margin-top:16px;">
          <article class="panel">
            <h3>Resume bullets</h3>
            {render_bullets(resume_bullets)}
          </article>
          <article class="panel">
            <h3>Slide outline</h3>
            {render_numbered(slide_outline)}
          </article>
        </div>
        <div class="two-col" style="margin-top:16px;">
          <article class="panel">
            <h3>Presentation guardrails</h3>
            {render_bullets(guardrails)}
          </article>
          <article class="panel">
            <h3>Next build steps</h3>
            {render_bullets(next_steps)}
          </article>
        </div>
      </section>

      <section id="artifacts">
        <div class="section-heading">
          <p class="eyebrow">Artifact Map</p>
          <h2>Where each audience should go.</h2>
        </div>
        <div class="artifact-grid">
          <a class="artifact-link" href="./bizhallu_portfolio_demo.html"><strong>Portfolio demo</strong><p>Visual case study around q_0064 and q_0069.</p></a>
          <a class="artifact-link" href="./full100_detector_interpretation.html"><strong>Detector interpretation</strong><p>Metric and error-review explanation.</p></a>
          <a class="artifact-link" href="./full100_label_lock_report.html"><strong>Label lock report</strong><p>Locked presentation labels and usage rules.</p></a>
          <a class="artifact-link" href="../site/index.html"><strong>Project overview</strong><p>Static overview of pipeline and current status.</p></a>
          <a class="artifact-link" href="../docs/project_blueprint.md"><strong>Project blueprint</strong><p>Repository policy, lifecycle, and design constraints.</p></a>
          <a class="artifact-link" href="../docs/current_state_audit.md"><strong>Current audit</strong><p>Detailed state review and issues fixed.</p></a>
        </div>
      </section>
    </main>
  </body>
</html>
"""

    NARRATIVE_HTML_PATH.write_text(html_text, encoding="utf-8")
    NARRATIVE_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
