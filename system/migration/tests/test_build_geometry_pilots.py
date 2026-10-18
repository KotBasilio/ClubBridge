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
TOOL_PATH = TOOLS_DIR / "build_geometry_pilots.py"
SPEC = importlib.util.spec_from_file_location("build_geometry_pilots", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
geometry_pilots = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = geometry_pilots
SPEC.loader.exec_module(geometry_pilots)


class BuildGeometryPilotsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.outputs = geometry_pilots.build_outputs(REPOSITORY_ROOT)
        cls.manifest = json.loads(cls.outputs[Path("manifest.json")])

    def test_manifest_covers_each_evidence_class_and_expected_variants(self):
        self.assertEqual(
            {
                "strict": 2,
                "human-reviewed": 1,
                "competing-variant": 4,
                "unresolved-fallback": 1,
            },
            self.manifest["summary"],
        )
        mappings = {
            output["output"]: [
                (table["rtf_table"], table["html_table"])
                for table in output["tables"]
            ]
            for output in self.manifest["outputs"]
        }
        self.assertEqual(
            [
                ("rtf-table-0039", "html-table-0042"),
                ("rtf-table-0044", "html-table-0047"),
            ],
            mappings["competing-gazilli-mapping-a.md"],
        )
        self.assertEqual(
            [
                ("rtf-table-0039", "html-table-0047"),
                ("rtf-table-0044", "html-table-0042"),
            ],
            mappings["competing-gazilli-mapping-b.md"],
        )

    def test_unmerged_table_uses_gfm_with_a_real_header(self):
        text = self.outputs[Path("strict-unmerged.md")]

        self.assertIn("| секвенция | заявки | коммент |", text)
        self.assertIn("| --- | --- | --- |", text)
        self.assertNotIn("<table>", text)
        self.assertIn("1♠ пас 2♦ ктр", text)

    def test_merged_table_uses_minimal_html_and_preserves_suits(self):
        text = self.outputs[Path("strict-merged.md")]

        self.assertIn('<td rowspan="11">1♣-1♦-2♠-??</td>', text)
        self.assertIn('<td colspan="5">', text)
        self.assertIn("3♥/♠", text)
        self.assertIn("with ♦", text)
        self.assertNotIn("class=", text)
        self.assertNotIn("style=", text)
        self.assertNotIn("mso-", text.lower())
        self.assertNotIn("<script", text.lower())

    def test_human_reviewed_geometry_retains_divergent_status_and_approval(self):
        text = self.outputs[Path("human-reviewed-gazilli.md")]
        table = next(
            output["tables"][0]
            for output in self.manifest["outputs"]
            if output["output"] == "human-reviewed-gazilli.md"
        )

        self.assertEqual("human-reviewed", table["evidence_class"])
        self.assertEqual("divergent", table["diagnostic_status"])
        self.assertIn("visual-review/review.md#case-2--articles-gazilli", text)
        self.assertIn("Односторонний ФГ", text)

    def test_unmatched_table_abstains_from_geometry(self):
        text = self.outputs[Path("unmatched-fallback.md")]

        self.assertIn("HTML geometry: deliberately absent", text)
        self.assertIn("ФП<br>────→", text)
        self.assertNotIn("<table>", text)

    def test_text_escaping_preserves_breaks_suits_and_gfm_pipe_safety(self):
        value = "<unsafe>& ♣<br>A|B"

        self.assertEqual(
            "&lt;unsafe&gt;&amp; ♣<br>A\\|B",
            geometry_pilots.escape_text(value, gfm=True),
        )
        self.assertEqual(
            "&lt;unsafe&gt;&amp; ♣<br>A|B",
            geometry_pilots.escape_text(value),
        )

    def test_generation_is_deterministic_and_check_detects_changes(self):
        self.assertEqual(self.outputs, geometry_pilots.build_outputs(REPOSITORY_ROOT))
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory) / "pilots"
            geometry_pilots.write_outputs(output_dir, self.outputs)
            self.assertEqual([], geometry_pilots.check_outputs(output_dir, self.outputs))
            (output_dir / "strict-unmerged.md").write_text(
                "changed\n", encoding="utf-8"
            )
            self.assertEqual(
                [output_dir / "strict-unmerged.md"],
                geometry_pilots.check_outputs(output_dir, self.outputs),
            )

    def test_output_guard_refuses_legacy_agreements_and_repository_root(self):
        for path in (
            REPOSITORY_ROOT,
            REPOSITORY_ROOT / "system" / "legacy" / "generated",
            REPOSITORY_ROOT / "system" / "agreements" / "generated",
        ):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    geometry_pilots.validate_output_dir(REPOSITORY_ROOT, path)

    def test_human_approval_is_bound_to_current_source_hashes(self):
        pair = geometry_pilots.load_pair(
            REPOSITORY_ROOT, geometry_pilots.PAIRS["Articles"]
        )
        approvals = geometry_pilots.load_approvals(REPOSITORY_ROOT)
        altered = pair | {"rtf_sha256": "0" * 64}

        with self.assertRaises(ValueError):
            geometry_pilots.find_approval(
                approvals,
                altered,
                "rtf-table-0019",
                "html-table-0020",
            )


if __name__ == "__main__":
    unittest.main()
