from __future__ import annotations

import codecs
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MIGRATION_DIR = Path(__file__).parents[1]
TOOLS_DIR = MIGRATION_DIR / "tools"
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "html"
REPOSITORY_ROOT = MIGRATION_DIR.parents[1]
sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "html_table_probe.py"
SPEC = importlib.util.spec_from_file_location("html_table_probe", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
html_table_probe = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = html_table_probe
SPEC.loader.exec_module(html_table_probe)


def parse_fixture(name: str):
    parser = html_table_probe.TableProbe()
    parser.feed((FIXTURES_DIR / name).read_text(encoding="utf-8"))
    parser.finish()
    return parser


class HtmlTableProbeTest(unittest.TestCase):
    def test_basic_table_preserves_text_breaks_and_strips_word_baggage(self):
        parser = parse_fixture("basic.html")

        self.assertEqual(1, len(parser.tables))
        table = parser.tables[0]
        self.assertEqual("Basic table", table["heading"])
        self.assertEqual("natural\nforcing", table["rows"][1][1]["text"])
        self.assertEqual(0, table["word_merge_hints"])

        fragment = html_table_probe.witness(table)
        self.assertIn("<td>natural<br>forcing</td>", fragment)
        self.assertIn("1♣", fragment)
        self.assertNotIn("class=", fragment)
        self.assertNotIn("style=", fragment)
        self.assertNotIn("mso-", fragment)

    def test_merged_table_expands_to_a_rectangular_logical_grid(self):
        report = html_table_probe.examine(FIXTURES_DIR / "merged.html", None, 0)
        table = report["tables"][0]

        self.assertEqual(3, table["logical_columns"])
        self.assertEqual([3, 3], table["row_coverage"])
        self.assertEqual(2, table["merged_cells"])
        self.assertEqual(1, table["rowspan_cells"])
        self.assertEqual(1, table["colspan_cells"])
        self.assertEqual([], table["geometry_issues"])

    def test_malformed_table_reports_invalid_span_and_implicit_row(self):
        report = html_table_probe.examine(FIXTURES_DIR / "malformed.html", None, 0)
        table = report["tables"][0]

        self.assertEqual([{"rowspan": "0"}], table["invalid_spans"])
        self.assertTrue(table["malformed_structure"])
        self.assertEqual(1, report["tables_with_invalid_spans"])
        self.assertEqual(1, report["tables_with_malformed_structure"])

    def test_nested_table_is_separate_and_not_flattened_into_parent(self):
        parser = parse_fixture("nested.html")

        self.assertEqual(2, len(parser.tables))
        parent, child = parser.tables
        self.assertTrue(parent["nested"])
        self.assertEqual(1, parent["nested_table_count"])
        self.assertEqual(1, child["parent_table"])
        self.assertEqual(2, child["depth"])
        self.assertEqual("before after", parent["rows"][0][0]["text"])
        self.assertEqual("inner", child["rows"][0][0]["text"])

        fragment = html_table_probe.witness(parent)
        self.assertIn("<!-- nested table omitted: 1 -->", fragment)
        self.assertNotIn(">inner<", fragment)

    def test_windows_1251_and_bridge_suit_entity_are_decoded(self):
        document = (
            '<meta charset="windows-1251"><h2>Тест</h2>'
            '<table><tr><td>Трефа &#9827;</td></tr></table>'
        ).encode("windows-1251")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "cp1251.html"
            path.write_bytes(document)
            report = html_table_probe.examine(path, None, 0)

        self.assertEqual("windows-1251", report["encoding"])
        self.assertEqual("meta", report["encoding_source"])
        self.assertEqual(1, report["table_suit_symbol_counts"]["♣"])
        self.assertEqual(0, report["table_replacement_character_count"])
        self.assertIn("Трефа ♣", report["tables"][0]["sample"])

    def test_utf8_bom_takes_precedence_over_a_conflicting_meta_declaration(self):
        document = codecs.BOM_UTF8 + (
            '<meta charset="windows-1251">'
            '<table><tr><td>Бубна ♦</td></tr></table>'
        ).encode("utf-8")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bom.html"
            path.write_bytes(document)
            report = html_table_probe.examine(path, None, 0)

        self.assertEqual("utf-8-sig", report["encoding"])
        self.assertEqual("bom", report["encoding_source"])
        self.assertIn("Бубна ♦", report["tables"][0]["sample"])

    def test_real_word_target_table_has_expected_merged_geometry(self):
        path = REPOSITORY_ROOT / "system" / "legacy" / "ns25_09.htm"
        report = html_table_probe.examine(path, None, 0)
        table = next(
            table
            for table in report["tables"]
            if table["sample"].startswith("1♣-1♦-2♠-??")
        )

        self.assertEqual(11, table["rows"])
        self.assertEqual(23, table["cells"])
        self.assertEqual(6, table["logical_columns"])
        self.assertEqual(13, table["merged_cells"])
        self.assertEqual([6] * 11, table["row_coverage"])
        self.assertEqual([], table["geometry_issues"])


if __name__ == "__main__":
    unittest.main()
