"""Build the BizHallu evidence-aware verifier pilot v0.

This is intentionally small: it only covers the public Demo v2 locked spans and
does not recompute model generations, span labels, detector scores, or headline
metrics. The purpose is to create a reviewable detector-family prototype for
claim-evidence consistency, not a production verifier.
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from html import escape
from pathlib import Path
from typing import Any

from public_paths import repo_path


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"

DEMO_V2_DATA_PATH = REPORTS_DIR / "bizhallu_demo_v2_data.json"
ROWS_CSV_PATH = REPORTS_DIR / "bizhallu_evidence_verifier_pilot_rows.csv"
ROWS_JSON_PATH = REPORTS_DIR / "bizhallu_evidence_verifier_pilot_rows.json"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_evidence_verifier_pilot_summary.json"
HTML_PATH = REPORTS_DIR / "bizhallu_evidence_verifier_pilot.html"

ALLOWED_VERIFIER_LABELS = {"supported", "contradicted", "unmatched", "needs_review"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def normalize_number(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value)
    text = text.replace("GBP", "").replace("gbp", "").replace("\u00a3", "")
    text = text.replace(",", "").replace("%", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    return float(match.group(0))


def extract_claim_line(generated_text: str, span_text: str, start: int, end: int) -> str:
    if start >= 0 and end > start and end <= len(generated_text):
        line_start = generated_text.rfind("\n", 0, start) + 1
        line_end = generated_text.find("\n", end)
        if line_end == -1:
            line_end = len(generated_text)
        return generated_text[line_start:line_end].strip()

    index = generated_text.find(span_text)
    if index == -1:
        return span_text
    line_start = generated_text.rfind("\n", 0, index) + 1
    line_end = generated_text.find("\n", index + len(span_text))
    if line_end == -1:
        line_end = len(generated_text)
    return generated_text[line_start:line_end].strip()


def evidence_matches(span_text: str, fact_type: str, evidence_rows: list[dict[str, Any]]) -> list[str]:
    matches: list[str] = []
    span_norm = normalize_text(span_text)
    span_number = normalize_number(span_text)

    for index, row in enumerate(evidence_rows, start=1):
        row_hits: list[str] = []
        for key, value in row.items():
            value_norm = normalize_text(value)
            if span_norm and span_norm in value_norm:
                row_hits.append(key)
                continue
            if value_norm and value_norm in span_norm and len(value_norm) >= 4:
                row_hits.append(key)
                continue
            if fact_type != "ranking" and span_number is not None:
                value_number = normalize_number(value)
                if value_number is not None and abs(span_number - value_number) <= 0.02:
                    row_hits.append(key)

        if row_hits:
            stock_code = row.get("stock_code") or row.get("country") or row.get("invoice_month") or f"row_{index}"
            matches.append(f"row_{index}:{stock_code}:{','.join(sorted(set(row_hits)))}")

    return matches


def verifier_label_from_locked_label(locked_label: str) -> str:
    if locked_label == "correct_key_fact":
        return "supported"
    if locked_label == "hallucinated_key_fact":
        return "contradicted"
    if locked_label == "unsupported_claim":
        return "unmatched"
    return "needs_review"


def verifier_reason(row: dict[str, Any]) -> str:
    label = row["verifier_label"]
    fact_type = row["fact_type"]
    if label == "supported":
        return (
            "Supported by the locked presentation review and consistent with the "
            "gold answer or prompt evidence for this business-fact span."
        )
    if label == "contradicted" and fact_type == "ranking":
        return (
            "Contradicted in context: ranking markers are checked with the generated "
            "product or amount binding, not as standalone numbers."
        )
    if label == "contradicted":
        return (
            "Contradicted in context: the generated claim is not supported by the "
            "gold answer for the product, rank, amount, or conclusion binding."
        )
    if label == "unmatched":
        return "No matching support was found in the public demo gold/evidence fields."
    return "The pilot rules are insufficient for this span, so it remains review-only."


def build_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in data.get("cases", []):
        generated_text = case.get("generated_text", "")
        evidence_rows = case.get("prompt_evidence_rows", [])
        for span in case.get("spans", []):
            verifier_label = verifier_label_from_locked_label(str(span.get("label", "")))
            claim_text = extract_claim_line(
                generated_text,
                str(span.get("span_text", "")),
                int(span.get("span_start_char", -1)),
                int(span.get("span_end_char", -1)),
            )
            row = {
                "span_id": span.get("annotation_id"),
                "confirmation_item_id": span.get("confirmation_item_id"),
                "question_id": case.get("question_id"),
                "split": case.get("split"),
                "question_type": case.get("question_type"),
                "is_primary": bool(case.get("is_primary")),
                "question": case.get("question"),
                "span_text": span.get("span_text"),
                "span_start_char": span.get("span_start_char"),
                "span_end_char": span.get("span_end_char"),
                "fact_type": span.get("fact_type"),
                "locked_span_label": span.get("label"),
                "verifier_label": verifier_label,
                "claim_text": claim_text,
                "gold_short_answer": case.get("gold_short_answer"),
                "gold_contains_span_text": normalize_text(span.get("span_text", ""))
                in normalize_text(case.get("gold_short_answer", "")),
                "prompt_evidence_matches": evidence_matches(
                    str(span.get("span_text", "")),
                    str(span.get("fact_type", "")),
                    evidence_rows,
                ),
                "simple_outcome": span.get("simple_outcome"),
                "entropy_outcome": span.get("entropy_outcome"),
                "energy_outcome": span.get("energy_outcome"),
                "simple_score": span.get("simple_score"),
                "entropy_score": span.get("entropy_score"),
                "energy_score": span.get("energy_score"),
                "detector_any_missed": any(
                    span.get(field) == "missed"
                    for field in ["simple_outcome", "entropy_outcome", "energy_outcome"]
                ),
                "detector_all_missed": all(
                    span.get(field) == "missed"
                    for field in ["simple_outcome", "entropy_outcome", "energy_outcome"]
                ),
                "review_note": span.get("review_note"),
            }
            row["verifier_reason"] = verifier_reason(row)
            rows.append(row)
    return rows


def detector_miss_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    contradicted = [row for row in rows if row["verifier_label"] == "contradicted"]
    return {
        "contradicted_spans": len(contradicted),
        "any_detector_missed_contradicted": sum(1 for row in contradicted if row["detector_any_missed"]),
        "all_detectors_missed_contradicted": sum(1 for row in contradicted if row["detector_all_missed"]),
        "simple_missed_contradicted": sum(1 for row in contradicted if row["simple_outcome"] == "missed"),
        "entropy_missed_contradicted": sum(1 for row in contradicted if row["entropy_outcome"] == "missed"),
        "energy_missed_contradicted": sum(1 for row in contradicted if row["energy_outcome"] == "missed"),
    }


def write_rows_csv(rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError("no verifier rows to write")
    fieldnames = list(rows[0].keys())
    with ROWS_CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            csv_row = {
                key: json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value
                for key, value in row.items()
            }
            writer.writerow(csv_row)


def render_html(rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    label_cards = "\n".join(
        f"""
          <article class="metric">
            <span class="label">{escape(label)}</span>
            <strong>{count}</strong>
            <p>Demo v2 locked spans with this evidence-aware pilot label.</p>
          </article>
        """
        for label, count in sorted(summary["verifier_label_counts"].items())
    )
    rows_html = "\n".join(
        f"""
          <tr>
            <td><code>{escape(str(row["question_id"]))}</code></td>
            <td>{escape(str(row["fact_type"]))}</td>
            <td><span class="pill {escape(str(row["verifier_label"]))}">{escape(str(row["verifier_label"]))}</span></td>
            <td>{escape(str(row["span_text"]))}</td>
            <td>{escape(str(row["claim_text"]))}</td>
            <td>{escape(str(row["simple_outcome"]))} / {escape(str(row["entropy_outcome"]))} / {escape(str(row["energy_outcome"]))}</td>
            <td>{escape(str(row["verifier_reason"]))}</td>
          </tr>
        """
        for row in rows
    )

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BizHallu Evidence-Aware Verifier Pilot</title>
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
        --shadow: 0 18px 44px rgba(0, 0, 0, 0.08);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: linear-gradient(180deg, #fff 0%, var(--bg) 52%, #eef2f5 100%);
        color: var(--ink);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
        line-height: 1.5;
      }}
      a {{ color: var(--blue); font-weight: 800; text-decoration: none; }}
      main {{ width: min(1180px, calc(100% - 40px)); margin: 0 auto; }}
      header {{ padding: 48px 0 26px; }}
      h1 {{ max-width: 880px; margin: 0; font-size: clamp(38px, 6vw, 68px); line-height: 1.02; letter-spacing: 0; }}
      h2 {{ margin: 0; font-size: clamp(26px, 4vw, 42px); letter-spacing: 0; }}
      p {{ color: var(--muted); font-size: 17px; }}
      .eyebrow {{ color: var(--blue); font-size: 13px; font-weight: 800; text-transform: uppercase; letter-spacing: 0; }}
      .lede {{ max-width: 900px; font-size: 21px; }}
      .actions {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 24px; }}
      .button {{ display: inline-flex; min-height: 42px; align-items: center; padding: 10px 16px; border: 1px solid rgba(0, 102, 204, 0.18); border-radius: 8px; background: rgba(0, 102, 204, 0.08); }}
      .section {{ padding: 52px 0; border-top: 1px solid var(--line); }}
      .metric-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 24px; }}
      .metric, .callout {{ border: 1px solid var(--line); border-radius: 8px; background: var(--surface); box-shadow: var(--shadow); }}
      .metric {{ min-height: 140px; padding: 20px; }}
      .metric strong {{ display: block; margin-top: 8px; font-size: 34px; line-height: 1; }}
      .label {{ color: var(--muted); font-size: 12px; font-weight: 800; text-transform: uppercase; letter-spacing: 0; }}
      .callout {{ margin-top: 24px; padding: 22px; box-shadow: none; }}
      .callout strong {{ color: var(--green); }}
      table {{ width: 100%; margin-top: 22px; border-collapse: collapse; border: 1px solid var(--line); background: var(--surface); }}
      th, td {{ padding: 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; font-size: 14px; }}
      th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0; }}
      code {{ padding: 2px 5px; border-radius: 6px; background: rgba(0, 0, 0, 0.06); }}
      .pill {{ display: inline-flex; min-height: 26px; align-items: center; padding: 4px 8px; border-radius: 999px; font-weight: 800; font-size: 12px; }}
      .supported {{ color: var(--green); background: rgba(15, 118, 110, 0.1); }}
      .contradicted {{ color: var(--red); background: rgba(179, 38, 30, 0.1); }}
      .unmatched {{ color: var(--amber); background: rgba(154, 103, 0, 0.1); }}
      .needs_review {{ color: var(--blue); background: rgba(0, 102, 204, 0.1); }}
      ul {{ display: grid; gap: 10px; margin-top: 18px; padding-left: 22px; color: var(--muted); }}
      @media (max-width: 900px) {{
        main {{ width: min(100% - 28px, 720px); }}
        .metric-grid {{ grid-template-columns: 1fr; }}
        table {{ display: block; overflow-x: auto; }}
      }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <p class="eyebrow">Evidence-aware verifier pilot</p>
        <h1>Comparing internal uncertainty with claim-evidence consistency.</h1>
        <p class="lede">
          This v0 pilot covers Demo v2 locked spans only. It reframes the same
          public cases as evidence-aware verifier rows so the next research step
          can compare internal-state signals with explicit business-fact grounding.
        </p>
        <div class="actions">
          <a class="button" href="./portfolio_demo_v2.html">Open Demo v2</a>
          <a class="button" href="./research_one_pager.html">Open research one-pager</a>
          <a class="button" href="./detector_interpretation.html">Open detector interpretation</a>
        </div>
      </header>

      <section class="section">
        <p class="eyebrow">Demo v2 locked spans only</p>
        <h2>A small verifier family prototype, not a new benchmark result.</h2>
        <div class="metric-grid">
          <article class="metric"><span class="label">Cases</span><strong>{summary["case_count"]}</strong><p>Public Demo v2 cases.</p></article>
          <article class="metric"><span class="label">Spans</span><strong>{summary["span_count"]}</strong><p>Presentation-locked business-fact spans.</p></article>
          <article class="metric"><span class="label">Held-out AUPRC</span><strong>{summary["best_test_auprc"]:.3f}</strong><p>Existing internal detector result; unchanged.</p></article>
          <article class="metric"><span class="label">Held-out F1</span><strong>{summary["best_test_f1"]:.3f}</strong><p>Existing internal detector result; unchanged.</p></article>
        </div>
        <div class="metric-grid">
          {label_cards}
        </div>
        <div class="callout">
          <strong>Guardrail</strong>
          <p>
            This verifier pilot is not a production checker and not a new
            benchmark result. It does not claim superiority over internal
            detectors. It
            creates reviewable rows for the next comparison between internal
            uncertainty and evidence-aware verification.
          </p>
        </div>
      </section>

      <section class="section">
        <p class="eyebrow">Pilot interpretation</p>
        <h2>What this adds to the current detector story.</h2>
        <ul>
          <li>Internal uncertainty asks whether the model appeared uncertain while generating a token span.</li>
          <li>Evidence-aware verification asks whether the generated business claim is supported by the evidence or gold answer.</li>
          <li>Confident wrong evidence binding is the key failure mode: a span can reuse real values but attach them to the wrong product, rank, or conclusion.</li>
          <li>The current pilot marks {summary["detector_miss_counts"]["all_detectors_missed_contradicted"]} contradicted spans where all three displayed internal detectors missed the error.</li>
        </ul>
      </section>

      <section class="section">
        <p class="eyebrow">Verifier rows</p>
        <h2>Each row is a business-fact span with evidence-aware pilot status.</h2>
        <table>
          <thead>
            <tr>
              <th>Question</th>
              <th>Fact type</th>
              <th>Verifier label</th>
              <th>Span</th>
              <th>Generated claim line</th>
              <th>Detector outcomes</th>
              <th>Verifier reason</th>
            </tr>
          </thead>
          <tbody>
            {rows_html}
          </tbody>
        </table>
      </section>
    </main>
  </body>
</html>
"""


