from __future__ import annotations

import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data" / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"

QUESTIONS_PATH = DATA_DIR / "business_questions_gold.jsonl"
QUESTION_REPORT_PATH = DATA_DIR / "business_questions_gold_report.json"
DATA_QUALITY_PATH = DATA_DIR / "data_quality_report.json"
NARRATIVE_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_narrative_summary.json"
INTERPRETATION_SUMMARY_PATH = REPORTS_DIR / "full100_detector_interpretation_summary.json"

RISK_HTML_PATH = REPORTS_DIR / "bizhallu_business_risk_lens.html"
RISK_SUMMARY_PATH = REPORTS_DIR / "bizhallu_business_risk_lens_summary.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def fmt_int(value: Any) -> str:
    return f"{int(value):,}"


def fmt_money(value: Any) -> str:
    return f"GBP {float(value):,.2f}"


def question_examples(questions: list[dict[str, Any]], question_types: list[str], limit: int = 3) -> list[dict[str, str]]:
    selected = []
    for row in questions:
        if row["question_type"] in question_types:
            selected.append(
                {
                    "question_id": row["question_id"],
                    "question_type": row["question_type"],
                    "split": row["split"],
                    "question": row["question"],
                    "gold_short_answer": row["gold_short_answer"],
                }
            )
        if len(selected) >= limit:
            break
    return selected


def render_examples(examples: list[dict[str, str]]) -> str:
    return "".join(
        f"""
        <article class="example">
          <span>{esc(item["question_id"])} / {esc(item["question_type"])} / {esc(item["split"])}</span>
          <strong>{esc(item["question"])}</strong>
          <p>{esc(item["gold_short_answer"])}</p>
        </article>"""
        for item in examples
    )


