#!/usr/bin/env python3
"""Build deterministic, review-only Markdown pilots with validated geometry."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from html_table_probe import TableProbe, detect_encoding, table_geometry
from match_rtf_html_tables import (
    TableRecord,
    extract_html_tables,
    extract_rtf_tables,
    html_structural_rows,
    match_tables,
    normalize_cell_text,
)
from rtf_inventory import DocumentInventory, Paragraph, parse_rtf


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
APPROVALS_PATH = Path("system/migration/geometry-approvals.json")
BREAK = re.compile(r"(?i)<br\s*/?>")


@dataclass(frozen=True)
class PairSpec:
    key: str
    rtf_source: str
    html_source: str


@dataclass(frozen=True)
class RawCell:
    text: str
    row: int
    cell: int
    source_start: int
    source_end: int


@dataclass(frozen=True)
class GeometryCell:
    row: int
    column: int
    rowspan: int
    colspan: int
    text: str
    rtf_row: int | None
    rtf_cell: int | None
    html_row: int
    html_cell: int


@dataclass(frozen=True)
class TableModel:
    key: str
    title: str
    evidence_class: str
    diagnostic_status: str
    rendering: str
    pair: str
    rtf_source: str
    rtf_sha256: str
    rtf_table: str
    rtf_source_start: int
    rtf_source_end: int
    html_source: str | None
    html_sha256: str | None
    html_table: str | None
    logical_columns: int | None
    cells: tuple[GeometryCell, ...]
    fallback_rows: tuple[tuple[RawCell, ...], ...]
    warning: str
    geometry_adjustments: tuple[str, ...] = ()
    approval_record: str | None = None
    variant_group: str | None = None
    variant_label: str | None = None


PAIRS = {
    "Articles": PairSpec(
        "Articles",
        "system/legacy/Articles_25_09.rtf",
        "system/legacy/Articles_25_09.htm",
    ),
    "ns": PairSpec(
        "ns",
        "system/legacy/ns25_09.rtf",
        "system/legacy/ns25_09.htm",
    ),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def split_raw_rtf_row(paragraph: Paragraph, row: int) -> tuple[RawCell, ...]:
    values = paragraph.text.split("|")
    if values and not values[-1].strip():
        values.pop()
    return tuple(
        RawCell(
            text=value.strip(),
            row=row,
            cell=cell,
            source_start=paragraph.source_start,
            source_end=paragraph.source_end,
        )
        for cell, value in enumerate(values, 1)
    )


def extract_raw_rtf_tables(
    inventory: DocumentInventory,
) -> list[tuple[tuple[RawCell, ...], ...]]:
    groups: list[list[Paragraph]] = []
    current: list[Paragraph] = []
    for paragraph in inventory.paragraphs:
        if paragraph.kind == "table-row":
            current.append(paragraph)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return [
        tuple(
            split_raw_rtf_row(paragraph, row)
            for row, paragraph in enumerate(group, 1)
        )
        for group in groups
    ]


def load_pair(repository_root: Path, spec: PairSpec) -> dict[str, object]:
    rtf_path = repository_root / spec.rtf_source
    html_path = repository_root / spec.html_source
    inventory = parse_rtf(rtf_path)
    html_source = html_path.read_bytes()
    encoding, _ = detect_encoding(html_source, html_path)
    parser = TableProbe()
    parser.feed(html_source.decode(encoding))
    parser.finish()
    rtf_tables = extract_rtf_tables(inventory)
    html_tables = extract_html_tables(parser)
    matches = match_tables(rtf_tables, html_tables)
    return {
        "spec": spec,
        "inventory": inventory,
        "rtf_tables": rtf_tables,
        "raw_rtf_tables": extract_raw_rtf_tables(inventory),
        "html_tables": html_tables,
        "html_raw": parser.tables,
        "matches": {match["rtf_table"]: match for match in matches},
        "rtf_sha256": inventory.sha256,
        "html_sha256": sha256_bytes(html_source),
    }


def load_approvals(repository_root: Path) -> list[dict[str, object]]:
    document = json.loads((repository_root / APPROVALS_PATH).read_text(encoding="utf-8"))
    if document.get("schema_version") != 1:
        raise ValueError("unsupported geometry approval schema")
    return list(document["approvals"])


def find_approval(
    approvals: list[dict[str, object]],
    pair: dict[str, object],
    rtf_table: str,
    html_table: str,
) -> dict[str, object]:
    spec: PairSpec = pair["spec"]  # type: ignore[assignment]
    matches = [
        approval
        for approval in approvals
        if approval["pair"] == spec.key
        and approval["rtf_source"] == spec.rtf_source
        and approval["rtf_sha256"] == pair["rtf_sha256"]
        and approval["rtf_table"] == rtf_table
        and approval["html_source"] == spec.html_source
        and approval["html_sha256"] == pair["html_sha256"]
        and approval["html_table"] == html_table
        and approval["geometry_judgment"] == "equivalent"
        and approval["meaning_judgment"] == "same"
    ]
    if len(matches) != 1:
        raise ValueError(
            f"expected one source-hash-keyed approval for {rtf_table} ↔ "
            f"{html_table}, found {len(matches)}"
        )
    return matches[0]


def table_by_id(tables: list[TableRecord], identifier: str) -> TableRecord:
    matches = [table for table in tables if table.id == identifier]
    if len(matches) != 1:
        raise ValueError(f"expected one {identifier}, found {len(matches)}")
    return matches[0]


def index_from_id(identifier: str) -> int:
    return int(identifier.rsplit("-", 1)[1])


def nonempty_raw_cells(
    rows: tuple[tuple[RawCell, ...], ...]
) -> list[RawCell]:
    return [
        cell
        for row in rows
        for cell in row
        if normalize_cell_text(cell.text)
    ]


def geometry_cells(
    raw_rows: tuple[tuple[RawCell, ...], ...], html_table: dict
) -> tuple[GeometryCell, ...]:
    rtf_content = nonempty_raw_cells(raw_rows)
    html_content = [
        normalize_cell_text(cell["text"])
        for row in html_table["rows"]
        for cell in row
        if normalize_cell_text(cell["text"])
    ]
    if [normalize_cell_text(cell.text) for cell in rtf_content] != html_content:
        raise ValueError("RTF and HTML ordered non-empty cell text no longer aligns")

    content = iter(rtf_content)
    occupied: set[tuple[int, int]] = set()
    result = []
    for row_index, row in enumerate(html_table["rows"], 1):
        column = 1
        for cell_index, html_cell in enumerate(row, 1):
            width = html_cell["colspan"]
            while any(
                (row_index, candidate) in occupied
                for candidate in range(column, column + width)
            ):
                column += 1
            for covered_row in range(
                row_index, row_index + html_cell["rowspan"]
            ):
                for covered_column in range(column, column + width):
                    occupied.add((covered_row, covered_column))
            normalized = normalize_cell_text(html_cell["text"])
            source_cell = next(content) if normalized else None
            result.append(
                GeometryCell(
                    row=row_index,
                    column=column,
                    rowspan=html_cell["rowspan"],
                    colspan=width,
                    text=source_cell.text if source_cell else "",
                    rtf_row=source_cell.row if source_cell else None,
                    rtf_cell=source_cell.cell if source_cell else None,
                    html_row=row_index,
                    html_cell=cell_index,
                )
            )
            column += width
    try:
        next(content)
    except StopIteration:
        pass
    else:
        raise ValueError("not all RTF content cells were placed")
    return tuple(result)


def omit_fully_empty_trailing_rows(table: dict) -> tuple[dict, int]:
    """Omit unspanned blank bottom rows explicitly approved as meaningless."""

    rows = list(table["rows"])
    removed = 0
    while rows and all(not normalize_cell_text(cell["text"]) for cell in rows[-1]):
        final_index = len(rows) - 1
        covered_from_above = any(
            row_index + cell["rowspan"] - 1 >= final_index
            for row_index, row in enumerate(rows[:-1])
            for cell in row
        )
        if covered_from_above:
            break
        rows.pop()
        removed += 1
    return table | {"rows": rows}, removed


def build_geometry_model(
    pair: dict[str, object],
    *,
    key: str,
    title: str,
    rtf_id: str,
    html_id: str,
    evidence_class: str,
    rendering: str,
    approvals: list[dict[str, object]],
    variant_group: str | None = None,
    variant_label: str | None = None,
) -> TableModel:
    rtf_tables: list[TableRecord] = pair["rtf_tables"]  # type: ignore[assignment]
    html_tables: list[TableRecord] = pair["html_tables"]  # type: ignore[assignment]
    raw_tables = pair["raw_rtf_tables"]
    raw_html = pair["html_raw"]
    matches = pair["matches"]
    spec: PairSpec = pair["spec"]  # type: ignore[assignment]
    rtf_record = table_by_id(rtf_tables, rtf_id)
    html_record = table_by_id(html_tables, html_id)
    html_table = raw_html[index_from_id(html_id) - 1]
    match = matches[rtf_id]

    approval_record = None
    geometry_adjustments: tuple[str, ...] = ()
    if evidence_class == "strict":
        if match["status"] != "matched" or match["html_candidates"] != [html_id]:
            raise ValueError(f"{rtf_id} ↔ {html_id} is no longer a strict match")
        if tuple(rtf_record.rows) != html_structural_rows(html_table):
            raise ValueError("strict structured rows changed after matching")
    elif evidence_class == "human-reviewed":
        if match["status"] != "divergent" or match["html_candidates"] != [html_id]:
            raise ValueError(f"{rtf_id} ↔ {html_id} is no longer divergent")
        approval = find_approval(approvals, pair, rtf_id, html_id)
        approval_record = str(approval["review_record"])
        if "fully-empty-bottom-row" in approval.get("ignorable_geometry", []):
            html_table, removed = omit_fully_empty_trailing_rows(html_table)
            if removed == 0:
                raise ValueError(
                    "approved fully empty bottom row is no longer present"
                )
            geometry_adjustments = (
                f"omitted {removed} fully empty trailing HTML row approved "
                "as non-meaningful",
            )
    elif evidence_class == "competing-variant":
        if match["status"] != "ambiguous" or html_id not in match["html_candidates"]:
            raise ValueError(f"{rtf_id} ↔ {html_id} is not an ambiguous candidate")
        if not variant_group or not variant_label:
            raise ValueError("competing variants require group and label")
    else:
        raise ValueError(f"unsupported geometry evidence class {evidence_class}")

    raw_rows = raw_tables[rtf_record.index - 1]
    cells = geometry_cells(raw_rows, html_table)
    geometry = table_geometry(html_table)
    if rendering == "gfm" and any(
        cell.rowspan != 1 or cell.colspan != 1 for cell in cells
    ):
        raise ValueError("GFM rendering cannot represent merged geometry")
    warning = {
        "strict": "Strict evidence still requires human review before promotion.",
        "human-reviewed": (
            "Diagnostic status remains divergent; HTML geometry is used only "
            "under the source-hash-keyed human approval."
        ),
        "competing-variant": (
            "Competing alternative only; no pairing has been selected or approved."
        ),
    }[evidence_class]
    return TableModel(
        key=key,
        title=title,
        evidence_class=evidence_class,
        diagnostic_status=str(match["status"]),
        rendering=rendering,
        pair=spec.key,
        rtf_source=spec.rtf_source,
        rtf_sha256=str(pair["rtf_sha256"]),
        rtf_table=rtf_id,
        rtf_source_start=int(rtf_record.context["source_start"]),
        rtf_source_end=int(rtf_record.context["source_end"]),
        html_source=spec.html_source,
        html_sha256=str(pair["html_sha256"]),
        html_table=html_id,
        logical_columns=geometry["logical_columns"],
        cells=cells,
        fallback_rows=(),
        warning=warning,
        geometry_adjustments=geometry_adjustments,
        approval_record=approval_record,
        variant_group=variant_group,
        variant_label=variant_label,
    )


def build_fallback_model(
    pair: dict[str, object], *, key: str, title: str, rtf_id: str
) -> TableModel:
    spec: PairSpec = pair["spec"]  # type: ignore[assignment]
    rtf_tables: list[TableRecord] = pair["rtf_tables"]  # type: ignore[assignment]
    record = table_by_id(rtf_tables, rtf_id)
    match = pair["matches"][rtf_id]
    if match["status"] != "unmatched" or match["html_candidates"]:
        raise ValueError(f"{rtf_id} is no longer an unmatched fallback")
    raw_rows = pair["raw_rtf_tables"][record.index - 1]
    return TableModel(
        key=key,
        title=title,
        evidence_class="unresolved-fallback",
        diagnostic_status="unmatched",
        rendering="rtf-token-list",
        pair=spec.key,
        rtf_source=spec.rtf_source,
        rtf_sha256=str(pair["rtf_sha256"]),
        rtf_table=rtf_id,
        rtf_source_start=int(record.context["source_start"]),
        rtf_source_end=int(record.context["source_end"]),
        html_source=None,
        html_sha256=None,
        html_table=None,
        logical_columns=None,
        cells=(),
        fallback_rows=raw_rows,
        warning=(
            "No evidence-supported HTML counterpart exists; cell geometry is "
            "deliberately not inferred."
        ),
        geometry_adjustments=(),
    )


def escape_text(value: str, *, gfm: bool = False) -> str:
    parts = BREAK.split(value)
    while parts and not parts[0].strip():
        parts.pop(0)
    while parts and not parts[-1].strip():
        parts.pop()
    escaped = [html.escape(part, quote=False) for part in parts]
    if gfm:
        escaped = [part.replace("|", "\\|") for part in escaped]
    return "<br>".join(escaped)


def cells_by_row(model: TableModel) -> list[list[GeometryCell]]:
    rows: dict[int, list[GeometryCell]] = {}
    for cell in model.cells:
        rows.setdefault(cell.row, []).append(cell)
    return [sorted(rows[index], key=lambda cell: cell.column) for index in sorted(rows)]


def render_gfm(model: TableModel, *, centered: bool = False) -> str:
    rows = cells_by_row(model)
    if not rows or any(len(row) != model.logical_columns for row in rows):
        raise ValueError("GFM table is not rectangular")
    rendered = [
        "| " + " | ".join(escape_text(cell.text, gfm=True) for cell in row) + " |"
        for row in rows
    ]
    marker = ":---:" if centered else "---"
    separator = "| " + " | ".join(
        marker for _ in range(model.logical_columns or 0)
    ) + " |"
    return "\n".join([rendered[0], separator, *rendered[1:]])


def render_html(model: TableModel) -> str:
    lines = ["<table>", "  <tbody>"]
    for row in cells_by_row(model):
        lines.append("    <tr>")
        for cell in row:
            attrs = "".join(
                f' {name}="{getattr(cell, name)}"'
                for name in ("rowspan", "colspan")
                if getattr(cell, name) > 1
            )
            lines.append(f"      <td{attrs}>{escape_text(cell.text)}</td>")
        lines.append("    </tr>")
    lines.extend(["  </tbody>", "</table>"])
    return "\n".join(lines)


def render_fallback(model: TableModel) -> str:
    lines = []
    for row_index, row in enumerate(model.fallback_rows, 1):
        lines.append(f"### RTF row {row_index}")
        lines.append("")
        for cell_index, cell in enumerate(row, 1):
            value = escape_text(cell.text, gfm=True) or "*(empty token)*"
            lines.append(f"- Cell {cell_index}: {value}")
        lines.append("")
    return "\n".join(lines).rstrip()


def provenance(model: TableModel) -> str:
    lines = [
        f"- Evidence class: `{model.evidence_class}`",
        f"- Diagnostic status: `{model.diagnostic_status}`",
        f"- RTF: `{model.rtf_source}` · `{model.rtf_table}` · "
        f"bytes `{model.rtf_source_start}..{model.rtf_source_end}`",
        f"- RTF SHA-256: `{model.rtf_sha256}`",
    ]
    if model.html_source:
        lines.extend(
            [
                f"- HTML: `{model.html_source}` · `{model.html_table}`",
                f"- HTML SHA-256: `{model.html_sha256}`",
                f"- Rendering: `{model.rendering}` · logical columns: "
                f"`{model.logical_columns}`",
            ]
        )
    else:
        lines.append("- HTML geometry: deliberately absent")
    if model.approval_record:
        lines.append(f"- Human geometry approval: `{model.approval_record}`")
    for adjustment in model.geometry_adjustments:
        lines.append(f"- Reviewed geometry adjustment: {adjustment}")
    if model.variant_group:
        lines.append(
            f"- Competing set: `{model.variant_group}` · alternative "
            f"`{model.variant_label}`"
        )
    return "\n".join(lines)


def render_document(title: str, models: list[TableModel], notice: str) -> str:
    lines = [
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        "status: pilot-needs-human-review",
        "generated_by: system/migration/tools/build_geometry_pilots.py",
        "---",
        "",
        "<!-- Review-only migration output. Not an approved partnership agreement. -->",
        "",
        f"# {title}",
        "",
        f"> **Review-only:** {notice}",
        "",
    ]
    for model in models:
        lines.extend(
            [
                f"## {model.title}",
                "",
                f"> **{model.evidence_class}:** {model.warning}",
                "",
                provenance(model),
                "",
            ]
        )
        if model.rendering == "gfm":
            lines.append(render_gfm(model))
        elif model.rendering == "html":
            lines.append(render_html(model))
        else:
            lines.append(render_fallback(model))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def manifest_table(model: TableModel) -> dict[str, object]:
    result = asdict(model)
    result.pop("cells")
    result.pop("fallback_rows")
    result["geometry_cell_count"] = len(model.cells)
    result["fallback_token_count"] = sum(len(row) for row in model.fallback_rows)
    return result


def selected_models(
    repository_root: Path,
) -> tuple[dict[str, list[TableModel]], dict[str, dict[str, object]]]:
    pairs = {key: load_pair(repository_root, spec) for key, spec in PAIRS.items()}
    approvals = load_approvals(repository_root)
    documents: dict[str, list[TableModel]] = {
        "strict-unmerged.md": [
            build_geometry_model(
                pairs["Articles"],
                key="strict-articles-0005",
                title="Strict unmerged example — System ON",
                rtf_id="rtf-table-0005",
                html_id="html-table-0005",
                evidence_class="strict",
                rendering="gfm",
                approvals=approvals,
            )
        ],
        "strict-merged.md": [
            build_geometry_model(
                pairs["ns"],
                key="strict-ns-0013",
                title="Strict merged example — development after 1♣–1♦–2♠",
                rtf_id="rtf-table-0013",
                html_id="html-table-0013",
                evidence_class="strict",
                rendering="html",
                approvals=approvals,
            )
        ],
        "human-reviewed-gazilli.md": [
            build_geometry_model(
                pairs["Articles"],
                key="reviewed-articles-0019-0020",
                title="Human-reviewed divergent example — rejected Gazilli",
                rtf_id="rtf-table-0019",
                html_id="html-table-0020",
                evidence_class="human-reviewed",
                rendering="html",
                approvals=approvals,
            )
        ],
        "competing-gazilli-mapping-a.md": [
            build_geometry_model(
                pairs["ns"],
                key="gazilli-a-0039-0042",
                title="Mapping A, pair 1",
                rtf_id="rtf-table-0039",
                html_id="html-table-0042",
                evidence_class="competing-variant",
                rendering="html",
                approvals=approvals,
                variant_group="ns-gazilli-duplicate-collision",
                variant_label="A",
            ),
            build_geometry_model(
                pairs["ns"],
                key="gazilli-a-0044-0047",
                title="Mapping A, pair 2",
                rtf_id="rtf-table-0044",
                html_id="html-table-0047",
                evidence_class="competing-variant",
                rendering="html",
                approvals=approvals,
                variant_group="ns-gazilli-duplicate-collision",
                variant_label="A",
            ),
        ],
        "competing-gazilli-mapping-b.md": [
            build_geometry_model(
                pairs["ns"],
                key="gazilli-b-0039-0047",
                title="Mapping B, pair 1",
                rtf_id="rtf-table-0039",
                html_id="html-table-0047",
                evidence_class="competing-variant",
                rendering="html",
                approvals=approvals,
                variant_group="ns-gazilli-duplicate-collision",
                variant_label="B",
            ),
            build_geometry_model(
                pairs["ns"],
                key="gazilli-b-0044-0042",
                title="Mapping B, pair 2",
                rtf_id="rtf-table-0044",
                html_id="html-table-0042",
                evidence_class="competing-variant",
                rendering="html",
                approvals=approvals,
                variant_group="ns-gazilli-duplicate-collision",
                variant_label="B",
            ),
        ],
        "unmatched-fallback.md": [
            build_fallback_model(
                pairs["ns"],
                key="fallback-ns-0003",
                title="Unmatched fallback — forcing-pass scale",
                rtf_id="rtf-table-0003",
            )
        ],
    }
    return documents, pairs


def report_text(summary: dict[str, int]) -> str:
    return f"""# Phase 3 geometry-aware pilot report

