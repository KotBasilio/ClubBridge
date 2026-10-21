#!/usr/bin/env python3
"""Build one deterministic, review-only section draft from a legacy source."""
from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass
from pathlib import Path

from build_geometry_pilots import (
    PAIRS,
    GeometryCell,
    PairSpec,
    TableModel,
    build_geometry_model,
    check_outputs,
    escape_text,
    load_approvals,
    load_pair,
    manifest_table,
    render_fallback,
    render_gfm,
    render_html,
    sha256_text,
    table_by_id,
    validate_output_dir,
    write_outputs,
)
from match_rtf_html_tables import TableRecord
from rtf_inventory import DocumentInventory, Paragraph


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PRESENTATION_DECISIONS_PATH = Path(
    "system/migration/presentation-decisions.json"
)
GENERATOR_PATH = "system/migration/tools/build_section_draft.py"


@dataclass(frozen=True)
class SectionSlice:
    heading: str
    occurrence: int
    paragraphs: tuple[Paragraph, ...]
    source_start: int
    source_end: int


@dataclass(frozen=True)
class TableOption:
    model: TableModel
    presentation_override: str | None = None
    unresolved_issue: str | None = None


def select_section(
    inventory: DocumentInventory,
    heading: str,
    occurrence: int | None = None,
) -> SectionSlice:
    """Select a heading through the next heading at its level or above."""

    matches = [
        index
        for index, paragraph in enumerate(inventory.paragraphs)
        if paragraph.outline_level is not None and paragraph.text == heading
    ]
    if not matches:
        candidates = [
            paragraph
            for paragraph in inventory.headings
            if heading.casefold() in paragraph.text.casefold()
            or paragraph.text.casefold() in heading.casefold()
        ][:8]
        detail = "; ".join(
            f"{item.text!r} at byte {item.source_start}" for item in candidates
        ) or "no similar headings found"
        raise ValueError(f"heading {heading!r} was not found; candidates: {detail}")
    if occurrence is None and len(matches) != 1:
        detail = "; ".join(
            f"--heading-occurrence {number} (byte "
            f"{inventory.paragraphs[index].source_start})"
            for number, index in enumerate(matches, 1)
        )
        raise ValueError(
            f"heading {heading!r} occurs {len(matches)} times; choose {detail}"
        )
    chosen = occurrence or 1
    if chosen < 1 or chosen > len(matches):
        raise ValueError(
            f"heading {heading!r} has {len(matches)} occurrence(s); "
            f"cannot select occurrence {chosen}"
        )
    start_index = matches[chosen - 1]
    root = inventory.paragraphs[start_index]
    assert root.outline_level is not None
    end_index = len(inventory.paragraphs)
    for index in range(start_index + 1, len(inventory.paragraphs)):
        level = inventory.paragraphs[index].outline_level
        if level is not None and level <= root.outline_level:
            end_index = index
            break
    source_end = (
        inventory.paragraphs[end_index].source_start
        if end_index < len(inventory.paragraphs)
        else inventory.byte_count
    )
    return SectionSlice(
        heading=heading,
        occurrence=chosen,
        paragraphs=tuple(inventory.paragraphs[start_index:end_index]),
        source_start=root.source_start,
        source_end=source_end,
    )


def load_presentation_decisions(repository_root: Path) -> list[dict[str, object]]:
    path = repository_root / PRESENTATION_DECISIONS_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError("unsupported presentation-decision schema")
    return list(document["decisions"])


def _token_model(
    pair: dict[str, object],
    record: TableRecord,
    *,
    evidence_class: str,
    warning: str,
) -> TableModel:
    spec: PairSpec = pair["spec"]  # type: ignore[assignment]
    match = pair["matches"][record.id]
    raw_rows = pair["raw_rtf_tables"][record.index - 1]
    return TableModel(
        key=f"{spec.key.lower()}-{record.id}",
        title=record.id,
        evidence_class=evidence_class,
        diagnostic_status=str(match["status"]),
        rendering="rtf-token-list",
        pair=spec.key,
        rtf_source=spec.rtf_source,
        rtf_sha256=str(pair["rtf_sha256"]),
        rtf_table=record.id,
        rtf_source_start=int(record.context["source_start"]),
        rtf_source_end=int(record.context["source_end"]),
        html_source=None,
        html_sha256=None,
        html_table=None,
        logical_columns=None,
        cells=(),
        fallback_rows=raw_rows,
        warning=warning,
    )


