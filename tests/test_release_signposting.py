"""Release-level checks for current explanations versus archived source records."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from build_github_pages_bundle import PAGE_COPIES, ARCHIVE_NOTICES, archive_notice, add_archive_notice, rewrite_links, add_public_metadata
from presentation_evidence import b2_note_html


class ReleaseSignpostingTests(unittest.TestCase):
    def test_main_reader_paths_include_b2_without_replacing_b1(self):
        for filename in ['index.html','portfolio_demo_v2.html','portfolio_demo.html',
                         'career_package.html','portfolio_narrative.html',
                         'research_one_pager.html','detector_interpretation.html']:
            with self.subTest(page=filename):
                text=(ROOT/'docs'/filename).read_text(encoding='utf-8')
                self.assertIn(b2_note_html(),text)
                self.assertIn('0.779',text)
                self.assertIn('0.752',text)
                self.assertNotIn('missing q_0048 is a dev-label gap',text)

    def test_archived_pages_preserve_source_and_add_exact_notice(self):
        for source,dest,role in PAGE_COPIES:
            if role in ARCHIVE_NOTICES:
                original=source.read_text(encoding='utf-8')
                copied=dest.read_text(encoding='utf-8')
                notice=archive_notice(role)
                self.assertEqual(copied.count(notice),1)
                self.assertEqual(copied.replace(notice,''),add_public_metadata(rewrite_links(original),dest))
                self.assertEqual(copied.split('</head>',1)[1].replace(notice,''),rewrite_links(original).split('</head>',1)[1])
                self.assertNotIn('id="archive-notice"',original)

    def test_archive_insertion_handles_body_attributes_and_rejects_duplicates(self):
        role='label_lock_report'
        source='<HTML><BODY class="old">history</BODY></HTML>'
        result=add_archive_notice(source,role)
        self.assertEqual(result.replace(archive_notice(role),''),source)
        with self.assertRaises(ValueError):
            add_archive_notice(result,role)
        with self.assertRaises(ValueError):
            add_archive_notice('<main>no body</main>',role)

    def test_current_pages_do_not_receive_an_archive_notice(self):
        self.assertEqual(add_archive_notice('<body>current</body>','interactive_demo_v2'),'<body>current</body>')

    def test_methods_long_labels_keep_responsive_safety_rules(self):
        # This guards the CSS contract; real viewport geometry is checked in-browser.
        text=(ROOT/'docs/detector_interpretation.html').read_text(encoding='utf-8')
        self.assertIn('.panel { min-width: 0;',text)
        self.assertIn('.error-list li > * { min-width: 0; max-width: 100%; overflow-wrap: anywhere; }',text)
        self.assertIn('.hero, .two-col, .claim-grid { grid-template-columns: minmax(0, 1fr); }',text)
        self.assertIn('.b2-table { max-width: 100%; overflow-x: auto;',text)
        self.assertIn('#b2-dev-sensitivity, #statistical-review { scroll-margin-top: 82px; }',text)


if __name__=='__main__':
    unittest.main()
