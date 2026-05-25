from __future__ import annotations

import csv
import html
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
RESULTS_DIR = PROJECT_ROOT / "results"
REPORTS_DIR = PROJECT_ROOT / "reports"

LOCK_DECISIONS_PATH = REPORTS_DIR / "full100_label_lock_decisions.jsonl"
LOCK_SUMMARY_PATH = REPORTS_DIR / "full100_label_lock_summary.json"
PACKET_PATH = REPORTS_DIR / "full100_label_confirmation_packet.jsonl"
REVIEW_PATH = OUTPUT_DIR / "full100_review.jsonl"
DETECTOR_SCORES_PATH = RESULTS_DIR / "full100_draft_detector_scores.csv"
DETECTOR_INTERPRETATION_SUMMARY_PATH = REPORTS_DIR / "full100_detector_interpretation_summary.json"
FAMILY_COMPARISON_REPORT_PATH = RESULTS_DIR / "full100_draft_detector_family_comparison_report.json"

PORTFOLIO_DEMO_HTML_PATH = REPORTS_DIR / "bizhallu_portfolio_demo.html"
PORTFOLIO_DEMO_SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_summary.json"

PRIMARY_QUESTION_IDS = ["q_0064", "q_0069"]
EXPECTED_LOCK_STATUS = "presentation_labels_locked"
EXPECTED_LOCK_BASIS = "assistant_full_review"
EXPECTED_PRIMARY_SPAN_COUNT = 7


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def as_float(value: Any) -> float:
    return float(value)


def fmt_money(value: Any) -> str:
    return f"GBP {float(value):,.2f}"


def fmt_score(value: Any) -> str:
    number = float(value)
    if number == 0:
        return "0"
    if abs(number) < 0.001:
        return f"{number:.2e}"
    return f"{number:.3f}"


def add_failure(failures: list[dict[str, Any]], message: str, detail: Any = None) -> None:
    failures.append({"message": message, "detail": detail})


def outcome_text(label: str, predicted_positive: bool) -> str:
    is_positive = label != "correct_key_fact"
    if is_positive and predicted_positive:
        return "caught"
    if is_positive and not predicted_positive:
        return "missed"
    if not is_positive and predicted_positive:
        return "false alarm"
    return "cleared"


def render_evidence_table(rows: list[dict[str, Any]], gold_answer: dict[str, Any]) -> str:
    gold_stock_codes = {item["stock_code"] for item in gold_answer["top_products"]}
    body = []
    for row in rows:
        is_gold = row["stock_code"] in gold_stock_codes
        class_name = "gold-row" if is_gold else ""
        body.append(
            f"""
              <tr class="{class_name}">
                <td>{esc(row['stock_code'])}</td>
                <td>{esc(row['description'])}</td>
                <td>{fmt_money(row['net_revenue'])}</td>
                <td>{fmt_money(row['gross_positive_revenue'])}</td>
                <td>{fmt_money(row['cancellation_revenue'])}</td>
              </tr>"""
        )
    return f"""
        <table class="data-table">
          <thead>
            <tr>
              <th>Stock code</th>
              <th>Product</th>
              <th>Net revenue</th>
              <th>Gross positive</th>
              <th>Returns impact</th>
            </tr>
          </thead>
          <tbody>{''.join(body)}
          </tbody>
        </table>"""


def render_gold_top3(gold_answer: dict[str, Any]) -> str:
    rows = []
    for item in gold_answer["top_products"]:
        rows.append(
            f"""
            <li>
              <strong>{item['rank']}. {esc(item['stock_code'])}</strong>
              <span>{esc(item['description'])}</span>
              <em>{fmt_money(item['merchandise_net_revenue'])}</em>
            </li>"""
        )
    return f"<ol class=\"gold-list\">{''.join(rows)}</ol>"


def highlight_generated_text(text: str, spans: list[dict[str, Any]]) -> str:
    safe_parts: list[str] = []
    cursor = 0
    for span in sorted(spans, key=lambda item: (item["span_start_char"], item["span_end_char"])):
        start = int(span["span_start_char"])
        end = int(span["span_end_char"])
        if start < cursor:
            continue
        safe_parts.append(esc(text[cursor:start]))
        label_class = "span-correct" if span["label"] == "correct_key_fact" else "span-wrong"
        safe_parts.append(
            f"<mark class=\"{label_class}\" title=\"{esc(span['label'])}: {esc(span['fact_type'])}\">"
            f"{esc(text[start:end])}</mark>"
        )
        cursor = end
    safe_parts.append(esc(text[cursor:]))
    return "".join(safe_parts)