def _diagram_option(
    pair: dict[str, object],
    record: TableRecord,
    decision: dict[str, object],
) -> TableOption:
    raw_rows = pair["raw_rtf_tables"][record.index - 1]
    if len(raw_rows) != 1:
        raise ValueError(f"{record.id}: approved diagram is no longer one RTF row")
    actual = [cell.text for cell in raw_rows[0]]
    expected = list(decision["expected_cell_text"])
    if [escape_text(value) for value in actual] != [
        escape_text(value) for value in expected
    ]:
        raise ValueError(
            f"{record.id}: approved diagram tokens changed: {actual!r} != {expected!r}"
        )
    spec: PairSpec = pair["spec"]  # type: ignore[assignment]
    match = pair["matches"][record.id]
    cells = tuple(
        GeometryCell(
            row=1,
            column=index,
            rowspan=1,
            colspan=1,
            text=cell.text,
            rtf_row=cell.row,
            rtf_cell=cell.cell,
            html_row=0,
            html_cell=0,
        )
        for index, cell in enumerate(raw_rows[0], 1)
    )
    decision_id = str(decision["id"])
    return TableOption(
        TableModel(
            key=f"{spec.key.lower()}-{record.id}-{decision_id}",
            title=record.id,
            evidence_class="approved-presentation",
            diagnostic_status=str(match["status"]),
            rendering="gfm-centered",
            pair=spec.key,
            rtf_source=spec.rtf_source,
            rtf_sha256=str(pair["rtf_sha256"]),
            rtf_table=record.id,
            rtf_source_start=int(record.context["source_start"]),
            rtf_source_end=int(record.context["source_end"]),
            html_source=None,
            html_sha256=None,
            html_table=None,
            logical_columns=len(cells),
            cells=cells,
            fallback_rows=(),
            warning=(
                "Source-hash-keyed presentation decision; it does not assert an "
                "HTML match."
            ),
            approval_record=(
                f"{PRESENTATION_DECISIONS_PATH.as_posix()}#{decision_id}"
            ),
        ),
        presentation_override=decision_id,
    )


def _decision_for(
    pair: dict[str, object],
    record: TableRecord,
    decisions: list[dict[str, object]],
) -> tuple[dict[str, object] | None, str | None]:
    spec: PairSpec = pair["spec"]  # type: ignore[assignment]
    relevant = [
        decision
        for decision in decisions
        if decision.get("source") == spec.rtf_source
        and decision.get("rtf_table") == record.id
        and decision.get("status") == "approved"
    ]
    applicable = [
        decision
        for decision in relevant
        if decision.get("source_sha256") == pair["rtf_sha256"]
    ]
    if len(applicable) > 1:
        raise ValueError(f"multiple presentation decisions apply to {record.id}")
    if applicable:
        return applicable[0], None
    if relevant:
        return None, (
            f"{record.id}: presentation decision abstained because its source "
            "hash does not match"
        )
    return None, None


def _rendering_for(pair: dict[str, object], html_id: str) -> str:
    raw = pair["html_raw"][int(html_id.rsplit("-", 1)[1]) - 1]
    merged = any(
        cell["rowspan"] > 1 or cell["colspan"] > 1
        for row in raw["rows"]
        for cell in row
    )
    return "html" if merged else "gfm"


