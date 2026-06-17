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

PACKET_JSONL_PATH = REPORTS_DIR / "full100_label_confirmation_packet.jsonl"
PACKET_SUMMARY_PATH = REPORTS_DIR / "full100_label_confirmation_packet_summary.json"

NOTES_CSV_PATH = REPORTS_DIR / "full100_label_confirmation_review_notes.csv"
NOTES_JSONL_PATH = REPORTS_DIR / "full100_label_confirmation_review_notes.jsonl"
NOTES_HTML_PATH = REPORTS_DIR / "full100_label_confirmation_review_notes.html"
NOTES_SUMMARY_PATH = REPORTS_DIR / "full100_label_confirmation_review_notes_summary.json"


REVIEW_NOTES: dict[str, dict[str, str]] = {
    "confirm_001": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "span_level_caveat",
        "demo_priority": "medium",
        "risk_level": "medium",
        "source_action": "none",
        "review_note": (
            "The selected delta amount is within tolerance, but the generated sentence also says France generated more "
            "despite listing Germany as higher. Use only as a span-level false-positive example, not as a whole-answer "
            "correctness example."
        ),
    },
    "confirm_002": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "span_level_caveat",
        "demo_priority": "medium",
        "risk_level": "medium",
        "source_action": "none",
        "review_note": (
            "The direction word is correct, while the amount in the same answer is off by a factor of about ten. "
            "This is safe only when framed as span-level labeling."
        ),
    },
    "confirm_003": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "span_level_caveat",
        "demo_priority": "medium",
        "risk_level": "medium",
        "source_action": "none",
        "review_note": (
            "The percentage is within the configured tolerance, but it appears in an answer with a wrong absolute "
            "amount. If shown, mention the tolerance and avoid implying the full answer is correct."
        ),
    },
    "confirm_004": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "span_level_caveat",
        "demo_priority": "medium",
        "risk_level": "medium",
        "source_action": "none",
        "review_note": (
            "The increase direction is correct, but the generated revenue and change figures are scaled down. "
            "Use as a span-level false-positive example only."
        ),
    },
    "confirm_005": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "offset_check_only",
        "demo_priority": "low",
        "risk_level": "low",
        "source_action": "none",
        "review_note": (
            "The span is the rank-3 list marker and is tied to the wrong generated product. This is mainly useful "
            "as an offset-regression check, not as a detector error example."
        ),
    },
    "confirm_006": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "paired_contrast_example",
        "demo_priority": "high",
        "risk_level": "low",
        "source_action": "none",
        "review_note": (
            "The rank-1 amount is supported by gold evidence. It works well in the April 2011 paired example, where "
            "nearby spans include both supported and hallucinated claims."
        ),
    },
    "confirm_007": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "paired_contrast_example",
        "demo_priority": "high",
        "risk_level": "low",
        "source_action": "none",
        "review_note": (
            "The rank-2 product name is supported by gold evidence. This is a clean correct span inside the April "
            "2011 paired contrast example."
        ),
    },
    "confirm_008": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "paired_contrast_example",
        "demo_priority": "high",
        "risk_level": "low",
        "source_action": "none",
        "review_note": (
            "The rank-3 marker is attached to WOODEN UNION JACK BUNTING, but gold rank 3 is PAPER CHAIN KIT EMPIRE. "
            "This is a clear hallucinated ranking span."
        ),
    },
    "confirm_009": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "paired_contrast_example",
        "demo_priority": "high",
        "risk_level": "low",
        "source_action": "none",
        "review_note": (
            "The rank-3 amount is for the wrong generated product and does not match the gold rank-3 revenue. "
            "This is a strong amount-level hallucination in the April 2011 example."
        ),
    },
    "confirm_010": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "offset_check_only",
        "demo_priority": "low",
        "risk_level": "low",
        "source_action": "none",
        "review_note": (
            "The span is the rank-3 list marker, not a decimal inside the nearby amount. Keep this primarily as an "
            "offset-regression check."
        ),
    },
    "confirm_011": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "strong_false_negative_example",
        "demo_priority": "high",
        "risk_level": "low",
        "source_action": "none",
        "review_note": (
            "The rank-2 marker is tied to PAPER CHAIN KIT 50'S CHRISTMAS, while gold rank 2 is REGENCY CAKESTAND "
            "3 TIER. This is a clear detector-missed hallucinated ranking span."
        ),
    },
    "confirm_012": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "strong_false_negative_example",
        "demo_priority": "high",
        "risk_level": "low",
        "source_action": "none",
        "review_note": (
            "The rank-3 marker is tied to REGENCY CAKESTAND 3 TIER, while gold rank 3 is JUMBO BAG RED RETROSPOT. "
            "This is a clear detector-missed hallucinated ranking span."
        ),
    },
    "confirm_013": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "strong_false_negative_example",
        "demo_priority": "high",
        "risk_level": "low",
        "source_action": "none",
        "review_note": (
            "The amount is a real rank-2 amount but is used for rank 3. This is a useful example of a value that is "
            "locally plausible but wrong in its assigned business context."
        ),
    },
    "confirm_014": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "span_level_caveat",
        "demo_priority": "medium",
        "risk_level": "medium",
        "source_action": "none",
        "review_note": (
            "The reduction amount is correct, but the generated final net revenue repeats that same value and is "
            "wrong. Use only to show a correct span that a detector flags, with a clear span-level caveat."
        ),
    },
    "confirm_015": {
        "assistant_label_verdict": "label_supported",
        "presentation_use": "span_level_caveat",
        "demo_priority": "medium",
        "risk_level": "medium",
        "source_action": "none",
        "review_note": (
            "The reduction amount is correct, but the final net revenue is off by a factor of ten. Use only as a "
            "span-level false-positive example."
        ),
    },
}


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


