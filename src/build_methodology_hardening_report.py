from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from public_paths import repo_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QUESTIONS_PATH = PROJECT_ROOT / "data" / "processed" / "business_questions_gold.jsonl"
SCORES_PATH = PROJECT_ROOT / "results" / "full100_draft_detector_scores.csv"
INTERPRETATION_PATH = PROJECT_ROOT / "reports" / "full100_detector_interpretation_summary.json"
PROTOCOL_PATH = PROJECT_ROOT / "configs" / "methodology_protocol_v1.json"
REVIEW_SOURCE_PATH = PROJECT_ROOT / "src" / "build_full100_review.py"
QUEUE_SOURCE_PATH = PROJECT_ROOT / "src" / "build_full100_annotation_queue.py"
SPLIT_SOURCE_PATH = PROJECT_ROOT / "src" / "generate_questions.py"

REPORTS_DIR = PROJECT_ROOT / "reports"
HTML_PATH = REPORTS_DIR / "bizhallu_methodology_hardening.html"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_methodology_hardening_summary.json"

PERIOD_RE = re.compile(r"^\d{4}-\d{2}$")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_questions(path: Path = QUESTIONS_PATH) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def load_scores(path: Path = SCORES_PATH) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def question_periods(question: dict[str, Any]) -> list[str]:
    values: set[str] = set()

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str) and PERIOD_RE.fullmatch(value):
            values.add(value)

    walk(question.get("evidence", {}).get("filters", {}))
    walk(question.get("gold_answer", {}))
    return sorted(values)


def cross_split_groups(
    questions: list[dict[str, Any]], field: str
) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for question in questions:
        evidence = question.get("evidence", {})
        groups[canonical_hash(evidence.get(field, [] if field == "rows" else {}))].append(question)

    results: list[dict[str, Any]] = []
    for fingerprint, members in groups.items():
        splits = sorted({member["split"] for member in members})
        if len(splits) < 2:
            continue
        results.append(
            {
                "fingerprint_sha256": fingerprint,
                "row_count": len(members[0].get("evidence", {}).get("rows", [])),
                "splits": splits,
                "questions": [
                    {
                        "question_id": member["question_id"],
                        "split": member["split"],
                        "question_type": member["question_type"],
                        "periods": question_periods(member),
                    }
                    for member in sorted(members, key=lambda item: item["question_id"])
                ],
            }
        )
    return sorted(results, key=lambda item: item["questions"][0]["question_id"])


