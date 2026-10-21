from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MIGRATION_DIR = Path(__file__).parents[1]
TOOLS_DIR = MIGRATION_DIR / "tools"
REPOSITORY_ROOT = MIGRATION_DIR.parents[1]
sys.path.insert(0, str(TOOLS_DIR))
TOOL_PATH = TOOLS_DIR / "build_section_draft.py"
SPEC = importlib.util.spec_from_file_location("build_section_draft", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
section_draft = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = section_draft
SPEC.loader.exec_module(section_draft)

from rtf_inventory import DocumentInventory, Paragraph  # noqa: E402


def paragraph(
    text: str,
    *,
    outline_level: int | None = None,
    source_start: int = 0,
) -> Paragraph:
    return Paragraph(
        text=text,
        style=None,
        outline_level=outline_level,
        page_region=1,
        kind="paragraph",
        in_table=False,
        source_start=source_start,
        source_end=source_start + len(text),
    )


def inventory(paragraphs: list[Paragraph]) -> DocumentInventory:
    return DocumentInventory(
        source="fixture.rtf",
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


class BuildSectionDraftTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = section_draft.build_outputs(
            REPOSITORY_ROOT, "ns", "Форспас"
        )
        cls.manifest = json.loads(cls.outputs[Path("manifest.json")])
        cls.ns_pair = section_draft.load_pair(
            REPOSITORY_ROOT, section_draft.PAIRS["ns"]
        )
        cls.approvals = section_draft.load_approvals(REPOSITORY_ROOT)
        cls.decisions = section_draft.load_presentation_decisions(REPOSITORY_ROOT)

    def test_section_boundary_stops_at_next_peer_or_ancestor(self):
        source = inventory(
            [
                paragraph("Root", outline_level=2, source_start=10),
                paragraph("Body", source_start=20),
                paragraph("Child", outline_level=3, source_start=30),
                paragraph("Next", outline_level=2, source_start=40),
            ]
        )

        selected = section_draft.select_section(source, "Root")

        self.assertEqual(
            ["Root", "Body", "Child"],
            [item.text for item in selected.paragraphs],
        )
        self.assertEqual((10, 40), (selected.source_start, selected.source_end))

    def test_duplicate_heading_requires_explicit_occurrence_and_lists_offsets(self):
        source = inventory(
            [
                paragraph("Same", outline_level=2, source_start=10),
                paragraph("First", source_start=20),
                paragraph("Same", outline_level=2, source_start=50),
                paragraph("Second", source_start=60),
            ]
        )

        with self.assertRaisesRegex(
            ValueError, r"--heading-occurrence 1 \(byte 10\).*byte 50"
        ):
            section_draft.select_section(source, "Same")
        selected = section_draft.select_section(source, "Same", 2)
        self.assertEqual("Second", selected.paragraphs[1].text)

    def test_demo_preserves_order_symbols_and_approved_centered_diagram(self):
        draft = self.outputs[Path("draft.md")]
        before = draft.index("Форспас с ограниченной руки")
        diagram = draft.index("| ограниченная рука | ФП<br>────→")
        after = draft.index("Частый спец-случай")

        self.assertLess(before, diagram)
        self.assertLess(diagram, after)
        self.assertIn("4♣/♦", draft)
        self.assertIn("4♥/♠", draft)
        self.assertIn("| :---: | :---: | :---: |", draft)
        self.assertNotIn("system/agreements/", draft)

        table = self.manifest["outputs"][0]["tables"][0]
        self.assertEqual("rtf-table-0003", table["rtf_table"])
        self.assertEqual("approved-presentation", table["evidence_class"])
        self.assertEqual("unmatched", table["diagnostic_status"])
        self.assertEqual(
            "forcing-pass-scale-diagram", table["presentation_override"]
        )

    def test_manifest_has_hashes_range_draft_hash_and_promotion_boundary(self):
        source = self.manifest["source"]
        section = self.manifest["section"]
        output = self.manifest["outputs"][0]

        self.assertEqual(64, len(source["rtf_sha256"]))
        self.assertEqual(64, len(source["html_sha256"]))
        self.assertLess(section["source_byte_start"], section["source_byte_end"])
        self.assertEqual(
            section_draft.sha256_text(self.outputs[Path("draft.md")]),
            output["generated_sha256"],
        )
        self.assertFalse(self.manifest["promotion"]["automatic"])
        self.assertIn("human approval", self.manifest["promotion"]["requirement"])

    def test_presentation_hash_guard_abstains_to_fallback(self):
        altered = self.ns_pair | {"rtf_sha256": "0" * 64}
        record = section_draft.table_by_id(
            altered["rtf_tables"], "rtf-table-0003"
        )

        options = section_draft.table_options(
            altered, record, self.approvals, self.decisions
        )

        self.assertEqual(1, len(options))
        self.assertEqual("unresolved-fallback", options[0].model.evidence_class)
        self.assertIn("source hash does not match", options[0].unresolved_issue)

    def test_ambiguous_table_emits_each_competing_candidate(self):
        record = section_draft.table_by_id(
            self.ns_pair["rtf_tables"], "rtf-table-0039"
        )

        options = section_draft.table_options(
            self.ns_pair, record, self.approvals, self.decisions
        )

        self.assertEqual(
            ["html-table-0042", "html-table-0047"],
            [option.model.html_table for option in options],
        )
        self.assertTrue(
            all(option.model.evidence_class == "competing-variant" for option in options)
        )
        self.assertTrue(all(option.unresolved_issue for option in options))

    def test_pipe_escaping_is_shared_with_geometry_renderer(self):
        self.assertEqual(
            "A\\|B &amp; ♠",
            section_draft.escape_text("A|B & ♠", gfm=True),
        )

    def test_reconversion_replaces_only_staged_draft(self):
        approved = REPOSITORY_ROOT / "system" / "agreements" / "vist.md"
        approved_before = approved.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "draft"
            section_draft.write_outputs(output_dir, self.outputs)
            (output_dir / "draft.md").write_text("review edits\n", encoding="utf-8")
            section_draft.write_outputs(output_dir, self.outputs)
            self.assertEqual(
                self.outputs[Path("draft.md")],
                (output_dir / "draft.md").read_text(encoding="utf-8"),
            )
        self.assertEqual(approved_before, approved.read_bytes())

    def test_output_guard_refuses_approved_tree(self):
        with self.assertRaises(ValueError):
            section_draft.validate_output_dir(
                REPOSITORY_ROOT,
                REPOSITORY_ROOT / "system" / "agreements" / "reconversion",
            )


if __name__ == "__main__":
    unittest.main()
