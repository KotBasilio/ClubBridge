#!/usr/bin/env python3
"""Build the static Phase 2.5 RTF/HTML table visual review pack."""
from __future__ import annotations

import argparse
import hashlib
import html
from pathlib import Path

from html_table_probe import TableProbe, detect_encoding, table_geometry
from match_rtf_html_tables import (
    extract_html_tables,
    extract_rtf_tables,
    normalize_cell_text,
)
from rtf_inventory import DocumentInventory, parse_rtf


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LEGACY_DIR = REPOSITORY_ROOT / "system" / "legacy"
DEFAULT_OUTPUT_DIR = REPOSITORY_ROOT / "system" / "migration" / "pilots" / "visual-review"

CASES = (
    {
        "number": 1,
        "slug": "case-1-ns-convention-card",
        "title": "NS convention card: large structural divergence",
        "source": "ns25_09",
        "rtf": (5,),
        "html": (5,),
        "kind": "divergent",
    },
    {
        "number": 2,
        "slug": "case-2-articles-gazilli",
        "title": "Articles Gazilli: one-row structural divergence",
        "source": "Articles_25_09",
        "rtf": (19,),
        "html": (20,),
        "kind": "divergent",
    },
    {
        "number": 3,
        "slug": "case-3-ns-duplicate-collision",
        "title": "NS Gazilli: genuine duplicate collision",
        "source": "ns25_09",
        "rtf": (39, 44),
        "html": (42, 47),
        "kind": "collision",
    },
)

CSS = """
:root { color-scheme: light; --ink:#1e293b; --muted:#64748b; --line:#cbd5e1;
  --paper:#f8fafc; --rtf:#fff7ed; --html:#eff6ff; --warn:#fff1f2; }
* { box-sizing: border-box; }
body { margin:0; color:var(--ink); background:#e2e8f0;
  font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; }
main { max-width:1600px; margin:auto; padding:24px; background:white; min-height:100vh; }
h1,h2,h3 { line-height:1.15; }
a { color:#075985; }
.lede,.note,.context,.prompt,.finding { border:1px solid var(--line); border-radius:10px;
  padding:12px 14px; margin:12px 0; background:var(--paper); }
.warning { background:var(--warn); border-color:#fda4af; }
.meta { display:grid; grid-template-columns:max-content 1fr; gap:4px 12px; }
.hash { font:12px/1.35 ui-monospace,SFMono-Regular,Consolas,monospace; overflow-wrap:anywhere; }
.comparison { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr);
  gap:18px; align-items:start; }
.pane { min-width:0; border:2px solid var(--line); border-radius:12px; padding:12px; overflow:auto; }
.rtf { background:var(--rtf); border-color:#fdba74; }
.html { background:var(--html); border-color:#93c5fd; }
.label { text-transform:uppercase; letter-spacing:.08em; font-size:12px; font-weight:800; }
.row-strip { display:grid; grid-template-columns:3.4em 1fr; gap:7px; margin:7px 0; align-items:stretch; }
.row-id { font:12px ui-monospace,SFMono-Regular,Consolas,monospace; color:var(--muted); padding-top:8px; }
.tokens { display:flex; flex-wrap:wrap; gap:5px; }
.token { min-width:78px; max-width:100%; border:1px solid #d6a76d; border-radius:7px;
  padding:7px; background:white; overflow-wrap:anywhere; white-space:pre-wrap; }
.empty { color:var(--muted); font-style:italic; background:#f1f5f9; }
.badge { display:inline-block; margin:0 5px 3px 0; border-radius:999px; padding:1px 6px;
  background:#334155; color:white; font:11px ui-monospace,SFMono-Regular,Consolas,monospace; }
.geometry { border-collapse:separate; border-spacing:3px; width:100%; table-layout:auto; }
.geometry th,.geometry td { border:1px solid #60a5fa; border-radius:5px; padding:7px;
  min-width:74px; background:white; vertical-align:top; overflow-wrap:anywhere; white-space:pre-wrap; }
.geometry .empty { background:#e2e8f0; }
.row-head { min-width:3.4em !important; color:var(--muted); font:12px ui-monospace,SFMono-Regular,Consolas,monospace; }
.span { display:block; color:#1d4ed8; font:11px ui-monospace,SFMono-Regular,Consolas,monospace; }
.context-grid,.four-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
.choice { display:inline-block; border:1px solid #94a3b8; border-radius:999px; padding:4px 9px;
  margin:3px 5px 3px 0; background:white; }
.map { display:grid; grid-template-columns:1fr auto 1fr; gap:8px; align-items:center;
  padding:7px; margin:7px 0; border:1px solid var(--line); border-radius:8px; }
.arrow { color:var(--muted); font-weight:bold; }
.legend { color:var(--muted); font-size:13px; }
code { font-family:ui-monospace,SFMono-Regular,Consolas,monospace; }
@media (max-width:900px) { .comparison,.context-grid,.four-grid { grid-template-columns:1fr; } }
@media print { body { background:white; } main { max-width:none; padding:10px; }
  .comparison { grid-template-columns:1fr 1fr; } a { color:inherit; } }
"""


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_source(legacy_dir: Path, stem: str) -> dict:
    rtf_path = legacy_dir / f"{stem}.rtf"
    html_path = legacy_dir / f"{stem}.htm"
    inventory = parse_rtf(rtf_path)
    source = html_path.read_bytes()
    encoding, _ = detect_encoding(source, html_path)
    parser = TableProbe()
    parser.feed(source.decode(encoding))
    parser.finish()
    return {
        "stem": stem,
        "rtf_path": rtf_path,
        "html_path": html_path,
        "inventory": inventory,
        "rtf_records": extract_rtf_tables(inventory),
        "html_records": extract_html_tables(parser),
        "html_raw": parser.tables,
        "rtf_hash": sha256(rtf_path),
        "html_hash": sha256(html_path),
    }


