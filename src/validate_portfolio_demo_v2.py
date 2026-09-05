from __future__ import annotations

import json
import math
import csv
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from public_paths import repo_path
from presentation_evidence import walkthrough, statistical_context, statistics_html, historical_thresholds


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "reports"

HTML_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_v2.html"
DATA_PATH = REPORTS_DIR / "bizhallu_demo_v2_data.json"
SUMMARY_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_v2_summary.json"
VALIDATION_PATH = REPORTS_DIR / "bizhallu_portfolio_demo_v2_validation.json"

REQUIRED_HTML_FRAGMENTS = [
    "Interactive demo v2",
    "BizHallu: evidence binding in business analysis",
    "Product-amount fidelity versus ranking correctness",
    "Historical selected spans and detector readouts",
    "relationshipPanel",
    "caseSelect",
    "Open JSON data bundle",
    "detectorFilter",
    "factTypeFilter",
    "labelFilter",
    "outcomeFilter",
    "q_0064",
    "q_0069",
    "not an independent human benchmark",
    "do not discover claims automatically",
    "Exploratory max test AUPRC",
    "Incorrect binding",
    "detectorHelp",
    "URLSearchParams",
]

FORBIDDEN_FRAGMENTS = [
    "large human-labeled benchmark",
    "production-ready detector",
    "Split-safe detector ranking result",
    "Dev-thresholded held-out result",
]


class HTMLCheckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.seen_tags = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.seen_tags += 1


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add_failure(failures: list[dict[str, Any]], name: str, detail: Any) -> None:
    failures.append({"name": name, "detail": detail})


def validate_data_contract(data: dict[str, Any]) -> None:
    for family, threshold in historical_thresholds().items():
        if data['meta'].get(family + '_threshold') != threshold:
            raise ValueError('Public thresholds differ from original dev threshold reports')
    for field, expected in {'independent_human_annotation': False,
                            'automatic_claim_extraction': False,
                            'metric_selection_status': 'exploratory_test_maxima'}.items():
        if data['meta'].get(field) != expected:
            raise ValueError('Public metadata must preserve the review and evaluation scope')
    cases = data['cases']
    if len(cases) != 9 or len({c['question_id'] for c in cases}) != 9:
        raise ValueError('Public cases must be nine unique questions')
    spans = [span for case in cases for span in case['spans']]
    if len(spans) != 15 or len({s['annotation_id'] for s in spans}) != 15:
        raise ValueError('Historical selected spans must remain 15 unique records')
    for case in cases:
        if case['presentation_walkthrough'] != walkthrough(case):
            raise ValueError('Curated relationship proof differs from source rows or quotes')
        for span in case['spans']:
            start,end=span['span_start_char'],span['span_end_char']
            if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(case['generated_text']):
                raise ValueError('Invalid public span range')
            if case['generated_text'][start:end] != span['span_text'] or span['question_id'] != case['question_id']:
                raise ValueError('Public span text or question join changed')
            if span['label'] not in {'correct_key_fact', 'hallucinated_key_fact'}:
                raise ValueError('Unexpected historical presentation label')
            positive=span['label']!='correct_key_fact'
            for detector in ['simple','entropy','energy']:
                score=span[detector+'_score'];threshold=data['meta'][detector+'_threshold']
                if type(score) not in [int,float] or type(threshold) not in [int,float] or not math.isfinite(score) or not math.isfinite(threshold):
                    raise ValueError('Non-finite or invalid public score/threshold')
                flagged=score>=threshold
                expected=('caught' if flagged else 'missed') if positive else ('false alarm' if flagged else 'cleared')
                if span[detector+'_outcome']!=expected:
                    raise ValueError('Historical detector outcome does not follow the frozen threshold')
    if data['statistical_review']!=statistical_context():
        raise ValueError('Statistical context differs from the B1 source')


def validate_historical_projection(data: dict[str, Any]) -> None:
    def jsonl(path):
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    locks = {r['annotation_id']: r for r in jsonl(REPORTS_DIR / 'full100_label_lock_decisions.jsonl')}
    atoms = {r['annotation_id']: r for r in jsonl(PROJECT_ROOT / 'data/annotations/span_annotations_full100_draft.jsonl')}
    with (PROJECT_ROOT / 'results/full100_draft_detector_scores.csv').open(encoding='utf-8-sig', newline='') as file:
        scores = {r['annotation_id']: r for r in csv.DictReader(file)}
    original = load_json(REPORTS_DIR / 'bizhallu_portfolio_demo_summary.json')
    for family in ['simple', 'entropy', 'energy']:
        if data['meta'][family + '_threshold'] != original[family + '_threshold']:
            raise ValueError('Public threshold differs from preserved historical source')
    spans = [s for c in data['cases'] for s in c['spans']]
    if {s['annotation_id'] for s in spans} != set(locks):
        raise ValueError('Presentation annotation membership changed')
    for span in spans:
        aid = span['annotation_id']
        for field in ['question_id', 'span_text', 'fact_type', 'label', 'review_note']:
            if span[field] != locks[aid][field]:
                raise ValueError('Historical presentation judgment changed')
        for field in ['span_start_char', 'span_end_char']:
            if span[field] != atoms[aid][field]:
                raise ValueError('Historical atom boundary changed')
        for family, field in [('simple', 'one_minus_min_top2_margin'), ('entropy', 'mean_token_entropy'),
                              ('energy', 'mean_spilled_probability_mass_after_top2')]:
            if span[family + '_score'] != float(scores[aid][field]):
                raise ValueError('Public score differs from preserved source')


