"""Local source arithmetic for three curated historical examples, never labels."""
from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'outputs/relation_calibration_admin_v2/source_checks.json'
IDS = ('q_0048', 'q_0053', 'q_0092')


def number(value):
    result = Decimal(str(value).replace(',', ''))
    if not result.is_finite():
        raise ValueError('Non-finite business amount')
    return result


def rounded(value, places='0.01'):
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def percent(numerator, denominator):
    if denominator <= 0:
        raise ValueError('Non-positive comparison denominator')
    return 100 * numerator / denominator


def quote(answer, text):
    if answer.count(text) != 1:
        raise ValueError('Curated quote changed or is ambiguous; re-review this example')
    start = answer.index(text)
    return {'text': text, 'start': start, 'end': start + len(text)}


def check_case(case):
    """Only question, answer and original evidence are inspected; no old labels/scores."""
    qid = case['question_id']
    answer = case['generated_text']
    evidence = case['prompt_evidence_rows']
    checks, quotes = [], []
    for row in evidence:
        for key in ('net_revenue', 'gross_positive_revenue', 'cancellation_revenue'):
            number(row[key])
        if number(row['gross_positive_revenue']) + number(row['cancellation_revenue']) != number(row['net_revenue']):
            raise ValueError('Evidence row does not reconcile')

    if qid == 'q_0048':
        if 'August 2011' not in case['question'] or 'August 2011' not in answer:
            raise ValueError('Unexpected period')
        rows = {r['country']: r for r in evidence}
        if len(rows) != len(evidence):
            raise ValueError('Duplicate country rows')
        netherlands, eire = number(rows['Netherlands']['net_revenue']), number(rows['EIRE']['net_revenue'])
        delta = netherlands - eire
        quotes = [quote(answer, "the Netherlands generated more net revenue (39,655.81 GBP) compared to EIRE (12,147.92 GBP)"),
                  quote(answer, "The Netherlands' net revenue was higher by approximately 27,508 GBP.")]
        checks = [{'field': 'Netherlands amount', 'observed': '39655.81', 'reference': str(netherlands), 'exact': number('39655.81') == netherlands},
                  {'field': 'EIRE amount', 'observed': '12147.92', 'reference': str(eire), 'exact': number('12147.92') == eire},
                  {'field': 'comparison', 'higher_country': 'Netherlands', 'supported_by_subtraction': delta > 0},
                  {'field': 'difference', 'observed': '27508', 'reference': str(delta),
                   'exact': number('27508') == delta, 'nearest_whole_GBP_match': number('27508') == rounded(delta, '1'),
                   'absolute_rounding_difference_GBP': str(abs(number('27508') - delta))}]
        note = 'Approximately 27,508 GBP is correct whole-pound rounding, not exact pence equality and not a hallucination merely because the gold has pence. This note does not create the missing v1 atomic labels.'
        gold_fields = {'country_a_net_revenue': netherlands, 'country_b_net_revenue': eire, 'revenue_delta': delta}
    elif qid == 'q_0053':
        if 'April 2011 to May 2011' not in case['question']:
            raise ValueError('Unexpected comparison periods')
        rows = {r['year_month']: r for r in evidence}
        if set(rows) != {'2011-04', '2011-05'} or len(rows) != len(evidence):
            raise ValueError('Unexpected monthly rows')
        previous, current = number(rows['2011-04']['net_revenue']), number(rows['2011-05']['net_revenue'])
        delta = current - previous
        rate = percent(delta, previous)
        quotes = [quote(answer, 'April 2011 was **492,367.84 GBP**'), quote(answer, 'May 2011, it was **722,094.10 GBP**'),
                  quote(answer, 'The absolute change is **229,726.26 GBP**'), quote(answer, 'the percentage change is **48.97%**')]
        checks = [{'field': 'April amount', 'reference': str(previous), 'observed': '492367.84', 'exact': previous == number('492367.84')},
                  {'field': 'May amount', 'reference': str(current), 'observed': '722094.10', 'exact': current == number('722094.10')},
                  {'field': 'absolute change', 'reference': str(delta), 'observed': '229726.26', 'exact': delta == number('229726.26')},
                  {'field': 'percentage change', 'reference_unrounded_percent': str(rate), 'reference_display_percent': str(rounded(rate)),
                   'observed_percent': '48.97', 'display_rounding_match': rounded(rate) == number('48.97'),
                   'absolute_difference_percentage_points': str(abs(rate - number('48.97')))}]
        note = 'The two monthly amounts and absolute change agree. The percentage is wrong using April as the denominator. No explicit increase/decrease word is given, but positive amounts/difference do not establish a reversed-direction claim. An absent keyword in the old auto-review is not an independently verified direction error; the cause of the percentage mistake is unknown.'
        gold_fields = {'previous_net_revenue': previous, 'current_net_revenue': current, 'absolute_change': delta, 'percent_change': rounded(rate)}
    elif qid == 'q_0092':
        if len(evidence) != 1 or evidence[0]['year_month'] != '2011-03' or 'March 2011' not in case['question']:
            raise ValueError('Unexpected reconciliation scope')
        row = evidence[0]
        positive, negative, net = [number(row[k]) for k in ('gross_positive_revenue', 'cancellation_revenue', 'net_revenue')]
        reduction = -negative
        quotes = [quote(answer, 'cancellations and returns reduced gross positive revenue by GBP 342,012.88'),
                  quote(answer, 'a final net revenue of GBP 682,013.98'),
                  quote(answer, 'The reduction is reported as a positive amount due to the negative cancellation_return_revenue.')]
        checks = [{'field': 'negative transaction magnitude', 'reference': str(reduction), 'observed': '342012.88',
                   'exact': reduction == number('342012.88'), 'absolute_difference_GBP': str(abs(number('342012.88') - reduction))},
                  {'field': 'final net', 'reference': str(net), 'observed': '682013.98', 'exact': net == number('682013.98')},
                  {'field': 'reconciliation using generated reduction', 'positive_evidence_GBP': str(positive),
                   'implied_net_GBP': str(positive - number('342012.88')), 'generated_net_GBP': '682013.98',
                   'reconciles': positive - number('342012.88') == number('682013.98')},
                  {'field': 'sign convention', 'positive_magnitude_of_negative_value': reduction >= 0 and negative <= 0}]
        note = 'The reduction is approximately ten times the source magnitude, but not exactly a tenfold transformation. The final net is copied correctly and does not reconcile with the stated reduction. The sign explanation is arithmetically reasonable; it does not repair the number or establish physical returns. The original question itself uses overbroad returns wording. A percentage was not requested, so its absence alone is not an answer error.'
        gold_fields = {'gross_positive_revenue': positive, 'cancellation_revenue': negative, 'reduction_amount': reduction, 'net_revenue': net}
    else:
        raise ValueError('Not one of the three curated calibration examples')
    return {'question_id': qid, 'source_quotes': quotes, 'calculations': checks, 'interpretation': note,
            'gold_replay_values': {k: str(v) for k, v in gold_fields.items()}}


