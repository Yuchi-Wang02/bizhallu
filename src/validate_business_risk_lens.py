"""Validate displayed ledger arithmetic and wording, not business effectiveness."""
from __future__ import annotations
import json
from build_business_risk_lens import REPORTS, HTML_PATH, SUMMARY_PATH, build_summary, render


def check(summary, html_text):
    expected = build_summary()
    if summary != expected:
        raise ValueError('Business lens summary differs from the current contract and Stage A source')
    if html_text != render(expected):
        raise ValueError('Displayed business scope or values differ from the validated source')


def main():
    failures = []
    try:
        check(json.loads(SUMMARY_PATH.read_text(encoding='utf-8')), HTML_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError, KeyError, TypeError, IndexError, ArithmeticError) as exc:
        failures.append(str(exc))
    result = {'business_risk_lens_html_path': 'reports/bizhallu_business_risk_lens.html',
              'ready_for_public_business_lens': not failures,
              'validation_scope': 'public_source_contract_category_reconciliation_and_exact_display; not raw replay, visual QA or deployed business impact',
              'live_deployment_verified': False, 'visual_review_verified': False,
              'independent_business_validation': False, 'num_failures': len(failures), 'failures': failures}
    (REPORTS / 'bizhallu_business_risk_lens_validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
