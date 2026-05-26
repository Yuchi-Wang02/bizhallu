"""Build a GitHub Pages-ready public bundle for BizHallu.

The experiment-native report pages live in reports/. GitHub Pages is easier to
serve from docs/, so this script copies the validated public-facing reports into
docs/ with stable filenames and rewrites their local navigation links.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from html import escape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
DOCS_ASSETS_DIR = DOCS_DIR / "assets"
REPORTS_DIR = ROOT / "reports"
RESULTS_DIR = ROOT / "results"

DEMO_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_summary.json"
NARRATIVE_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_narrative_summary.json"
PREFLIGHT_VALIDATION_PATH = ROOT / "results" / "full100_preflight_validation.json"
MANIFEST_PATH = DOCS_DIR / "github_pages_manifest.json"

PAGE_COPIES = [
    (
        REPORTS_DIR / "bizhallu_portfolio_demo.html",
        DOCS_DIR / "portfolio_demo.html",
        "interactive_demo",
    ),
    (
        REPORTS_DIR / "bizhallu_portfolio_narrative.html",
        DOCS_DIR / "portfolio_narrative.html",
        "portfolio_narrative",
    ),
    (
        REPORTS_DIR / "full100_detector_interpretation.html",
        DOCS_DIR / "detector_interpretation.html",
        "detector_interpretation",
    ),
    (
        REPORTS_DIR / "full100_label_lock_report.html",
        DOCS_DIR / "label_lock_report.html",
        "label_lock_report",
    ),
    (
        REPORTS_DIR / "full100_label_confirmation_packet.html",
        DOCS_DIR / "label_confirmation_packet.html",
        "label_confirmation_packet",
    ),
]

ASSET_COPIES = [
    (
        RESULTS_DIR / "full100_draft_detector_error_review_examples.csv",
        DOCS_ASSETS_DIR / "full100_draft_detector_error_review_examples.csv",
        "detector_error_examples_csv",
    ),
    (
        REPORTS_DIR / "bizhallu_ai_reliability_deck.pptx",
        DOCS_ASSETS_DIR / "bizhallu_ai_reliability_deck.pptx",
        "presentation_deck_pptx",
    ),
    (
        REPORTS_DIR / "bizhallu_ai_reliability_deck_contact_sheet.png",
        DOCS_ASSETS_DIR / "bizhallu_ai_reliability_deck_contact_sheet.png",
        "presentation_deck_contact_sheet_png",
    ),
]

LINK_REWRITES = {
    "../site/index.html": "./index.html",
    "../docs/project_blueprint.md": "./project_blueprint.md",
    "../docs/current_state_audit.md": "./current_state_audit.md",
    "../results/full100_draft_detector_error_review_examples.csv": (
        "./assets/full100_draft_detector_error_review_examples.csv"
    ),
    "./bizhallu_portfolio_demo.html": "./portfolio_demo.html",
    "./full100_detector_interpretation.html": "./detector_interpretation.html",
    "./full100_label_lock_report.html": "./label_lock_report.html",
    "./full100_label_confirmation_packet.html": "./label_confirmation_packet.html",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rewrite_links(html: str) -> str:
    rewritten = html
    for old, new in sorted(LINK_REWRITES.items(), key=lambda item: len(item[0]), reverse=True):
        rewritten = rewritten.replace(old, new)
    return rewritten


def metric(value: Any, digits: int = 3) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return "n/a"


def render_index(demo: dict[str, Any], narrative: dict[str, Any], preflight: dict[str, Any]) -> str:
    primary_ids = narrative.get("primary_question_ids") or demo.get("primary_question_ids") or []
    primary_text = " / ".join(escape(str(item)) for item in primary_ids)
    question_count = narrative.get("question_count", 100)
    span_count = narrative.get("annotated_span_count", 205)
    locked_primary = narrative.get("locked_primary_span_count", demo.get("locked_primary_span_count", 7))
    best_auprc = metric(narrative.get("best_test_auprc"))
    best_f1 = metric(narrative.get("best_test_f1"))
    energy_f1 = metric(narrative.get("energy_best_f1"))
    current_stage = escape(str(preflight.get("current_stage", "portfolio_narrative_ready")))
    model_id = escape(str(narrative.get("qwen_model_id", "Qwen/Qwen3-0.6B")))
    lock_basis = escape(str(narrative.get("label_lock_basis", "assistant_full_review")))
    positioning = escape(
        str(
            narrative.get(
                "positioning_statement",
                "I build business analytics systems that audit whether generated answers are grounded in transaction evidence.",
            )
        )
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BizHallu GitHub Pages</title>
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
        --shadow: 0 18px 46px rgba(0, 0, 0, 0.08);
        color-scheme: light;
      }}
      * {{ box-sizing: border-box; }}
      html {{ scroll-behavior: smooth; }}
      body {{
        margin: 0;
        background: linear-gradient(180deg, #ffffff 0%, var(--bg) 48%, #eef2f5 100%);
        color: var(--ink);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
        line-height: 1.5;
      }}
      a {{ color: inherit; text-decoration: none; }}
      .topbar {{
        position: sticky;
        top: 0;
        z-index: 20;
        display: flex;
        align-items: center;
        justify-content: space-between;
        min-height: 64px;
        padding: 0 40px;
        background: rgba(246, 247, 249, 0.86);
        border-bottom: 1px solid var(--line);
        backdrop-filter: blur(16px);
      }}
      .brand {{
        display: inline-flex;
        align-items: center;
        gap: 10px;
        font-size: 15px;
        font-weight: 800;
      }}
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
      nav {{ display: flex; gap: 8px; }}
      nav a {{
        min-height: 36px;
        padding: 8px 12px;
        border-radius: 8px;
        color: var(--muted);
        font-size: 14px;
        font-weight: 700;
      }}
      nav a:hover {{ background: rgba(0, 0, 0, 0.06); color: var(--ink); }}
      main {{
        width: min(1160px, calc(100% - 40px));
        margin: 0 auto;
      }}
      .hero {{
        display: grid;
        grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
        gap: 32px;
        align-items: center;
        min-height: calc(100vh - 64px);
        padding: 64px 0 56px;
      }}
      .eyebrow {{
        margin: 0 0 12px;
        color: var(--blue);
        font-size: 13px;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
      }}
      h1, h2, h3, p {{ overflow-wrap: anywhere; }}
      h1 {{
        max-width: 800px;
        margin: 0;
        font-size: clamp(42px, 7vw, 78px);
        line-height: 0.98;
        letter-spacing: 0;
      }}
      h2 {{
        margin: 0;
        font-size: clamp(30px, 4vw, 46px);
        line-height: 1.08;
        letter-spacing: 0;
      }}
      h3 {{
        margin: 0;
        font-size: 18px;
        line-height: 1.25;
        letter-spacing: 0;
      }}
      .hero p {{
        max-width: 760px;
        margin: 24px 0 0;
        color: var(--muted);
        font-size: 21px;
      }}
      .actions {{
        display: flex;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 32px;
      }}
      .button {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 44px;
        padding: 11px 18px;
        border-radius: 8px;
        border: 1px solid transparent;
        font-size: 15px;
        font-weight: 800;
      }}
      .button.primary {{ background: var(--blue); color: white; }}
      .button.secondary {{
        background: rgba(0, 102, 204, 0.08);
        border-color: rgba(0, 102, 204, 0.18);
        color: var(--blue);
      }}
      .snapshot {{
        display: grid;
        gap: 0;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.88);
        box-shadow: var(--shadow);
        backdrop-filter: blur(14px);
      }}
      .snapshot-row {{
        display: grid;
        gap: 6px;
        padding: 22px;
        border-bottom: 1px solid var(--line);
      }}
      .snapshot-row:last-child {{ border-bottom: 0; }}
      .label {{
        color: var(--muted);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
      }}
      .snapshot-row strong {{ font-size: 18px; }}
      .section {{
        padding: 72px 0;
        border-top: 1px solid var(--line);
      }}
      .lede {{
        max-width: 900px;
        margin: 18px 0 0;
        color: var(--muted);
        font-size: 24px;
        line-height: 1.3;
      }}
      .metric-grid, .card-grid {{
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
        margin-top: 30px;
      }}
      .card-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .metric, .card {{
        min-height: 160px;
        padding: 22px;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
      }}
      .metric strong {{
        display: block;
        margin-top: 10px;
        font-size: 34px;
        line-height: 1;
      }}
      .metric p, .card p, li {{
        color: var(--muted);
        font-size: 15px;
      }}
      .card p {{ margin: 10px 0 0; }}
      .card a {{
        color: var(--blue);
        font-weight: 800;
      }}
      .callout {{
        display: grid;
        gap: 14px;
        margin-top: 30px;
        padding: 24px;
        border: 1px solid rgba(15, 118, 110, 0.22);
        border-radius: 8px;
        background: rgba(15, 118, 110, 0.07);
      }}
      .callout strong {{ color: var(--green); }}
      ul {{
        display: grid;
        gap: 10px;
        margin: 22px 0 0;
        padding-left: 20px;
      }}
      code {{
        padding: 2px 5px;
        border-radius: 6px;
        background: rgba(0, 0, 0, 0.06);
        font-family: "SFMono-Regular", Consolas, monospace;
        font-size: 0.95em;
      }}
      footer {{
        padding: 36px 0 56px;
        color: var(--muted);
        border-top: 1px solid var(--line);
        font-size: 14px;
      }}
      @media (max-width: 900px) {{
        .topbar {{ padding: 0 20px; }}
        nav {{ display: none; }}
        main {{ width: min(100% - 28px, 720px); }}
        .hero {{ grid-template-columns: 1fr; min-height: auto; padding-top: 46px; }}
        .metric-grid, .card-grid {{ grid-template-columns: 1fr; }}
      }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <a class="brand" href="#top"><span>BH</span>BizHallu</a>
      <nav aria-label="Page sections">
        <a href="#demo">Demo</a>
        <a href="#results">Results</a>
        <a href="#repo">Repo</a>
        <a href="#claims">Claims</a>
      </nav>
    </header>

    <main id="top">
      <section class="hero">
        <div>
          <p class="eyebrow">GitHub Pages portfolio bundle</p>
          <h1>Auditing hallucinated business facts in LLM retail analysis.</h1>
          <p>{positioning}</p>
          <div class="actions">
            <a class="button primary" href="./portfolio_demo.html">Open interactive demo</a>
            <a class="button secondary" href="./portfolio_narrative.html">Read portfolio narrative</a>
            <a class="button secondary" href="./assets/bizhallu_ai_reliability_deck.pptx">Download interview deck</a>
          </div>
        </div>
        <aside class="snapshot" aria-label="Project snapshot">
          <div class="snapshot-row"><span class="label">Current stage</span><strong>{current_stage}</strong></div>
          <div class="snapshot-row"><span class="label">Model</span><strong>{model_id}</strong></div>
          <div class="snapshot-row"><span class="label">Primary cases</span><strong>{primary_text}</strong></div>
          <div class="snapshot-row"><span class="label">Label basis</span><strong>{lock_basis}</strong></div>
        </aside>
      </section>

      <section id="demo" class="section">
        <p class="eyebrow">What to click first</p>
        <h2>The public demo shows evidence, Qwen answers, span labels, and detector scores.</h2>
        <p class="lede">
          This package is designed for a recruiter, classmate, or interviewer who needs
          to understand the project without rerunning Qwen locally.
        </p>
        <div class="card-grid">
          <article class="card">
            <h3>Interactive case demo</h3>
            <p>Inspect q_0064 and q_0069, including gold evidence, generated answer text, locked span labels, and detector outcomes.</p>
            <p><a href="./portfolio_demo.html">Open demo</a></p>
          </article>
          <article class="card">
            <h3>Portfolio narrative</h3>
            <p>Use this as the source of truth for the project story, resume bullets, LinkedIn wording, and presentation outline.</p>
            <p><a href="./portfolio_narrative.html">Open narrative</a></p>
          </article>
          <article class="card">
            <h3>Detector interpretation</h3>
            <p>Read how AUPRC, F1, simple uncertainty signals, and energy-family baselines should be interpreted.</p>
            <p><a href="./detector_interpretation.html">Open interpretation</a></p>
          </article>
          <article class="card">
            <h3>Interview deck</h3>
            <p>Use the 10-slide PowerPoint deck for a concise walkthrough of motivation, pipeline, results, cases, and positioning.</p>
            <p><a href="./assets/bizhallu_ai_reliability_deck.pptx">Download PPTX</a> / <a href="./assets/bizhallu_ai_reliability_deck_contact_sheet.png">Preview slides</a></p>
          </article>
        </div>
      </section>

      <section id="results" class="section">
        <p class="eyebrow">Validated experiment summary</p>
        <h2>Small enough to audit, complete enough to show real evaluation discipline.</h2>
        <div class="metric-grid">
          <article class="metric"><span class="label">Gold questions</span><strong>{question_count}</strong><p>Deterministic business questions generated from Online Retail evidence.</p></article>
          <article class="metric"><span class="label">Annotated spans</span><strong>{span_count}</strong><p>Held-out high-priority business fact spans aligned to token traces.</p></article>
          <article class="metric"><span class="label">Best test AUPRC</span><strong>{best_auprc}</strong><p>Best split-safe ranking metric from the simple detector family.</p></article>
          <article class="metric"><span class="label">Best test F1</span><strong>{best_f1}</strong><p>Best split-safe threshold metric; energy-family best F1 is {energy_f1}.</p></article>
        </div>
        <div class="callout">
          <strong>Central finding</strong>
          <span>
            Qwen can produce fluent business analysis while binding real transaction
            values to the wrong product, rank, or conclusion. The detector results
            should be discussed at span level, not as whole-answer correctness.
          </span>
        </div>
      </section>

      <section id="repo" class="section">
        <p class="eyebrow">Repository map</p>
        <h2>What belongs in GitHub and what stays local.</h2>
        <div class="card-grid">
          <article class="card">
            <h3>Track</h3>
            <p><code>src/</code>, <code>configs/</code>, <code>docs/</code>, <code>reports/</code>, <code>results/</code>, README files, and lightweight validation summaries.</p>
          </article>
          <article class="card">
            <h3>Keep local</h3>
            <p>Raw Online Retail files, full model traces, Hugging Face cache, model weights, and unmodified external baseline repositories.</p>
          </article>
          <article class="card">
            <h3>Reproduce</h3>
            <p>Use <code>README.md</code> and <code>docs/project_blueprint.md</code> for the pipeline. The public pages are generated from validated reports.</p>
          </article>
        </div>
      </section>

      <section id="claims" class="section">
        <p class="eyebrow">Presentation guardrails</p>
        <h2>The strongest public version is honest about scope.</h2>
        <ul>
          <li>Say the project evaluates span-level business facts, not full report truthfulness.</li>
          <li>Say labels are locked for presentation with <code>{lock_basis}</code>; do not claim a large human-labeled benchmark.</li>
          <li>Say the data source is UCI Online Retail and the model run is local <code>{model_id}</code>.</li>
          <li>Use q_0064 and q_0069 as the main case studies because they show realistic business-risk errors.</li>
          <li>Frame the project as business analytics and AI reliability, not as a generic sales dashboard.</li>
        </ul>
      </section>
    </main>

    <footer>
      <main>
        GitHub Pages bundle generated from validated BizHallu artifacts. Public demo spans: {locked_primary}.
      </main>
    </footer>
  </body>
</html>
"""