def nonempty_positions(rows) -> list[tuple[int, int, str]]:
    return [
        (row_index, cell_index, cell)
        for row_index, row in enumerate(rows, 1)
        for cell_index, cell in enumerate(row, 1)
        if cell
    ]


def raw_html_positions(table: dict) -> list[tuple[int, int, str]]:
    return [
        (row_index, cell_index, normalize_cell_text(cell["text"]))
        for row_index, row in enumerate(table["rows"], 1)
        for cell_index, cell in enumerate(row, 1)
        if normalize_cell_text(cell["text"])
    ]


def assert_same_content(rtf_record, html_table: dict) -> None:
    rtf_text = [text for _, _, text in nonempty_positions(rtf_record.rows)]
    html_text = [text for _, _, text in raw_html_positions(html_table)]
    if rtf_text != html_text:
        raise ValueError(
            f"{rtf_record.id} and html-table-{html_table['index']:04d} "
            "no longer share ordered non-empty content"
        )


def sequence_lookup(rows) -> dict[tuple[int, int], int]:
    result = {}
    sequence = 0
    for row_index, row in enumerate(rows, 1):
        for cell_index, cell in enumerate(row, 1):
            if cell:
                sequence += 1
                result[(row_index, cell_index)] = sequence
    return result


def render_rtf(record) -> str:
    lookup = sequence_lookup(record.rows)
    rendered_rows = []
    for row_index, row in enumerate(record.rows, 1):
        cells = []
        for cell_index, text in enumerate(row, 1):
            if text:
                badge = f'<span class="badge">T{lookup[(row_index, cell_index)]:02d}</span>'
                cells.append(f'<div class="token">{badge}{esc(text)}</div>')
            else:
                cells.append('<div class="token empty">∅ empty token</div>')
        rendered_rows.append(
            f'<div class="row-strip"><div class="row-id">R{row_index:02d}</div>'
            f'<div class="tokens">{"".join(cells)}</div></div>'
        )
    return "".join(rendered_rows)


def render_html_table(table: dict) -> str:
    normalized_rows = tuple(
        tuple(normalize_cell_text(cell["text"]) for cell in row)
        for row in table["rows"]
    )
    lookup = sequence_lookup(normalized_rows)
    rendered_rows = []
    for row_index, row in enumerate(table["rows"], 1):
        cells = []
        for cell_index, cell in enumerate(row, 1):
            text = normalize_cell_text(cell["text"])
            attrs = "".join(
                f' {name}="{cell[name]}"'
                for name in ("rowspan", "colspan")
                if cell[name] > 1
            )
            badge = (
                f'<span class="badge">T{lookup[(row_index, cell_index)]:02d}</span>'
                if text
                else ""
            )
            span = (
                f'<span class="span">rowspan={cell["rowspan"]}, '
                f'colspan={cell["colspan"]}</span>'
                if cell["rowspan"] > 1 or cell["colspan"] > 1
                else ""
            )
            class_name = ' class="empty"' if not text else ""
            content = f"{badge}{esc(text) if text else '∅ empty physical cell'}{span}"
            cells.append(f"<td{attrs}{class_name}>{content}</td>")
        rendered_rows.append(
            f'<tr><th class="row-head">H{row_index:02d}</th>{"".join(cells)}</tr>'
        )
    return f'<table class="geometry"><tbody>{"".join(rendered_rows)}</tbody></table>'