def render_lens_cards(lenses: list[dict[str, Any]]) -> str:
    cards = []
    for lens in lenses:
        cards.append(
            f"""
            <article class="lens-card">
              <p class="eyebrow">{esc(lens["owner"])}</p>
              <h3>{esc(lens["title"])}</h3>
              <p>{esc(lens["business_value"])}</p>
              <ul>
                <li><strong>Question types:</strong> {esc(", ".join(lens["question_types"]))}</li>
                <li><strong>Existing coverage:</strong> {esc(lens["coverage_text"])}</li>
                <li><strong>AI reliability risk:</strong> {esc(lens["ai_risk"])}</li>
              </ul>
              <div class="examples">{render_examples(lens["examples"])}</div>
            </article>"""
        )
    return "\n".join(cards)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    questions = load_jsonl(QUESTIONS_PATH)
    question_report = load_json(QUESTION_REPORT_PATH)
    data_quality = load_json(DATA_QUALITY_PATH)
    narrative = load_json(NARRATIVE_SUMMARY_PATH)
    interpretation = load_json(INTERPRETATION_SUMMARY_PATH)

    counts = Counter(row["question_type"] for row in questions)
    split_counts = Counter(row["split"] for row in questions)
    type_to_questions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in questions:
        type_to_questions[row["question_type"]].append(row)

    lens_specs = [
        {
            "title": "Net revenue reconciliation",
            "owner": "Accounting lens",
            "question_types": ["monthly_revenue_change", "country_comparison_month", "return_impact_month"],
            "business_value": "Translate gross sales, cancellations, returns, and net revenue into auditable claims that can support monthly reporting.",
            "ai_risk": "A model may get the direction right while scaling the amount incorrectly, or may mix gross revenue with net revenue.",
        },
        {
            "title": "Returns impact and margin-risk triage",
            "owner": "Accounting + operations lens",
            "question_types": ["return_impact_month", "product_revenue_share_month"],
            "business_value": "Surface products or months where cancellations and returns change the business conclusion a stakeholder would draw from gross sales.",
            "ai_risk": "A generated answer can copy a plausible percentage or amount while failing to reconcile it to the source table.",
        },
        {
            "title": "Product concentration and inventory priority",
            "owner": "Supply management lens",
            "question_types": ["top_product_month", "top3_products_month", "product_revenue_share_month"],
            "business_value": "Identify which products dominate monthly merchandise revenue and would deserve procurement, stocking, or vendor attention.",
            "ai_risk": "Top-3 product questions are the clearest confident-error failure mode because rank, product, and amount must stay bound together.",
        },
        {
            "title": "Country exposure and market comparison",
            "owner": "Business analyst lens",
            "question_types": ["top_country_month", "country_comparison_month"],
            "business_value": "Compare country-level revenue exposure and explain which market is driving monthly performance.",
            "ai_risk": "A model can state the correct countries but reverse the comparison direction or attach the wrong delta.",
        },
    ]

    lenses = []
    for lens in lens_specs:
        coverage = sum(counts[qtype] for qtype in lens["question_types"])
        lenses.append(
            {
                **lens,
                "coverage": coverage,
                "coverage_text": f"{coverage} existing questions in the current 100-question gold set",
                "examples": question_examples(questions, lens["question_types"], limit=3),
            }
        )

    next_questions = [
        "Which products have high gross sales but poor net revenue after returns, and should they be reviewed for quality or demand issues?",
        "Which monthly revenue changes are driven by returns rather than sales growth or decline?",
        "Which top-3 products are most vulnerable to rank changes if return activity increases?",
        "Which country contributes the largest non-UK revenue exposure after excluding one-off cancellations?",
        "Which product categories should be prioritized for replenishment because they appear in recurring top-product answers?",
        "Which answer claims should be verified against structured evidence before being sent to a stakeholder?",
        "Which detector false negatives correspond to the highest business risk because the hallucinated span is a currency amount or rank?",
        "Which detector false positives are acceptable as conservative review flags in accounting-style workflows?",
        "How often does Qwen copy a real amount but bind it to the wrong product or rank?",
        "Would an evidence-aware verifier catch errors that entropy and top-2 margin miss?",
    ]

    summary = {
        "status": "business_risk_lens_ready",
        "business_risk_lens_html_path": str(RISK_HTML_PATH),
        "question_count": question_report["record_count"],
        "question_type_count": len(question_report["question_type_counts"]),
        "split_counts": dict(split_counts),
        "lens_count": len(lenses),
        "next_question_count": len(next_questions),
        "data_rows_raw": data_quality["raw_shape"][0],
        "country_count": data_quality["country_count"],
        "stock_code_count": data_quality["stock_code_count"],
        "net_revenue": data_quality["net_revenue"],
        "merchandise_net_revenue": data_quality["merchandise_net_revenue"],
        "cancellation_or_return_rows": data_quality["cancellation_or_return_rows"],
        "best_test_auprc": narrative["best_test_auprc"],
        "best_test_f1": narrative["best_test_f1"],
        "simple_false_negative_top_fact_type": interpretation["grouped_error_patterns"]["simple_false_negative_fact_types"][0],
        "num_failures": 0,
        "failures": [],
    }

    metric_cards = [
        ("Raw rows", fmt_int(summary["data_rows_raw"]), "Original Online Retail records before cleaning."),
        ("Countries", fmt_int(summary["country_count"]), "Country values available for market comparison."),
        ("Stock codes", fmt_int(summary["stock_code_count"]), "Product identifiers available for supply-management analysis."),
        ("Net revenue", fmt_money(summary["net_revenue"]), "Cleaned net revenue after returns and cancellations."),
        ("Merchandise net revenue", fmt_money(summary["merchandise_net_revenue"]), "Primary product-level metric used in the project."),
        ("Return/cancellation rows", fmt_int(summary["cancellation_or_return_rows"]), "Rows that make reconciliation and risk framing necessary."),
        ("Gold questions", fmt_int(summary["question_count"]), "Existing deterministic question set, not a new model run."),
        ("Best test AUPRC", f"{summary['best_test_auprc']:.3f}", "Current detector ranking result for span-level errors."),
    ]
    metric_html = "".join(
        f"""
        <article class="metric">
          <span>{esc(label)}</span>
          <strong>{esc(value)}</strong>
          <p>{esc(text)}</p>
        </article>"""
        for label, value, text in metric_cards
    )

    type_rows = "".join(
        f"<tr><td>{esc(qtype)}</td><td>{count}</td><td>{len(type_to_questions[qtype])}</td></tr>"
        for qtype, count in sorted(counts.items())
    )

    html_text = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BizHallu Business Risk Lens</title>
    <style>
      :root {{
        --bg: #f6f7f9;
        --surface: #ffffff;
        --ink: #1d1d1f;
        --muted: #5f6368;
        --line: rgba(29, 29, 31, 0.13);
        --blue: #0066cc;
        --green: #0f766e;
        --amber: #9a6700;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: linear-gradient(180deg, #ffffff 0%, var(--bg) 48%, #eef2f5 100%);
        color: var(--ink);
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
      nav {{ display: flex; gap: 14px; color: var(--muted); font-size: 14px; font-weight: 750; }}
      main {{ width: min(1160px, calc(100% - 40px)); margin: 0 auto; }}
      section {{ padding: 58px 0; border-top: 1px solid var(--line); }}
      .hero {{ min-height: calc(100vh - 62px); display: grid; align-content: center; border-top: 0; }}
      .eyebrow {{
        margin: 0 0 12px;
        color: var(--blue);
        font-size: 12px;
        font-weight: 850;
        letter-spacing: 0;
        text-transform: uppercase;
      }}
      h1, h2, h3, p, td, th, li {{ overflow-wrap: anywhere; }}
      h1 {{ margin: 0; max-width: 920px; font-size: clamp(42px, 6vw, 70px); line-height: 1; letter-spacing: 0; }}
      h2 {{ margin: 0; font-size: clamp(30px, 4vw, 42px); line-height: 1.1; letter-spacing: 0; }}
      h3 {{ margin: 0; font-size: 20px; line-height: 1.22; letter-spacing: 0; }}
      .lede {{ margin: 22px 0 0; max-width: 900px; color: var(--muted); font-size: 21px; }}
      .metric-grid, .lens-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin-top: 28px;
      }}
      .lens-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .metric, .lens-card, .panel, .example {{
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
      }}
      .metric, .lens-card, .panel {{ padding: 22px; }}
      .metric span, .example span {{ color: var(--muted); font-size: 12px; font-weight: 850; text-transform: uppercase; }}
      .metric strong {{ display: block; margin-top: 8px; font-size: 28px; line-height: 1; }}
      .metric p, .lens-card p, .panel p, .example p, li {{ color: var(--muted); }}
      ul, ol {{ display: grid; gap: 10px; margin: 16px 0 0; padding-left: 20px; }}
      .examples {{ display: grid; gap: 10px; margin-top: 18px; }}
      .example {{ padding: 14px; }}
      .example strong {{ display: block; margin-top: 6px; }}
      table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
      th, td {{ padding: 12px; border-bottom: 1px solid var(--line); text-align: left; }}
      th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; }}
      .callout {{
        margin-top: 24px;
        padding: 22px;
        border-radius: 8px;
        border: 1px solid rgba(15, 118, 110, 0.22);
        background: rgba(15, 118, 110, 0.08);
      }}
      footer {{ padding: 34px 0 50px; color: var(--muted); border-top: 1px solid var(--line); }}
      @media (max-width: 900px) {{
        .topbar {{ padding: 0 20px; }}
        nav {{ display: none; }}
        main {{ width: min(100% - 28px, 720px); }}
        .metric-grid, .lens-grid {{ grid-template-columns: 1fr; }}
        .hero {{ min-height: auto; padding-top: 46px; }}
      }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <a class="brand" href="./index.html"><span>BH</span>BizHallu</a>
      <nav>
        <a href="./career_package.html">Career package</a>
        <a href="./portfolio_demo_v2.html">Demo v2</a>
        <a href="./portfolio_narrative.html">Narrative</a>
      </nav>
    </header>

    <main>
      <section class="hero">
        <p class="eyebrow">Accounting and supply-management extension</p>
        <h1>Use BizHallu to talk about business risk, not only hallucination metrics.</h1>
        <p class="lede">The same Online Retail experiment can be framed around reconciliation, returns, product concentration, market exposure, and inventory priority. This keeps the project aligned with BA / DS / AI Analyst roles while using the validated 100-question setup.</p>
      </section>

      <section>
        <p class="eyebrow">Dataset and evaluation facts</p>
        <h2>The business story is already present in the current artifacts.</h2>
        <div class="metric-grid">{metric_html}</div>
      </section>

      <section>
        <p class="eyebrow">Four ways to present the project</p>
        <h2>Each lens maps the same experiment to a business stakeholder.</h2>
        <div class="lens-grid">{render_lens_cards(lenses)}</div>
      </section>

      <section>
        <p class="eyebrow">Question-set coverage</p>
        <h2>The current 100 questions already cover the core business-analysis tasks.</h2>
        <div class="panel">
          <table>
            <thead><tr><th>Question type</th><th>Count</th><th>Existing records</th></tr></thead>
            <tbody>{type_rows}</tbody>
          </table>
        </div>
      </section>

      <section>
        <p class="eyebrow">Next extension</p>
        <h2>Do this after the portfolio package, not before it.</h2>
        <div class="panel">
          <p>These are the strongest follow-up questions because they connect the hallucination detector to accounting and supply-management decisions.</p>
          <ol>{"".join(f"<li>{esc(item)}</li>" for item in next_questions)}</ol>
          <div class="callout">
            <strong>Implementation rule:</strong> keep Qwen3-0.6B and Online Retail as the core setup. Add a small 10-20 question business-risk extension before considering a larger benchmark or a new model family.
          </div>
        </div>
      </section>
    </main>

    <footer>
      <main>
        Business risk lens generated from existing BizHallu artifacts. It introduces no new model run and no new raw data.
      </main>
    </footer>
  </body>
</html>
"""

    RISK_HTML_PATH.write_text(html_text, encoding="utf-8")
    RISK_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "html": str(RISK_HTML_PATH)}, indent=2))


if __name__ == "__main__":
    main()
