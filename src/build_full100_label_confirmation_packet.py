from __future__ import annotations

import csv
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RESULTS_DIR = PROJECT_ROOT / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"

ANNOTATION_PATH = DATA_DIR / "annotations" / "span_annotations_full100_draft.jsonl"
REVIEW_PATH = OUTPUT_DIR / "full100_review.jsonl"
GENERATION_PATH = OUTPUT_DIR / "qwen_full100_generations.jsonl"
ERROR_EXAMPLES_PATH = RESULTS_DIR / "full100_draft_detector_error_review_examples.csv"
INTERPRETATION_SUMMARY_PATH = REPORTS_DIR / "full100_detector_interpretation_summary.json"

PACKET_CSV_PATH = REPORTS_DIR / "full100_label_confirmation_packet.csv"
PACKET_JSONL_PATH = REPORTS_DIR / "full100_label_confirmation_packet.jsonl"
PACKET_HTML_PATH = REPORTS_DIR / "full100_label_confirmation_packet.html"
PACKET_SUMMARY_PATH = REPORTS_DIR / "full100_label_confirmation_packet_summary.json"

OFFSET_REGRESSION_ANNOTATION_IDS = [
    "ann_full100_draft_q_0063_010",
    "ann_full100_draft_q_0068_008",
    "ann_full100_draft_q_0064_008",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=True) + "\n")


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def highlight_span(text: str, start: int, end: int, width: int = 130) -> str:
    left = max(0, start - width)
    right = min(len(text), end + width)
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(text) else ""
    return f"{prefix}{text[left:start]}[[{text[start:end]}]]{text[end:right]}{suffix}"


def role_key(row: dict[str, str]) -> str:
    return f"{row['family']}::{row['baseline_role']}::{row['error_type']}"


