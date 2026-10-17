#!/usr/bin/env python3
"""Read-only inventory of Word-exported HTML tables; no agreement generation.

Uses Python's standard library. Reports source table geometry and extracts
minimal HTML witnesses for human comparison with the RTF originals.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

SOURCES = ("Articles_25_09.htm", "ns25_09.htm")
BLOCKED = {"style", "script", "head", "xml"}
HEADINGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


def compact(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def cell_html(cell: dict) -> str:
    attrs = "".join(
        f' {key}="{cell[key]}"'
        for key in ("rowspan", "colspan")
        if cell[key] > 1
    )
    text = html.escape(compact(cell["text"]))
    return f'<{cell["tag"]}{attrs}>{text}</{cell["tag"]}>'


def witness(table: dict) -> str:
    rows = []
    for row in table["rows"]:
        rows.append("  <tr>" + "".join(cell_html(c) for c in row) + "</tr>")
    return "<table>\n" + "\n".join(rows) + "\n</table>\n"


class TableProbe(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.stack = []
        self.skip = []
        self.heading = None
        self.heading_text = []
        self.last_heading = ""
        self.cell = None
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in BLOCKED:
            self.skip.append(tag)
        if self.skip:
            return
        if tag in HEADINGS and not self.stack:
            self.heading = tag
            self.heading_text = []
        if tag == "table":
            self.depth += 1
            self.stack.append({
                "heading": self.last_heading, "rows": [], "nested": False,
                "word_merge_hints": 0, "invalid_spans": [],
            })
            if len(self.stack) > 1:
                self.stack[-2]["nested"] = True
        elif tag == "tr" and self.stack:
            self.stack[-1]["rows"].append([])
        elif tag in ("td", "th") and self.stack and self.stack[-1]["rows"]:
            if self.cell is not None:
                self.stack[-1]["nested"] = True
            def span(key):
                value = attrs.get(key, "1")
                if not re.fullmatch(r"[1-9][0-9]*", value):
                    self.stack[-1]["invalid_spans"].append({key: value})
                    return 1
                return int(value)
            self.cell = {
                "tag": tag, "rowspan": span("rowspan"), "colspan": span("colspan"),
                "text": "", "style_hints": bool(re.search(
                    r"mso-|vmerge|hmerge", str(attrs), re.I
                )),
            }
            if self.cell["style_hints"]:
                self.stack[-1]["word_merge_hints"] += 1
        elif tag == "br" and self.cell is not None:
            self.cell["text"] += " "

    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip[-1]:
                self.skip.pop()
            return
        if tag in HEADINGS and self.heading == tag:
            self.last_heading = compact("".join(self.heading_text))[:200]
            self.heading = None
        elif tag in ("td", "th") and self.cell is not None and self.stack:
            self.cell["text"] = compact(self.cell["text"])
            self.stack[-1]["rows"][-1].append(self.cell)
            self.cell = None
        elif tag == "table" and self.stack:
            table = self.stack.pop()
            self.tables.append(table)
            self.depth -= 1

    def handle_data(self, data):
        if self.skip:
            return
        if self.heading is not None:
            self.heading_text.append(data)
        if self.cell is not None:
            self.cell["text"] += data


def examine(path: Path, sample_dir: Path | None, sample_limit: int) -> dict:
    source = path.read_bytes()
    # HTMLParser understands character references; Word may specify legacy encodings.
    declaration = source[:8192].decode("ascii", errors="ignore")
    match = re.search(r'charset\s*=\s*["\x27]?([A-Za-z0-9_-]+)', declaration, re.I)
    encoding = match.group(1) if match else "utf-8"
    try:
        text = source.decode(encoding)
    except (LookupError, UnicodeDecodeError) as ex:
        raise ValueError(f"{path}: cannot decode using {encoding}: {ex}") from ex
    parser = TableProbe()
    parser.feed(text)
    results = []
    for idx, table in enumerate(parser.tables, 1):
        cells = [cell for row in table["rows"] for cell in row]
        merges = sum(c["rowspan"] > 1 or c["colspan"] > 1 for c in cells)
        info = {
            "index": idx, "heading": table["heading"],
            "rows": len(table["rows"]), "cells": len(cells),
            "merged_cells": merges, "nested": table["nested"],
            "word_merge_hints": table["word_merge_hints"],
            "invalid_spans": table["invalid_spans"],
            "sample": " / ".join(c["text"][:60] for c in cells[:4]),
        }
        results.append(info)
        if sample_dir and idx <= sample_limit:
            (sample_dir / f"{path.stem}-table-{idx:04}.html").write_text(
                witness(table), encoding="utf-8"
            )
    return {
        "source": str(path), "sha256": hashlib.sha256(source).hexdigest(),
        "encoding": encoding, "total_tables": len(results),
        "tables_with_merges": sum(t["merged_cells"] > 0 for t in results),
        "tables": results,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("sources", nargs="*", type=Path)
    p.add_argument("--output", type=Path, help="optional JSON report")
    p.add_argument("--samples-dir", type=Path, help="optional minimal HTML samples")
    p.add_argument("--sample-limit", type=int, default=10)
    args = p.parse_args()
    if args.sample_limit < 0:
        p.error("--sample-limit must be nonnegative")
    sources = args.sources or [
        Path("system/legacy") / name for name in SOURCES
    ]
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
