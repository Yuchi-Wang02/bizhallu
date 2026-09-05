import copy
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from presentation_story import build_story, timed_script_html
from validate_interview_deck import validate_package
from build_career_package import build_rehearsal, rehearsal_html, business_summary


def changed_part(payload, name, old, new):
    out=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(payload)) as source,zipfile.ZipFile(out,'w') as dest:
        for item in source.infolist():
            data=source.read(item.filename)
            if item.filename==name:
                if old not in data:
                    raise AssertionError('Mutation target missing')
                data=data.replace(old,new)
            dest.writestr(item,data)
    return out.getvalue()


class InterviewMaterialsTests(unittest.TestCase):
    def setUp(self):
        self.story=build_story()
        self.payload=(ROOT/'reports/bizhallu_interview_v2.pptx').read_bytes()

    def test_timing_is_budget_not_claimed_measurement(self):
        self.assertEqual(len(self.story['slides']),10)
        self.assertEqual(sum(s['seconds'] for s in self.story['slides']),300)
        self.assertTrue(170<=self.story['pitch_word_count']<=210)
        self.assertTrue(550<=self.story['five_minute_word_count']<=720)
        self.assertIn('not a recorded',self.story['timing_basis'])

    def test_checked_business_example_is_consistent(self):
        c=self.story['april']
        self.assertEqual((c['stated_rank'],c['rank_in_shown_evidence'],c['amount_lexical']),(3,7,'4,173.18'))
        self.assertEqual([c['rank_in_shown_evidence'] for c in self.story['september']],[3,8,2])
        self.assertTrue(all(c['row_value_supported'] for c in self.story['september']))

    def test_saved_career_story_matches_source(self):
        summary=json.loads((ROOT/'reports/bizhallu_career_package_summary.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['story'],self.story)
        self.assertFalse(summary['owner_mastery_verified'])
        self.assertFalse(summary['independent_human_annotation'])

    def test_html_escaping_for_spoken_text(self):
        story=copy.deepcopy(self.story)
        story['slides'][0]['script']='<script>alert(1)</script>'
        rendered=timed_script_html(story)
        self.assertIn('&lt;script&gt;',rendered)
        self.assertNotIn('<script>',rendered)

    def test_final_deck_source_and_editable_evidence(self):
        validate_package(self.payload,self.story)

    def test_wrong_evidence_amount_is_rejected(self):
        mutated=changed_part(self.payload,'ppt/slides/slide2.xml',b'4,173.18',b'4,173.19')
        with self.assertRaises(ValueError):
            validate_package(mutated,self.story)

    def test_changed_speaker_notes_are_rejected(self):
        altered=copy.deepcopy(self.story)
        altered['slides'][0]['script']+=' Unsupported claim.'
        with self.assertRaises(ValueError):
            validate_package(self.payload,altered)

    def test_truncated_chart_axis_is_rejected(self):
        with zipfile.ZipFile(io.BytesIO(self.payload)) as z:
            chart=next(n for n in z.namelist() if n.endswith('/chart1.xml'))
        mutated=changed_part(self.payload,chart,b'<c:min val="0"',b'<c:min val="0.7"')
        with self.assertRaises(ValueError):
            validate_package(mutated,self.story)

    def test_b2_note_cannot_disappear_or_claim_a_new_test(self):
        for old,new in [(b'B2 adds 9 provisional dev atoms', b'No sensitivity is available'),
                        (b'Same old test, not new confirmation.', b'Fresh independent confirmation.')]:
            mutated=changed_part(self.payload,'ppt/slides/slide6.xml',old,new)
            with self.assertRaises(ValueError):
                validate_package(mutated,self.story)

    def test_b2_story_keeps_b1_values_separate(self):
        b2=self.story['b2_sensitivity']
        self.assertEqual(b2['test_span_count'],103)
        self.assertEqual(b2['supplement_span_count'],9)
        self.assertFalse(b2['confirmatory'])
        self.assertEqual(b2['entropy']['test_metrics_after']['f1'],.752)
        self.assertIn('not a B2 interval',self.story['slides'][5]['script'])

    def test_practice_recomputes_business_and_metric_examples(self):
        practice = build_rehearsal(self.story, business_summary())
        self.assertEqual([e['id'] for e in practice['exercises']], ['ledger', 'binding', 'metrics'])
        ledger, binding, metrics = [' '.join(e['solution']) for e in practice['exercises']]
        self.assertIn('10,642,110.80 + (-893,979.73) = GBP 9,748,131.07', ledger)
        self.assertIn('GBP -23,577.92', ledger)
        self.assertIn('rank = 1 + that count = 7, not 3', binding)
        self.assertIn('PAPER CHAIN KIT EMPIRE at GBP 6,619.51', binding)
        self.assertIn('106 / (106 + 22 + 8) = 0.7794', metrics)
        self.assertIn('122 / (122 + 42 + 0) = 0.7439', metrics)
        self.assertIn('20 fewer false alarms', metrics)
        self.assertIn('8 additional labeled errors', metrics)
        self.assertIn('Crossing zero is not proof of equality', metrics)
        self.assertIn('not a B2 interval', metrics)

    def test_practice_rejects_wrong_ledger_sign_or_nonfinite_value(self):
        for value in (893979.73, float('nan'), float('inf')):
            business = business_summary()
            business['ledger']['negative_transaction_value_gbp'] = value
            with self.assertRaises(ValueError):
                build_rehearsal(self.story, business)

    def test_practice_rejects_wrong_counts_or_f1(self):
        for key, value in [('tp', 54), ('fn', -1), ('f1', .9), ('f1', float('nan'))]:
            story = copy.deepcopy(self.story)
            row = next(r for r in story['statistical_review']['test_rows'] if r['signal'] == 'mean_token_entropy')
            row[key] = value
            with self.assertRaises(ValueError):
                build_rehearsal(story, business_summary())

    def test_practice_discloses_exposure_without_collecting_reviews(self):
        practice = build_rehearsal(self.story, business_summary())
        self.assertFalse(practice['owner_mastery_verified'])
        self.assertFalse(practice['independent_human_review'])
        self.assertFalse(practice['new_model_run'])
        self.assertIn('not blind annotation', practice['scope'])
        self.assertIn('No responses, identity or progress are collected', practice['scope'])
        rendered = rehearsal_html(practice)
        self.assertEqual(rendered.count('<details>'), 3)
        for tag in ('<input', '<form', '<script'):
            self.assertNotIn(tag, rendered)
        practice['exercises'][0]['solution'] = ['<script>bad()</script>']
        self.assertIn('&lt;script&gt;', rehearsal_html(practice))
        self.assertNotIn('<script>', rehearsal_html(practice))

    def test_committed_practice_matches_source_without_changing_story(self):
        summary = json.loads((ROOT/'reports/bizhallu_career_package_summary.json').read_text(encoding='utf-8'))
        self.assertEqual(summary['explanation_practice'], build_rehearsal(self.story, business_summary()))
        self.assertEqual(summary['story'], self.story)


if __name__=='__main__':
    unittest.main()
