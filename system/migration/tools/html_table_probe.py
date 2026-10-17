#!/usr/bin/env python3
"""Read-only inventory of Word-exported HTML tables; no agreement generation.

Uses Python's standard library. Reports source table geometry and extracts
minimal HTML witnesses for human comparison with the RTF originals.
"""
from __future__ import annotations

import argparse
import codecs
import hashlib
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

SOURCES = ("Articles_25_09.htm", "ns25_09.htm")
BLOCKED = {"style", "script", "head", "xml"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
CELL_BREAK_TAGS = {"div", "li", "p"}
CELL_BREAK = "\0"
SUITS = ("♣", "♦", "♥", "♠")
WORD_MERGE_HINT = re.compile(
    r"\b(?:vmerge|hmerge|mso-(?:vmerge|hmerge|merge|rowspan|colspan))\b",
    re.IGNORECASE,
)


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def clean_cell_text(value: str) -> str:
    return "\n".join(
        cleaned for part in value.split(CELL_BREAK) if (cleaned := compact(part))
    )


def cell_html(cell: dict) -> str:
    attrs = "".join(
        f' {key}="{cell[key]}"'
        for key in ("rowspan", "colspan")
        if cell[key] > 1
    )
    text = "<br>".join(html.escape(line) for line in cell["text"].splitlines())
    if cell["nested_tables"]:
        suffix = f'<!-- nested table omitted: {cell["nested_tables"]} -->'
        text = f"{text}{suffix}" if text else suffix
    return f'<{cell["tag"]}{attrs}>{text}</{cell["tag"]}>'


def witness(table: dict) -> str:
    rows = [
        "  <tr>" + "".join(cell_html(cell) for cell in row) + "</tr>"
        for row in table["rows"]
    ]
    return "<table>\n" + "\n".join(rows) + "\n</table>\n"


def table_geometry(table: dict) -> dict:
    occupied: dict[tuple[int, int], int] = {}
    issues: list[str] = []

    for row_index, row in enumerate(table["rows"]):
        column = 0
        for cell_index, cell in enumerate(row):
            width = cell["colspan"]
            while any(
                (row_index, candidate) in occupied
                for candidate in range(column, column + width)
            ):
                column += 1
            if row_index + cell["rowspan"] > len(table["rows"]):
                issues.append(
                    f"row {row_index + 1} cell {cell_index + 1}: rowspan "
                    f"{cell['rowspan']} extends beyond the final row"
                )
            for covered_row in range(row_index, row_index + cell["rowspan"]):
                for covered_column in range(column, column + width):
                    occupied[(covered_row, covered_column)] = cell_index
            column += width

    logical_columns = max((column for _, column in occupied), default=-1) + 1
    row_coverage = []
    for row_index in range(len(table["rows"])):
        covered = sum(
            (row_index, column) in occupied for column in range(logical_columns)
        )
        row_coverage.append(covered)
        if covered != logical_columns:
            missing = [
                column + 1
                for column in range(logical_columns)
                if (row_index, column) not in occupied
            ]
            issues.append(
                f"row {row_index + 1}: uncovered logical columns {missing}"
            )

    return {
        "logical_columns": logical_columns,
        "row_coverage": row_coverage,
        "geometry_issues": issues,
    }


class TableProbe(HTMLParser):
    """Extract tables without allowing nested-table state to bleed outward."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: list[dict] = []
        self.stack: list[dict] = []
        self.skip: list[str] = []
        self.heading: str | None = None
        self.heading_text: list[str] = []
        self.last_heading = ""

    def _append_cell_text(self, value: str) -> None:
        if self.stack and self.stack[-1]["cell"] is not None:
            self.stack[-1]["cell"]["text"] += value

    def _finish_cell(self) -> None:
        table = self.stack[-1]
        cell = table["cell"]
        if cell is None:
            return
        cell["text"] = clean_cell_text(cell["text"])
        table["rows"][table["current_row"]].append(cell)
        table["cell"] = None

    def _span(self, attrs: dict[str, str | None], key: str) -> int:
        if key not in attrs:
            return 1
        value = attrs[key]
        if value is None or not re.fullmatch(r"[1-9][0-9]*", value.strip()):
            self.stack[-1]["invalid_spans"].append({key: value})
            return 1
        return int(value)

    def handle_starttag(self, tag, attrs):
        if self.skip:
            return
        if tag in BLOCKED:
            self.skip.append(tag)
            return

        attrs_dict = dict(attrs)
        if tag in HEADINGS and not self.stack:
            self.heading = tag
            self.heading_text = []

        if tag == "table":
            parent = self.stack[-1] if self.stack else None
            index = len(self.tables) + 1
            table = {
                "index": index,
                "heading": self.last_heading,
                "rows": [],
                "nested": False,
                "nested_table_count": 0,
                "depth": len(self.stack) + 1,
                "parent_table": parent["index"] if parent else None,
                "word_merge_hints": 0,
                "invalid_spans": [],
                "malformed_structure": [],
                "current_row": None,
                "row_open": False,
                "cell": None,
            }
            if parent is not None:
                parent["nested"] = True
                parent["nested_table_count"] += 1
                if parent["cell"] is None:
                    parent["malformed_structure"].append(
                        "nested table occurs outside a parent cell"
                    )
                else:
                    parent["cell"]["nested_tables"] += 1
                    parent["cell"]["text"] += " "
            self.tables.append(table)
            self.stack.append(table)
            return

        if not self.stack:
            return
        table = self.stack[-1]

        if tag == "tr":
            if table["row_open"]:
                table["malformed_structure"].append(
                    "new row started before the previous row ended"
                )
                if table["cell"] is not None:
                    self._finish_cell()
            table["rows"].append([])
            table["current_row"] = len(table["rows"]) - 1
            table["row_open"] = True
        elif tag in ("td", "th"):
            if table["cell"] is not None:
                table["malformed_structure"].append(
                    "new cell started before the previous cell ended"
                )
                self._finish_cell()
            if table["current_row"] is None or not table["row_open"]:
                table["rows"].append([])
                table["current_row"] = len(table["rows"]) - 1
                table["row_open"] = True
                table["malformed_structure"].append(
                    "cell occurred outside a row; an implicit row was created"
                )
            attrs_text = " ".join(
                f"{key}={value or ''}" for key, value in attrs_dict.items()
            )
            style_hints = bool(WORD_MERGE_HINT.search(attrs_text))
            table["cell"] = {
                "tag": tag,
                "rowspan": self._span(attrs_dict, "rowspan"),
                "colspan": self._span(attrs_dict, "colspan"),
                "text": "",
                "word_merge_hints": style_hints,
                "nested_tables": 0,
            }
            if style_hints:
                table["word_merge_hints"] += 1
        elif tag == "br":
            self._append_cell_text(CELL_BREAK)

    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip[-1]:
                self.skip.pop()
            return

        if tag in HEADINGS and self.heading == tag:
            self.last_heading = compact("".join(self.heading_text))[:200]
            self.heading = None
            return
        if not self.stack:
            return

        table = self.stack[-1]
        if tag in ("td", "th"):
            if table["cell"] is None:
                table["malformed_structure"].append(
                    f"closing {tag} occurred without an open cell"
                )
            else:
                self._finish_cell()
        elif tag == "tr":
            if table["cell"] is not None:
                table["malformed_structure"].append(
                    "row ended before its current cell ended"
                )
                self._finish_cell()
            table["row_open"] = False
        elif tag == "table":
            if table["cell"] is not None:
                table["malformed_structure"].append(
                    "table ended before its current cell ended"
                )
                self._finish_cell()
            if table["row_open"]:
                table["malformed_structure"].append(
                    "table ended before its current row ended"
                )
                table["row_open"] = False
            self.stack.pop()
        elif tag in CELL_BREAK_TAGS and table["cell"] is not None:
            self._append_cell_text(CELL_BREAK)

    def handle_data(self, data):
        if self.skip:
            return
        if self.heading is not None:
            self.heading_text.append(data)
        self._append_cell_text(data)

    def finish(self) -> None:
        self.close()
        while self.stack:
            table = self.stack[-1]
            table["malformed_structure"].append("table was not closed before EOF")
            if table["cell"] is not None:
                self._finish_cell()
            table["row_open"] = False
            self.stack.pop()


def detect_encoding(source: bytes, path: Path) -> tuple[str, str]:
    if source.startswith(codecs.BOM_UTF8):
        return "utf-8-sig", "bom"
    declaration = source[:8192].decode("ascii", errors="ignore")
    match = re.search(
        r'charset\s*=\s*["\x27]?\s*([A-Za-z0-9._-]+)', declaration, re.I
    )
    encoding = match.group(1) if match else "utf-8"
    try:
        codecs.lookup(encoding)
    except LookupError as ex:
        raise ValueError(f"{path}: unknown declared encoding {encoding!r}") from ex
    return encoding, "meta" if match else "default-utf8"


def examine(path: Path, sample_dir: Path | None, sample_limit: int) -> dict:
    source = path.read_bytes()
    encoding, encoding_source = detect_encoding(source, path)
    try:
        text = source.decode(encoding)
    except UnicodeDecodeError as ex:
        raise ValueError(f"{path}: cannot decode using {encoding}: {ex}") from ex

    parser = TableProbe()
    parser.feed(text)
    parser.finish()
    results = []
    all_table_text = []
    for table in parser.tables:
        cells = [cell for row in table["rows"] for cell in row]
        all_table_text.extend(cell["text"] for cell in cells)
        merged_cells = sum(
            cell["rowspan"] > 1 or cell["colspan"] > 1 for cell in cells
        )
        rowspans = sum(cell["rowspan"] > 1 for cell in cells)
        colspans = sum(cell["colspan"] > 1 for cell in cells)
        geometry = table_geometry(table)
        info = {
            "index": table["index"],
            "heading": table["heading"],
            "rows": len(table["rows"]),
            "cells": len(cells),
            "logical_columns": geometry["logical_columns"],
            "row_coverage": geometry["row_coverage"],
            "merged_cells": merged_cells,
            "rowspan_cells": rowspans,
            "colspan_cells": colspans,
            "nested": table["nested"],
            "nested_table_count": table["nested_table_count"],
            "depth": table["depth"],
            "parent_table": table["parent_table"],
            "word_merge_hints": table["word_merge_hints"],
            "invalid_spans": table["invalid_spans"],
            "malformed_structure": table["malformed_structure"],
            "geometry_issues": geometry["geometry_issues"],
            "sample": " / ".join(compact(cell["text"])[:60] for cell in cells[:4]),
        }
        results.append(info)
        if sample_dir and table["index"] <= sample_limit:
            (sample_dir / f"{path.stem}-table-{table['index']:04}.html").write_text(
                witness(table), encoding="utf-8"
            )

    table_text = "\n".join(all_table_text)
    return {
        "source": str(path),
        "sha256": hashlib.sha256(source).hexdigest(),
        "encoding": encoding,
        "encoding_source": encoding_source,
        "total_tables": len(results),
        "top_level_tables": sum(table["depth"] == 1 for table in results),
        "tables_with_merges": sum(table["merged_cells"] > 0 for table in results),
        "tables_with_rowspans": sum(table["rowspan_cells"] > 0 for table in results),
        "tables_with_colspans": sum(table["colspan_cells"] > 0 for table in results),
        "tables_with_word_merge_hints": sum(
            table["word_merge_hints"] > 0 for table in results
        ),
        "nested_tables": sum(table["depth"] > 1 for table in results),
        "tables_with_invalid_spans": sum(
            bool(table["invalid_spans"]) for table in results
        ),
        "tables_with_malformed_structure": sum(
            bool(table["malformed_structure"]) for table in results
        ),
        "tables_with_geometry_issues": sum(
            bool(table["geometry_issues"]) for table in results
        ),
        "table_suit_symbol_counts": {suit: table_text.count(suit) for suit in SUITS},
        "table_replacement_character_count": table_text.count("\ufffd"),
        "tables": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="*", type=Path)
    parser.add_argument("--output", type=Path, help="optional JSON report")
    parser.add_argument(
        "--samples-dir", type=Path, help="optional directory for minimal HTML witnesses"
    )
    parser.add_argument("--sample-limit", type=int, default=10)
    args = parser.parse_args()
    if args.sample_limit < 0:
        parser.error("--sample-limit must be nonnegative")
    sources = args.sources or [Path("system/legacy") / name for name in SOURCES]
    if args.samples_dir:
        args.samples_dir.mkdir(parents=True, exist_ok=True)
    report = [examine(path, args.samples_dir, args.sample_limit) for path in sources]
    result = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
