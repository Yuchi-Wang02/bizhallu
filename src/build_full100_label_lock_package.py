from __future__ import annotations

import csv
import html
import json
from collections import Counter
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"

REVIEW_NOTES_JSONL_PATH = REPORTS_DIR / "full100_label_confirmation_review_notes.jsonl"
REVIEW_NOTES_SUMMARY_PATH = REPORTS_DIR / "full100_label_confirmation_review_notes_summary.json"
DETECTOR_INTERPRETATION_SUMMARY_PATH = REPORTS_DIR / "full100_detector_interpretation_summary.json"

LOCK_DECISIONS_CSV_PATH = REPORTS_DIR / "full100_label_lock_decisions.csv"
LOCK_DECISIONS_JSONL_PATH = REPORTS_DIR / "full100_label_lock_decisions.jsonl"
LOCK_SUMMARY_PATH = REPORTS_DIR / "full100_label_lock_summary.json"
LOCK_REPORT_HTML_PATH = REPORTS_DIR / "full100_label_lock_report.html"

LOCK_BASIS = "assistant_full_review"
LOCK_STATUS = "presentation_labels_locked"
LOCK_SCOPE = "15 presentation-selected held-out spans"
LOCKED_ON = "2026-05-25"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=True) + "\n")


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def publish_use_for(row: dict[str, Any]) -> str:
    presentation_use = row["presentation_use"]
    if presentation_use in {"paired_contrast_example", "strong_false_negative_example"}:
        return "primary_demo"
    if presentation_use == "span_level_caveat":
        return "caveat_demo"
    if presentation_use == "offset_check_only":
        return "qa_regression_only"
    return "supporting_detail"


