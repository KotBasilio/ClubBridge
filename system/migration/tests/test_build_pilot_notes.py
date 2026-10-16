from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "build_pilot_notes.py"
SPEC = importlib.util.spec_from_file_location("build_pilot_notes", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
build_pilot_notes = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build_pilot_notes
SPEC.loader.exec_module(build_pilot_notes)

from rtf_inventory import DocumentInventory, Paragraph  # noqa: E402


def paragraph(
    text: str,
    *,
    outline_level: int | None = None,
    in_table: bool = False,
    source_start: int = 0,
) -> Paragraph:
    return Paragraph(
        text=text,
        style=None,
        outline_level=outline_level,
        page_region=1,
        kind="paragraph",
        in_table=in_table,
        source_start=source_start,
        source_end=source_start + len(text),
    )


def inventory(paragraphs: list[Paragraph]) -> DocumentInventory:
    return DocumentInventory(
        source="source.rtf",
        byte_count=1_000,
        sha256="a" * 64,
        document_codepage="cp1251",
        explicit_page_region_count=1,
        paragraph_count=len(paragraphs),
        table_row_count=0,
        field_count=0,
        list_marker_count=0,
        bookmark_count=0,
        hyperlink_count=0,
        toc_hyperlink_count=0,
        embedded_picture_count=0,
        embedded_object_count=0,
        headings=[item for item in paragraphs if item.outline_level is not None],
        paragraphs=paragraphs,
    )


class BuildPilotNotesTest(unittest.TestCase):
    def test_section_stops_at_next_peer_and_ignores_plain_text_match(self):
        source = inventory(
            [
                paragraph("Target"),
                paragraph("Target", outline_level=2, source_start=10),
                paragraph("Body", source_start=20),
                paragraph("Child", outline_level=3, source_start=30),
                paragraph("Next", outline_level=2, source_start=40),
            ]
        )

        selected, end = build_pilot_notes.select_section(source, "Target")

        self.assertEqual(["Target", "Body", "Child"], [item.text for item in selected])
        self.assertEqual(4, end)

    def test_render_marks_tables_and_source_navigation_without_inventing_shape(self):
        source = inventory(
            [
                paragraph("Root", outline_level=0, source_start=10),
                paragraph("Child", outline_level=2, source_start=20),
                paragraph("A | B |", in_table=True, source_start=30),
                paragraph("TOC", source_start=40),
            ]
        )
        spec = build_pilot_notes.PilotSpec(
            title="Root",
            source="source.rtf",
            source_heading="Root",
            output="root.md",
        )

        rendered = build_pilot_notes.render_note(spec, source, source.paragraphs, 50)

        self.assertIn("## Child", rendered)
        self.assertIn("```text\nA | B |\n```", rendered)
        self.assertIn("<!-- Source navigation marker: TOC -->", rendered)


if __name__ == "__main__":
    unittest.main()