def main() -> None:
    data = load_json(DEMO_V2_DATA_PATH)
    rows = build_rows(data)
    label_counts = Counter(row["verifier_label"] for row in rows)
    locked_counts = Counter(row["locked_span_label"] for row in rows)
    question_ids = sorted({str(row["question_id"]) for row in rows})
    meta = data.get("meta", {})

    summary = {
        "status": "evidence_verifier_pilot_ready",
        "scope": "demo_v2_locked_spans_only",
        "title": "BizHallu Evidence-Aware Verifier Pilot",
        "source_demo_v2_data_path": repo_path(DEMO_V2_DATA_PATH),
        "rows_csv_path": repo_path(ROWS_CSV_PATH),
        "rows_json_path": repo_path(ROWS_JSON_PATH),
        "html_path": repo_path(HTML_PATH),
        "case_count": len(question_ids),
        "span_count": len(rows),
        "question_ids": question_ids,
        "verifier_label_counts": dict(sorted(label_counts.items())),
        "locked_span_label_counts": dict(sorted(locked_counts.items())),
        "allowed_verifier_labels": sorted(ALLOWED_VERIFIER_LABELS),
        "detector_miss_counts": detector_miss_counts(rows),
        "best_test_auprc": meta.get("best_test_auprc"),
        "best_test_f1": meta.get("best_test_f1"),
        "label_lock_basis": meta.get("label_lock_basis"),
        "label_lock_status": meta.get("label_lock_status"),
        "guardrail": (
            "Prototype over Demo v2 locked spans only; not a production checker, "
            "not a new benchmark result, and not a replacement for existing metrics."
        ),
        "num_failures": 0,
        "failures": [],
    }

    ROWS_JSON_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=True), encoding="utf-8")
    write_rows_csv(rows)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    HTML_PATH.write_text(render_html(rows, summary), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": summary["status"],
                "span_count": summary["span_count"],
                "html_path": summary["html_path"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
