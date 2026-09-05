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


if __name__=='__main__':
    unittest.main()
