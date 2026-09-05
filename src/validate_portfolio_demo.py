"""Check the preserved primary subset against committed source labels and scores."""
from __future__ import annotations
import json

from build_portfolio_demo import REPORTS, HTML_PATH, SUMMARY_PATH, load_data, build_summary, render
from validate_portfolio_demo_v2 import validate_data_contract, validate_historical_projection


def check(data, summary, html_text):
    validate_data_contract(data)
    validate_historical_projection(data)
    expected = build_summary(data)
    if summary != expected:
        raise ValueError('Primary demo summary is not the preserved source projection')
    if html_text != render(data, expected):
        raise ValueError('Primary demo displayed evidence or interpretation drifted')


def main():
    failures = []
    try:
        check(load_data(), json.loads(SUMMARY_PATH.read_text(encoding='utf-8')), HTML_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError, KeyError, TypeError, IndexError, ArithmeticError) as exc:
        failures.append(str(exc))
    result = {'html_path': 'reports/bizhallu_portfolio_demo.html', 'summary_path': 'reports/bizhallu_portfolio_demo_summary.json',
              'case_count': 2, 'primary_question_ids': ['q_0064','q_0069'], 'locked_primary_span_count': 7,
              'ready_for_portfolio_demo': not failures,
              'validation_scope': 'committed_label_score_projection_curated_evidence_and_exact_display; not private replay or independent review',
              'visual_review_verified': False, 'independent_human_review_verified': False,
              'num_failures': len(failures), 'failures': failures}
    (REPORTS / 'bizhallu_portfolio_demo_validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