def make_checklist(record: dict[str, Any], is_offset_regression: bool, has_error_example: bool) -> list[str]:
    checklist = [
        "Highlighted span points to the intended generated claim.",
        "Gold reference matches the deterministic gold answer/evidence.",
        "Label is correct_key_fact only when the generated claim is supported; otherwise hallucinated_key_fact or unsupported_claim is justified.",
        "Annotation reason is specific enough to explain the label in a presentation.",
    ]
    if has_error_example:
        checklist.append("Detector error type is presentation-safe: false positive means correct span flagged; false negative means wrong/unsupported span missed.")
    if is_offset_regression:
        checklist.append("Rank marker span is the list marker, not a decimal inside a currency amount.")
    return checklist


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    annotations = load_jsonl(ANNOTATION_PATH)
    reviews = load_jsonl(REVIEW_PATH)
    generations = load_jsonl(GENERATION_PATH)
    error_examples = load_csv(ERROR_EXAMPLES_PATH)
    interpretation_summary = load_json(INTERPRETATION_SUMMARY_PATH)

    annotation_by_id = {record["annotation_id"]: record for record in annotations}
    review_by_qid = {record["question_id"]: record for record in reviews}
    generation_by_qid = {record["question_id"]: record for record in generations}

    example_rows_by_annotation: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in error_examples:
        example_rows_by_annotation[row["annotation_id"]].append(row)

    selected_ids = set(example_rows_by_annotation)
    selected_ids.update(OFFSET_REGRESSION_ANNOTATION_IDS)
    missing_ids = sorted(selected_ids - set(annotation_by_id))
    if missing_ids:
        raise SystemExit(f"Missing selected annotations: {missing_ids}")

    packet_rows: list[dict[str, Any]] = []
    for annotation_id in sorted(selected_ids):
        annotation = annotation_by_id[annotation_id]
        question_id = annotation["question_id"]
        review = review_by_qid[question_id]
        generation = generation_by_qid[question_id]
        generated_text = generation["generated_text"]
        start = int(annotation["span_start_char"])
        end = int(annotation["span_end_char"])
        example_rows = example_rows_by_annotation.get(annotation_id, [])
        is_offset_regression = annotation_id in OFFSET_REGRESSION_ANNOTATION_IDS
        has_error_example = bool(example_rows)
        detector_roles = [
            {
                "family": row["family"],
                "baseline_role": row["baseline_role"],
                "baseline": row["baseline"],
                "error_type": row["error_type"],
                "score": row["score"],
                "threshold": row["threshold"],
                "selection_reason": row["selection_reason"],
                "example_rank": int(row["example_rank"]),
            }
            for row in sorted(example_rows, key=lambda item: (item["family"], item["error_type"], int(item["example_rank"])))
        ]
        focus_tags = []
        if has_error_example:
            focus_tags.append("detector_error_example")
        if is_offset_regression:
            focus_tags.append("offset_regression_check")
        if annotation["question_id"] in {"q_0064", "q_0069"}:
            focus_tags.append("top3_confident_miss_pattern")
        if annotation["fact_type"] == "currency_amount":
            focus_tags.append("currency_amount_pattern")

        highlighted_excerpt = highlight_span(generated_text, start, end)
        packet_rows.append(
            {
                "confirmation_item_id": f"confirm_{len(packet_rows) + 1:03d}",
                "annotation_id": annotation_id,
                "question_id": question_id,
                "prompt_id": annotation["prompt_id"],
                "split": review["split"],
                "question_type": review["question_type"],
                "difficulty": review["difficulty"],
                "question": review["question"],
                "gold_short_answer": review["gold_short_answer"],
                "span_text": annotation["span_text"],
                "span_start_char": start,
                "span_end_char": end,
                "fact_type": annotation["fact_type"],
                "label": annotation["label"],
                "gold_reference": annotation["gold_reference"],
                "annotation_reason": annotation["reason"],
                "annotation_notes": annotation["notes"],
                "annotation_confidence": annotation["confidence"],
                "highlighted_excerpt": highlighted_excerpt,
                "detector_error_roles": detector_roles,
                "focus_tags": focus_tags,
                "confirmation_checklist": make_checklist(annotation, is_offset_regression, has_error_example),
                "precheck_status": "pass",
                "confirmation_status": "pending_human_review",
                "requires_human_confirmation": True,
                "evidence_table_markdown": review.get("evidence_table_markdown", ""),
                "generated_text": generated_text,
            }
        )

    fieldnames = [
        "confirmation_item_id",
        "annotation_id",
        "question_id",
        "split",
        "question_type",
        "difficulty",
        "fact_type",
        "label",
        "span_text",
        "annotation_reason",
        "focus_tags",
        "detector_error_roles",
        "highlighted_excerpt",
        "gold_short_answer",
        "question",
        "gold_reference",
        "confirmation_checklist",
        "precheck_status",
        "confirmation_status",
        "requires_human_confirmation",
    ]
    with PACKET_CSV_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in packet_rows:
            writer.writerow(
                {
                    field: json.dumps(row[field], ensure_ascii=True)
                    if isinstance(row.get(field), (list, dict))
                    else row.get(field, "")
                    for field in fieldnames
                }
            )
    write_jsonl(PACKET_JSONL_PATH, packet_rows)

    by_fact_type = Counter(row["fact_type"] for row in packet_rows)
    by_label = Counter(row["label"] for row in packet_rows)
    by_question_type = Counter(row["question_type"] for row in packet_rows)
    by_focus_tag = Counter(tag for row in packet_rows for tag in row["focus_tags"])

    summary = {
        "status": "confirmation_packet_ready_not_locked",
        "packet_csv_path": repo_path(PACKET_CSV_PATH),
        "packet_jsonl_path": repo_path(PACKET_JSONL_PATH),
        "packet_html_path": repo_path(PACKET_HTML_PATH),
        "source_error_examples_path": repo_path(ERROR_EXAMPLES_PATH),
        "source_interpretation_summary_path": repo_path(INTERPRETATION_SUMMARY_PATH),
        "source_error_example_row_count": len(error_examples),
        "source_unique_error_example_annotation_count": len(example_rows_by_annotation),
        "offset_regression_annotation_ids": OFFSET_REGRESSION_ANNOTATION_IDS,
        "selected_annotation_count": len(packet_rows),
        "selected_question_count": len({row["question_id"] for row in packet_rows}),
        "selected_question_ids": sorted({row["question_id"] for row in packet_rows}),
        "by_fact_type": dict(sorted(by_fact_type.items())),
        "by_label": dict(sorted(by_label.items())),
        "by_question_type": dict(sorted(by_question_type.items())),
        "by_focus_tag": dict(sorted(by_focus_tag.items())),
        "interpretation_claims_checked": {
            "best_auprc_baseline": interpretation_summary["best_overall_by_test_auprc"]["baseline"],
            "best_f1_baseline": interpretation_summary["best_overall_by_test_f1"]["baseline"],
            "error_row_count": interpretation_summary["error_row_count"],
            "all_positive_like_energy_count": interpretation_summary["all_positive_like_energy_count"],
        },
        "human_confirmation_required": True,
        "all_items_confirmation_status": "pending_human_review",
        "num_failures": 0,
        "failures": [],
    }

    cards = []
    for row in packet_rows:
        roles = row["detector_error_roles"]
        role_text = "No detector-error example; offset regression check only."
        if roles:
            role_text = "; ".join(
                f"{role['family']} {role['error_type']} via {role['baseline']}" for role in roles
            )
        checklist_items = "\n".join(f"<li>{esc(item)}</li>" for item in row["confirmation_checklist"])
        cards.append(
            f"""
        <article class="item-card">
          <div class="item-top">
            <span class="tag">{esc(row['confirmation_item_id'])}</span>
            <span class="status">Pending human review</span>
          </div>
          <h3>{esc(row['question_id'])} - {esc(row['fact_type'])} - {esc(row['label'])}</h3>
          <p class="question">{esc(row['question'])}</p>
          <div class="excerpt">{esc(row['highlighted_excerpt'])}</div>
          <dl>
            <dt>Gold answer</dt><dd>{esc(row['gold_short_answer'])}</dd>
            <dt>Reason</dt><dd>{esc(row['annotation_reason'])}</dd>
            <dt>Why selected</dt><dd>{esc(', '.join(row['focus_tags']))}</dd>
            <dt>Detector role</dt><dd>{esc(role_text)}</dd>
          </dl>
          <details>
            <summary>Confirmation checklist</summary>
            <ul>{checklist_items}</ul>
          </details>
          <details>
            <summary>Gold reference</summary>
            <pre>{esc(json.dumps(row['gold_reference'], indent=2, ensure_ascii=False))}</pre>
          </details>
        </article>"""
        )

    html_text = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BizHallu Label Confirmation Packet</title>
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
        --shadow: 0 16px 38px rgba(0, 0, 0, 0.08);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: linear-gradient(180deg, #ffffff 0%, var(--bg) 46%, #edf2f7 100%);
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
      .hero {{ padding: 66px 0 48px; }}
      .eyebrow, .tag {{
        color: var(--blue);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
      }}
      h1, h2, h3, p {{ overflow-wrap: anywhere; }}
      h1 {{ max-width: 820px; margin: 0; font-size: 58px; line-height: 1; letter-spacing: 0; }}
      h2 {{ margin: 0 0 18px; font-size: 36px; line-height: 1.08; }}
      h3 {{ margin: 0; font-size: 19px; line-height: 1.24; }}
      .lede {{ max-width: 820px; margin: 20px 0 0; color: var(--muted); font-size: 21px; }}
      .metric-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-top: 28px; }}
      .metric-card, .item-card {{
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
        box-shadow: var(--shadow);
      }}
      .metric-card {{ padding: 22px; min-height: 150px; }}
      .metric-card span {{ color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .metric-card strong {{ display: block; margin-top: 8px; font-size: 36px; }}
      section {{ padding: 56px 0; border-top: 1px solid var(--line); }}
      .item-grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }}
      .item-card {{ padding: 22px; box-shadow: none; }}
      .item-top {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 10px; }}
      .status {{ color: var(--amber); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      .question {{ color: var(--muted); margin: 10px 0 14px; }}
      .excerpt {{
        padding: 14px;
        border-radius: 8px;
        border: 1px solid rgba(0, 102, 204, 0.18);
        background: rgba(0, 102, 204, 0.07);
        font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
        font-size: 13px;
        white-space: pre-wrap;
      }}
      dl {{ display: grid; gap: 8px; margin: 16px 0; }}
      dt {{ color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; }}
      dd {{ margin: 0 0 8px; }}
      details {{ border-top: 1px solid var(--line); padding-top: 12px; margin-top: 12px; }}
      summary {{ cursor: pointer; font-weight: 800; }}
      pre {{ overflow: auto; white-space: pre-wrap; }}
      .callout {{
        padding: 18px;
        border: 1px solid rgba(154, 103, 0, 0.24);
        border-radius: 8px;
        background: rgba(154, 103, 0, 0.08);
      }}
      @media (max-width: 860px) {{
        .topbar {{ padding: 0 20px; }}
        .metric-grid, .item-grid {{ grid-template-columns: 1fr; }}
        h1 {{ font-size: 42px; }}
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
        <p class="eyebrow">Presentation-level label confirmation</p>
        <h1>Review the examples behind the detector claims.</h1>
        <p class="lede">
          This packet selects the spans most likely to appear in the final story:
          detector FP/FN examples, top-3 confident misses, currency patterns, and the rank-marker offset regression checks.
          Every item remains pending human confirmation.
        </p>
        <div class="metric-grid">
          <article class="metric-card"><span>Selected spans</span><strong>{summary['selected_annotation_count']}</strong></article>
          <article class="metric-card"><span>Questions covered</span><strong>{summary['selected_question_count']}</strong></article>
          <article class="metric-card"><span>Error example rows</span><strong>{summary['source_error_example_row_count']}</strong></article>
          <article class="metric-card"><span>Status</span><strong>Pending</strong></article>
        </div>
      </section>
      <section>
        <h2>How to use this packet</h2>
        <div class="callout">
          Confirm each highlighted span, gold reference, label, and reason. If any item is wrong, update the source annotation first, then rerun alignment, scoring, metrics, error review, and interpretation.
        </div>
      </section>
      <section>
        <h2>Selected confirmation items</h2>
        <div class="item-grid">
{''.join(cards)}
        </div>
      </section>
    </main>
  </body>
</html>
"""

    PACKET_HTML_PATH.write_text(html_text, encoding="utf-8")
    PACKET_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")

    print(
        json.dumps(
            {
                "packet_csv_path": repo_path(PACKET_CSV_PATH),
                "packet_jsonl_path": repo_path(PACKET_JSONL_PATH),
                "packet_html_path": repo_path(PACKET_HTML_PATH),
                "packet_summary_path": repo_path(PACKET_SUMMARY_PATH),
                "selected_annotation_count": summary["selected_annotation_count"],
                "selected_question_count": summary["selected_question_count"],
                "status": summary["status"],
                "num_failures": 0,
            },
            indent=2,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