def lock_reason_for(row: dict[str, Any]) -> str:
    if row["presentation_use"] == "paired_contrast_example":
        return "Locked as a primary paired example because it contains nearby supported and hallucinated spans."
    if row["presentation_use"] == "strong_false_negative_example":
        return "Locked as a primary miss example because detectors missed a clear hallucinated business fact."
    if row["presentation_use"] == "span_level_caveat":
        return "Locked for caveat use only because the selected span is supported but the surrounding answer has other errors."
    if row["presentation_use"] == "offset_check_only":
        return "Locked as a QA regression example for rank-marker offset correctness."
    return "Locked after assistant full review."


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    review_rows = load_jsonl(REVIEW_NOTES_JSONL_PATH)
    review_summary = load_json(REVIEW_NOTES_SUMMARY_PATH)
    detector_summary = load_json(DETECTOR_INTERPRETATION_SUMMARY_PATH)

    source_fix_required = [row for row in review_rows if row.get("source_action") != "none"]
    unsupported = [row for row in review_rows if row.get("assistant_label_verdict") != "label_supported"]
    if source_fix_required or unsupported:
        raise SystemExit(
            "Cannot lock labels with unresolved review rows: "
            f"source_fix_required={len(source_fix_required)}, unsupported={len(unsupported)}"
        )

    lock_date = LOCKED_ON
    decisions: list[dict[str, Any]] = []
    for row in review_rows:
        publish_use = publish_use_for(row)
        decisions.append(
            {
                "confirmation_item_id": row["confirmation_item_id"],
                "annotation_id": row["annotation_id"],
                "question_id": row["question_id"],
                "split": row["split"],
                "question_type": row["question_type"],
                "fact_type": row["fact_type"],
                "label": row["label"],
                "span_text": row["span_text"],
                "lock_decision": "locked",
                "lock_status": LOCK_STATUS,
                "lock_basis": LOCK_BASIS,
                "lock_scope": LOCK_SCOPE,
                "locked_on": lock_date,
                "labels_locked": True,
                "assistant_label_verdict": row["assistant_label_verdict"],
                "presentation_use": row["presentation_use"],
                "publish_use": publish_use,
                "demo_priority": row["demo_priority"],
                "risk_level": row["risk_level"],
                "source_action": row["source_action"],
                "source_fix_required": False,
                "span_level_caveat": row["presentation_use"] == "span_level_caveat",
                "review_note": row["review_note"],
                "lock_reason": lock_reason_for(row),
                "detector_role_text": row["detector_role_text"],
                "highlighted_excerpt": row["highlighted_excerpt"],
                "gold_short_answer": row["gold_short_answer"],
            }
        )

    fieldnames = [
        "confirmation_item_id",
        "annotation_id",
        "question_id",
        "split",
        "question_type",
        "fact_type",
        "label",
        "span_text",
        "lock_decision",
        "lock_status",
        "lock_basis",
        "lock_scope",
        "locked_on",
        "labels_locked",
        "assistant_label_verdict",
        "presentation_use",
        "publish_use",
        "demo_priority",
        "risk_level",
        "source_action",
        "source_fix_required",
        "span_level_caveat",
        "review_note",
        "lock_reason",
        "detector_role_text",
        "highlighted_excerpt",
        "gold_short_answer",
    ]
    with LOCK_DECISIONS_CSV_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(decisions)
    write_jsonl(LOCK_DECISIONS_JSONL_PATH, decisions)

    by_label = Counter(row["label"] for row in decisions)
    by_publish_use = Counter(row["publish_use"] for row in decisions)
    by_presentation_use = Counter(row["presentation_use"] for row in decisions)
    by_demo_priority = Counter(row["demo_priority"] for row in decisions)
    high_priority_ids = [row["confirmation_item_id"] for row in decisions if row["demo_priority"] == "high"]
    primary_question_ids = sorted({row["question_id"] for row in decisions if row["publish_use"] == "primary_demo"})

    summary = {
        "status": LOCK_STATUS,
        "review_status": "locked_after_assistant_full_review",
        "lock_basis": LOCK_BASIS,
        "lock_scope": LOCK_SCOPE,
        "locked_on": lock_date,
        "labels_locked": True,
        "human_confirmation_required": False,
        "source_review_notes_summary_path": repo_path(REVIEW_NOTES_SUMMARY_PATH),
        "source_detector_interpretation_summary_path": repo_path(DETECTOR_INTERPRETATION_SUMMARY_PATH),
        "label_lock_decisions_csv_path": repo_path(LOCK_DECISIONS_CSV_PATH),
        "label_lock_decisions_jsonl_path": repo_path(LOCK_DECISIONS_JSONL_PATH),
        "label_lock_report_html_path": repo_path(LOCK_REPORT_HTML_PATH),
        "selected_annotation_count": len(decisions),
        "selected_question_count": len({row["question_id"] for row in decisions}),
        "locked_label_count": sum(1 for row in decisions if row["lock_decision"] == "locked"),
        "source_fix_required_count": sum(1 for row in decisions if row["source_fix_required"]),
        "assistant_supported_count": sum(1 for row in decisions if row["assistant_label_verdict"] == "label_supported"),
        "by_label": dict(sorted(by_label.items())),
        "by_publish_use": dict(sorted(by_publish_use.items())),
        "by_presentation_use": dict(sorted(by_presentation_use.items())),
        "by_demo_priority": dict(sorted(by_demo_priority.items())),
        "high_priority_confirmation_item_ids": high_priority_ids,
        "primary_demo_question_ids": primary_question_ids,
        "span_level_caveat_count": by_presentation_use.get("span_level_caveat", 0),
        "qa_regression_only_count": by_publish_use.get("qa_regression_only", 0),
        "detector_claims_locked_for_use": {
            "best_test_auprc_baseline": detector_summary["best_overall_by_test_auprc"]["baseline"],
            "best_test_auprc": detector_summary["best_overall_by_test_auprc"]["test_auprc"],
            "best_test_f1_baseline": detector_summary["best_overall_by_test_f1"]["baseline"],
            "best_test_f1": detector_summary["best_overall_by_test_f1"]["test_f1"],
            "error_row_count": detector_summary["error_row_count"],
        },
        "presentation_guardrails": [
            "Report detector results as span-level hallucination detection, not whole-answer correctness.",
            "Use q_0064 and q_0069 as primary portfolio examples.",
            "Use span_level_caveat rows only with explicit surrounding-answer caveats.",
            "Keep offset_check_only rows as QA/regression evidence rather than headline detector examples.",
        ],
        "source_review_status": review_summary.get("status"),
        "num_failures": 0,
        "failures": [],
    }

    cards = []
    for row in decisions:
        cards.append(
            f"""
        <article class="item-card {esc(row['publish_use'])}">
          <div class="item-top">
            <span class="tag">{esc(row['confirmation_item_id'])}</span>
            <span class="status">{esc(row['publish_use'])}</span>
          </div>
          <h3>{esc(row['question_id'])} - {esc(row['fact_type'])} - {esc(row['label'])}</h3>
          <p class="excerpt">{esc(row['highlighted_excerpt'])}</p>
          <dl>
            <dt>Lock decision</dt><dd>{esc(row['lock_decision'])}</dd>
            <dt>Lock reason</dt><dd>{esc(row['lock_reason'])}</dd>
            <dt>Presentation use</dt><dd>{esc(row['presentation_use'])}</dd>
            <dt>Detector role</dt><dd>{esc(row['detector_role_text'])}</dd>
            <dt>Review note</dt><dd>{esc(row['review_note'])}</dd>
          </dl>
        </article>"""
        )

    html_text = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BizHallu Label Lock Report</title>
    <style>
      :root {{
        --bg: #f5f5f7;
        --surface: #ffffff;
        --text: #1d1d1f;
        --muted: #5f6368;
        --line: rgba(29, 29, 31, 0.12);
        --blue: #0066cc;
        --green: #0a7f42;
        --amber: #9a6700;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: linear-gradient(180deg, #ffffff 0%, var(--bg) 48%, #eef3f8 100%);
        color: var(--text);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
        line-height: 1.5;
      }}
      a {{ color: inherit; text-decoration: none; }}
      main {{ width: min(1120px, calc(100% - 40px)); margin: 0 auto; }}
      .topbar {{
        position: sticky;
        top: 0;
        z-index: 5;
        display: flex;
        justify-content: space-between;
        align-items: center;
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
      .hero {{ padding: 66px 0 48px; }}
      .eyebrow, .tag {{
        color: var(--blue);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
      }}
      h1, h2, h3, p, dd {{ overflow-wrap: anywhere; }}
      h1 {{ max-width: 880px; margin: 0; font-size: 56px; line-height: 1; letter-spacing: 0; }}
      h2 {{ margin: 0 0 18px; font-size: 34px; line-height: 1.08; }}
      h3 {{ margin: 0; font-size: 19px; line-height: 1.24; }}
      .lede {{ max-width: 860px; margin: 20px 0 0; color: var(--muted); font-size: 21px; }}
      .metric-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 28px; }}
      .metric-card, .item-card {{
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
      }}
      .metric-card {{ padding: 22px; min-height: 142px; }}
      .metric-card span {{ color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .metric-card strong {{ display: block; margin-top: 8px; font-size: 34px; }}
      section {{ padding: 52px 0; border-top: 1px solid var(--line); }}
      .callout {{
        padding: 18px;
        border: 1px solid rgba(10, 127, 66, 0.26);
        border-radius: 8px;
        background: rgba(10, 127, 66, 0.08);
      }}
      .item-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
      .item-card {{ padding: 22px; }}
      .item-card.primary_demo {{ border-color: rgba(10, 127, 66, 0.34); }}
      .item-card.caveat_demo {{ border-color: rgba(154, 103, 0, 0.28); }}
      .item-card.qa_regression_only {{ border-color: rgba(95, 99, 104, 0.26); }}
      .item-top {{ display: flex; justify-content: space-between; gap: 12px; margin-bottom: 10px; }}
      .status {{ color: var(--green); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .excerpt {{
        padding: 14px;
        border: 1px solid rgba(0, 102, 204, 0.18);
        border-radius: 8px;
        background: rgba(0, 102, 204, 0.07);
        font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
        font-size: 13px;
        white-space: pre-wrap;
      }}
      dl {{ display: grid; gap: 8px; margin: 16px 0 0; }}
      dt {{ color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      dd {{ margin: 0 0 8px; }}
      @media (max-width: 860px) {{
        .topbar {{ padding: 0 20px; }}
        .metric-grid, .item-grid {{ grid-template-columns: 1fr; }}
        h1 {{ font-size: 40px; }}
      }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <a class="brand" href="../site/index.html"><span>BH</span>BizHallu</a>
      <a href="./full100_detector_interpretation.html">Detector interpretation</a>
    </header>
    <main>
      <section class="hero">
        <p class="eyebrow">Label lock report</p>
        <h1>Presentation labels are locked after assistant full review.</h1>
        <p class="lede">
          This report converts the 15 reviewed confirmation items into a locked
          presentation label package. The lock applies to selected spans for
          portfolio/demo use; it does not turn the full generated answer into a
          correctness label.
        </p>
        <div class="metric-grid">
          <article class="metric-card"><span>Locked spans</span><strong>{summary['locked_label_count']}</strong></article>
          <article class="metric-card"><span>Primary demo</span><strong>{summary['by_publish_use'].get('primary_demo', 0)}</strong></article>
          <article class="metric-card"><span>Caveat rows</span><strong>{summary['span_level_caveat_count']}</strong></article>
          <article class="metric-card"><span>Source fixes</span><strong>{summary['source_fix_required_count']}</strong></article>
        </div>
      </section>
      <section>
        <h2>Lock basis</h2>
        <div class="callout">
          Labels are locked with basis <strong>{esc(LOCK_BASIS)}</strong>.
          The strongest portfolio examples are {esc(', '.join(primary_question_ids))}.
          Public claims should stay span-level and use caveat rows only with the documented surrounding-answer warning.
        </div>
      </section>
      <section>
        <h2>Locked label decisions</h2>
        <div class="item-grid">
{''.join(cards)}
        </div>
      </section>
    </main>
  </body>
</html>
"""
    LOCK_REPORT_HTML_PATH.write_text(html_text, encoding="utf-8")
    LOCK_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