def rtf_local_context(inventory: DocumentInventory, record) -> dict[str, list[str]]:
    paragraphs = inventory.paragraphs
    start = next(
        i for i, paragraph in enumerate(paragraphs)
        if paragraph.source_start == record.context["source_start"]
    )
    end = next(
        i for i, paragraph in enumerate(paragraphs)
        if paragraph.source_end == record.context["source_end"]
    )
    before = [p.text for p in paragraphs[max(0, start - 3):start] if not p.in_table]
    after = [p.text for p in paragraphs[end + 1:end + 4] if not p.in_table]
    return {"before": before, "after": after}


def render_context(title: str, heading: str, before: list[str], after: list[str]) -> str:
    def items(values):
        return "".join(f"<li>{esc(value)}</li>" for value in values) or "<li>None captured</li>"
    return (
        f'<section class="context"><h3>{esc(title)}</h3>'
        f'<p><strong>Nearest heading:</strong> {esc(heading or "None captured")}</p>'
        f'<p><strong>Immediately before:</strong></p><ul>{items(before)}</ul>'
        f'<p><strong>Immediately after:</strong></p><ul>{items(after)}</ul></section>'
    )


def render_html_neighbor_context(bundle: dict, index: int) -> str:
    records = bundle["html_records"]
    current = records[index - 1]
    before = records[index - 2:index - 1] if index > 1 else []
    after = records[index:index + 1]
    return render_context(
        current.id,
        str(current.context["heading"]),
        [f'{item.id}: {item.context["sample"]}' for item in before],
        [f'{item.id}: {item.context["sample"]}' for item in after],
    )


def structural_findings(rtf_record, html_record, html_table: dict) -> list[str]:
    rtf_positions = nonempty_positions(rtf_record.rows)
    html_positions = raw_html_positions(html_table)
    shifted = [
        sequence
        for sequence, (rtf_cell, html_cell) in enumerate(
            zip(rtf_positions, html_positions), 1
        )
        if rtf_cell[:2] != html_cell[:2]
    ]
    geometry = table_geometry(html_table)
    cells = [cell for row in html_table["rows"] for cell in row]
    rtf_empty = sum(not cell for row in rtf_record.rows for cell in row)
    html_empty = sum(not normalize_cell_text(cell["text"]) for cell in cells)
    merged = sum(
        cell["rowspan"] > 1 or cell["colspan"] > 1 for cell in cells
    )
    if shifted:
        shift_text = (
            f"{len(shifted)} of {len(rtf_positions)} shared non-empty tokens occupy "
            f"different row/cell coordinates; first affected: "
            + ", ".join(f"T{value:02d}" for value in shifted[:8])
            + ("…" if len(shifted) > 8 else "")
        )
    else:
        shift_text = "All shared non-empty tokens occupy the same row/cell coordinates."
    return [
        f"RTF interpretation: {len(rtf_record.rows)} rows, "
        f"{sum(len(row) for row in rtf_record.rows)} tokens, {rtf_empty} empty tokens.",
        f"HTML export: {len(html_table['rows'])} rows, {len(cells)} physical cells, "
        f"{html_empty} empty physical cells, {geometry['logical_columns']} logical columns.",
        f"HTML explicitly contains {merged} merged cells; RTF merge geometry is unknown.",
        shift_text,
    ]


def metadata(bundle: dict, rtf_ids: str, html_ids: str) -> str:
    return f"""
<div class="meta">
  <strong>RTF source</strong><span>{esc(bundle['rtf_path'].name)} · {esc(rtf_ids)}</span>
  <strong>RTF SHA-256</strong><span class="hash">{bundle['rtf_hash']}</span>
  <strong>HTML source</strong><span>{esc(bundle['html_path'].name)} · {esc(html_ids)}</span>
  <strong>HTML SHA-256</strong><span class="hash">{bundle['html_hash']}</span>
</div>"""


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><style>{CSS}</style></head>
<body><main><p><a href="index.html">← Review-pack index</a></p>
{body}
<footer class="note"><strong>Limitation:</strong> the right pane renders the
Word-exported HTML geometry. It is not an independent rendering of the original
Word/RTF document. The left pane is the current parser's flattened interpretation,
not reconstructed merge geometry.</footer></main></body></html>
"""


def review_prompt() -> str:
    return """
