"""Reader links should open a report and reach the named section."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import validate_github_pages_bundle as checks


class PublicReaderLinkTests(unittest.TestCase):
    def test_readme_distinguishes_report_from_html_source(self):
        failures = []
        checks.validate_readme_reader_links(
            '[B2](docs/methods.html#b2) '
            '[B1](https://github.com/owner/repo/blob/main/reports/b1.html) '
            '[Report](https://owner.github.io/repo/methods.html#b2) '
            '[HTML source](docs/methods.html)', failures)
        self.assertEqual([x['href'] for x in failures], [
            'docs/methods.html#b2', 'https://github.com/owner/repo/blob/main/reports/b1.html'])

    def test_local_links_reject_missing_section_on_existing_page(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            page = root / 'index.html'
            page.write_text('<a href="./methods.html#missing">Read B2</a>', encoding='utf-8')
            (root / 'methods.html').write_text('<section id="b2"></section>', encoding='utf-8')
            failures = []
            with patch.object(checks, 'ROOT', root):
                checks.validate_local_links(page, failures)
            self.assertEqual([x['name'] for x in failures], ['local_link_anchor'])

    def test_same_page_encoded_and_external_links(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            page = root / 'index.html'
            page.write_text('<main id="main"></main><a href="#main">Skip</a>'
                            '<a href="./methods.html#B%202">B2</a>'
                            '<a href="//example.com/report.html#outside">External</a>', encoding='utf-8')
            (root / 'methods.html').write_text('<section id="B 2"></section>', encoding='utf-8')
            failures = []
            with patch.object(checks, 'ROOT', root):
                checks.validate_local_links(page, failures)
            self.assertEqual(failures, [])


if __name__ == '__main__':
    unittest.main()