def build_case_title(question_id: str) -> str:
    if question_id == "q_0064":
        return "Case 1: the answer mixes correct facts with a wrong rank-3 binding"
    if question_id == "q_0069":
        return "Case 2: confident ranking errors are missed by uncertainty signals"
    return f"Case: {question_id}"


def build_case_takeaway(question_id: str) -> str:
    if question_id == "q_0064":
        return (
            "Qwen copied the correct rank-1 amount and rank-2 product, but then selected the wrong rank-3 product "
            "and amount. This is the cleanest span-level contrast: correct spans and hallucinated spans sit in the "
            "same answer."
        )
    if question_id == "q_0069":
        return (
            "Qwen used plausible product names and real revenue values, but assigned them to the wrong ranks. "
            "The selected baselines gave these wrong spans very low uncertainty, producing false negatives."
        )
    return "This case shows why span-level labels are more useful than whole-answer labels."


def render_span_rows(spans: list[dict[str, Any]]) -> str:
    rows = []
    for span in spans:
        label_class = "ok" if span["label"] == "correct_key_fact" else "bad"
        simple_outcome = outcome_text(span["label"], span["simple_predicted_positive"])
        entropy_outcome = outcome_text(span["label"], span["entropy_predicted_positive"])
        energy_outcome = outcome_text(span["label"], span["energy_predicted_positive"])
        rows.append(
            f"""
            <tr>
              <td><span class="pill {label_class}">{esc(span['label'])}</span></td>
              <td>{esc(span['span_text'])}<small>{esc(span['fact_type'])}</small></td>
              <td>{esc(simple_outcome)}<small>{fmt_score(span['simple_score'])}</small></td>
              <td>{esc(entropy_outcome)}<small>{fmt_score(span['entropy_score'])}</small></td>
              <td>{esc(energy_outcome)}<small>{fmt_score(span['energy_score'])}</small></td>
              <td>{esc(span['publish_use'])}</td>
            </tr>"""
        )
    return f"""
        <table class="span-table">
          <thead>
            <tr>
              <th>Gold label</th>
              <th>Locked span</th>
              <th>Top-2 margin</th>
              <th>Entropy</th>
              <th>Energy-family</th>
              <th>Demo role</th>
            </tr>
          </thead>
          <tbody>{''.join(rows)}
          </tbody>
        </table>"""


def render_threshold_note(summary: dict[str, Any]) -> str:
    return (
        "Thresholds: "
        f"one_minus_min_top2_margin >= {summary['simple_threshold']:.6f}; "
        f"mean_token_entropy >= {summary['entropy_threshold']:.6f}; "
        f"mean_spilled_probability_mass_after_top2 >= {summary['energy_threshold']:.6f}."
    )