This limited pilot uses RTF wording and provenance with HTML geometry only at
the evidence levels stated in `manifest.json`. Nothing here is an approved
partnership agreement.

## Generated evidence classes

| Evidence class | Generated tables |
|---|---:|
| Strict | {summary.get('strict', 0)} |
| Human-reviewed divergent | {summary.get('human-reviewed', 0)} |
| Competing variant | {summary.get('competing-variant', 0)} |
| Unresolved fallback | {summary.get('unresolved-fallback', 0)} |

The sample demonstrates GFM for a rectangular unmerged table, minimal HTML for
merged geometry, a hash-keyed human approval that does not erase the original
`divergent` diagnosis, both complete mappings for the unresolved 2×2 collision,
and abstention from HTML geometry for an unmatched RTF table.

## Review boundaries

- RTF supplies the displayed wording and byte-offset provenance.
- HTML supplies only validated `rowspan`/`colspan` geometry.
- The reviewed Gazilli draft omits its fully empty bottom HTML row, which Archy
  explicitly judged non-meaningful; the manifest records that adjustment.
- Competing drafts are alternatives, not agreements; neither mapping is chosen.
- The fallback is a row/cell token list because its geometry is unresolved.
- Minimal HTML contains no Word classes, styles, scripts, or `mso-*` baggage.
- A later human review may redraw tables for clearer bridge meaning.