def replay_ledger(path, cases):
    targets = {(r['year_month'], None) for c in cases if c['question_id'] != 'q_0048' for r in c['prompt_evidence_rows']}
    targets.update(('2011-08', r['country']) for c in cases if c['question_id'] == 'q_0048' for r in c['prompt_evidence_rows'])
    totals = {key: {'positive': Decimal(0), 'negative': Decimal(0), 'rows': 0} for key in targets}
    with path.open(encoding='utf-8-sig', newline='') as file:
        for row in csv.DictReader(file):
            keys = [(row['year_month'], None), (row['year_month'], row['country'])]
            for key in keys:
                if key not in totals:
                    continue
                value = number(row['quantity']) * number(row['unit_price'])
                totals[key]['positive' if value > 0 else 'negative'] += value
                totals[key]['rows'] += 1
    verified = []
    for case in cases:
        for row in case['prompt_evidence_rows']:
            key = ('2011-08', row['country']) if case['question_id'] == 'q_0048' else (row['year_month'], None)
            item = totals[key]
            if not item['rows']:
                raise ValueError('No local source rows for evidence scope')
            actual = {'net_revenue': item['positive'] + item['negative'], 'gross_positive_revenue': item['positive'], 'cancellation_revenue': item['negative']}
            for field, value in actual.items():
                if rounded(value) != number(row[field]):
                    raise ValueError(f'Local quantity-price replay differs: {key} {field}')
            verified.append({'question_id': case['question_id'], 'period': key[0], 'country': key[1], 'source_row_count': item['rows']})
    return verified


def main():
    paths = [ROOT / 'outputs/full100_review.jsonl', ROOT / 'data/processed/retail_net_revenue_lines.csv',
             ROOT / 'configs/business_metric_contract_v1_1.json']
    reviews = [json.loads(line) for line in paths[0].read_text(encoding='utf-8').splitlines() if line.strip()]
    selected = [r for r in reviews if r['question_id'] in IDS]
    if len(selected) != 3 or {r['question_id'] for r in selected} != set(IDS):
        raise ValueError('Missing or duplicate curated questions')
    cases = [{'question_id': r['question_id'], 'question': r['question'], 'generated_text': r['generation']['generated_text'],
              'prompt_evidence_rows': r['prompt_evidence_rows']} for r in selected]
    calculations = [check_case(c) for c in cases]
    for checked, original in zip(calculations, selected):
        for key, value in checked['gold_replay_values'].items():
            if number(original['gold_answer'][key]) != number(value):
                raise ValueError('Gold differs from independently computed evidence arithmetic')
    source_rows = replay_ledger(paths[1], cases)
    hashes = {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    result = {'status': 'assistant_source_arithmetic_checked_not_annotations', 'case_count': len(cases),
              'independent_human_review': False, 'new_evaluation_labels': 0, 'new_detector_predictions': 0,
              'q0048_atomic_supplement_complete': False, 'ready_for_new_metrics': False,
              'private_admin_only': True, 'cases': calculations, 'ledger_replay': source_rows, 'source_sha256': hashes,
              'scope': 'Curated source checks with exact quote anchors, not automated extraction, full-answer adjudication or independent review. Do not load into the blinded reviewer packet.'}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=True, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in {'cases', 'source_sha256'}}, indent=2))


if __name__ == '__main__':
    main()
