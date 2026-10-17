from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MIGRATION_DIR = Path(__file__).parents[1]
TOOLS_DIR = MIGRATION_DIR / "tools"
REPOSITORY_ROOT = MIGRATION_DIR.parents[1]
sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "match_rtf_html_tables.py"
SPEC = importlib.util.spec_from_file_location("match_rtf_html_tables", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
matcher = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = matcher
SPEC.loader.exec_module(matcher)


def record(kind: str, index: int, rows, *, supported: bool = True):
    normalized = tuple(
        tuple(matcher.normalize_cell_text(cell) for cell in row) for row in rows
    )
    return matcher.TableRecord(
        id=f"{kind}-table-{index:04d}",
        index=index,
        rows=normalized,
        structured_fingerprint=matcher.fingerprint(normalized),
        ordered_content_fingerprint=matcher.fingerprint(
            matcher.ordered_content(normalized)
        ),
        supported=supported,
        support_issues=() if supported else ("synthetic unsupported table",),
        context={},
    )


def parse_html(source: str):
    parser = matcher.TableProbe()
    parser.feed(source)
    parser.finish()
    return matcher.extract_html_tables(parser)


class RtfHtmlTableMatcherTest(unittest.TestCase):
    def test_exact_match_normalizes_whitespace_breaks_entities_and_suits(self):
        rtf = record(
            "rtf",
            1,
            ((" 1♣ <br> forcing ", "2♦\n natural"),),
        )
        html = parse_html(
            "<table><tr><td><p>1&clubs;</p><p>forcing</p></td>"
            "<td>2&#9830; &nbsp; natural</td></tr></table>"
        )[0]

        result = matcher.match_tables([rtf], [html])[0]

        self.assertEqual("matched", result["status"])
        self.assertEqual(["html-table-0001"], result["html_candidates"])

    def test_duplicate_text_is_ambiguous_on_both_sides(self):
        rtfs = [record("rtf", index, (("same",),)) for index in (1, 2)]
        html = [record("html", index, (("same",),)) for index in (1, 2)]

        results = matcher.match_tables(rtfs, html)

        self.assertEqual(["ambiguous", "ambiguous"], [r["status"] for r in results])
        self.assertEqual(
            ["html-table-0001", "html-table-0002"],
            results[0]["html_candidates"],
        )

    def test_swapped_cell_content_is_not_a_match(self):
        rtf = record("rtf", 1, (("alpha", "beta"),))
        html = record("html", 1, (("beta", "alpha"),))

        result = matcher.match_tables([rtf], [html])[0]

        self.assertEqual("unmatched", result["status"])
        self.assertEqual([], result["html_candidates"])

    def test_missing_html_table_is_unmatched(self):
        result = matcher.match_tables([record("rtf", 1, (("only",),))], [])[0]

        self.assertEqual("unmatched", result["status"])

    def test_repeated_heading_does_not_create_or_prevent_content_matches(self):
        html = parse_html(
            "<h2>Repeated</h2><table><tr><td>alpha</td></tr></table>"
            "<h2>Repeated</h2><table><tr><td>beta</td></tr></table>"
        )
        rtfs = [
            record("rtf", 1, (("alpha",),)),
            record("rtf", 2, (("beta",),)),
        ]

        results = matcher.match_tables(rtfs, html)

        self.assertEqual(["matched", "matched"], [r["status"] for r in results])

    def test_same_ordered_content_with_different_row_boundaries_is_divergent(self):
        rtf = record("rtf", 1, (("alpha", "beta"),))
        html = record("html", 1, (("alpha",), ("beta",)))

        result = matcher.match_tables([rtf], [html])[0]

        self.assertEqual("divergent", result["status"])
        self.assertIn("structure differs", result["evidence"])

    def test_unsupported_html_is_never_promoted(self):
        rtf = record("rtf", 1, (("same",),))
        html = record("html", 1, (("same",),), supported=False)

        result = matcher.match_tables([rtf], [html])[0]

        self.assertEqual("unsupported", result["status"])

    def test_rowspan_placeholders_and_colspan_cells_mirror_rtf_flattening(self):
        html = parse_html(
            "<table>"
            '<tr><td rowspan="2">A</td><td colspan="2">B</td></tr>'
            "<tr><td>C</td><td>D</td></tr>"
            "</table>"
        )[0]

        self.assertEqual((("A", "B"), ("", "C", "D")), html.rows)

    def test_real_ns_table_13_is_uniquely_matched_with_expected_geometry(self):
        legacy = REPOSITORY_ROOT / "system" / "legacy"
        report = matcher.diagnose_pair(
            "ns", legacy / "ns25_09.rtf", legacy / "ns25_09.htm"
        )
        match = next(
            item for item in report["matches"] if item["html_candidates"] == ["html-table-0013"]
        )
        table = next(
            item for item in report["html_tables"] if item["id"] == "html-table-0013"
        )

        self.assertEqual("matched", match["status"])
        self.assertEqual("rtf-table-0013", match["rtf_table"])
        self.assertEqual(11, table["context"]["rows"])
        self.assertEqual(23, table["context"]["physical_cells"])
        self.assertEqual(6, table["context"]["logical_columns"])
        self.assertEqual(13, table["context"]["merges"])


if __name__ == "__main__":
    unittest.main()
