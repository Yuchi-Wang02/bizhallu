"""Build a GitHub Pages-ready public bundle for BizHallu.

The experiment-native report pages live in reports/. GitHub Pages is easier to
serve from docs/, so this script copies the validated public-facing reports into
docs/ with stable filenames and rewrites their local navigation links.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from html import escape
from pathlib import Path
from typing import Any

from public_paths import repo_path


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
DOCS_ASSETS_DIR = DOCS_DIR / "assets"
REPORTS_DIR = ROOT / "reports"
RESULTS_DIR = ROOT / "results"

DEMO_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_summary.json"
DEMO_V2_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_v2_summary.json"
CAREER_SUMMARY_PATH = REPORTS_DIR / "bizhallu_career_package_summary.json"
RISK_SUMMARY_PATH = REPORTS_DIR / "bizhallu_business_risk_lens_summary.json"
RESEARCH_SUMMARY_PATH = REPORTS_DIR / "bizhallu_research_one_pager_summary.json"
VERIFIER_SUMMARY_PATH = REPORTS_DIR / "bizhallu_evidence_verifier_pilot_summary.json"
METHODOLOGY_SUMMARY_PATH = REPORTS_DIR / "bizhallu_methodology_hardening_summary.json"
CONFIRMATION_OVERLAP_PATH = REPORTS_DIR / "bizhallu_confirmation_dataset_overlap_report.json"
CONFIRMATION_FEASIBILITY_PATH = REPORTS_DIR / "bizhallu_confirmation_context_feasibility_report.json"
CONFIRMATION_PRECISION_PATH = REPORTS_DIR / "bizhallu_confirmation_precision_review_report.json"
CONFIRMATION_PRECISION_AMENDMENT_PATH = ROOT / "configs" / "confirmation_precision_scope_amendment_v1.json"
CONFIRMATION_CONTEXT_MANIFEST_PATH = REPORTS_DIR / "bizhallu_confirmation_context_manifest_report.json"
CONFIRMATION_QUESTION_DESIGN_PATH = REPORTS_DIR / "bizhallu_confirmation_question_design_report.json"
NARRATIVE_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_narrative_summary.json"
PREFLIGHT_VALIDATION_PATH = ROOT / "results" / "full100_preflight_validation.json"
MANIFEST_PATH = DOCS_DIR / "github_pages_manifest.json"
TEXT_HASH_SUFFIXES = {".csv", ".html", ".json", ".md", ".txt", ".yml", ".yaml"}

PAGE_COPIES = [
    (
        REPORTS_DIR / "bizhallu_portfolio_demo.html",
        DOCS_DIR / "portfolio_demo.html",
        "interactive_demo",
    ),
    (
        REPORTS_DIR / "bizhallu_portfolio_demo_v2.html",
        DOCS_DIR / "portfolio_demo_v2.html",
        "interactive_demo_v2",
    ),
    (
        REPORTS_DIR / "bizhallu_portfolio_narrative.html",
        DOCS_DIR / "portfolio_narrative.html",
        "portfolio_narrative",
    ),
    (
        REPORTS_DIR / "bizhallu_career_package.html",
        DOCS_DIR / "career_package.html",
        "career_package",
    ),
    (
        REPORTS_DIR / "bizhallu_business_risk_lens.html",
        DOCS_DIR / "business_risk_lens.html",
        "business_risk_lens",
    ),
    (
        REPORTS_DIR / "bizhallu_research_one_pager.html",
        DOCS_DIR / "research_one_pager.html",
        "research_one_pager",
    ),
    (
        REPORTS_DIR / "bizhallu_evidence_verifier_pilot.html",
        DOCS_DIR / "evidence_verifier_pilot.html",
        "evidence_verifier_pilot",
    ),
    (
        REPORTS_DIR / "bizhallu_methodology_hardening.html",
        DOCS_DIR / "methodology_hardening.html",
        "methodology_hardening",
    ),
    (
        REPORTS_DIR / "bizhallu_confirmation_dataset_source_audit.html",
        DOCS_DIR / "confirmation_dataset_source_audit.html",
        "confirmation_dataset_source_audit",
    ),
    (
        REPORTS_DIR / "bizhallu_confirmation_dataset_quality.html",
        DOCS_DIR / "confirmation_dataset_quality.html",
        "confirmation_dataset_quality",
    ),
    (
        REPORTS_DIR / "bizhallu_confirmation_dataset_overlap.html",
        DOCS_DIR / "confirmation_dataset_overlap.html",
        "confirmation_dataset_overlap",
    ),
    (
        REPORTS_DIR / "bizhallu_confirmation_context_feasibility.html",
        DOCS_DIR / "confirmation_context_feasibility.html",
        "confirmation_context_feasibility",
    ),
    (
        REPORTS_DIR / "bizhallu_confirmation_precision_review.html",
        DOCS_DIR / "confirmation_precision_review.html",
        "confirmation_precision_review",
    ),
    (
        REPORTS_DIR / "bizhallu_confirmation_context_manifest.html",
        DOCS_DIR / "confirmation_context_manifest.html",
        "confirmation_context_manifest",
    ),
    (
        REPORTS_DIR / "bizhallu_confirmation_set_v1_design.html",
        DOCS_DIR / "confirmation_set_v1_design.html",
        "confirmation_set_v1_design",
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
        REPORTS_DIR / "bizhallu_research_brief.pdf",
        DOCS_ASSETS_DIR / "bizhallu_research_brief.pdf",
        "research_brief_pdf",
    ),
    (
        ROOT / "src" / "assets" / "bizhallu_mark.svg",
        DOCS_ASSETS_DIR / "bizhallu_mark.svg",
        "site_icon_svg",
    ),
    (
        RESULTS_DIR / "full100_draft_detector_error_review_examples.csv",
        DOCS_ASSETS_DIR / "full100_draft_detector_error_review_examples.csv",
        "detector_error_examples_csv",
    ),
    (
        REPORTS_DIR / "bizhallu_demo_v2_data.json",
        DOCS_ASSETS_DIR / "bizhallu_demo_v2_data.json",
        "interactive_demo_v2_data_json",
    ),
    (
        REPORTS_DIR / "bizhallu_evidence_verifier_pilot_rows.csv",
        DOCS_ASSETS_DIR / "bizhallu_evidence_verifier_pilot_rows.csv",
        "evidence_verifier_pilot_rows_csv",
    ),
    (
        REPORTS_DIR / "bizhallu_evidence_verifier_pilot_rows.json",
        DOCS_ASSETS_DIR / "bizhallu_evidence_verifier_pilot_rows.json",
        "evidence_verifier_pilot_rows_json",
    ),
    (
        REPORTS_DIR / "bizhallu_ai_reliability_deck.pptx",
        DOCS_ASSETS_DIR / "bizhallu_ai_reliability_deck.pptx",
        "presentation_deck_pptx",
    ),
    (
        REPORTS_DIR / "bizhallu_interview_v2.pptx",
        DOCS_ASSETS_DIR / "bizhallu_interview_v2.pptx",
        "current_interview_deck_pptx",
    ),
    (
        REPORTS_DIR / "bizhallu_interview_v2_preview.png",
        DOCS_ASSETS_DIR / "bizhallu_interview_v2_preview.png",
        "current_interview_deck_preview_png",
    ),
    (
        REPORTS_DIR / "bizhallu_interview_v2_overview.png",
        DOCS_ASSETS_DIR / "bizhallu_interview_v2_overview.png",
        "current_interview_deck_overview_png",
    ),
    (
        REPORTS_DIR / "bizhallu_ai_reliability_deck_contact_sheet.png",
        DOCS_ASSETS_DIR / "bizhallu_ai_reliability_deck_contact_sheet.png",
        "presentation_deck_contact_sheet_png",
    ),
]

LINK_REWRITES = {
    "../site/index.html": "./index.html",
    "../docs/index.html": "./index.html",
    "../docs/project_blueprint.md": "./project_blueprint.md",
    "../docs/current_state_audit.md": "./current_state_audit.md",
    "../results/full100_draft_detector_error_review_examples.csv": (
        "./assets/full100_draft_detector_error_review_examples.csv"
    ),
    "./bizhallu_portfolio_demo.html": "./portfolio_demo.html",
    "./bizhallu_portfolio_demo_v2.html": "./portfolio_demo_v2.html",
    "./bizhallu_methodology_hardening.html": "./methodology_hardening.html",
    "./bizhallu_research_one_pager.html": "./research_one_pager.html",
    "./bizhallu_confirmation_dataset_source_audit.html": "./confirmation_dataset_source_audit.html",
    "./bizhallu_confirmation_dataset_quality.html": "./confirmation_dataset_quality.html",
    "./bizhallu_confirmation_dataset_overlap.html": "./confirmation_dataset_overlap.html",
    "./bizhallu_confirmation_context_feasibility.html": "./confirmation_context_feasibility.html",
    "./bizhallu_confirmation_precision_review.html": "./confirmation_precision_review.html",
    "./bizhallu_confirmation_context_manifest.html": "./confirmation_context_manifest.html",
    "./bizhallu_confirmation_set_v1_design.html": "./confirmation_set_v1_design.html",
    "./full100_detector_interpretation.html": "./detector_interpretation.html",
    "./full100_label_lock_report.html": "./label_lock_report.html",
    "./full100_label_confirmation_packet.html": "./label_confirmation_packet.html",
}

ARCHIVE_NOTICES = {
    'methodology_hardening': 'Historical methodology audit. Its missing-q_0048 finding describes the original 205-span package; B1 and the separate B2 sensitivity now provide the updated statistical discussion.',
    'label_lock_report': 'Historical assistant-review record for 15 selected presentation spans. A presentation lock is not independent human annotation, owner review, or validation of completed business relationships.',
    'label_confirmation_packet': 'Historical assistant-led confirmation packet, retained for provenance. It is not the current private C1 review workbench or evidence of completed independent human review.',
    'evidence_verifier_pilot': 'Historical label-derived review schema. Its statuses are not predictions from an independent verifier and must not be compared as detector performance.',
}


def archive_notice(role):
    message = ARCHIVE_NOTICES.get(role)
    if message is None:
        return ''
    return ('<aside id="archive-notice" aria-label="Historical artifact scope" '
            'style="padding:16px 24px;background:#fff;color:#202124;border-bottom:2px solid #9a6700;font:15px/1.5 Arial,sans-serif">'
            '<strong>Historical artifact.</strong> '+escape(message)+
            ' <a href="./detector_interpretation.html#b2-dev-sensitivity">Current methods and sensitivity</a> | '
            '<a href="./portfolio_demo_v2.html">Current cases</a>.</aside>')


def add_archive_notice(text, role):
    notice = archive_notice(role)
    if not notice:
        return text
    if 'id="archive-notice"' in text:
        raise ValueError('Source already contains an archive notice')
    result, count = re.subn(r'(<body\b[^>]*>)', lambda match:match[0]+notice, text, count=1, flags=re.IGNORECASE)
    if count != 1:
        raise ValueError('Archived page has no body')
    return result


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    if path.suffix.lower() in TEXT_HASH_SUFFIXES:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
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


def render_index(
    demo: dict[str, Any],
    demo_v2: dict[str, Any],
    career: dict[str, Any],
    risk: dict[str, Any],
    research: dict[str, Any],
    verifier: dict[str, Any],
    methodology: dict[str, Any],
    confirmation_overlap: dict[str, Any],
    confirmation_feasibility: dict[str, Any],
    confirmation_precision: dict[str, Any],
    confirmation_precision_amendment: dict[str, Any],
    confirmation_context_manifest: dict[str, Any],
    confirmation_question_design: dict[str, Any],
    narrative: dict[str, Any],
    preflight: dict[str, Any],
) -> str:
    from presentation_evidence import statistical_context, statistics_html, walkthrough, METRIC_NOTE
    data = load_json(REPORTS_DIR / 'bizhallu_demo_v2_data.json')
    example = walkthrough(next(c for c in data['cases'] if c['question_id']=='q_0064'))['claims'][2]
    stats = statistical_context()
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>BizHallu | Evidence-grounded business analysis</title>
<meta name="description" content="An exploratory study of evidence-binding errors in AI-generated business analysis. Inspect retail cases, methods, limitations and a research collaboration brief.">
<style>
*{{box-sizing:border-box;letter-spacing:0}}body{{margin:0;background:#f6f7f9;color:#202124;font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif}}main,nav,footer{{max-width:1050px;margin:auto;padding:20px 26px}}nav{{display:flex;align-items:center;gap:12px 22px;flex-wrap:wrap;border-bottom:1px solid #d6dde0;font-size:14px}}nav .brand{{margin-right:auto;color:#202124;font-weight:750}}nav a{{min-height:32px;display:inline-flex;align-items:center}}nav [aria-current="page"]{{font-weight:750;text-decoration-thickness:2px}}a{{color:#145e77;text-underline-offset:3px}}a:focus-visible,summary:focus-visible,[tabindex]:focus-visible{{outline:3px solid #145e77;outline-offset:4px;border-radius:3px}}.skip-link{{position:absolute;left:16px;top:-100px;background:#fff;padding:12px;z-index:20}}.skip-link:focus{{top:12px}}h1{{max-width:880px;font-size:34px;margin:4px 0 16px;line-height:1.2}}h2{{font-size:22px;margin:8px 0}}h3{{font-size:18px;margin:8px 0}}p{{margin:8px 0 14px}}section{{padding:20px 0 26px;border-bottom:1px solid #d6dde0}}.eyebrow{{color:#145e77;font-size:14px;font-weight:700}}.muted,footer{{color:#57636b;font-size:14px}}.case-proof{{border-left:3px solid #18765e;padding:3px 18px;margin:22px 0}}.routes{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin-top:18px}}.route{{min-width:0;padding:18px 20px;background:#fff;border:1px solid #d6dde0;border-radius:8px}}.route p{{color:#57636b}}.route a{{display:inline-block;font-weight:650;padding:5px 0}}.entry-links{{display:flex;flex-wrap:wrap;gap:12px 22px;margin:18px 0}}.entry-links a{{font-weight:650}}table{{border-collapse:collapse;width:100%;font-size:14px}}td,th{{border-bottom:1px solid #d6dde0;text-align:left;padding:9px}}td,th{{min-width:88px}}summary{{cursor:pointer;font-weight:700;padding:18px 0}}li{{margin:8px 0}}.scroll{{overflow:auto}}h1,h2,h3,p,li,td,th{{overflow-wrap:anywhere}}@media(max-width:650px){{main,nav,footer{{padding:16px}}nav{{gap:8px 16px}}nav .brand{{flex-basis:100%}}h1{{font-size:30px}}.routes{{grid-template-columns:1fr;gap:12px}}}}
</style></head><body>
<a class="skip-link" href="#main">Skip to content</a>
<nav aria-label="Primary"><a class="brand" href="./index.html">BizHallu</a><a href="./index.html" aria-current="page">Home</a><a href="./portfolio_demo_v2.html">Cases</a><a href="./detector_interpretation.html">Methods</a><a href="./research_one_pager.html">Research</a><a href="https://github.com/Yuchi-Wang02/bizhallu">GitHub</a></nav>
<main id="main">
<section><p class="eyebrow">BizHallu · Exploratory research in business analytics and AI reliability</p><h1>Can the right number support the wrong business claim?</h1>
<p>AI-generated analysis can copy a real product and its exact transaction value, yet assign it the wrong rank. BizHallu studies these evidence-binding errors through retail transactions, inspectable model answers and span-level evaluation.</p>
<p class="muted">Yuchi Wang · MS student in Business Analytics and Artificial Intelligence · Johns Hopkins Carey Business School</p>
<p class="muted">Independent exploratory project · Accounting and supply-management background · AI-assisted implementation and review</p>
<div class="entry-links"><a href="./research_one_pager.html">Start with the research brief</a><a href="./portfolio_demo_v2.html?case=q_0064">Inspect one worked case</a></div>
<div class="case-proof"><h2>A correct amount, an incorrect rank</h2>
<p>April 2011: Qwen placed <strong>{escape(example['product_name'])}</strong> at rank {example['stated_rank']}, with GBP {escape(example['amount_lexical'])}. That amount matches its product row, but the product is <strong>rank {example['rank_in_shown_evidence']}</strong> in the eight evidence rows shown to the model.</p>
<p>Rank 3 instead belongs to {escape(example['expected_product_at_stated_rank'])}, at GBP {escape(example['expected_amount_at_stated_rank'])}. <a href="./portfolio_demo_v2.html?case=q_0064">Open the April case</a> · <a href="./portfolio_demo_v2.html?case=q_0069">Compare September</a></p></div>
<p class="muted">A curated, assistant-reviewed explanation, not an independent verifier prediction. A low score on an early list marker is not proof of confidence in the completed relationship.</p></section>
<section aria-labelledby="review-paths"><h2 id="review-paths">Choose a reading path</h2>
<p>The research brief frames the question. Cases show the evidence; methods explain what the results can support.</p>
<div class="routes">
<article class="route"><h3>Research</h3><p>A concise problem statement, one worked example and a specific request for feedback on annotation and comparison design.</p><a href="./research_one_pager.html">Research one-pager</a></article>
<article class="route"><h3>Cases</h3><p>Inspect original answers and evidence rows, then distinguish correct amount copying from correct product ranking.</p><a href="./portfolio_demo_v2.html">Open demo v2</a></article>
<article class="route"><h3>Methods</h3><p>Check provisional labels, dev-selected thresholds, simple references, uncertainty and the limits of the existing test set.</p><a href="./detector_interpretation.html">Methods and results</a></article>
<article class="route"><h3>Presentation</h3><p>A ten-slide walkthrough of the business example, exploratory results and open research questions.</p><a href="./assets/bizhallu_interview_v2.pptx" download>Download current PPTX</a><p><a href="./assets/bizhallu_interview_v2_overview.png">Preview all ten slides</a></p></article>
</div>
</section>
<section><h2>An auditable exploratory workflow</h2><p>{narrative['question_count']} deterministic business questions; {narrative['qwen_record_count']} local {escape(narrative['qwen_model_id'])} answers; {narrative['annotated_span_count']} AI-assisted provisional spans from 35 dev/test questions. Fifteen selected spans received additional assistant review. No independent human agreement or whole-answer accuracy is claimed.</p>
<p>B1 covers all 18 test questions and 103 pre-identified test spans. B2 separately adds provisional atoms for the omitted dev answer q_0048 and checks threshold sensitivity. Original labels and results remain historical provenance, not a new confirmation study.</p>
<p><strong>Evidence boundary:</strong> the original annotation queue was outcome-informed and error-enriched. Development and test examples share periods and evidence contexts. Thresholds were selected on development data, while headline signals were selected after test comparison.</p></section>
<section><h2>What the results support</h2><p>The cases demonstrate a distinction between copying a value correctly and stating a correct relationship. The exploratory detector results do not establish stable superiority over simple references. Entropy F1 is 0.779 versus 0.744 for flagging every span in B1; its paired difference interval crosses zero. The separate B2 dev-omission check changes entropy F1 to 0.752 on the same old test.</p>
<p><a href="./detector_interpretation.html#statistical-review">Read the statistical interpretation</a> or <a href="./detector_interpretation.html#b2-dev-sensitivity">inspect the B2 sensitivity</a>.</p>
<details><summary>Detailed B1 reference table and sensitivity note</summary>{statistics_html(stats)}</details></section>
<section><h2>Business scope</h2><p>{escape(METRIC_NOTE)}</p><p>The project motivates controls for revenue summaries and product prioritization; it does not demonstrate realized savings, profit improvement, physical-return rates or inventory optimization. The <a href="./business_risk_lens.html">business risk lens</a> explains the transaction-value reconciliation and accounting boundaries.</p></section>
<details><summary>Supporting materials and historical study records</summary>
<p>Start with Cases, Methods and Research for the current explanation. The supporting materials below provide business context and preserve earlier study records; preparation and assistant review do not establish independent validation.</p>
<ul>
<li><a href="./assets/bizhallu_interview_v2.pptx" download>English interview deck v2</a> · <a href="./assets/bizhallu_interview_v2_preview.png">Statistical slide preview</a></li>
<li><a href="./portfolio_demo.html">Historical spans, updated interpretation</a> · <a href="./portfolio_narrative.html">Portfolio narrative</a></li>
<li><a href="./career_package.html">Career package</a> · <a href="./business_risk_lens.html">Business risk lens</a></li>
<li><a href="./evidence_verifier_pilot.html">Claim-Evidence Review Schema v0</a>: label-derived organization, not an independent verifier.</li>
<li><a href="./methodology_hardening.html">Methodology audit</a> · <a href="./confirmation_set_v1_design.html">Confirmation study design</a></li>
<li><a href="./confirmation_dataset_source_audit.html">Source audit</a> · <a href="./confirmation_dataset_quality.html">Quality profile</a> · <a href="./confirmation_dataset_overlap.html">Overlap analysis</a></li>
<li><a href="./confirmation_context_feasibility.html">Capacity proof</a> · <a href="./confirmation_precision_review.html">Precision review</a> · <a href="./confirmation_context_manifest.html">Manifest commitment</a></li>
<li><a href="./assets/bizhallu_ai_reliability_deck.pptx">Historical PPTX</a> · <a href="./assets/bizhallu_ai_reliability_deck_contact_sheet.png">Historical slide preview</a></li>
</ul><p>The 48-context / 96-question next study is estimation-focused and has not been executed. Confirmation remains sealed. The v1.1 business-definition amendment retains the original contexts and splits; preparation is not an outcome.</p>
</details>
</main><footer>Evidence-grounded business analysis · <a href="https://github.com/Yuchi-Wang02/bizhallu">GitHub repository</a>. Public artifact validation is separate from scientific validity.</footer>
</body></html>
"""


