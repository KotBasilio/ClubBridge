from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


TOOL_PATH = Path(__file__).parents[1] / "tools" / "rtf_inventory.py"
SPEC = importlib.util.spec_from_file_location("rtf_inventory", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
rtf_inventory = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = rtf_inventory
SPEC.loader.exec_module(rtf_inventory)


class RtfInventoryTest(unittest.TestCase):
    def parse(self, source: str):
        return rtf_inventory.parse_rtf_bytes(source.encode("latin1"))

    def test_font_charset_decodes_russian_and_ignores_raw_line_wraps(self):
        inventory = self.parse(
            r"""{\rtf1\ansi\ansicpg1252
{\fonttbl{\f0\fswiss\fcharset0 Arial;}{\f1\fswiss\fcharset204 Arial Cyr;}}
\pard\outlinelevel0\f1 \'cf\'f0\'e8
\'e2\'e5\'f2\par}"""
        )

        self.assertEqual(["Привет"], [heading.text for heading in inventory.headings])
        self.assertEqual("Привет", inventory.paragraphs[0].text)

    def test_unicode_suit_skips_fallback_character(self):
        inventory = self.parse(r"{\rtf1\ansi\uc1 Clubs: \u9827?\par}")

        self.assertEqual("Clubs: ♣", inventory.paragraphs[0].text)

    def test_ignored_field_instruction_keeps_visible_result(self):
        inventory = self.parse(
            r"{\rtf1\ansi Before {\field{\*\fldinst HYPERLINK hidden}{\fldrslt visible}} after\par}"
        )

        self.assertEqual("Before visible after", inventory.paragraphs[0].text)
        self.assertEqual(1, inventory.field_count)
        self.assertEqual(1, inventory.hyperlink_count)

    def test_symbol_field_without_result_is_preserved(self):
        inventory = self.parse(
            r'{\rtf1\ansi 3{\field{\*\fldinst SYMBOL 169 \\f "Symbol" \\s 10}{\fldrslt\f3\fs20}}/\u9824?\par}'
        )

        self.assertEqual("3♥/♠", inventory.paragraphs[0].text)

    def test_symbol_font_hex_byte_uses_adobe_mapping(self):
        inventory = self.parse(
            r"{\rtf1\ansi{\fonttbl{\f0\fswiss\fcharset0 Arial;}{\f3\froman\fcharset2 Symbol;}}\f3\'de\par}"
        )

        self.assertEqual("⇒", inventory.paragraphs[0].text)

    def test_wingdings_symbol_field_uses_declared_font(self):
        inventory = self.parse(
            r'{\rtf1\ansi Smile {\field{\*\fldinst SYMBOL 74 \\f "Wingdings"}{\fldrslt}}\par}'
        )

        self.assertEqual("Smile ☺", inventory.paragraphs[0].text)

    def test_wingdings_hex_byte_uses_compatibility_mapping(self):
        inventory = self.parse(
            r"{\rtf1\ansi{\fonttbl{\f0\fswiss Arial;}{\f10\fnil\fcharset2 Wingdings;}}\f10\'fc\par}"
        )

        self.assertEqual("✓", inventory.paragraphs[0].text)

    def test_wingdings_arrowhead_list_marker_is_preserved(self):
        inventory = self.parse(
            r"{\rtf1\ansi{\fonttbl{\f0\fswiss Arial;}{\f10\fnil\fcharset2 Wingdings;}}\f10\'d8\par}"
        )

        self.assertEqual("➢", inventory.paragraphs[0].text)

    def test_wingdings_square_list_marker_is_preserved(self):
        inventory = self.parse(
            r"{\rtf1\ansi{\fonttbl{\f0\fswiss Arial;}{\f10\fnil\fcharset2 Wingdings;}}\f10\'a7\par}"
        )

        self.assertEqual("▪", inventory.paragraphs[0].text)

    def test_formatting_bom_does_not_create_a_paragraph(self):
        inventory = self.parse(r"{\rtf1\ansi\u-257?\par Visible\par}")

        self.assertEqual(["Visible"], [item.text for item in inventory.paragraphs])

    def test_outline_page_region_table_and_offsets_are_recorded(self):
        inventory = self.parse(
            r"{\rtf1\ansi\pard\outlinelevel2 Heading\par\page\pard\intbl A\cell B\cell\row}"
        )

        self.assertEqual("Heading", inventory.headings[0].text)
        self.assertEqual(2, inventory.headings[0].outline_level)
        self.assertEqual(2, inventory.explicit_page_region_count)
        self.assertEqual(1, inventory.table_row_count)
        self.assertIn("A | B |", inventory.paragraphs[-1].text)
        self.assertLess(
            inventory.paragraphs[0].source_start,
            inventory.paragraphs[0].source_end,
        )

    def test_inventory_writer_uses_utf8(self):
        inventory = self.parse(r"{\rtf1\ansi\uc1 \u9824?\par}")
        inventory.source = "sample.rtf"

        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            rtf_inventory.write_inventory(inventory, output_dir)
            text = (output_dir / "sample.inspection.txt").read_text(encoding="utf-8")

        self.assertEqual("♠\n", text)


if __name__ == "__main__":
    unittest.main()