## Reproduction

```bash
python3 system/migration/tools/build_geometry_pilots.py \\
  --output-dir system/migration/pilots/geometry-aware
python3 system/migration/tools/build_geometry_pilots.py \\
  --output-dir system/migration/pilots/geometry-aware --check
python3 -m unittest discover -s system/migration/tests -v
```

## Open issue

The duplicate-spade Gazilli pairing remains unresolved. The two generated
mapping documents are intentionally textually similar because the duplicated
source tables are themselves identical; their distinct value is provenance,
not invented semantic difference.
"""


def readme_text() -> str:
    return """# Geometry-aware Markdown pilots

These files are deterministic review drafts, not approved agreements:

- [`strict-unmerged.md`](strict-unmerged.md)
- [`strict-merged.md`](strict-merged.md)
- [`human-reviewed-gazilli.md`](human-reviewed-gazilli.md)
- [`competing-gazilli-mapping-a.md`](competing-gazilli-mapping-a.md)
- [`competing-gazilli-mapping-b.md`](competing-gazilli-mapping-b.md)
- [`unmatched-fallback.md`](unmatched-fallback.md)
- [`manifest.json`](manifest.json)
- [`REPORT.md`](REPORT.md)

The competing Gazilli files are mutually exclusive provenance alternatives.
Neither is selected. See the manifest for hashes, source IDs, diagnostic
statuses, and warnings.
"""


def build_outputs(repository_root: Path) -> dict[Path, str]:
    documents, _ = selected_models(repository_root)
    notices = {
        "strict-unmerged.md": "Strict unique match rendered as a simple GFM table.",
        "strict-merged.md": "Strict unique match rendered with minimal HTML spans.",
        "human-reviewed-gazilli.md": (
            "HTML geometry is used under an explicit hash-keyed human approval; "
            "the diagnostic status remains divergent."
        ),
        "competing-gazilli-mapping-a.md": (
            "Competing Mapping A. Do not promote unless a human selects it."
        ),
        "competing-gazilli-mapping-b.md": (
            "Competing Mapping B. Do not promote unless a human selects it."
        ),
        "unmatched-fallback.md": (
            "No HTML geometry is used; this is an RTF token fallback."
        ),
    }
    outputs = {
        Path(filename): render_document(
            models[0].title if len(models) == 1 else filename.removesuffix(".md"),
            models,
            notices[filename],
        )
        for filename, models in documents.items()
    }
    all_models = [model for models in documents.values() for model in models]
    summary = {
        evidence_class: sum(
            model.evidence_class == evidence_class for model in all_models
        )
        for evidence_class in (
            "strict",
            "human-reviewed",
            "competing-variant",
            "unresolved-fallback",
        )
    }
    manifest = {
        "schema_version": 1,
        "status": "pilot-needs-human-review",
        "generator": "system/migration/tools/build_geometry_pilots.py",
        "summary": summary,
        "outputs": [
            {
                "output": filename,
                "generated_sha256": sha256_text(outputs[Path(filename)]),
                "tables": [manifest_table(model) for model in models],
            }
            for filename, models in documents.items()
        ],
    }
    outputs[Path("manifest.json")] = (
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    )
    outputs[Path("REPORT.md")] = report_text(summary)
    outputs[Path("README.md")] = readme_text()
    return outputs


def validate_output_dir(repository_root: Path, output_dir: Path) -> None:
    resolved = output_dir.resolve()
    protected_trees = [
        (repository_root / "system" / "agreements").resolve(),
        (repository_root / "system" / "legacy").resolve(),
    ]
    if resolved == repository_root.resolve():
        raise ValueError(f"refusing repository root as output directory: {output_dir}")
    for path in protected_trees:
        if resolved == path or path in resolved.parents:
            raise ValueError(f"refusing protected output directory: {output_dir}")


def write_outputs(output_dir: Path, outputs: dict[Path, str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for relative, content in outputs.items():
        path = output_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def check_outputs(output_dir: Path, outputs: dict[Path, str]) -> list[Path]:
    return [
        output_dir / relative
        for relative, expected in outputs.items()
        if not (output_dir / relative).exists()
        or (output_dir / relative).read_text(encoding="utf-8") != expected
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="explicit review-output directory; legacy and agreements are refused",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if the explicit output directory differs from a fresh build",
    )
    args = parser.parse_args()
    try:
        validate_output_dir(REPOSITORY_ROOT, args.output_dir)
        outputs = build_outputs(REPOSITORY_ROOT)
    except ValueError as error:
        parser.error(str(error))
    if args.check:
        differences = check_outputs(args.output_dir, outputs)
        for path in differences:
            print(f"DIFFERS: {path}")
        return 1 if differences else 0
    write_outputs(args.output_dir, outputs)
    for path in outputs:
        print(args.output_dir / path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