def add_public_metadata(text: str, dest: Path) -> str:
    """Give rendered pages a stable identity when linked or forwarded."""
    base = "https://yuchi-wang02.github.io/bizhallu/"
    title_match = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    title = title_match.group(1) if title_match else "BizHallu"
    description = "Exploratory evidence checks for AI-generated business analysis. Inspect retail cases, provisional span evaluations and the proposed relation-annotation study."
    additions = []
    if not re.search(r'<meta\s+name=[\"\']description[\"\']', text, re.IGNORECASE):
        additions.append(f'<meta name="description" content="{description}">')
    additions.extend([
        '<link rel="icon" type="image/svg+xml" href="./assets/bizhallu_mark.svg">',
        f'<link rel="canonical" href="{base}{dest.name}">',
        '<meta name="theme-color" content="#18765e">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:title" content="{escape(title, quote=True)}">',
        f'<meta property="og:description" content="{description}">',
        f'<meta property="og:url" content="{base}{dest.name}">',
    ])
    return text.replace('</head>', '\n'.join(additions) + '\n</head>', 1)


def copy_html_pages() -> list[dict[str, Any]]:
    records = []
    for source, dest, role in PAGE_COPIES:
        if not source.exists():
            raise FileNotFoundError(source)
        original = source.read_text(encoding="utf-8")
        transformed = add_public_metadata(add_archive_notice(rewrite_links(original), role), dest)
        dest.write_text(transformed, encoding="utf-8")
        records.append(
            {
                "role": role,
                "archive_notice": role in ARCHIVE_NOTICES,
                "source": repo_path(source),
                "dest": repo_path(dest),
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
                "source": repo_path(source),
                "dest": repo_path(dest),
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
    demo_v2 = load_json(DEMO_V2_SUMMARY_PATH)
    career = load_json(CAREER_SUMMARY_PATH)
    risk = load_json(RISK_SUMMARY_PATH)
    research = load_json(RESEARCH_SUMMARY_PATH)
    verifier = load_json(VERIFIER_SUMMARY_PATH)
    methodology = load_json(METHODOLOGY_SUMMARY_PATH)
    confirmation_overlap = load_json(CONFIRMATION_OVERLAP_PATH)
    confirmation_feasibility = load_json(CONFIRMATION_FEASIBILITY_PATH)
    confirmation_precision = load_json(CONFIRMATION_PRECISION_PATH)
    confirmation_precision_amendment = load_json(CONFIRMATION_PRECISION_AMENDMENT_PATH)
    confirmation_context_manifest = load_json(CONFIRMATION_CONTEXT_MANIFEST_PATH)
    confirmation_question_design = load_json(CONFIRMATION_QUESTION_DESIGN_PATH)
    narrative = load_json(NARRATIVE_SUMMARY_PATH)
    preflight = load_json(PREFLIGHT_VALIDATION_PATH)

    index_html = render_index(
        demo,
        demo_v2,
        career,
        risk,
        research,
        verifier,
        methodology,
        confirmation_overlap,
        confirmation_feasibility,
        confirmation_precision,
        confirmation_precision_amendment,
        confirmation_context_manifest,
        confirmation_question_design,
        narrative,
        preflight,
    )
    index_path = DOCS_DIR / "index.html"
    index_path.write_text(add_public_metadata(index_html, index_path), encoding="utf-8")

    page_records = copy_html_pages()
    asset_records = copy_assets()

    manifest = {
        "status": "github_pages_bundle_ready",
        "index_path": repo_path(index_path),
        "index_sha256": sha256_file(index_path),
        "source_demo_summary_path": repo_path(DEMO_SUMMARY_PATH),
        "source_demo_v2_summary_path": repo_path(DEMO_V2_SUMMARY_PATH),
        "source_career_summary_path": repo_path(CAREER_SUMMARY_PATH),
        "source_risk_summary_path": repo_path(RISK_SUMMARY_PATH),
        "source_research_summary_path": repo_path(RESEARCH_SUMMARY_PATH),
        "source_verifier_summary_path": repo_path(VERIFIER_SUMMARY_PATH),
        "source_methodology_summary_path": repo_path(METHODOLOGY_SUMMARY_PATH),
        "source_confirmation_overlap_path": repo_path(CONFIRMATION_OVERLAP_PATH),
        "source_confirmation_feasibility_path": repo_path(CONFIRMATION_FEASIBILITY_PATH),
        "source_confirmation_precision_path": repo_path(CONFIRMATION_PRECISION_PATH),
        "source_confirmation_precision_amendment_path": repo_path(CONFIRMATION_PRECISION_AMENDMENT_PATH),
        "source_confirmation_context_manifest_path": repo_path(CONFIRMATION_CONTEXT_MANIFEST_PATH),
        "source_confirmation_question_design_path": repo_path(CONFIRMATION_QUESTION_DESIGN_PATH),
        "source_narrative_summary_path": repo_path(NARRATIVE_SUMMARY_PATH),
        "source_preflight_validation_path": repo_path(PREFLIGHT_VALIDATION_PATH),
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
        "demo_v2_case_count": demo_v2.get("case_count"),
        "demo_v2_locked_span_count": demo_v2.get("locked_span_count"),
        "career_faq_count": career.get("faq_count"),
        "business_risk_lens_count": risk.get("lens_count"),
        "research_extension_count": research.get("extension_count"),
        "verifier_pilot_span_count": verifier.get("span_count"),
        "verifier_pilot_contradicted_count": (verifier.get("review_status_counts") or {}).get("contradicted"),
        "methodology_status": methodology.get("status"),
        "methodology_share_status": methodology.get("share_status"),
        "methodology_heldout_question_count": methodology.get("audit", {}).get("heldout_question_count"),
        "methodology_annotated_heldout_question_count": methodology.get("audit", {}).get("annotated_heldout_question_count"),
        "methodology_cross_split_evidence_group_count": methodology.get("audit", {}).get("exact_evidence_row_cross_split_group_count"),
        "confirmation_historical_overlap_status": confirmation_overlap.get("status"),
        "confirmation_canonical_overlap_row_count": confirmation_overlap.get("record_overlap", {}).get("canonical_eight_field", {}).get("multiset_overlap_row_count"),
        "confirmation_date_blind_overlap_row_count": confirmation_overlap.get("record_overlap", {}).get("date_blind_seven_field_sensitivity", {}).get("multiset_overlap_row_count"),
        "confirmation_context_feasibility_status": confirmation_feasibility.get("status"),
        "confirmation_context_feasibility_complete": confirmation_feasibility.get("context_feasibility_check_complete"),
        "confirmation_observed_complete_period_count": confirmation_feasibility.get("source_capacity", {}).get("observed_complete_period_count"),
        "confirmation_required_context_count": confirmation_feasibility.get("capacity_proof", {}).get("required_total_context_count"),
        "confirmation_maximum_slot_matching_count": confirmation_feasibility.get("capacity_proof", {}).get("maximum_slot_matching_count"),
        "confirmation_minimum_hall_capacity_slack": confirmation_feasibility.get("capacity_proof", {}).get("minimum_hall_capacity_slack"),
        "confirmation_context_manifest_status": confirmation_context_manifest.get("status"),
        "confirmation_context_manifest_created": confirmation_context_manifest.get("execution_boundary", {}).get("context_manifest_created"),
        "confirmation_split_assignment_created": confirmation_context_manifest.get("execution_boundary", {}).get("split_assignment_created"),
        "confirmation_context_manifest_commitment_sha256": confirmation_context_manifest.get("private_manifest_commitment", {}).get("canonical_sha256"),
        "confirmation_context_manifest_selected_context_count": confirmation_context_manifest.get("frozen_inventory", {}).get("selected_context_count"),
        "confirmation_context_manifest_reserve_period_count": confirmation_context_manifest.get("frozen_inventory", {}).get("reserve_period_count"),
        "confirmation_question_design_status": confirmation_question_design.get("status"),
        "confirmation_question_manifest_commitment_sha256": confirmation_question_design.get("private_question_manifest_commitment", {}).get("canonical_sha256"),
        "confirmation_question_count": confirmation_question_design.get("frozen_inventory", {}).get("question_count"),
        "confirmation_question_template_count": len(confirmation_question_design.get("frozen_inventory", {}).get("template_counts", {})),
        "confirmation_question_payload_fingerprint_check": confirmation_question_design.get("evidence_payload_integrity", {}).get("question_level_evidence_payload_fingerprint_check"),
        "confirmation_question_payload_cross_split_overlap_count": confirmation_question_design.get("evidence_payload_integrity", {}).get("cross_split_fingerprint_count"),
        "confirmation_question_evidence_content_fingerprint_count": confirmation_question_design.get("evidence_payload_integrity", {}).get("unique_content_fingerprint_count"),
        "confirmation_question_evidence_content_cross_split_overlap_count": confirmation_question_design.get("evidence_payload_integrity", {}).get("content_cross_split_fingerprint_count"),
        "confirmation_historical_unique_evidence_content_fingerprint_count": confirmation_question_design.get("evidence_payload_integrity", {}).get("historical_full100_content_fingerprint_count"),
        "confirmation_question_evidence_content_historical_overlap_count": confirmation_question_design.get("evidence_payload_integrity", {}).get("historical_full100_content_fingerprint_overlap_count"),
        "confirmation_question_created": confirmation_question_design.get("execution_boundary", {}).get("question_created"),
        "confirmation_prompt_created": confirmation_question_design.get("execution_boundary", {}).get("prompt_created"),
        "confirmation_precision_review_status": confirmation_precision.get("status"),
        "confirmation_precision_candidate_count": len(confirmation_precision.get("candidate_summaries", [])),
        "confirmation_precision_passing_candidate_count": confirmation_precision_amendment.get("failed_strong_comparison_design", {}).get("passing_candidate_count"),
        "confirmation_precision_thresholds_changed_after_simulation": confirmation_precision_amendment.get("failed_strong_comparison_design", {}).get("thresholds_changed_after_simulation"),
        "confirmation_precision_scope_amendment_status": confirmation_precision_amendment.get("status"),
        "confirmation_precision_scope_decision": confirmation_precision_amendment.get("scope_amendment", {}).get("decision"),
        "confirmation_selected_confirmation_context_count": confirmation_precision_amendment.get("revised_planning_counts", {}).get("confirmation_context_count"),
        "confirmation_selected_total_context_count": confirmation_precision_amendment.get("revised_planning_counts", {}).get("total_context_count"),
        "confirmation_selected_total_question_count": confirmation_precision_amendment.get("revised_planning_counts", {}).get("total_question_count"),
        "confirmation_context_manifest_authorized": confirmation_precision_amendment.get("gate_effect", {}).get("context_manifest_authorized_now"),
        "annotation_status": "205_ai_assisted_provisional_15_additionally_reviewed",
        "metric_selection_status": "exploratory_test_maxima",
        "automatic_claim_extraction": False,
        "independent_human_annotation": False,
        "pages": page_records,
        "assets": asset_records,
        "num_failures": 0,
        "failures": [],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")

    print(json.dumps({"status": manifest["status"], "manifest_path": repo_path(MANIFEST_PATH)}, indent=2))


if __name__ == "__main__":
    main()