<section class="prompt"><h2>Archy's judgment</h2>
<p><strong>Geometry:</strong>
<span class="choice">Equivalent geometry</span>
<span class="choice">Different geometry</span>
<span class="choice">Uncertain</span></p>
<p><strong>Meaning:</strong>
<span class="choice">Same bidding meaning</span>
<span class="choice">Different meaning</span>
<span class="choice">Uncertain</span></p>
<p>Record both choices plus any explanation in your review reply. Nothing on
this static page is submitted automatically.</p></section>"""


def render_divergent(case: dict, bundle: dict) -> str:
    rtf_record = bundle["rtf_records"][case["rtf"][0] - 1]
    html_record = bundle["html_records"][case["html"][0] - 1]
    html_table = bundle["html_raw"][case["html"][0] - 1]
    assert_same_content(rtf_record, html_table)
    findings = structural_findings(rtf_record, html_record, html_table)
    context = rtf_local_context(bundle["inventory"], rtf_record)
    body = f"""
<h1>Case {case['number']}: {esc(case['title'])}</h1>
<div class="lede"><strong>Status entering review:</strong> divergent. Ordered
non-empty cell wording is the same, but row/cell structure is not. This page
does not change that classification.</div>
{metadata(bundle, rtf_record.id, html_record.id)}
<section class="finding"><h2>Observed structural differences</h2><ul>
{''.join(f'<li>{esc(item)}</li>' for item in findings)}</ul></section>
<p class="legend">T-numbers identify the same ordered non-empty text on both
sides. ∅ identifies an empty token or physical cell; it receives no T-number.</p>
<div class="comparison">
  <section class="pane rtf"><div class="label">RTF-derived flattened interpretation</div>
    <h2>{esc(rtf_record.id)}</h2>{render_rtf(rtf_record)}</section>
  <section class="pane html"><div class="label">HTML-exported geometry</div>
    <h2>{esc(html_record.id)}</h2>{render_html_table(html_table)}</section>
</div>
<h2>Local context</h2><div class="context-grid">
{render_context(rtf_record.id, str(rtf_record.context['nearest_heading']), context['before'], context['after'])}
{render_html_neighbor_context(bundle, html_record.index)}
</div>{review_prompt()}"""
    return page(f"Case {case['number']} — {case['title']}", body)


def render_collision(case: dict, bundle: dict) -> str:
    rtfs = [bundle["rtf_records"][index - 1] for index in case["rtf"]]
    html_records = [bundle["html_records"][index - 1] for index in case["html"]]
    html_tables = [bundle["html_raw"][index - 1] for index in case["html"]]
    for rtf_record in rtfs:
        for html_table in html_tables:
            assert_same_content(rtf_record, html_table)
    rtf_contexts = [rtf_local_context(bundle["inventory"], item) for item in rtfs]
    body = f"""
<h1>Case {case['number']}: {esc(case['title'])}</h1>
<div class="lede warning"><strong>Status entering review:</strong> ambiguous.
Both RTF tables and both HTML tables have the same normalized structured
content. Ordinal and heading are navigation context only, not match evidence.</div>
{metadata(bundle, ', '.join(item.id for item in rtfs), ', '.join(item.id for item in html_records))}
<section class="finding"><h2>The two possible one-to-one mappings</h2>
<h3>Mapping A</h3>
<div class="map"><code>{rtfs[0].id}</code><span class="arrow">↔</span><code>{html_records[0].id}</code></div>
<div class="map"><code>{rtfs[1].id}</code><span class="arrow">↔</span><code>{html_records[1].id}</code></div>
<h3>Mapping B</h3>
<div class="map"><code>{rtfs[0].id}</code><span class="arrow">↔</span><code>{html_records[1].id}</code></div>
<div class="map"><code>{rtfs[1].id}</code><span class="arrow">↔</span><code>{html_records[0].id}</code></div>
<p><span class="choice">Mapping A</span><span class="choice">Mapping B</span>
<span class="choice">Evidence insufficient</span></p></section>
<p class="legend">All four diagrams deliberately retain their own identifiers.
Identical T-numbers show identical ordered non-empty content; they do not imply
a selected cross-source mapping.</p>
<h2>RTF candidates</h2><div class="four-grid">
{''.join(f'<section class="pane rtf"><div class="label">RTF-derived flattened interpretation</div><h3>{item.id}</h3>{render_rtf(item)}</section>' for item in rtfs)}
</div><h2>HTML candidates</h2><div class="four-grid">
{''.join(f'<section class="pane html"><div class="label">HTML-exported geometry</div><h3>{record.id}</h3>{render_html_table(table)}</section>' for record, table in zip(html_records, html_tables))}
</div><h2>Disambiguating local context</h2><div class="context-grid">
{''.join(render_context(item.id, str(item.context['nearest_heading']), context['before'], context['after']) for item, context in zip(rtfs, rtf_contexts))}
{''.join(render_html_neighbor_context(bundle, item.index) for item in html_records)}
</div><section class="prompt"><h2>Archy's judgment</h2>
<p>Choose <strong>Mapping A</strong>, <strong>Mapping B</strong>, or
<strong>Evidence insufficient</strong>. If choosing a mapping, also state
whether each pair has the same bidding meaning. Nothing is recorded automatically.</p></section>"""
    return page(f"Case {case['number']} — {case['title']}", body)


def render_index() -> str:
    cards = "".join(
        f'<li><a href="{case["slug"]}.html"><strong>Case {case["number"]}:</strong> '
        f'{esc(case["title"])}</a></li>'
        for case in CASES
    )
    body = f"""
