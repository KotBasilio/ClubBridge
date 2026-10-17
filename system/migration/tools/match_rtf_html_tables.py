#!/usr/bin/env python3
"""Diagnose evidence-supported correspondences between RTF and HTML tables.

The RTF remains authoritative for wording and provenance.  This tool only
identifies HTML tables whose geometry may be considered later; it does not
modify sources or generate agreements.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from html_table_probe import TableProbe, detect_encoding, table_geometry
from rtf_inventory import DocumentInventory, parse_rtf


SOURCE_PAIRS = (
    ("Articles", "Articles_25_09.rtf", "Articles_25_09.htm"),
    ("ns", "ns25_09.rtf", "ns25_09.htm"),
)
BREAK = re.compile(r"(?i)<br\s*/?>")


@dataclass(frozen=True)
class TableRecord:
    id: str
    index: int
    rows: tuple[tuple[str, ...], ...]
    structured_fingerprint: str
    ordered_content_fingerprint: str
    supported: bool
    support_issues: tuple[str, ...]
    context: dict[str, object]


def normalize_cell_text(value: str) -> str:
    """Normalize only representation noise, not punctuation or bridge meaning."""

    value = unicodedata.normalize("NFC", value).replace("\xa0", " ")
    value = BREAK.sub(" ", value)
    return " ".join(value.split())


def fingerprint(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def ordered_content(rows: Iterable[Iterable[str]]) -> tuple[str, ...]:
    """Retain cell order while omitting structural empty continuation cells."""

    return tuple(cell for row in rows for cell in row if cell)


def split_rtf_row(text: str) -> tuple[str, ...]:
    """Split delimiters emitted by rtf_inventory while retaining leading blanks."""

    cells = text.split("|")
    if cells and not cells[-1].strip():
        cells.pop()
    return tuple(normalize_cell_text(cell) for cell in cells)


def _nearest_heading(inventory: DocumentInventory, source_start: int) -> str:
    preceding = [
        heading for heading in inventory.headings if heading.source_start <= source_start
    ]
    return preceding[-1].text if preceding else ""


def extract_rtf_tables(inventory: DocumentInventory) -> list[TableRecord]:
    """Group consecutive inventory table rows into source table regions."""

    groups: list[list] = []
    current: list = []
    for paragraph in inventory.paragraphs:
        if paragraph.kind == "table-row":
            current.append(paragraph)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)

    records = []
    for index, group in enumerate(groups, 1):
        rows = tuple(split_rtf_row(paragraph.text) for paragraph in group)
        issues = []
        if not rows or any(not row for row in rows):
            issues.append("RTF table region contains an empty row structure")
        records.append(
            TableRecord(
                id=f"rtf-table-{index:04d}",
                index=index,
                rows=rows,
                structured_fingerprint=fingerprint(rows),
                ordered_content_fingerprint=fingerprint(ordered_content(rows)),
                supported=not issues,
                support_issues=tuple(issues),
                context={
                    "source_start": group[0].source_start,
                    "source_end": group[-1].source_end,
                    "page_region": group[0].page_region,
                    "nearest_heading": _nearest_heading(
                        inventory, group[0].source_start
                    ),
                    "rows": len(rows),
                    "normalized_cells": sum(len(row) for row in rows),
                    "sample": " / ".join(
                        cell for row in rows for cell in row if cell
                    )[:240],
                },
            )
        )
    return records


def html_structural_rows(table: dict) -> tuple[tuple[str, ...], ...]:
    """Represent each physical cell once and each active rowspan as one blank.

    Word's RTF emits an empty cell token where a vertical merge continues, but
    it does not emit extra tokens for the logical columns covered by colspan.
    This representation mirrors that behavior without pretending the RTF
    retained the actual span geometry.
    """

    active: list[tuple[int, int, int]] = []  # start, width, final row index
    result = []
    for row_index, row in enumerate(table["rows"]):
        prior = [span for span in active if span[2] >= row_index]
        occupied: set[int] = set()
        tokens: list[tuple[int, str]] = []
        for start, width, _ in prior:
            occupied.update(range(start, start + width))
            tokens.append((start, ""))

        column = 0
        added = []
        for cell in row:
            width = max(1, cell["colspan"])
            while any(
                candidate in occupied
                for candidate in range(column, column + width)
            ):
                column += 1
            tokens.append((column, normalize_cell_text(cell["text"])))
            occupied.update(range(column, column + width))
            if cell["rowspan"] > 1:
                added.append(
                    (column, width, row_index + cell["rowspan"] - 1)
                )
            column += width
        active = prior + added
        result.append(tuple(value for _, value in sorted(tokens)))
    return tuple(result)


def extract_html_tables(parser: TableProbe) -> list[TableRecord]:
    records = []
    for table in parser.tables:
        rows = html_structural_rows(table)
        geometry = table_geometry(table)
        issues = []
        if table["depth"] != 1:
            issues.append("nested HTML table is not an independent source table")
        if table["nested"]:
            issues.append("HTML table contains a nested table")
        if table["invalid_spans"]:
            issues.append("HTML table contains invalid span attributes")
        if table["malformed_structure"]:
            issues.append("HTML table has malformed structure")
        if geometry["geometry_issues"]:
            issues.append("HTML table has incomplete or invalid geometry")
        cells = [cell for row in table["rows"] for cell in row]
        records.append(
            TableRecord(
                id=f"html-table-{table['index']:04d}",
                index=table["index"],
                rows=rows,
                structured_fingerprint=fingerprint(rows),
                ordered_content_fingerprint=fingerprint(ordered_content(rows)),
                supported=not issues,
                support_issues=tuple(issues),
                context={
                    "heading": table["heading"],
                    "rows": len(table["rows"]),
                    "physical_cells": len(cells),
                    "logical_columns": geometry["logical_columns"],
                    "merges": sum(
                        cell["rowspan"] > 1 or cell["colspan"] > 1
                        for cell in cells
                    ),
                    "rowspan_cells": sum(cell["rowspan"] > 1 for cell in cells),
                    "colspan_cells": sum(cell["colspan"] > 1 for cell in cells),
                    "sample": " / ".join(
                        cell for row in rows for cell in row if cell
                    )[:240],
                },
            )
        )
    return records


def _group(
    records: Iterable[TableRecord], attribute: str
) -> dict[str, list[TableRecord]]:
    result: dict[str, list[TableRecord]] = {}
    for record in records:
        if record.supported:
            result.setdefault(getattr(record, attribute), []).append(record)
    return result


def match_tables(
    rtf_tables: list[TableRecord], html_tables: list[TableRecord]
) -> list[dict[str, object]]:
    """Classify RTF tables without ordinal, heading, or fuzzy-score matching."""

    rtf_structured = _group(rtf_tables, "structured_fingerprint")
    html_structured = _group(html_tables, "structured_fingerprint")
    rtf_ordered = _group(rtf_tables, "ordered_content_fingerprint")
    html_ordered = _group(html_tables, "ordered_content_fingerprint")
    unsupported_structured = {}
    unsupported_ordered = {}
    for table in html_tables:
        if not table.supported:
            unsupported_structured.setdefault(
                table.structured_fingerprint, []
            ).append(table)
            unsupported_ordered.setdefault(
                table.ordered_content_fingerprint, []
            ).append(table)

    results = []
    for table in rtf_tables:
        exact = html_structured.get(table.structured_fingerprint, [])
        same_rtf = rtf_structured.get(table.structured_fingerprint, [])
        ordered = html_ordered.get(table.ordered_content_fingerprint, [])
        same_ordered_rtf = rtf_ordered.get(table.ordered_content_fingerprint, [])
        if not table.supported:
            status = "unsupported"
            candidates: list[TableRecord] = []
            evidence = "RTF table region is not safely representable"
        elif exact and len(exact) == 1 and len(same_rtf) == 1:
            status = "matched"
            candidates = exact
            evidence = "bilaterally unique structured row/cell fingerprint"
        elif exact:
            status = "ambiguous"
            candidates = exact
            evidence = (
                "structured fingerprint collides on the RTF side, HTML side, or both"
            )
        elif ordered and len(ordered) == 1 and len(same_ordered_rtf) == 1:
            status = "divergent"
            candidates = ordered
            evidence = (
                "bilaterally unique ordered non-empty cell content, but row/cell "
                "structure differs"
            )
        elif ordered:
            status = "ambiguous"
            candidates = ordered
            evidence = (
                "ordered non-empty cell content collides; structural fingerprint differs"
            )
        else:
            unsupported = unsupported_structured.get(
                table.structured_fingerprint, []
            ) or unsupported_ordered.get(table.ordered_content_fingerprint, [])
            if unsupported:
                status = "unsupported"
                candidates = unsupported
                evidence = "content corresponds only to structurally unsupported HTML"
            else:
                status = "unmatched"
                candidates = []
                evidence = "no exact or ordered-content candidate"
        results.append(
            {
                "rtf_table": table.id,
                "status": status,
                "html_candidates": [candidate.id for candidate in candidates],
                "evidence": evidence,
                "structured_fingerprint": table.structured_fingerprint,
                "ordered_content_fingerprint": table.ordered_content_fingerprint,
                "rtf_context": table.context,
            }
        )
    return results


def _record_for_json(record: TableRecord) -> dict[str, object]:
    result = asdict(record)
    result.pop("rows")
    return result


def diagnose_pair(name: str, rtf_path: Path, html_path: Path) -> dict[str, object]:
    inventory = parse_rtf(rtf_path)
    html_source = html_path.read_bytes()
    encoding, encoding_source = detect_encoding(html_source, html_path)
    parser = TableProbe()
    parser.feed(html_source.decode(encoding))
    parser.finish()

    rtf_tables = extract_rtf_tables(inventory)
    html_tables = extract_html_tables(parser)
    matches = match_tables(rtf_tables, html_tables)
    by_status = {
        status: sum(match["status"] == status for match in matches)
        for status in ("matched", "ambiguous", "unmatched", "divergent", "unsupported")
    }
    referenced_html = {
        candidate
        for match in matches
        for candidate in match["html_candidates"]
    }
    html_status = []
    for table in html_tables:
        related = [
            match for match in matches if table.id in match["html_candidates"]
        ]
        if not table.supported:
            status = "unsupported"
        elif related:
            statuses = {match["status"] for match in related}
            status = statuses.pop() if len(statuses) == 1 else "ambiguous"
        else:
            status = "unmatched"
        html_status.append({"html_table": table.id, "status": status})

    return {
        "pair": name,
        "rtf_source": {
            "path": str(rtf_path),
            "sha256": inventory.sha256,
            "table_regions": len(rtf_tables),
        },
        "html_source": {
            "path": str(html_path),
            "sha256": hashlib.sha256(html_source).hexdigest(),
            "encoding": encoding,
            "encoding_source": encoding_source,
            "tables": len(html_tables),
        },
        "summary": by_status
        | {
            "html_unreferenced": len(html_tables) - len(referenced_html),
        },
        "matches": matches,
        "rtf_tables": [_record_for_json(table) for table in rtf_tables],
        "html_tables": [_record_for_json(table) for table in html_tables],
        "html_status": html_status,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--legacy-dir", type=Path, default=Path("system/legacy")
    )
    parser.add_argument("--output", type=Path, help="optional JSON report")
    args = parser.parse_args()
    report = [
        diagnose_pair(name, args.legacy_dir / rtf_name, args.legacy_dir / html_name)
        for name, rtf_name, html_name in SOURCE_PAIRS
    ]
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