def audit_current_methodology(
    questions: list[dict[str, Any]], scores: list[dict[str, str]]
) -> dict[str, Any]:
    question_by_id = {question["question_id"]: question for question in questions}
    heldout = [question for question in questions if question["split"] in {"dev", "test"}]
    scored_ids = sorted({row["question_id"] for row in scores})
    missing_heldout = sorted({question["question_id"] for question in heldout} - set(scored_ids))

    periods_by_split: dict[str, set[str]] = defaultdict(set)
    for question in questions:
        periods_by_split[question["split"]].update(question_periods(question))

    period_overlaps: dict[str, list[str]] = {}
    for left, right in [("dev", "test"), ("train", "dev"), ("train", "test")]:
        period_overlaps[f"{left}_{right}"] = sorted(periods_by_split[left] & periods_by_split[right])

    evidence_groups = cross_split_groups(questions, "rows")
    filter_groups = cross_split_groups(questions, "filters")

    review_source = REVIEW_SOURCE_PATH.read_text(encoding="utf-8")
    queue_source = QUEUE_SOURCE_PATH.read_text(encoding="utf-8")
    split_source = SPLIT_SOURCE_PATH.read_text(encoding="utf-8")
    source_checks = {
        "heldout_priority_depends_on_auto_status": (
            'if split in {"dev", "test"} and status != "likely_correct":' in review_source
        ),
        "initial_batch_is_heldout_high_priority": (
            'is_initial_batch = phase == "phase_1_heldout_high"' in queue_source
        ),
        "split_uses_within_type_position_modulo_five": (
            "if position % 5 in (1, 2, 3):" in split_source
            and "elif position % 5 == 4:" in split_source
        ),
    }

    annotated_split_counts = Counter(question_by_id[qid]["split"] for qid in scored_ids)
    span_split_counts = Counter(row["split"] for row in scores)
    label_counts = Counter(row["label"] for row in scores)
    question_type_split_counts: dict[str, dict[str, int]] = {}
    for question_type in sorted({question["question_type"] for question in questions}):
        counts = Counter(
            question["split"] for question in questions if question["question_type"] == question_type
        )
        question_type_split_counts[question_type] = {
            split: counts.get(split, 0) for split in ["train", "dev", "test"]
        }

    return {
        "question_count": len(questions),
        "split_counts": dict(sorted(Counter(question["split"] for question in questions).items())),
        "heldout_question_count": len(heldout),
        "annotated_heldout_question_count": len(scored_ids),
        "annotated_heldout_split_counts": dict(sorted(annotated_split_counts.items())),
        "missing_heldout_question_ids": missing_heldout,
        "missing_heldout_questions": [
            {
                "question_id": qid,
                "split": question_by_id[qid]["split"],
                "question_type": question_by_id[qid]["question_type"],
                "question": question_by_id[qid]["question"],
            }
            for qid in missing_heldout
        ],
        "annotated_span_count": len(scores),
        "span_split_counts": dict(sorted(span_split_counts.items())),
        "span_label_counts": dict(sorted(label_counts.items())),
        "periods_by_split": {key: sorted(value) for key, value in sorted(periods_by_split.items())},
        "period_overlap": period_overlaps,
        "exact_evidence_row_cross_split_group_count": len(evidence_groups),
        "exact_evidence_row_cross_split_question_count": sum(
            len(group["questions"]) for group in evidence_groups
        ),
        "exact_evidence_row_cross_split_groups": evidence_groups,
        "exact_filter_cross_split_group_count": len(filter_groups),
        "exact_filter_cross_split_groups": filter_groups,
        "question_type_split_counts": question_type_split_counts,
        "source_code_checks": source_checks,
    }


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def render_list(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in items) + "</ul>"


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    questions = load_questions()
    scores = load_scores()
    interpretation = load_json(INTERPRETATION_PATH)
    protocol = load_json(PROTOCOL_PATH)
    audit = audit_current_methodology(questions, scores)

    best_auprc = interpretation["best_overall_by_test_auprc"]
    best_f1 = interpretation["best_overall_by_test_f1"]
    locked = protocol["locked_public_results"]

    findings = [
        {
            "severity": "high",
            "name": "Outcome-informed annotation subset",
            "evidence": (
                f"Score rows cover {audit['annotated_heldout_question_count']} of "
                f"{audit['heldout_question_count']} dev/test questions. The queue code prioritizes "
                "held-out answers when generated-answer auto-status is not likely_correct."
            ),
            "implication": (
                "The 205-span evaluation is conditional on a high-priority error-enriched subset; "
                "it is not a representative estimate over all generated business answers."
            ),
        },
        {
            "severity": "high",
            "name": "Post-hoc headline signal selection",
            "evidence": (
                "Each signal threshold was selected on dev, but the public AUPRC and F1 winners "
                "were identified after comparing candidate signals on test."
            ),
            "implication": (
                "The observed maxima are useful exploratory summaries, not unbiased confirmation-set estimates."
            ),
        },
        {
            "severity": "high",
            "name": "Context overlap across splits",
            "evidence": (
                f"Dev and test share {len(audit['period_overlap']['dev_test'])} business periods. "
                f"There are {audit['exact_evidence_row_cross_split_group_count']} exact gold evidence-row "
                f"fingerprint groups crossing splits, involving "
                f"{audit['exact_evidence_row_cross_split_question_count']} questions."
            ),
            "implication": (
                "The split is question-level, not evidence-context independent; results do not establish "
                "generalization to unseen months or evidence payloads."
            ),
        },
        {
            "severity": "high",
            "name": "Provisional labels without independent agreement",
            "evidence": (
                "The 205 spans are AI-assisted provisional labels. Fifteen selected spans received "
                "additional assistant review; no independent human annotation or IAA is available."
            ),
            "implication": "Label reliability is not yet independently estimated.",
        },
        {
            "severity": "medium",
            "name": "Oracle span boundary",
            "evidence": "Detector signals are scored on pre-identified business-fact spans.",
            "implication": (
                "The current experiment evaluates span scoring, not automatic claim extraction or an end-to-end audit system."
            ),
        },
    ]

    summary = {
        "status": "methodology_hardening_v1_ready",
        "share_status": "share_with_caveats",
        "html_path": repo_path(HTML_PATH),
        "protocol_path": repo_path(PROTOCOL_PATH),
        "study_classification": protocol["current_study"]["classification"],
        "locked_public_results": locked,
        "audit": audit,
        "finding_count": len(findings),
        "high_severity_finding_count": sum(item["severity"] == "high" for item in findings),
        "findings": findings,
        "confirmation_protocol_status": protocol["future_confirmation_protocol"]["status"],
        "primary_confirmation_metric": protocol["future_confirmation_protocol"]["detector_policy"]["primary_metric"],
        "public_interpretation": (
            "The current metrics are reproducible exploratory results on an outcome-informed, "
            "question-level split with provisional labels. They motivate, but do not replace, a fresh "
            "context-separated confirmation study."
        ),
        "num_failures": 0,
        "failures": [],
    }

    finding_rows = "\n".join(
        f"""
          <tr>
            <td><strong>{esc(item['name'])}</strong><span class="severity">{esc(item['severity'])}</span></td>
            <td>{esc(item['evidence'])}</td>
            <td>{esc(item['implication'])}</td>
          </tr>
        """.strip()
        for item in findings
    )

    evidence_groups = audit["exact_evidence_row_cross_split_groups"]
    overlap_rows = "\n".join(
        f"""
          <tr>
            <td><code>{esc(group['fingerprint_sha256'][:10])}</code></td>
            <td>{esc(', '.join(group['splits']))}</td>
            <td>{esc(', '.join(item['question_id'] for item in group['questions']))}</td>
            <td>{esc(', '.join(sorted({period for item in group['questions'] for period in item['periods']})))}</td>
          </tr>
        """.strip()
        for group in evidence_groups
    )

    confirmation = protocol["future_confirmation_protocol"]
    html_text = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>BizHallu Methodology Hardening v1</title>
    <style>
      :root {{ --bg:#f5f6f8; --surface:#fff; --ink:#1d1d1f; --muted:#5f6368; --line:#d9dde3; --blue:#075ea8; --red:#a42b2b; --green:#126b4f; }}
      * {{ box-sizing:border-box; }}
      body {{ margin:0; background:var(--bg); color:var(--ink); font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif; line-height:1.55; }}
      a {{ color:var(--blue); text-decoration:none; }}
      .topbar {{ min-height:60px; display:flex; align-items:center; justify-content:space-between; padding:0 28px; border-bottom:1px solid var(--line); background:rgba(255,255,255,.94); position:sticky; top:0; z-index:5; }}
      .brand {{ color:var(--ink); font-weight:850; }}
      nav {{ display:flex; gap:16px; font-size:14px; font-weight:700; }}
      main {{ width:min(1120px,calc(100% - 36px)); margin:0 auto; }}
      section {{ padding:44px 0; border-bottom:1px solid var(--line); }}
      .hero {{ padding-top:64px; }}
      .eyebrow {{ margin:0 0 10px; color:var(--blue); font-size:12px; font-weight:850; text-transform:uppercase; }}
      h1 {{ max-width:920px; margin:0; font-size:clamp(38px,6vw,68px); line-height:1.02; letter-spacing:0; }}
      h2 {{ margin:0; font-size:clamp(28px,4vw,40px); line-height:1.12; letter-spacing:0; }}
      h3 {{ margin:0; font-size:20px; letter-spacing:0; }}
      p, li, td, th {{ overflow-wrap:anywhere; }}
      .lede {{ max-width:900px; margin:20px 0 0; color:var(--muted); font-size:20px; }}
      .status {{ margin-top:26px; padding:18px 0; border-top:1px solid var(--line); border-bottom:1px solid var(--line); display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:18px; }}
      .status span {{ display:block; color:var(--muted); font-size:12px; font-weight:800; text-transform:uppercase; }}
      .status strong {{ display:block; margin-top:6px; font-size:24px; }}
      .callout {{ margin-top:22px; padding:20px; border-left:4px solid var(--red); background:#fff8f7; }}
      .callout.good {{ border-left-color:var(--green); background:#f4fbf7; }}
      .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; margin-top:22px; }}
      .panel {{ padding:22px; border:1px solid var(--line); border-radius:8px; background:var(--surface); }}
      .panel p {{ color:var(--muted); }}
      .table-wrap {{ width:100%; margin-top:22px; overflow-x:auto; border:1px solid var(--line); background:var(--surface); }}
      table {{ width:100%; min-width:780px; border-collapse:collapse; background:var(--surface); font-size:14px; }}
      th, td {{ padding:14px; text-align:left; vertical-align:top; border-right:1px solid var(--line); border-bottom:1px solid var(--line); }}
      tr:last-child td {{ border-bottom:0; }}
      th:last-child, td:last-child {{ border-right:0; }}
      th {{ background:#eef1f4; font-size:12px; text-transform:uppercase; }}
      .severity {{ display:block; margin-top:5px; color:var(--red); font-size:11px; font-weight:800; text-transform:uppercase; }}
      ul, ol {{ display:grid; gap:9px; padding-left:22px; }}
      li {{ color:var(--muted); }}
      code {{ padding:2px 5px; background:#eef1f4; border-radius:4px; font-family:"SFMono-Regular",Consolas,monospace; }}
      footer {{ padding:32px 0 46px; color:var(--muted); }}
      @media (max-width:820px) {{ nav {{ display:none; }} .status,.grid {{ grid-template-columns:1fr; }} }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <a class="brand" href="../site/index.html">BizHallu</a>
      <nav><a href="./bizhallu_portfolio_demo_v2.html">Demo</a><a href="./full100_detector_interpretation.html">Results</a><a href="./bizhallu_research_one_pager.html">Research</a></nav>
    </header>
    <main>
      <section class="hero">
        <p class="eyebrow">Methodology Hardening v1</p>
        <h1>What the current result proves, and what it does not.</h1>
        <p class="lede">This audit preserves the published experiment while separating reproducible exploratory evidence from the design of a future confirmation study.</p>
        <div class="status">
          <div><span>Study class</span><strong>Exploratory</strong></div>
          <div><span>Annotated questions</span><strong>{audit['annotated_heldout_question_count']} / {audit['heldout_question_count']}</strong></div>
          <div><span>Provisional spans</span><strong>{audit['annotated_span_count']}</strong></div>
          <div><span>Share status</span><strong>With caveats</strong></div>
        </div>
        <div class="callout"><strong>Bottom line.</strong> The 0.835 AUPRC and 0.779 F1 values are real outputs of the committed pipeline, but they are exploratory maxima on an error-enriched subset with context overlap and provisional labels. They should motivate a fresh confirmation study, not be presented as its result.</div>
      </section>

      <section>
        <p class="eyebrow">Evidence audit</p>
        <h2>Five boundaries now made explicit</h2>
        <div class="table-wrap"><table>
          <thead><tr><th>Finding</th><th>Observed evidence</th><th>Interpretation</th></tr></thead>
          <tbody>{finding_rows}</tbody>
        </table></div>
      </section>

      <section>
        <p class="eyebrow">Selection and split diagnosis</p>
        <h2>The current test is held out for thresholds, not for the full research decision.</h2>
        <div class="grid">
          <article class="panel"><h3>What is valid</h3><p>Each candidate signal uses a threshold chosen on dev spans and reuses that fixed threshold on test spans. Character offsets, token alignment, and score rows are reproducibly validated.</p></article>
          <article class="panel"><h3>What remains exploratory</h3><p>The headline signal was selected after viewing test results, and the annotated subset was chosen through an answer-quality triage queue. This prevents confirmatory interpretation.</p></article>
          <article class="panel"><h3>Missing held-out item</h3><p><code>q_0048</code> is the sole dev/test question without detector score rows. It asks which of Netherlands or EIRE generated more net revenue in August 2011.</p></article>
          <article class="panel"><h3>Context overlap</h3><p>Dev and test share {len(audit['period_overlap']['dev_test'])} months: {esc(', '.join(audit['period_overlap']['dev_test']))}. Split assignment is periodic within question type, not grouped by evidence context.</p></article>
        </div>
        <div class="table-wrap"><table>
          <thead><tr><th>Evidence hash</th><th>Splits</th><th>Question IDs</th><th>Period</th></tr></thead>
          <tbody>{overlap_rows}</tbody>
        </table></div>
        <p>These are exact fingerprints of the gold <code>evidence.rows</code> payload. They are not claims that prompts are byte-identical; they show that the same underlying evidence table can support questions assigned to different splits.</p>
      </section>

      <section>
        <p class="eyebrow">Public claim boundary</p>
        <h2>Use the result, but name its evidence level.</h2>
        <div class="grid">
          <article class="panel"><h3>Accurate wording</h3>{render_list(protocol['current_claim_policy']['allowed'])}</article>
          <article class="panel"><h3>Claims not supported yet</h3>{render_list(protocol['current_claim_policy']['disallowed'])}</article>
        </div>
      </section>

      <section>
        <p class="eyebrow">Protocol v1</p>
        <h2>Design the next run before seeing its answers.</h2>
        <ol>
          <li><strong>Fresh contexts.</strong> {esc(confirmation['data_policy']['preferred'])}.</li>
          <li><strong>Context-separated splits.</strong> Group by {esc(confirmation['data_policy']['group_key'])}; never place identical evidence payloads across development and confirmation.</li>
          <li><strong>Independent labels.</strong> {esc(confirmation['annotation_policy']['reviewers'])}; {esc(confirmation['annotation_policy']['agreement'])}.</li>
          <li><strong>Freeze decisions.</strong> Primary metric is {esc(confirmation['detector_policy']['primary_metric'])}; detector families, thresholds, extraction rules, prompts, and verifier logic are fixed before confirmation-set access.</li>
          <li><strong>Separate tasks.</strong> Report oracle-span diagnostics, claim extraction, and end-to-end verification as different evaluations.</li>
        </ol>
        <div class="callout good"><strong>Research direction.</strong> The next study compares internal uncertainty, literature-grounded baselines, and an independently implemented evidence-aware verifier. It does not assume one family will win.</div>
      </section>

      <section>
        <p class="eyebrow">Locked current record</p>
        <h2>No result was recomputed in this phase.</h2>
        <div class="status">
          <div><span>Max test AUPRC</span><strong>{float(best_auprc['test_auprc']):.3f}</strong></div>
          <div><span>Max test F1</span><strong>{float(best_f1['test_f1']):.3f}</strong></div>
          <div><span>Test spans</span><strong>{locked['test_span_count']}</strong></div>
          <div><span>Independent IAA</span><strong>Not done</strong></div>
        </div>
      </section>
    </main>
    <footer><main>Generated from committed question, score, source-code, interpretation, and protocol artifacts. Protocol: <code>configs/methodology_protocol_v1.json</code>.</main></footer>
  </body>
</html>
"""

    HTML_PATH.write_text(html_text, encoding="utf-8")
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "html_path": summary["html_path"],
                "summary_path": repo_path(SUMMARY_PATH),
                "high_severity_finding_count": summary["high_severity_finding_count"],
            },
            indent=2,
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
