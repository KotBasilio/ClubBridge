#!/usr/bin/env python3
"""Build deterministic Markdown pilots from the structural RTF inventory."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from rtf_inventory import DocumentInventory, Paragraph, parse_rtf


REPOSITORY_ROOT = Path(__file__).parents[3]


@dataclass(frozen=True)
class PilotSpec:
    key: str
    title: str
    source: str
    source_heading: str
    output: str


@dataclass(frozen=True)
class PilotManifestEntry:
    title: str
    output: str
    source: str
    source_sha256: str
    source_heading: str
    source_byte_start: int
    source_byte_end: int
    extracted_block_count: int
    heading_count: int
    table_region_count: int
    source_hyperlink_count: int
    source_navigation_marker_count: int
    generated_sha256: str


PILOTS = (
    PilotSpec(
        key="kosaya-sistema",
        title="«Косая система»",
        source="system/legacy/Articles_25_09.rtf",
        source_heading="«Косая система»",
        output="kosaya-sistema.md",
    ),
    PilotSpec(
        key="otvety-na-1-trefu",
        title="Ответы на 1♣",
        source="system/legacy/ns25_09.rtf",
        source_heading="Ответы на 1♣",
        output="otvety-na-1-trefu.md",
    ),
    PilotSpec(
        key="shlemovaya-torgovlya",
        title="Шлемовая торговля",
        source="system/legacy/ns25_09.rtf",
        source_heading="Шлемовая торговля",
        output="shlemovaya-torgovlya.md",
    ),
    PilotSpec(
        key="vist-articles",
        title="Вист",
        source="system/legacy/Articles_25_09.rtf",
        source_heading="Вист",
        output="vist-articles.md",
    ),
    PilotSpec(
        key="vist-system-map",
        title="Вист",
        source="system/legacy/ns25_09.rtf",
        source_heading="Вист",
        output="vist-system-map.md",
    ),
)


def select_section(
    inventory: DocumentInventory, heading_text: str
) -> tuple[list[Paragraph], int]:
    """Select one outline section through the next peer or ancestor heading."""

    matches = [
        index
        for index, paragraph in enumerate(inventory.paragraphs)
        if paragraph.outline_level is not None and paragraph.text == heading_text
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one outline heading {heading_text!r}, found {len(matches)}"
        )

    start = matches[0]
    root_level = inventory.paragraphs[start].outline_level
    assert root_level is not None
    end = len(inventory.paragraphs)
    for index in range(start + 1, len(inventory.paragraphs)):
        level = inventory.paragraphs[index].outline_level
        if level is not None and level <= root_level:
            end = index
            break
    return inventory.paragraphs[start:end], end


def table_region_count(paragraphs: list[Paragraph]) -> int:
    count = 0
    in_region = False
    for paragraph in paragraphs:
        if paragraph.in_table and not in_region:
            count += 1
        in_region = paragraph.in_table
    return count


def render_note(
    spec: PilotSpec,
    inventory: DocumentInventory,
    paragraphs: list[Paragraph],
    source_byte_end: int,
) -> str:
    root = paragraphs[0]
    root_level = root.outline_level
    assert root_level is not None
    child_levels = sorted(
        {
            paragraph.outline_level
            for paragraph in paragraphs[1:]
            if paragraph.outline_level is not None
        }
    )
    markdown_levels = {level: index + 2 for index, level in enumerate(child_levels)}

    lines = [
        "---",
        f"title: {json.dumps(spec.title, ensure_ascii=False)}",
        "status: pilot-needs-human-review",
        f"source: {spec.source}",
        f"source_heading: {json.dumps(spec.source_heading, ensure_ascii=False)}",
        f"source_sha256: {inventory.sha256}",
        f"source_byte_start: {root.source_start}",
        f"source_byte_end: {source_byte_end}",
        "---",
        "",
        "<!--",
        "Migration pilot: mechanically generated from the legacy RTF inventory.",
        "It is not yet an approved partnership-system note. Table regions are",
        "deliberately left as source-shaped text pending visual verification.",
        "Internal source links retain their visible wording pending stable note targets.",
        "-->",
        "",
        f"# {spec.title}",
        "",
    ]

    in_table = False
    for paragraph in paragraphs[1:]:
        if paragraph.outline_level is not None:
            if in_table:
                lines.extend(["```", ""])
                in_table = False
            level = markdown_levels[paragraph.outline_level]
            lines.extend([f"{'#' * level} {paragraph.text}", ""])
            continue

        if paragraph.text == "TOC":
            if in_table:
                lines.extend(["```", ""])
                in_table = False
            lines.extend(["<!-- Source navigation marker: TOC -->", ""])
            continue

        if paragraph.in_table:
            if not in_table:
                lines.extend(
                    [
                        "<!-- REVIEW: verify table geometry against the rendered RTF. -->",
                        "```text",
                    ]
                )
                in_table = True
            lines.extend(paragraph.text.splitlines())
            continue

        if in_table:
            lines.extend(["```", ""])
            in_table = False
        lines.extend(paragraph.text.splitlines())
        lines.append("")

    if in_table:
        lines.extend(["```", ""])

    return "\n".join(lines).rstrip() + "\n"


def build_outputs(
    repository_root: Path, specs: tuple[PilotSpec, ...] = PILOTS
) -> tuple[dict[Path, str], list[PilotManifestEntry]]:
    inventories: dict[str, DocumentInventory] = {}
    outputs: dict[Path, str] = {}
    manifest: list[PilotManifestEntry] = []

    for spec in specs:
        if spec.source not in inventories:
            inventories[spec.source] = parse_rtf(repository_root / spec.source)
        inventory = inventories[spec.source]
        paragraphs, end_index = select_section(inventory, spec.source_heading)
        source_byte_end = (
            inventory.paragraphs[end_index].source_start
            if end_index < len(inventory.paragraphs)
            else inventory.byte_count
        )
        rendered = render_note(spec, inventory, paragraphs, source_byte_end)
        output_path = Path(spec.output)
        outputs[output_path] = rendered

        raw_source = (repository_root / spec.source).read_bytes()
        source_slice = raw_source[paragraphs[0].source_start:source_byte_end].decode(
            "latin1"
        )
        manifest.append(
            PilotManifestEntry(
                title=spec.title,
                output=spec.output,
                source=spec.source,
                source_sha256=inventory.sha256,
                source_heading=spec.source_heading,
                source_byte_start=paragraphs[0].source_start,
                source_byte_end=source_byte_end,
                extracted_block_count=len(paragraphs),
                heading_count=sum(
                    paragraph.outline_level is not None for paragraph in paragraphs
                ),
                table_region_count=table_region_count(paragraphs),
                source_hyperlink_count=len(re.findall(r"\bHYPERLINK\b", source_slice)),
                source_navigation_marker_count=sum(
                    paragraph.text == "TOC" for paragraph in paragraphs
                ),
                generated_sha256=hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
            )
        )

    manifest_text = json.dumps(
        [asdict(entry) for entry in manifest], ensure_ascii=False, indent=2
    ) + "\n"
    outputs[Path("manifest.json")] = manifest_text
    return outputs, manifest


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="explicit pilot output directory; approved agreements are never overwritten",
    )
    parser.add_argument(
        "--pilot",
        action="append",
        choices=[spec.key for spec in PILOTS],
        help="pilot key to build; repeat as needed (default: all)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if checked-in outputs differ from a fresh build",
    )
    return parser


def main() -> int:
    args = build_argument_parser().parse_args()
    by_key = {spec.key: spec for spec in PILOTS}
    specs = tuple(by_key[key] for key in args.pilot) if args.pilot else PILOTS
    outputs, manifest = build_outputs(REPOSITORY_ROOT, specs)

    if args.check:
        failures = []
        for relative_path, expected in outputs.items():
            path = args.output_dir / relative_path
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                failures.append(str(path))
        if failures:
            for path in failures:
                print(f"DIFFERS: {path}")
            return 1
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for relative_path, content in outputs.items():
            path = args.output_dir / relative_path
            path.write_text(content, encoding="utf-8")

    for entry in manifest:
        print(
            f"{entry.output}: {entry.extracted_block_count} blocks, "
            f"{entry.heading_count} headings, {entry.table_region_count} table regions, "
            f"{entry.source_hyperlink_count} hyperlinks"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
