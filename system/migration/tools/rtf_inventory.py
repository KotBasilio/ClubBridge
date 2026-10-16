#!/usr/bin/env python3
"""Build a review-oriented structural inventory of legacy RTF documents.

This is deliberately not an RTF-to-Markdown converter. It extracts enough
structure and provenance to plan semantic note boundaries without pretending
that automatic output has been verified against the rendered source.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


IGNORED_DESTINATIONS = {
    "author",
    "category",
    "colortbl",
    "comment",
    "company",
    "creatim",
    "datafield",
    "datastore",
    "doccomm",
    "filetbl",
    "fldinst",
    "fonttbl",
    "footer",
    "footerf",
    "footerl",
    "footerr",
    "footnote",
    "generator",
    "header",
    "headerf",
    "headerl",
    "headerr",
    "info",
    "keywords",
    "latentstyles",
    "listoverridetable",
    "listtable",
    "manager",
    "object",
    "operator",
    "pgptbl",
    "pict",
    "printim",
    "private",
    "revtbl",
    "rsidtbl",
    "stylesheet",
    "subject",
    "themedata",
    "title",
    "xmlnstbl",
}

CHARSET_CODEPAGES = {
    0: "cp1252",
    128: "shift_jis",
    129: "cp949",
    134: "gbk",
    136: "big5",
    161: "cp1253",
    162: "cp1254",
    177: "cp1255",
    178: "cp1256",
    186: "cp1257",
    204: "cp1251",
    222: "cp874",
    238: "cp1250",
}

# Compatibility mappings for Adobe Symbol glyphs found in the source files.
# Code 190 is a private-use horizontal arrow extender; a box-drawing line is
# used so the constructed arrow remains visible in ordinary Markdown fonts.
SYMBOL_CHARACTERS = {
    167: "♣",
    168: "♦",
    169: "♥",
    170: "♠",
    174: "→",
    182: "∂",
    183: "•",
    190: "─",
    197: "⊕",
    222: "⇒",
}

SPECIAL_CHARS = {
    "bullet": "•",
    "emdash": "—",
    "emspace": "\u2003",
    "endash": "–",
    "enspace": "\u2002",
    "ldblquote": "“",
    "lquote": "‘",
    "qmspace": "\u2005",
    "rdblquote": "”",
    "rquote": "’",
}


@dataclass
class ParserState:
    ignored: bool = False
    pending_destination: bool = False
    unicode_fallback_width: int = 1
    style: int | None = None
    outline_level: int | None = None
    in_table: bool = False
    font: int | None = None


@dataclass
class Paragraph:
    text: str
    style: int | None
    outline_level: int | None
    page_region: int
    kind: str
    in_table: bool
    source_start: int
    source_end: int


@dataclass
class DocumentInventory:
    source: str
    byte_count: int
    sha256: str
    document_codepage: str
    explicit_page_region_count: int
    paragraph_count: int
    table_row_count: int
    field_count: int
    list_marker_count: int
    bookmark_count: int
    hyperlink_count: int
    toc_hyperlink_count: int
    embedded_picture_count: int
    embedded_object_count: int
    headings: list[Paragraph]
    paragraphs: list[Paragraph]


def _document_codepage(source: str) -> str:
    match = re.search(r"\\ansicpg(\d+)", source[:5_000])
    return f"cp{match.group(1)}" if match else "cp1252"


def _font_charsets(source: str) -> dict[int, int]:
    return {
        int(font): int(charset)
        for font, charset in re.findall(
            r"\\f(\d+)(?:(?:\\[A-Za-z]+-?\d* ?)|\s)*?\\fcharset(\d+)",
            source[:500_000],
        )
    }


def _font_names(source: str) -> dict[int, str]:
    start = source.find("{\\fonttbl")
    if start < 0:
        return {}

    depth = 0
    end = len(source)
    for index in range(start, len(source)):
        if source[index] == "{" and (index == 0 or source[index - 1] != "\\"):
            depth += 1
        elif source[index] == "}" and (index == 0 or source[index - 1] != "\\"):
            depth -= 1
            if depth == 0:
                end = index + 1
                break

    font_table = source[start:end]
    names: dict[int, str] = {}
    matches = list(re.finditer(r"{\\f(\d+)", font_table))
    for match in matches:
        entry_end = font_table.find(";", match.end())
        if entry_end < 0:
            continue
        entry = font_table[match.end():entry_end]
        while re.search(r"{[^{}]*}", entry):
            entry = re.sub(r"{[^{}]*}", "", entry)
        entry = re.sub(r"\\[A-Za-z]+-?\d* ?", "", entry).strip()
        if entry:
            names[int(match.group(1))] = entry
    return names


def _decode_symbol(number: int) -> str:
    return SYMBOL_CHARACTERS.get(number, f"⟦SYMBOL {number}⟧")


def _decode_hex_byte(value: str, codepage: str, font_name: str = "") -> str:
    number = int(value, 16)
    if font_name.casefold() == "symbol":
        return _decode_symbol(number)
    raw = bytes([number])
    try:
        return raw.decode(codepage)
    except (LookupError, UnicodeDecodeError):
        return raw.decode("cp1252", errors="replace")


def _normalized_text(chars: Iterable[str]) -> str:
    text = "".join(chars).replace("\xa0", " ").replace("\ufeff", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def _normalized_heading(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_rtf_bytes(data: bytes, source_name: str = "<memory>") -> DocumentInventory:
    """Parse review-relevant RTF structure without modifying the source."""

    # Latin-1 provides a lossless one-byte-to-one-codepoint view, so recorded
    # source offsets are also byte offsets.
    source = data.decode("latin1")
    document_codepage = _document_codepage(source)
    font_charsets = _font_charsets(source)
    font_names = _font_names(source)

    state = ParserState()
    stack: list[ParserState] = []
    chars: list[str] = []
    paragraphs: list[Paragraph] = []
    unicode_fallback = 0
    paragraph_start: int | None = None
    page_region = 1
    table_rows = 0

    def append(text: str, offset: int, *, fallback: bool = True) -> None:
        nonlocal paragraph_start, unicode_fallback
        if state.ignored or not text:
            return
        if fallback and unicode_fallback:
            skipped = min(unicode_fallback, len(text))
            unicode_fallback -= skipped
            text = text[skipped:]
        if text:
            if paragraph_start is None:
                paragraph_start = offset
            chars.append(text)

    def flush(offset: int, kind: str = "paragraph") -> None:
        nonlocal paragraph_start
        text = _normalized_text(chars)
        chars.clear()
        if text:
            paragraphs.append(
                Paragraph(
                    text=text,
                    style=state.style,
                    outline_level=state.outline_level,
                    page_region=page_region,
                    kind=kind,
                    in_table=state.in_table,
                    source_start=paragraph_start if paragraph_start is not None else offset,
                    source_end=offset,
                )
            )
        paragraph_start = None

    i = 0
    while i < len(source):
        token_start = i
        char = source[i]

        if char == "{":
            stack.append(copy.copy(state))
            i += 1
            continue

        if char == "}":
            if stack:
                state = stack.pop()
            i += 1
            continue

        if char != "\\":
            # Raw CR/LF wrap the RTF source and are not visible document text.
            if char not in "\r\n":
                append(char, token_start)
            i += 1
            continue

        i += 1
        if i >= len(source):
            break

        symbol = source[i]
        if symbol in "\\{}":
            append(symbol, token_start)
            i += 1
            continue
        if symbol == "*":
            state.pending_destination = True
            i += 1
            continue
        if symbol == "'" and i + 2 < len(source):
            charset = font_charsets.get(state.font if state.font is not None else -1)
            codepage = CHARSET_CODEPAGES.get(charset, document_codepage)
            font_name = font_names.get(state.font if state.font is not None else -1, "")
            append(
                _decode_hex_byte(source[i + 1 : i + 3], codepage, font_name),
                token_start,
            )
            i += 3
            continue
        if not symbol.isalpha():
            if symbol == "~":
                append(" ", token_start)
            elif symbol == "_":
                append("‑", token_start)
            elif symbol == "-":
                append("\u00ad", token_start)
            i += 1
            continue

        word_start = i
        while i < len(source) and source[i].isalpha():
            i += 1
        word = source[word_start:i]

        sign = 1
        if i < len(source) and source[i] == "-":
            sign = -1
            i += 1
        number_start = i
        while i < len(source) and source[i].isdigit():
            i += 1
        number = sign * int(source[number_start:i]) if i > number_start else None
        if i < len(source) and source[i] == " ":
            i += 1

        if state.pending_destination and word == "fldinst":
            symbol_field = re.match(r"SYMBOL\s+(\d+)\b", source[i:])
            if symbol_field:
                append(_decode_symbol(int(symbol_field.group(1))), token_start, fallback=False)
        if state.pending_destination:
            state.ignored = True
            state.pending_destination = False
        if word in IGNORED_DESTINATIONS:
            state.ignored = True

        if word == "uc" and number is not None:
            state.unicode_fallback_width = number
        elif word == "u" and number is not None and not state.ignored:
            codepoint = number if number >= 0 else number + 65_536
            append(chr(codepoint), token_start, fallback=False)
            unicode_fallback = state.unicode_fallback_width
        elif word == "s" and number is not None:
            state.style = number
        elif word == "f" and number is not None:
            state.font = number
        elif word == "outlinelevel" and number is not None:
            state.outline_level = number
        elif word == "pard":
            state.style = None
            state.outline_level = None
            state.in_table = False
        elif word == "intbl":
            state.in_table = True
        elif word == "par":
            flush(token_start)
        elif word == "line":
            append("\n", token_start)
        elif word == "tab":
            append("\t", token_start)
        elif word == "cell":
            append(" | ", token_start)
        elif word == "row":
            flush(token_start, "table-row")
            table_rows += 1
        elif word == "page":
            flush(token_start)
            page_region += 1
        elif word in SPECIAL_CHARS:
            append(SPECIAL_CHARS[word], token_start)

    flush(len(source))

    headings = [
        Paragraph(**(asdict(paragraph) | {"text": _normalized_heading(paragraph.text)}))
        for paragraph in paragraphs
        if paragraph.outline_level is not None
    ]
    hyperlink_count = len(re.findall(r"\bHYPERLINK\b", source))
    toc_hyperlink_count = len(
        re.findall(r"\bHYPERLINK\b[^}]{0,300}_Toc\d+", source)
    )

    return DocumentInventory(
        source=source_name,
        byte_count=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        document_codepage=document_codepage,
        explicit_page_region_count=page_region,
        paragraph_count=len(paragraphs),
        table_row_count=table_rows,
        field_count=len(re.findall(r"\\field\b", source)),
        list_marker_count=len(re.findall(r"\\listtext\b", source)),
        bookmark_count=len(re.findall(r"\\bkmkstart\b", source)),
        hyperlink_count=hyperlink_count,
        toc_hyperlink_count=toc_hyperlink_count,
        embedded_picture_count=len(re.findall(r"\\pict\b", source)),
        embedded_object_count=len(re.findall(r"\\object\b", source)),
        headings=headings,
        paragraphs=paragraphs,
    )


def parse_rtf(path: Path) -> DocumentInventory:
    return parse_rtf_bytes(path.read_bytes(), str(path))


def summary(inventory: DocumentInventory) -> dict[str, object]:
    return {
        "source": inventory.source,
        "byte_count": inventory.byte_count,
        "sha256": inventory.sha256,
        "document_codepage": inventory.document_codepage,
        "explicit_page_region_count": inventory.explicit_page_region_count,
        "paragraph_count": inventory.paragraph_count,
        "heading_count": len(inventory.headings),
        "headings_by_outline_level": {
            str(level): sum(
                1 for heading in inventory.headings if heading.outline_level == level
            )
            for level in sorted(
                {
                    heading.outline_level
                    for heading in inventory.headings
                    if heading.outline_level is not None
                }
            )
        },
        "table_row_count": inventory.table_row_count,
        "field_count": inventory.field_count,
        "list_marker_count": inventory.list_marker_count,
        "bookmark_count": inventory.bookmark_count,
        "hyperlink_count": inventory.hyperlink_count,
        "toc_hyperlink_count": inventory.toc_hyperlink_count,
        "non_toc_hyperlink_count": (
            inventory.hyperlink_count - inventory.toc_hyperlink_count
        ),
        "embedded_picture_count": inventory.embedded_picture_count,
        "embedded_object_count": inventory.embedded_object_count,
    }


def write_inventory(inventory: DocumentInventory, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(inventory.source).stem
    (output_dir / f"{stem}.inventory.json").write_text(
        json.dumps(asdict(inventory), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (output_dir / f"{stem}.inspection.txt").open("w", encoding="utf-8") as handle:
        for paragraph in inventory.paragraphs:
            prefix = ""
            if paragraph.outline_level is not None:
                prefix = f"[H{paragraph.outline_level + 1}] "
            handle.write(prefix + paragraph.text + "\n")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path, help="RTF sources to inspect")
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="optional directory for UTF-8 JSON and inspection text",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    inventories = [parse_rtf(path) for path in args.sources]

    if args.output_dir:
        for inventory in inventories:
            write_inventory(inventory, args.output_dir)
        (args.output_dir / "summary.json").write_text(
            json.dumps([summary(item) for item in inventories], ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )

    for inventory in inventories:
        print(json.dumps(summary(inventory), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