def copy_html_pages() -> list[dict[str, Any]]:
    records = []
    for source, dest, role in PAGE_COPIES:
        if not source.exists():
            raise FileNotFoundError(source)
        original = source.read_text(encoding="utf-8")
        transformed = rewrite_links(original)
        dest.write_text(transformed, encoding="utf-8")
        records.append(
            {
                "role": role,
                "source": str(source),
                "dest": str(dest),
                "source_sha256": sha256_text(original),
                "dest_sha256": sha256_file(dest),
                "dest_size_bytes": dest.stat().st_size,
            }
        )
    return records


def copy_assets() -> list[dict[str, Any]]:
    records = []
    for source, dest, role in ASSET_COPIES:
        if not source.exists():
            raise FileNotFoundError(source)
        shutil.copyfile(source, dest)
        records.append(
            {
                "role": role,
                "source": str(source),
                "dest": str(dest),
                "source_sha256": sha256_file(source),
                "dest_sha256": sha256_file(dest),
                "dest_size_bytes": dest.stat().st_size,
            }
        )
    return records


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    DOCS_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    demo = load_json(DEMO_SUMMARY_PATH)
    narrative = load_json(NARRATIVE_SUMMARY_PATH)
    preflight = load_json(PREFLIGHT_VALIDATION_PATH)

    index_html = render_index(demo, narrative, preflight)
    index_path = DOCS_DIR / "index.html"
    index_path.write_text(index_html, encoding="utf-8")

    page_records = copy_html_pages()
    asset_records = copy_assets()

    manifest = {
        "status": "github_pages_bundle_ready",
        "index_path": str(index_path),
        "index_sha256": sha256_file(index_path),
        "source_demo_summary_path": str(DEMO_SUMMARY_PATH),
        "source_narrative_summary_path": str(NARRATIVE_SUMMARY_PATH),
        "source_preflight_validation_path": str(PREFLIGHT_VALIDATION_PATH),
        "source_preflight_stage": preflight.get("current_stage"),
        "current_stage": "github_pages_ready",
        "primary_question_ids": narrative.get("primary_question_ids"),
        "question_count": narrative.get("question_count"),
        "annotated_span_count": narrative.get("annotated_span_count"),
        "locked_primary_span_count": narrative.get("locked_primary_span_count"),
        "best_test_auprc": narrative.get("best_test_auprc"),
        "best_test_f1": narrative.get("best_test_f1"),
        "energy_best_f1": narrative.get("energy_best_f1"),
        "label_lock_basis": narrative.get("label_lock_basis"),
        "pages": page_records,
        "assets": asset_records,
        "num_failures": 0,
        "failures": [],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")

    print(json.dumps({"status": manifest["status"], "manifest_path": str(MANIFEST_PATH)}, indent=2))


if __name__ == "__main__":
    main()