def detector_role_text(row: dict[str, Any]) -> str:
    roles = row.get("detector_error_roles", [])
    if not roles:
        return "No detector-error row; offset check only."
    return "; ".join(f"{role['family']} {role['error_type']} via {role['baseline']}" for role in roles)


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    packet_rows = load_jsonl(PACKET_JSONL_PATH)
    packet_summary = load_json(PACKET_SUMMARY_PATH)

    missing_notes = sorted(row["confirmation_item_id"] for row in packet_rows if row["confirmation_item_id"] not in REVIEW_NOTES)
    extra_notes = sorted(set(REVIEW_NOTES) - {row["confirmation_item_id"] for row in packet_rows})
    if missing_notes or extra_notes:
        raise SystemExit(f"Review-note coverage mismatch: missing={missing_notes}, extra={extra_notes}")

    rows: list[dict[str, Any]] = []
    for packet_row in packet_rows:
        note = REVIEW_NOTES[packet_row["confirmation_item_id"]]
        rows.append(
            {
                "confirmation_item_id": packet_row["confirmation_item_id"],
                "annotation_id": packet_row["annotation_id"],
                "question_id": packet_row["question_id"],
                "split": packet_row["split"],
                "question_type": packet_row["question_type"],
                "fact_type": packet_row["fact_type"],
                "label": packet_row["label"],
                "span_text": packet_row["span_text"],
                "assistant_label_verdict": note["assistant_label_verdict"],
                "presentation_use": note["presentation_use"],
                "demo_priority": note["demo_priority"],
                "risk_level": note["risk_level"],
                "source_action": note["source_action"],
                "review_note": note["review_note"],
                "detector_role_text": detector_role_text(packet_row),
                "highlighted_excerpt": packet_row["highlighted_excerpt"],
                "gold_short_answer": packet_row["gold_short_answer"],
                "human_confirmation_required": True,
                "labels_locked": False,
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
        "assistant_label_verdict",
        "presentation_use",
        "demo_priority",
        "risk_level",
        "source_action",
        "review_note",
        "detector_role_text",
        "highlighted_excerpt",
        "gold_short_answer",
        "human_confirmation_required",
        "labels_locked",
    ]
    with NOTES_CSV_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    write_jsonl(NOTES_JSONL_PATH, rows)

    by_verdict = Counter(row["assistant_label_verdict"] for row in rows)
    by_presentation_use = Counter(row["presentation_use"] for row in rows)
    by_priority = Counter(row["demo_priority"] for row in rows)
    by_risk = Counter(row["risk_level"] for row in rows)
    source_action_counts = Counter(row["source_action"] for row in rows)
    high_priority_ids = [row["confirmation_item_id"] for row in rows if row["demo_priority"] == "high"]

    summary = {
        "status": "assistant_review_complete_not_human_locked",
        "source_packet_summary_path": repo_path(PACKET_SUMMARY_PATH),
        "review_notes_csv_path": repo_path(NOTES_CSV_PATH),
        "review_notes_jsonl_path": repo_path(NOTES_JSONL_PATH),
        "review_notes_html_path": repo_path(NOTES_HTML_PATH),
        "selected_annotation_count": len(rows),
        "selected_question_count": len({row["question_id"] for row in rows}),
        "assistant_label_verdict_counts": dict(sorted(by_verdict.items())),
        "presentation_use_counts": dict(sorted(by_presentation_use.items())),
        "demo_priority_counts": dict(sorted(by_priority.items())),
        "risk_level_counts": dict(sorted(by_risk.items())),
        "source_action_counts": dict(sorted(source_action_counts.items())),
        "high_priority_confirmation_item_ids": high_priority_ids,
        "source_fix_required_count": sum(1 for row in rows if row["source_action"] != "none"),
        "human_confirmation_required": True,
        "labels_locked": False,
        "packet_status": packet_summary.get("status"),
        "num_failures": 0,
        "failures": [],
    }

    cards = []
    for row in rows:
        cards.append(
            f"""
        <article class="item-card {esc(row['demo_priority'])}">
          <div class="item-top">
            <span class="tag">{esc(row['confirmation_item_id'])}</span>
            <span class="status">{esc(row['demo_priority'])} priority</span>
          </div>
          <h3>{esc(row['question_id'])} - {esc(row['fact_type'])} - {esc(row['label'])}</h3>
          <p class="excerpt">{esc(row['highlighted_excerpt'])}</p>
          <dl>
            <dt>Review verdict</dt><dd>{esc(row['assistant_label_verdict'])}</dd>
            <dt>Presentation use</dt><dd>{esc(row['presentation_use'])}</dd>
            <dt>Detector role</dt><dd>{esc(row['detector_role_text'])}</dd>
            <dt>Review note</dt><dd>{esc(row['review_note'])}</dd>
            <dt>Source action</dt><dd>{esc(row['source_action'])}</dd>
          </dl>
        </article>"""
        )

    html_text = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BizHallu Label Review Notes</title>
    <style>
      :root {{
        --bg: #f5f5f7;
        --surface: #ffffff;
        --text: #1d1d1f;
        --muted: #5f6368;
        --line: rgba(29, 29, 31, 0.12);
        --blue: #0066cc;
        --amber: #9a6700;
        --green: #0a7f42;
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
      h1 {{ max-width: 860px; margin: 0; font-size: 54px; line-height: 1; letter-spacing: 0; }}
      h2 {{ margin: 0 0 18px; font-size: 34px; line-height: 1.08; }}
      h3 {{ margin: 0; font-size: 19px; line-height: 1.24; }}
      .lede {{ max-width: 840px; margin: 20px 0 0; color: var(--muted); font-size: 21px; }}
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
        border: 1px solid rgba(154, 103, 0, 0.26);
        border-radius: 8px;
        background: rgba(154, 103, 0, 0.08);
      }}
      .item-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
      .item-card {{ padding: 22px; }}
      .item-card.high {{ border-color: rgba(10, 127, 66, 0.34); }}
      .item-card.medium {{ border-color: rgba(154, 103, 0, 0.26); }}
      .item-top {{ display: flex; justify-content: space-between; gap: 12px; margin-bottom: 10px; }}
      .status {{ color: var(--amber); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
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
      <a href="./full100_label_confirmation_packet.html">Confirmation packet</a>
    </header>
    <main>
      <section class="hero">
        <p class="eyebrow">Assistant review notes</p>
        <h1>Labels look supported, but public claims should stay span-level.</h1>
        <p class="lede">
          This review checks the 15 selected confirmation items for presentation use.
          It does not lock labels; human confirmation is still required before final portfolio claims.
        </p>
        <div class="metric-grid">
          <article class="metric-card"><span>Reviewed spans</span><strong>{summary['selected_annotation_count']}</strong></article>
          <article class="metric-card"><span>Supported labels</span><strong>{summary['assistant_label_verdict_counts'].get('label_supported', 0)}</strong></article>
          <article class="metric-card"><span>High priority</span><strong>{summary['demo_priority_counts'].get('high', 0)}</strong></article>
          <article class="metric-card"><span>Source fixes</span><strong>{summary['source_fix_required_count']}</strong></article>
        </div>
      </section>
      <section>
        <h2>Review conclusion</h2>
        <div class="callout">
          No source annotation edits are recommended from this pass. The main caution is presentation framing:
          several correct spans occur inside answers that also contain other numeric or ranking mistakes.
          The detector story should therefore be described as span-level hallucination detection.
        </div>
      </section>
      <section>
        <h2>Per-item review notes</h2>
        <div class="item-grid">
{''.join(cards)}
        </div>
      </section>
    </main>
  </body>
</html>
"""
    NOTES_HTML_PATH.write_text(html_text, encoding="utf-8")
    NOTES_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