def table_options(
    pair: dict[str, object],
    record: TableRecord,
    approvals: list[dict[str, object]],
    decisions: list[dict[str, object]],
) -> list[TableOption]:
    decision, decision_warning = _decision_for(pair, record, decisions)
    if decision:
        return [_diagram_option(pair, record, decision)]

    match = pair["matches"][record.id]
    status = str(match["status"])
    candidates = list(match["html_candidates"])
    title = record.id
    if status == "matched":
        html_id = candidates[0]
        model = build_geometry_model(
            pair,
            key=f"{record.id}-{html_id}",
            title=title,
            rtf_id=record.id,
            html_id=html_id,
            evidence_class="strict",
            rendering=_rendering_for(pair, html_id),
            approvals=approvals,
        )
        return [TableOption(model)]
    if status == "ambiguous" and candidates:
        return [
            TableOption(
                build_geometry_model(
                    pair,
                    key=f"{record.id}-{html_id}",
                    title=title,
                    rtf_id=record.id,
                    html_id=html_id,
                    evidence_class="competing-variant",
                    rendering=_rendering_for(pair, html_id),
                    approvals=approvals,
                    variant_group=f"{record.id}-html-candidates",
                    variant_label=html_id,
                ),
                unresolved_issue=(
                    f"{record.id}: ambiguous HTML geometry; this draft uses "
                    f"candidate {html_id}"
                ),
            )
            for html_id in candidates
        ]
    geometry_failure: str | None = None
    if status == "divergent" and len(candidates) == 1:
        html_id = candidates[0]
        try:
            model = build_geometry_model(
                pair,
                key=f"{record.id}-{html_id}",
                title=title,
                rtf_id=record.id,
                html_id=html_id,
                evidence_class="human-reviewed",
                rendering=_rendering_for(pair, html_id),
                approvals=approvals,
            )
            return [TableOption(model)]
        except ValueError as error:
            geometry_failure = (
                f"{record.id}: divergent candidate {html_id} was not eligible "
                f"for geometry ({error}); RTF tokens retained"
            )
    issue = decision_warning or geometry_failure or (
        f"{record.id}: {status} table has no approved HTML geometry; "
        "RTF tokens retained"
    )
    return [
        TableOption(
            _token_model(
                pair,
                record,
                evidence_class="unresolved-fallback",
                warning=issue,
            ),
            unresolved_issue=issue,
        )
    ]


def _section_tables(
    pair: dict[str, object], section: SectionSlice
) -> list[TableRecord]:
    return [
        record
        for record in pair["rtf_tables"]
        if section.source_start <= int(record.context["source_start"])
        < section.source_end
    ]


def _render_model(option: TableOption) -> str:
    model = option.model
    if model.rendering == "gfm":
        return render_gfm(model)
    if model.rendering == "gfm-centered":
        return render_gfm(model, centered=True)
    if model.rendering == "html":
        return render_html(model)
    return render_fallback(model)


def render_section(
    source: str,
    inventory: DocumentInventory,
    section: SectionSlice,
    table_selection: dict[str, TableOption],
) -> str:
    child_levels = sorted(
        {
            paragraph.outline_level
            for paragraph in section.paragraphs[1:]
            if paragraph.outline_level is not None
        }
    )
    markdown_levels = {level: index + 2 for index, level in enumerate(child_levels)}
    lines = [
        "---",
        f"title: {json.dumps(section.heading, ensure_ascii=False)}",
        "status: migration-draft-needs-human-review",
        f"generated_by: {GENERATOR_PATH}",
        f"source: {source}",
        f"source_heading: {json.dumps(section.heading, ensure_ascii=False)}",
        f"source_heading_occurrence: {section.occurrence}",
        f"source_sha256: {inventory.sha256}",
        f"source_byte_start: {section.source_start}",
        f"source_byte_end: {section.source_end}",
        "---",
        "",
        "<!-- Review-only migration draft. Not an approved partnership agreement. -->",
        "",
        f"# {section.heading}",
        "",
    ]
    paragraphs = section.paragraphs
    index = 1
    while index < len(paragraphs):
        paragraph = paragraphs[index]
        if paragraph.kind == "table-row":
            option = next(
                value
                for value in table_selection.values()
                if value.model.rtf_source_start == paragraph.source_start
            )
            model = option.model
            lines.append(
                f"<!-- {model.rtf_table}: {model.evidence_class}; "
                f"diagnostic={model.diagnostic_status} -->"
            )
            if option.unresolved_issue:
                lines.extend([f"> **Table review needed:** {option.unresolved_issue}", ""])
            lines.extend([_render_model(option), ""])
            index += 1
            while index < len(paragraphs) and paragraphs[index].kind == "table-row":
                index += 1
            continue
        if paragraph.outline_level is not None:
            level = markdown_levels[paragraph.outline_level]
            lines.extend([f"{'#' * level} {paragraph.text}", ""])
        elif paragraph.text == "TOC":
            lines.extend(["<!-- Source navigation marker: TOC -->", ""])
        else:
            lines.extend([*paragraph.text.splitlines(), ""])
        index += 1
    return "\n".join(lines).rstrip() + "\n"


def _variant_name(index: int) -> str:
    value = index
    label = ""
    while value:
        value, remainder = divmod(value - 1, 26)
        label = chr(ord("a") + remainder) + label
    return label