def validate_embedded_data(html_text: str, data: dict[str, Any]) -> None:
    marker = 'const DEMO_DATA = '
    if html_text.count(marker) != 1:
        raise ValueError('Expected exactly one embedded demo payload')
    embedded, _ = json.JSONDecoder().raw_decode(html_text.split(marker, 1)[1])
    if embedded != data:
        raise ValueError('Visible demo script and downloadable JSON disagree')


def main() -> None:
    failures: list[dict[str, Any]] = []
    for path in [HTML_PATH, DATA_PATH, SUMMARY_PATH]:
        if not path.exists():
            add_failure(failures, "required_file_missing", repo_path(path))

    html_text = HTML_PATH.read_text(encoding="utf-8") if HTML_PATH.exists() else ""
    data = load_json(DATA_PATH) if DATA_PATH.exists() else {}
    summary = load_json(SUMMARY_PATH) if SUMMARY_PATH.exists() else {}
    try:
        validate_data_contract(data)
        validate_historical_projection(data)
        validate_embedded_data(html_text, data)
        if statistics_html(data['statistical_review']) not in html_text:
            raise ValueError('Demo does not display the current statistical comparison')
    except (ValueError,KeyError,TypeError,IndexError) as exc:
        add_failure(failures,'presentation_evidence_contract',str(exc))

    if html_text:
        parser = HTMLCheckParser()
        parser.feed(html_text)
        if parser.seen_tags == 0:
            add_failure(failures, "html_parse", "no HTML tags parsed")
        for fragment in REQUIRED_HTML_FRAGMENTS:
            if fragment not in html_text:
                add_failure(failures, "required_html_fragment_missing", fragment)
        for fragment in FORBIDDEN_FRAGMENTS:
            if fragment in html_text:
                add_failure(failures, "forbidden_html_fragment", fragment)

    meta = data.get("meta", {})
    cases = data.get("cases", [])
    all_spans = [span for case in cases for span in case.get("spans", [])]
    case_ids = {case.get("question_id") for case in cases}

    if meta.get("status") != "portfolio_demo_v2_ready":
        add_failure(failures, "data_status", meta.get("status"))
    for question_id in ["q_0064", "q_0069"]:
        if question_id not in case_ids:
            add_failure(failures, "primary_case_missing", question_id)
    if len(cases) < 9:
        add_failure(failures, "case_count_too_small", len(cases))
    if len(all_spans) != 15:
        add_failure(failures, "locked_span_count", len(all_spans))
    if not data.get("filters", {}).get("fact_types"):
        add_failure(failures, "missing_fact_type_filters", data.get("filters"))
    if not data.get("filters", {}).get("outcomes"):
        add_failure(failures, "missing_outcome_filters", data.get("filters"))
    if {span.get("label") for span in all_spans} != {"correct_key_fact", "hallucinated_key_fact"}:
        add_failure(failures, "unexpected_label_set", sorted({span.get("label") for span in all_spans}))
    for span in all_spans:
        for field in ["simple_outcome", "entropy_outcome", "energy_outcome"]:
            if span.get(field) not in {"caught", "missed", "false alarm", "cleared"}:
                add_failure(failures, "bad_detector_outcome", {"annotation_id": span.get("annotation_id"), "field": field})

    expected_summary = {
        "status": "portfolio_demo_v2_ready",
        "case_count": len(cases),
        "locked_span_count": 15,
        "primary_case_count": 2,
        "label_lock_basis": "assistant_full_review",
        "independent_human_annotation": False,
        "automatic_claim_extraction": False,
        "metric_selection_status": "exploratory_test_maxima",
        "presentation_revision": "english_evidence_review_2026_09_05",
        "curated_relationship_count": 6,
        "statistical_source_sha256": statistical_context()['source_sha256'],
    }
    for key, expected in expected_summary.items():
        if summary.get(key) != expected:
            add_failure(
                failures,
                "summary_value_mismatch",
                {"field": key, "expected": expected, "actual": summary.get(key)},
            )

    validation = {
        "portfolio_demo_v2_html_path": repo_path(HTML_PATH),
        "portfolio_demo_v2_data_path": repo_path(DATA_PATH),
        "ready_for_public_demo_v2": len(failures) == 0,
        "case_count": len(cases),
        "locked_span_count": len(all_spans),
        "num_failures": len(failures),
        "failures": failures,
        "validation_scope": "content_source_offsets_scores_and_schema_only",
        "visual_review_verified": False,
        "independent_human_review_verified": False,
    }
    VALIDATION_PATH.write_text(json.dumps(validation, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(validation, indent=2, ensure_ascii=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