def render_case(case: dict[str, Any], threshold_note: str) -> str:
    review = case["review"]
    spans = case["spans"]
    generated_html = highlight_generated_text(review["generation"]["generated_text"], spans)
    return f"""
      <section class="case-section" id="{esc(case['question_id'])}">
        <div class="case-heading">
          <p class="eyebrow">{esc(case['question_id'])} / {esc(review['split'])} split</p>
          <h2>{esc(build_case_title(case['question_id']))}</h2>
          <p>{esc(build_case_takeaway(case['question_id']))}</p>
        </div>
        <div class="case-grid">
          <article class="panel question-panel">
            <span class="tag">Business question</span>
            <h3>{esc(review['question'])}</h3>
            <div class="gold-answer">
              <strong>Deterministic gold answer</strong>
              {render_gold_top3(review['gold_answer'])}
            </div>
          </article>
          <article class="panel generated-panel">
            <span class="tag">Qwen answer with locked spans</span>
            <pre>{generated_html}</pre>
            <div class="legend">
              <span><i class="legend-ok"></i> supported span</span>
              <span><i class="legend-bad"></i> hallucinated span</span>
            </div>
          </article>
        </div>
        <div class="panel">
          <div class="panel-top">
            <div>
              <span class="tag">Evidence table shown to Qwen</span>
              <h3>Rows were not sorted into answer order.</h3>
            </div>
            <p>Gold rows are highlighted.</p>
          </div>
          {render_evidence_table(review['prompt_evidence_rows'], review['gold_answer'])}
        </div>
        <div class="panel">
          <div class="panel-top">
            <div>
              <span class="tag">Detector readout</span>
              <h3>Span-level predictions explain the failure mode.</h3>
            </div>
            <p>{esc(threshold_note)}</p>
          </div>
          {render_span_rows(spans)}
        </div>
      </section>"""


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[dict[str, Any]] = []
    lock_rows = load_jsonl(LOCK_DECISIONS_PATH)
    lock_summary = load_json(LOCK_SUMMARY_PATH)
    packet_rows = load_jsonl(PACKET_PATH)
    reviews = load_jsonl(REVIEW_PATH)
    scores = load_csv(DETECTOR_SCORES_PATH)
    detector_summary = load_json(DETECTOR_INTERPRETATION_SUMMARY_PATH)
    family_report = load_json(FAMILY_COMPARISON_REPORT_PATH)

    packet_by_annotation = {row["annotation_id"]: row for row in packet_rows}
    review_by_question = {row["question_id"]: row for row in reviews}
    score_by_annotation = {row["annotation_id"]: row for row in scores}

    simple_threshold = as_float(detector_summary["best_overall_by_test_auprc"]["threshold"])
    entropy_threshold = as_float(detector_summary["best_overall_by_test_f1"]["threshold"])
    energy_threshold = as_float(family_report["energy_best_by_test_f1"]["threshold"])

    if lock_summary.get("status") != EXPECTED_LOCK_STATUS:
        add_failure(failures, "unexpected label lock status", lock_summary.get("status"))
    if lock_summary.get("lock_basis") != EXPECTED_LOCK_BASIS:
        add_failure(failures, "unexpected label lock basis", lock_summary.get("lock_basis"))
    if lock_summary.get("labels_locked") is not True:
        add_failure(failures, "label lock summary is not locked", lock_summary.get("labels_locked"))
    if lock_summary.get("human_confirmation_required") is not False:
        add_failure(
            failures,
            "label lock summary still requires human confirmation",
            lock_summary.get("human_confirmation_required"),
        )
    if lock_summary.get("primary_demo_question_ids") != PRIMARY_QUESTION_IDS:
        add_failure(
            failures,
            "primary demo question IDs differ from portfolio configuration",
            lock_summary.get("primary_demo_question_ids"),
        )

    primary_lock_rows = [
        row
        for row in lock_rows
        if row["publish_use"] == "primary_demo" and row["question_id"] in PRIMARY_QUESTION_IDS
    ]
    if len(primary_lock_rows) != EXPECTED_PRIMARY_SPAN_COUNT:
        add_failure(failures, "unexpected primary demo span count", len(primary_lock_rows))

    cases_by_question: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in primary_lock_rows:
        annotation_id = row["annotation_id"]
        question_id = row["question_id"]
        if row.get("lock_status") != EXPECTED_LOCK_STATUS:
            add_failure(failures, "primary row lock status mismatch", {"annotation_id": annotation_id})
            continue
        if row.get("lock_basis") != EXPECTED_LOCK_BASIS:
            add_failure(failures, "primary row lock basis mismatch", {"annotation_id": annotation_id})
            continue
        if row.get("labels_locked") is not True:
            add_failure(failures, "primary row is not locked", {"annotation_id": annotation_id})
            continue
        if annotation_id not in packet_by_annotation:
            add_failure(failures, "missing confirmation packet row", {"annotation_id": annotation_id})
            continue
        if annotation_id not in score_by_annotation:
            add_failure(failures, "missing detector score row", {"annotation_id": annotation_id})
            continue
        if question_id not in review_by_question:
            add_failure(failures, "missing review row", {"question_id": question_id})
            continue

        packet_row = packet_by_annotation[annotation_id]
        score_row = score_by_annotation[annotation_id]
        generated_text = review_by_question[question_id]["generation"]["generated_text"]
        start = int(packet_row["span_start_char"])
        end = int(packet_row["span_end_char"])
        if not 0 <= start < end <= len(generated_text):
            add_failure(
                failures,
                "span offset is outside generated text",
                {"annotation_id": annotation_id, "start": start, "end": end, "length": len(generated_text)},
            )
            continue
        actual_span_text = generated_text[start:end]
        if actual_span_text != row["span_text"]:
            add_failure(
                failures,
                "span offset text does not match locked span text",
                {"annotation_id": annotation_id, "expected": row["span_text"], "actual": actual_span_text},
            )
            continue
        enriched = {
            **row,
            "span_start_char": start,
            "span_end_char": end,
            "simple_score": as_float(score_row["one_minus_min_top2_margin"]),
            "entropy_score": as_float(score_row["mean_token_entropy"]),
            "energy_score": as_float(score_row["mean_spilled_probability_mass_after_top2"]),
        }
        enriched["simple_predicted_positive"] = enriched["simple_score"] >= simple_threshold
        enriched["entropy_predicted_positive"] = enriched["entropy_score"] >= entropy_threshold
        enriched["energy_predicted_positive"] = enriched["energy_score"] >= energy_threshold
        cases_by_question[row["question_id"]].append(enriched)

    for question_id in PRIMARY_QUESTION_IDS:
        if not cases_by_question.get(question_id):
            add_failure(failures, "primary demo question has no locked spans", question_id)

    cases = [
        {
            "question_id": question_id,
            "review": review_by_question[question_id],
            "spans": sorted(cases_by_question[question_id], key=lambda item: item["span_start_char"]),
        }
        for question_id in PRIMARY_QUESTION_IDS
        if question_id in review_by_question
    ]
    if len(cases) != len(PRIMARY_QUESTION_IDS):
        add_failure(failures, "portfolio case count does not match expected primary questions", len(cases))

    label_counts = Counter(row["label"] for row in primary_lock_rows)
    simple_outcomes = Counter(outcome_text(row["label"], row["simple_predicted_positive"]) for case in cases for row in case["spans"])
    entropy_outcomes = Counter(outcome_text(row["label"], row["entropy_predicted_positive"]) for case in cases for row in case["spans"])
    energy_outcomes = Counter(outcome_text(row["label"], row["energy_predicted_positive"]) for case in cases for row in case["spans"])

    summary = {
        "status": "portfolio_demo_ready",
        "portfolio_demo_html_path": str(PORTFOLIO_DEMO_HTML_PATH),
        "source_label_lock_summary_path": str(LOCK_SUMMARY_PATH),
        "source_detector_interpretation_summary_path": str(DETECTOR_INTERPRETATION_SUMMARY_PATH),
        "primary_question_ids": PRIMARY_QUESTION_IDS,
        "case_count": len(cases),
        "locked_primary_span_count": len(primary_lock_rows),
        "by_label": dict(sorted(label_counts.items())),
        "simple_threshold": simple_threshold,
        "entropy_threshold": entropy_threshold,
        "energy_threshold": energy_threshold,
        "simple_outcomes": dict(sorted(simple_outcomes.items())),
        "entropy_outcomes": dict(sorted(entropy_outcomes.items())),
        "energy_outcomes": dict(sorted(energy_outcomes.items())),
        "best_test_auprc": detector_summary["best_overall_by_test_auprc"]["test_auprc"],
        "best_test_auprc_baseline": detector_summary["best_overall_by_test_auprc"]["baseline"],
        "best_test_f1": detector_summary["best_overall_by_test_f1"]["test_f1"],
        "best_test_f1_baseline": detector_summary["best_overall_by_test_f1"]["baseline"],
        "label_lock_status": lock_summary["status"],
        "label_lock_basis": lock_summary["lock_basis"],
        "labels_locked": lock_summary["labels_locked"],
        "human_confirmation_required": lock_summary["human_confirmation_required"],
        "num_failures": len(failures),
        "failures": failures,
    }
    threshold_note = render_threshold_note(summary)

    if failures:
        PORTFOLIO_DEMO_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
        print(json.dumps(summary, indent=2, ensure_ascii=True))
        raise SystemExit(1)

    case_sections = "\n".join(render_case(case, threshold_note) for case in cases)
    html_text = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BizHallu Portfolio Demo</title>
    <style>
      :root {{
        --bg: #f5f5f7;
        --surface: #ffffff;
        --text: #1d1d1f;
        --muted: #5f6368;
        --line: rgba(29, 29, 31, 0.12);
        --blue: #0066cc;
        --green: #0a7f42;
        --red: #b3261e;
        --amber: #9a6700;
        --soft-green: rgba(10, 127, 66, 0.12);
        --soft-red: rgba(179, 38, 30, 0.12);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: linear-gradient(180deg, #ffffff 0%, var(--bg) 44%, #eef3f8 100%);
        color: var(--text);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
        line-height: 1.5;
      }}
      a {{ color: inherit; text-decoration: none; }}
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
        background: rgba(245, 245, 247, 0.86);
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
      .nav-links {{ display: flex; gap: 18px; color: var(--muted); font-size: 14px; font-weight: 700; }}
      main {{ width: min(1180px, calc(100% - 40px)); margin: 0 auto; }}
      .hero {{
        display: grid;
        grid-template-columns: minmax(0, 1.2fr) minmax(300px, 0.8fr);
        gap: 32px;
        align-items: end;
        min-height: calc(100vh - 74px);
        padding: 70px 0 46px;
      }}
      .eyebrow, .tag {{
        margin: 0 0 12px;
        color: var(--blue);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
      }}
      h1, h2, h3, p, td, th, li, dd {{ overflow-wrap: anywhere; }}
      h1 {{ max-width: 840px; margin: 0; font-size: 64px; line-height: 0.99; letter-spacing: 0; }}
      h2 {{ margin: 0; font-size: 38px; line-height: 1.08; letter-spacing: 0; }}
      h3 {{ margin: 0; font-size: 20px; line-height: 1.22; letter-spacing: 0; }}
      .lede {{ max-width: 840px; margin: 22px 0 0; color: var(--muted); font-size: 21px; }}
      .snapshot, .metric-card, .panel, .claim-card {{
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--surface);
      }}
      .snapshot {{ display: grid; overflow: hidden; }}
      .snapshot div {{ padding: 20px; border-bottom: 1px solid var(--line); }}
      .snapshot div:last-child {{ border-bottom: 0; }}
      .label, .metric-card span {{
        color: var(--muted);
        font-size: 12px;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
      }}
      .snapshot strong {{ display: block; margin-top: 4px; font-size: 22px; }}
      section {{ padding: 64px 0; border-top: 1px solid var(--line); }}
      .metric-grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }}
      .metric-card {{ min-height: 160px; padding: 22px; }}
      .metric-card strong {{ display: block; margin: 10px 0 8px; font-size: 40px; line-height: 1; }}
      .metric-card p, .panel p, .claim-card p {{ margin: 0; color: var(--muted); }}
      .claim-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
      .claim-card {{ padding: 22px; }}
      .claim-card h3 {{ margin-bottom: 10px; }}
      .case-heading {{ max-width: 920px; margin-bottom: 24px; }}
      .case-heading p:last-child {{ margin: 16px 0 0; color: var(--muted); font-size: 18px; }}
      .case-grid {{ display: grid; grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr); gap: 16px; margin-bottom: 16px; }}
      .panel {{ padding: 24px; margin-bottom: 16px; }}
      .panel-top {{ display: flex; align-items: end; justify-content: space-between; gap: 20px; margin-bottom: 16px; }}
      .question-panel h3 {{ margin-bottom: 18px; }}
      .gold-answer {{ padding: 16px; border-radius: 8px; background: rgba(0, 102, 204, 0.07); }}
      .gold-answer strong {{ display: block; margin-bottom: 10px; }}
      .gold-list {{ display: grid; gap: 10px; margin: 0; padding-left: 22px; }}
      .gold-list li span, .gold-list li em {{ display: block; color: var(--muted); font-style: normal; }}
      .generated-panel pre {{
        margin: 0;
        white-space: pre-wrap;
        font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
        font-size: 14px;
        line-height: 1.65;
      }}
      mark {{ padding: 2px 4px; border-radius: 6px; color: inherit; }}
      .span-correct {{ background: var(--soft-green); border: 1px solid rgba(10, 127, 66, 0.28); }}
      .span-wrong {{ background: var(--soft-red); border: 1px solid rgba(179, 38, 30, 0.28); }}
      .legend {{ display: flex; gap: 16px; flex-wrap: wrap; margin-top: 18px; color: var(--muted); font-size: 13px; }}
      .legend i {{ display: inline-block; width: 12px; height: 12px; border-radius: 4px; margin-right: 6px; vertical-align: -1px; }}
      .legend-ok {{ background: var(--soft-green); border: 1px solid rgba(10, 127, 66, 0.28); }}
      .legend-bad {{ background: var(--soft-red); border: 1px solid rgba(179, 38, 30, 0.28); }}
      .data-table, .span-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
      th {{ color: var(--muted); font-size: 12px; text-align: left; text-transform: uppercase; }}
      th, td {{ padding: 12px 10px; border-top: 1px solid var(--line); vertical-align: top; }}
      thead th {{ border-top: 0; }}
      .gold-row {{ background: rgba(10, 127, 66, 0.07); }}
      .span-table small {{ display: block; margin-top: 4px; color: var(--muted); font-size: 12px; }}
      .pill {{ display: inline-block; padding: 4px 8px; border-radius: 8px; font-size: 12px; font-weight: 800; }}
      .pill.ok {{ background: var(--soft-green); color: var(--green); }}
      .pill.bad {{ background: var(--soft-red); color: var(--red); }}
      .next {{ display: flex; align-items: center; justify-content: space-between; gap: 24px; }}
      .button {{ display: inline-flex; align-items: center; justify-content: center; min-height: 44px; padding: 11px 18px; border-radius: 8px; background: var(--blue); color: #fff; font-weight: 800; }}
      @media (max-width: 920px) {{
        .topbar {{ padding: 0 20px; }}
        .nav-links {{ display: none; }}
        .hero, .case-grid, .claim-grid {{ grid-template-columns: 1fr; }}
        .metric-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
        h1 {{ font-size: 46px; }}
        h2 {{ font-size: 31px; }}
        .panel-top, .next {{ align-items: flex-start; flex-direction: column; }}
      }}
      @media (max-width: 620px) {{
        main {{ width: min(100% - 28px, 1180px); }}
        .metric-grid {{ grid-template-columns: 1fr; }}
        h1 {{ font-size: 38px; }}
        .data-table, .span-table {{ font-size: 12px; }}
        th, td {{ padding: 10px 7px; }}
      }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <a class="brand" href="../site/index.html"><span>BH</span>BizHallu</a>
      <nav class="nav-links">
        <a href="#q_0064">q_0064</a>
        <a href="#q_0069">q_0069</a>
        <a href="./full100_label_lock_report.html">Label lock</a>
      </nav>
    </header>
    <main>
      <section class="hero">
        <div>
          <p class="eyebrow">BizHallu Portfolio Demo</p>
          <h1>Business hallucinations appear as wrong fact bindings, not just wrong words.</h1>
          <p class="lede">
            BizHallu asks Qwen3-0.6B to answer deterministic retail analytics questions,
            locks key fact spans, and checks whether internal uncertainty scores catch the wrong spans.
            The final demo uses two top-3 product cases because they make the business failure visible.
          </p>
        </div>
        <aside class="snapshot" aria-label="Demo snapshot">
          <div><span class="label">Dataset</span><strong>UCI Online Retail</strong></div>
          <div><span class="label">Model</span><strong>Qwen3-0.6B</strong></div>
          <div><span class="label">Label state</span><strong>Presentation labels locked by assistant_full_review</strong></div>
          <div><span class="label">Primary cases</span><strong>{', '.join(PRIMARY_QUESTION_IDS)}</strong></div>
        </aside>
      </section>
      <section>
        <div class="metric-grid">
          <article class="metric-card"><span>Gold questions</span><strong>100</strong><p>Deterministic business questions from cleaned transaction data.</p></article>
          <article class="metric-card"><span>Locked demo spans</span><strong>{summary['locked_primary_span_count']}</strong><p>Primary spans selected from the label lock package.</p></article>
          <article class="metric-card"><span>Best test AUPRC</span><strong>{summary['best_test_auprc']:.3f}</strong><p>{esc(summary['best_test_auprc_baseline'])} ranks wrong spans best.</p></article>
          <article class="metric-card"><span>Best test F1</span><strong>{summary['best_test_f1']:.3f}</strong><p>{esc(summary['best_test_f1_baseline'])} gives the best dev-thresholded F1.</p></article>
        </div>
      </section>
      <section>
        <div class="claim-grid">
          <article class="claim-card"><span class="tag">Span-level</span><h3>The unit is the business fact.</h3><p>A whole answer can mix correct and hallucinated spans, so the demo labels exact facts rather than full responses.</p></article>
          <article class="claim-card"><span class="tag">Result</span><h3>Simple uncertainty is useful but incomplete.</h3><p>Top-2 margin and entropy produce signal, but confident ranking and amount bindings are still missed.</p></article>
          <article class="claim-card"><span class="tag">Business value</span><h3>Evidence binding is the hard part.</h3><p>The model often copies real values but assigns them to the wrong rank or product, which is dangerous in analytics work.</p></article>
        </div>
      </section>
{case_sections}
      <section class="next">
        <div>
          <p class="eyebrow">Portfolio next step</p>
          <h2>Turn this static demo into a concise project story.</h2>
          <p>The strongest narrative is: Qwen can sound analytic while binding evidence incorrectly; simple internal signals help, but business-context checking is still needed. Source label lock: assistant_full_review.</p>
        </div>
        <a class="button" href="./full100_detector_interpretation.html">Open detector interpretation</a>
      </section>
    </main>
  </body>
</html>
"""

    PORTFOLIO_DEMO_HTML_PATH.write_text(html_text, encoding="utf-8")
    PORTFOLIO_DEMO_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