def review_text(source: str, section: SectionSlice) -> str:
    return f"""# Review boundary — {section.heading}

The generated Markdown files in this directory are review drafts, not approved
partnership agreements. The runner never writes into `system/agreements/`.

Review the wording, paragraph/table order, symbols, every table classification,
and all warnings in `manifest.json`. If Archy approves a draft, Vel should copy
the reviewed content into a deliberately named agreement note, remove the
generator-only review framing as appropriate, and record the chosen draft hash
and human review in the migration provenance. That promotion is a separate,
human-authorized commit; rerunning this generator cannot alter it.

Source: `{source}`

Heading: `{section.heading}`

Occurrence: `{section.occurrence}`

Bytes: `{section.source_start}..{section.source_end}`
"""


def build_outputs(
    repository_root: Path,
    source_key: str,
    heading: str,
    occurrence: int | None = None,
) -> dict[Path, str]:
    if source_key not in PAIRS:
        raise ValueError(f"unknown source {source_key!r}; choose Articles or ns")
    pair = load_pair(repository_root, PAIRS[source_key])
    inventory: DocumentInventory = pair["inventory"]  # type: ignore[assignment]
    section = select_section(inventory, heading, occurrence)
    approvals = load_approvals(repository_root)
    decisions = load_presentation_decisions(repository_root)
    records = _section_tables(pair, section)
    options = [table_options(pair, record, approvals, decisions) for record in records]
    combinations = list(itertools.product(*options)) if options else [()]
    competing = any(len(item) > 1 for item in options)
    outputs: dict[Path, str] = {}
    manifest_outputs = []
    for index, combination in enumerate(combinations, 1):
        filename = (
            f"draft-alternative-{_variant_name(index)}.md"
            if competing
            else "draft.md"
        )
        selection = {
            record.id: option for record, option in zip(records, combination)
        }
        rendered = render_section(
            PAIRS[source_key].rtf_source, inventory, section, selection
        )
        outputs[Path(filename)] = rendered
        issues = [
            option.unresolved_issue
            for option in combination
            if option.unresolved_issue
        ]
        manifest_outputs.append(
            {
                "output": filename,
                "generated_sha256": sha256_text(rendered),
                "tables": [
                    manifest_table(option.model)
                    | {"presentation_override": option.presentation_override}
                    for option in combination
                ],
                "warnings": issues,
                "unresolved_issues": issues,
            }
        )
    spec: PairSpec = pair["spec"]  # type: ignore[assignment]
    manifest = {
        "schema_version": 1,
        "status": "migration-draft-needs-human-review",
        "generator": GENERATOR_PATH,
        "source": {
            "key": source_key,
            "rtf_path": spec.rtf_source,
            "rtf_sha256": pair["rtf_sha256"],
            "html_path": spec.html_source,
            "html_sha256": pair["html_sha256"],
        },
        "section": {
            "heading": section.heading,
            "heading_occurrence": section.occurrence,
            "source_byte_start": section.source_start,
            "source_byte_end": section.source_end,
        },
        "competing_variants": [
            output["output"] for output in manifest_outputs
        ] if competing else [],
        "outputs": manifest_outputs,
        "promotion": {
            "automatic": False,
            "approved_tree": "system/agreements",
            "requirement": "explicit human approval and separate provenance record",
        },
    }
    outputs[Path("manifest.json")] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    outputs[Path("REVIEW.md")] = review_text(spec.rtf_source, section)
    return outputs


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, choices=sorted(PAIRS))
    parser.add_argument("--section", required=True, help="exact outline heading")
    parser.add_argument(
        "--heading-occurrence",
        type=int,
        help="one-based selector required only when the exact heading is duplicated",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
        help="explicit staged draft directory; legacy and agreements are refused",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the output directory differs from deterministic regeneration",
    )
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()
    try:
        validate_output_dir(REPOSITORY_ROOT, args.output_dir)
        outputs = build_outputs(
            REPOSITORY_ROOT,
            args.source,
            args.section,
            args.heading_occurrence,
        )
    except ValueError as error:
        parser.error(str(error))
    if args.check:
        differences = check_outputs(args.output_dir, outputs)
        for path in differences:
            print(f"DIFFERS: {path}")
        return 1 if differences else 0
    write_outputs(args.output_dir, outputs)
    for relative in outputs:
        print(args.output_dir / relative)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
