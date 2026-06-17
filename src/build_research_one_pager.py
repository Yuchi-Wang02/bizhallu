from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"

NARRATIVE_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_narrative_summary.json"
INTERPRETATION_SUMMARY_PATH = REPORTS_DIR / "full100_detector_interpretation_summary.json"
DEMO_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_v2_summary.json"
RISK_SUMMARY_PATH = REPORTS_DIR / "bizhallu_business_risk_lens_summary.json"
VERIFIER_SUMMARY_PATH = REPORTS_DIR / "bizhallu_evidence_verifier_pilot_summary.json"

HTML_PATH = REPORTS_DIR / "bizhallu_research_one_pager.html"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_research_one_pager_summary.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_list(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def metric(value: Any) -> str:
    return f"{float(value):.3f}"


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    narrative = load_json(NARRATIVE_SUMMARY_PATH)
    interpretation = load_json(INTERPRETATION_SUMMARY_PATH)
    demo = load_json(DEMO_SUMMARY_PATH)
    risk = load_json(RISK_SUMMARY_PATH)
    verifier = load_json(VERIFIER_SUMMARY_PATH)

    best_auprc = interpretation["best_overall_by_test_auprc"]
    best_f1 = interpretation["best_overall_by_test_f1"]

    research_questions = [
        "When LLMs generate business analysis from structured evidence, which fact spans fail most often: products, ranks, amounts, percentages, countries, or comparison directions?",
        "Can token-level uncertainty signals detect hallucinated business-fact spans when the generated answer is fluent and numerically plausible?",
        "Where do internal uncertainty signals fail, especially when the model confidently binds a real evidence value to the wrong entity, rank, or conclusion?",
        "How should evidence-aware verification be compared with internal-state hallucination signals rather than treated as a replacement for them?",
    ]

    method_steps = [
        "Clean UCI Online Retail transactions into auditable business evidence tables.",
        "Generate deterministic business questions and gold answers across seven retail analytics question types.",
        "Run local Qwen3-0.6B generations and preserve token-level probability, entropy, margin, and energy-style traces.",
        "Review exact business-fact spans and align each span to generated tokens.",
        "Evaluate split-safe detector baselines with dev-selected thresholds and held-out test metrics.",
    ]

    key_findings = [
        f"Best held-out span-level AUPRC is {metric(best_auprc['test_auprc'])} from {best_auprc['baseline']}.",
        f"Best held-out span-level F1 is {metric(best_f1['test_f1'])} from {best_f1['baseline']}.",
        "Top-3 product questions expose the most presentation-friendly failure mode: the model can use real values while assigning them to the wrong rank or product.",
        "Internal uncertainty has signal, but confident wrong evidence binding remains hard; this motivates a comparison with explicit evidence-aware verification.",
    ]

    jhu_extensions = [
        "Healthcare analytics: audit whether AI-generated utilization, cost, or quality summaries are grounded in source tables.",
        "Operations analytics: verify product, inventory, vendor, or demand claims before they influence prioritization decisions.",
        "Responsible AI governance: turn evidence-grounding checks into an audit layer for business decision-support tools.",
        "Capstone direction: compare internal-state signals, literature-grounded baselines, and evidence-aware verifiers on business claims.",
    ]

    research_tracks = [
        "Internal uncertainty: entropy, top-2 margin, and energy-style probability-mass signals already used in this project.",
        "Literature-grounded baselines: Semantic Entropy, TOHA, and entity-level hallucination detection as future comparison candidates.",
        "Evidence-aware verification: claim-evidence consistency checks against structured source rows and deterministic gold answers; current v0 covers Demo v2 locked spans only.",
    ]

    baseline_backlog = [
        "Semantic Entropy: useful for testing semantic consistency across sampled answers; requires multiple generations per question.",
        "TOHA: relevant as an attention-graph topology baseline; implementation depends on reliable access to attention tensors and runnable reference code.",
        "Real-time hallucinated entity detection: relevant for product, country, month, and stock-code spans; needs entity extraction and entity-level evidence matching.",
        "Spilled Energy: already represented through current energy-family fields; future work can separate pure adjacent-step energy from probability-mass controls more explicitly.",
    ]

    summary = {
        "status": "research_one_pager_ready",
        "research_one_pager_html_path": repo_path(HTML_PATH),
        "title": "BizHallu: Auditing Evidence Binding Errors in LLM-Generated Business Analysis",
        "question_count": narrative["question_count"],
        "annotated_span_count": narrative["annotated_span_count"],
        "heldout_test_span_count": 103,
        "best_test_auprc": best_auprc["test_auprc"],
        "best_test_f1": best_f1["test_f1"],
        "demo_case_count": demo["case_count"],
        "business_risk_lens_count": risk["lens_count"],
        "verifier_pilot_span_count": verifier["span_count"],
        "verifier_pilot_contradicted_count": verifier["verifier_label_counts"]["contradicted"],
        "research_question_count": len(research_questions),
        "extension_count": len(jhu_extensions),
        "research_track_count": len(research_tracks),
        "baseline_backlog_count": len(baseline_backlog),
        "next_stage_scope": "verifier pilot v0 over Demo v2 locked spans; no full100 rerun",
        "label_lock_basis": narrative["label_lock_basis"],
        "num_failures": 0,
        "failures": [],
    }

    html_text = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{esc(summary["title"])}</title>
    <style>
      :root {{
        --bg: #f6f7f9;
        --surface: #ffffff;
        --ink: #1d1d1f;
        --muted: #5f6368;
        --line: rgba(29, 29, 31, 0.13);
        --blue: #0066cc;
        --green: #0f766e;
        color-scheme: light;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: linear-gradient(180deg, #ffffff 0%, var(--bg) 54%, #eef2f5 100%);
        color: var(--ink);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
        line-height: 1.52;
      }}
      a {{ color: inherit; text-decoration: none; }}
      .topbar {{
        position: sticky;
        top: 0;
        z-index: 10;
        min-height: 62px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 34px;
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
      main {{ width: min(1080px, calc(100% - 40px)); margin: 0 auto; }}
      section {{ padding: 48px 0; border-top: 1px solid var(--line); }}
      .hero {{
        min-height: calc(100vh - 62px);
        display: grid;
        grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
        gap: 30px;
        align-items: center;
        border-top: 0;
      }}
      .eyebrow {{
        margin: 0 0 12px;
        color: var(--blue);
        font-size: 12px;
        font-weight: 850;
        letter-spacing: 0;
        text-transform: uppercase;
      }}
      h1, h2, h3, p, li {{ overflow-wrap: anywhere; }}
      h1 {{ margin: 0; font-size: clamp(40px, 5.6vw, 66px); line-height: 1; letter-spacing: 0; }}
      h2 {{ margin: 0; font-size: clamp(28px, 3.6vw, 40px); line-height: 1.1; letter-spacing: 0; }}
      h3 {{ margin: 0; font-size: 19px; line-height: 1.24; letter-spacing: 0; }}
      .lede {{ max-width: 820px; margin: 22px 0 0; color: var(--muted); font-size: 21px; }}
      .snapshot, .panel, .metric {{
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
      }}
      .snapshot {{ display: grid; overflow: hidden; }}
      .snapshot div {{ padding: 20px; border-bottom: 1px solid var(--line); }}
      .snapshot div:last-child {{ border-bottom: 0; }}
      .label {{ display: block; color: var(--muted); font-size: 12px; font-weight: 850; text-transform: uppercase; }}
      .snapshot strong {{ display: block; margin-top: 6px; font-size: 20px; }}
      .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 24px; }}
      .metric-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 24px; }}
      .panel, .metric {{ padding: 22px; }}
      .metric strong {{ display: block; margin-top: 8px; font-size: 30px; line-height: 1; }}
      .panel p, .metric p, li {{ color: var(--muted); }}
      ul {{ display: grid; gap: 10px; margin: 18px 0 0; padding-left: 20px; }}
      .callout {{
        margin-top: 22px;
        padding: 22px;
        border-radius: 8px;
        border: 1px solid rgba(15, 118, 110, 0.22);
        background: rgba(15, 118, 110, 0.08);
      }}
      .links {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 24px; }}
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
      code {{
        padding: 2px 5px;
        border-radius: 6px;
        background: rgba(0, 0, 0, 0.06);
        font-family: "SFMono-Regular", Consolas, monospace;
      }}
      footer {{ padding: 34px 0 50px; color: var(--muted); border-top: 1px solid var(--line); }}
      @media (max-width: 900px) {{
        .topbar {{ padding: 0 20px; }}
        nav {{ display: none; }}
        main {{ width: min(100% - 28px, 720px); }}
        .hero, .grid, .metric-grid {{ grid-template-columns: 1fr; }}
        .hero {{ min-height: auto; padding-top: 46px; }}
      }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <a class="brand" href="./index.html"><span>BH</span>BizHallu</a>
      <nav>
        <a href="./portfolio_demo_v2.html">Demo v2</a>
        <a href="./business_risk_lens.html">Business lens</a>
        <a href="./detector_interpretation.html">Metrics</a>
      </nav>
    </header>

    <main>
      <section class="hero">
        <div>
          <p class="eyebrow">Professor / research advisor one-pager</p>
          <h1>{esc(summary["title"])}</h1>
          <p class="lede">BizHallu studies evidence-grounding failures in LLM-generated business analysis: cases where the answer sounds fluent and may use real values, but binds them to the wrong product, rank, amount, comparison, or conclusion.</p>
          <div class="links">
            <a href="./portfolio_demo_v2.html">Open demo v2</a>
            <a href="./evidence_verifier_pilot.html">Open verifier pilot</a>
            <a href="./business_risk_lens.html">Open business risk lens</a>
            <a href="./detector_interpretation.html">Open detector interpretation</a>
          </div>
        </div>
        <aside class="snapshot">
          <div><span class="label">Gold questions</span><strong>{summary["question_count"]}</strong></div>
          <div><span class="label">Aligned spans</span><strong>{summary["annotated_span_count"]}</strong></div>
          <div><span class="label">Held-out test spans</span><strong>{summary["heldout_test_span_count"]}</strong></div>
          <div><span class="label">Best AUPRC / F1</span><strong>{metric(summary["best_test_auprc"])} / {metric(summary["best_test_f1"])}</strong></div>
          <div><span class="label">Label basis</span><strong>{esc(summary["label_lock_basis"])}</strong></div>
        </aside>
      </section>

      <section>
        <p class="eyebrow">Research problem</p>
        <h2>Business hallucinations are evidence-binding failures, not only unsupported text.</h2>
        <div class="grid">
          <article class="panel">
            <h3>Problem</h3>
            <p>In business analytics, an answer can be dangerous even when it contains real values from the source table. If the value is attached to the wrong product, rank, month, country, or conclusion, the resulting recommendation is still wrong.</p>
          </article>
          <article class="panel">
            <h3>Dataset and task</h3>
            <p>The current artifact uses UCI Online Retail transactions to build deterministic retail questions and gold answers. The evaluation unit is the individual business-fact span, not the whole generated answer.</p>
          </article>
        </div>
      </section>

      <section>
        <p class="eyebrow">Method</p>
        <h2>Pipeline from transaction evidence to span-level detector metrics.</h2>
        <div class="panel">{render_list(method_steps)}</div>
        <div class="metric-grid">
          <article class="metric"><span class="label">Questions</span><strong>{summary["question_count"]}</strong><p>Deterministic business questions across seven question types.</p></article>
          <article class="metric"><span class="label">Demo cases</span><strong>{summary["demo_case_count"]}</strong><p>Presentation-locked cases available in demo v2.</p></article>
          <article class="metric"><span class="label">Business lenses</span><strong>{summary["business_risk_lens_count"]}</strong><p>Accounting, operations, product, and market-risk framings.</p></article>
          <article class="metric"><span class="label">Test spans</span><strong>{summary["heldout_test_span_count"]}</strong><p>Held-out span-level detector evaluation units.</p></article>
        </div>
      </section>

      <section>
        <p class="eyebrow">Findings</p>
        <h2>Internal uncertainty has signal, but it is not the same as evidence verification.</h2>
        <div class="panel">{render_list(key_findings)}</div>
        <div class="callout"><strong>Main research seed:</strong> internal uncertainty signals can rank some risky spans, but confident wrong evidence bindings remain difficult. The next research step is to compare internal-state signals with evidence-aware verification for business-fact grounding.</div>
      </section>

      <section>
        <p class="eyebrow">Possible JHU extensions</p>
        <h2>Use this as a bridge into responsible AI, analytics, and operations research.</h2>
        <div class="grid">
          <article class="panel">
            <h3>Research questions</h3>
            {render_list(research_questions)}
          </article>
          <article class="panel">
            <h3>Extension paths</h3>
            {render_list(jhu_extensions)}
          </article>
        </div>
      </section>

      <section>
        <p class="eyebrow">Research backlog</p>
        <h2>Keep the academic route open while building the business-facing verifier.</h2>
        <div class="grid">
          <article class="panel">
            <h3>Comparison tracks</h3>
            {render_list(research_tracks)}
          </article>
          <article class="panel">
            <h3>Baseline candidates</h3>
            {render_list(baseline_backlog)}
          </article>
        </div>
        <div class="callout"><strong>Implementation caution:</strong> the current evidence-aware verifier is a v0 pilot over {esc(summary["verifier_pilot_span_count"])} Demo v2 locked spans, including {esc(summary["verifier_pilot_contradicted_count"])} contradicted bindings. Do not rerun full100, relabel spans, or add new metric claims until the comparison protocol is locked.</div>
      </section>

      <section>
        <p class="eyebrow">Scope guardrails</p>
        <h2>How to describe this accurately.</h2>
        <div class="panel">
          <p>BizHallu is a portfolio-scale, span-level AI reliability artifact. It should not be described as a production detector, a large independent human-labeled benchmark, or a whole-answer correctness benchmark.</p>
          <p>Best wording: <code>assistant-reviewed presentation labels</code>, <code>span-level business-fact evaluation</code>, and <code>diagnostic detector baselines</code>.</p>
        </div>
      </section>
    </main>

    <footer>
      <main>Research one-pager generated from validated BizHallu public artifacts.</main>
    </footer>
  </body>
</html>
"""

    HTML_PATH.write_text(html_text, encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({"status": summary["status"], "html": repo_path(HTML_PATH)}, indent=2))


if __name__ == "__main__":
    main()
