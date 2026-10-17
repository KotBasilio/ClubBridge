from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace


MIGRATION_DIR = Path(__file__).parents[1]
TOOLS_DIR = MIGRATION_DIR / "tools"
REPOSITORY_ROOT = MIGRATION_DIR.parents[1]
sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "build_table_visual_review.py"
SPEC = importlib.util.spec_from_file_location("build_table_visual_review", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
visual_review = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = visual_review
SPEC.loader.exec_module(visual_review)


class LinkCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attributes = dict(attrs)
            if "href" in attributes:
                self.links.append(attributes["href"])


class BuildTableVisualReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temporary.name) / "pack"
        cls.legacy = REPOSITORY_ROOT / "system" / "legacy"
        visual_review.build(cls.legacy, cls.output)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_pack_contains_index_readme_and_three_static_case_pages(self):
        expected = {
            "README.md",
            "index.html",
            "case-1-ns-convention-card.html",
            "case-2-articles-gazilli.html",
            "case-3-ns-duplicate-collision.html",
        }
        self.assertEqual(expected, {path.name for path in self.output.iterdir()})

        for path in self.output.glob("*.html"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("<script", text.lower())
            self.assertNotIn("http://", text.lower())
            self.assertNotIn("https://", text.lower())
            self.assertNotIn("mso-", text.lower())

    def test_index_local_links_resolve_and_html_parses(self):
        parser = LinkCollector()
        parser.feed((self.output / "index.html").read_text(encoding="utf-8"))
        parser.close()

        for target in parser.links:
            self.assertTrue((self.output / target).exists(), target)

    def test_generated_text_preserves_suits_and_escapes_source_content(self):
        case = (self.output / "case-2-articles-gazilli.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("1♥ 1БК 2♣ ??", case)
        self.assertIn("1♠ 1БК 2♣ ??", case)

        record = SimpleNamespace(rows=(("<unsafe&text>",),))
        fragment = visual_review.render_rtf(record)
        self.assertIn("&lt;unsafe&amp;text&gt;", fragment)
        self.assertNotIn("<unsafe&text>", fragment)

    def test_divergent_pages_label_sources_and_include_both_prompts(self):
        for name in (
            "case-1-ns-convention-card.html",
            "case-2-articles-gazilli.html",
        ):
            text = (self.output / name).read_text(encoding="utf-8")
            self.assertIn("RTF-derived flattened interpretation", text)
            self.assertIn("HTML-exported geometry", text)
            self.assertIn("Equivalent geometry", text)
            self.assertIn("Different geometry", text)
            self.assertIn("Same bidding meaning", text)
            self.assertIn("Different meaning", text)

    def test_collision_shows_all_tables_and_both_possible_pairings(self):
        text = (self.output / "case-3-ns-duplicate-collision.html").read_text(
            encoding="utf-8"
        )
        for identifier in (
            "rtf-table-0039",
            "rtf-table-0044",
            "html-table-0042",
            "html-table-0047",
        ):
            self.assertIn(identifier, text)
        self.assertIn("Mapping A", text)
        self.assertIn("Mapping B", text)
        self.assertIn("Evidence insufficient", text)

    def test_generation_is_byte_deterministic(self):
        second = Path(self.temporary.name) / "second"
        visual_review.build(self.legacy, second)

        first_files = sorted(path.name for path in self.output.iterdir())
        second_files = sorted(path.name for path in second.iterdir())
        self.assertEqual(first_files, second_files)
        for name in first_files:
            self.assertEqual((self.output / name).read_bytes(), (second / name).read_bytes())


if __name__ == "__main__":
    unittest.main()