<h1>Phase 2.5 — Table visual review pack</h1>
<div class="lede">Three diagnostic exceptions shown without changing matcher
classifications or creating overrides. Open each case, compare the two source
interpretations, and report the requested human judgment.</div>
<ol>{cards}</ol>
<section class="note"><h2>How to read the diagrams</h2><ul>
<li>The orange pane is the current RTF parser's row/token interpretation. It
does not claim rowspan or colspan knowledge.</li>
<li>The blue pane is clean geometry from Word-exported HTML. It uses real
<code>rowspan</code> and <code>colspan</code> attributes, without Word CSS.</li>
<li>Matching T-numbers identify the same ordered non-empty wording.</li>
<li>Within-cell whitespace and line breaks are normalized exactly as in the
matcher; wording, punctuation, and suit symbols are retained.</li>
<li>These HTML files contain inline CSS only: no scripts, external resources,
or network-dependent links.</li></ul></section>"""
    return page("Phase 2.5 — Table visual review pack", body)


def readme() -> str:
    return """# Phase 2.5 visual review pack

Open [`index.html`](index.html) in a browser. It links to:

1. [`case-1-ns-convention-card.html`](case-1-ns-convention-card.html) — large
   convention-card structural divergence;
2. [`case-2-articles-gazilli.html`](case-2-articles-gazilli.html) — compact
   Gazilli structural divergence;
3. [`case-3-ns-duplicate-collision.html`](case-3-ns-duplicate-collision.html) —
   the 2×2 duplicate collision with both possible pairings.

For cases 1 and 2, report one choice from each line:

- `Equivalent geometry / Different geometry / Uncertain`
- `Same bidding meaning / Different meaning / Uncertain`

For case 3, report `Mapping A`, `Mapping B`, or `Evidence insufficient`, plus
whether the paired tables have the same bidding meaning if you select a map.

The pages are static and self-contained. T-number badges connect identical
ordered non-empty wording across the RTF and HTML views. Empty RTF tokens do
not imply merge geometry. The rendered HTML export is geometry evidence, not
an independent rendering of the original Word/RTF document. Within-cell
whitespace and line breaks are normalized by the matcher; wording,
punctuation, and suit symbols are retained.

Regenerate from the repository root:

```bash
python3 system/migration/tools/build_table_visual_review.py
```
"""


def build(legacy_dir: Path, output_dir: Path) -> list[Path]:
    bundles = {
        stem: load_source(legacy_dir, stem)
        for stem in {str(case["source"]) for case in CASES}
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = []
    for case in CASES:
        bundle = bundles[str(case["source"])]
        rendered = (
            render_collision(case, bundle)
            if case["kind"] == "collision"
            else render_divergent(case, bundle)
        )
        path = output_dir / f'{case["slug"]}.html'
        path.write_text(rendered, encoding="utf-8")
        outputs.append(path)
    index = output_dir / "index.html"
    index.write_text(render_index(), encoding="utf-8")
    outputs.append(index)
    instructions = output_dir / "README.md"
    instructions.write_text(readme(), encoding="utf-8")
    outputs.append(instructions)
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-dir", type=Path, default=DEFAULT_LEGACY_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    for output in build(args.legacy_dir, args.output_dir):
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
