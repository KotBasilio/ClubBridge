# Migration Workspace

This directory holds provisional tools and review surfaces for converting the
legacy partnership documents. It does not define a permanent migration policy.
The source material may teach us to change the approach.

## RTF Inventory Tool

`tools/rtf_inventory.py` performs a read-only structural extraction. It:

- fingerprints each source with SHA-256;
- decodes font-specific character sets, including Word RTF whose document
  header says Windows-1252 while Russian runs use Windows-1251 fonts;
- preserves the Adobe Symbol glyphs used for suits, arrows, and notation, and
  the known Wingdings check-mark, arrowhead, and smiley glyphs in these sources,
  including `SYMBOL` fields with empty fallback results;
- extracts paragraphs, outline headings, explicit page-break regions, tables,
  and source byte offsets;
- reports fields, lists, bookmarks, hyperlinks, and embedded-object counts;
- writes UTF-8 JSON and inspection text when an output directory is requested.

Run it from the repository root:

```sh
python3 system/migration/tools/rtf_inventory.py \
  --output-dir /tmp/clubbridge-rtf-inventory \
  system/legacy/Articles_25_09.rtf \
  system/legacy/ns25_09.rtf
```

Run the regression tests with:

```sh
python3 -m unittest discover -s system/migration/tests -v
```

The output is evidence for planning and review, not converted partnership
authority. Explicit page-break regions are not guaranteed to equal rendered
page numbers. The tool does not yet preserve visual layout, formatting spans,
merged table cells, color meaning, or final Markdown note boundaries.

## HTML Table Probe

`tools/html_table_probe.py` inspects the Word-exported HTML companions without
changing them. It reports physical and logical table geometry, conventional
`rowspan`/`colspan` merges, nesting, malformed structures, encoding, and bridge
suit-symbol counts. Optional JSON and clean HTML witnesses are written only
when their output paths are supplied:

```sh
python3 system/migration/tools/html_table_probe.py \
  --output /tmp/clubbridge-html-report.json \
  --samples-dir /tmp/clubbridge-html-samples \
  --sample-limit 13
```

The witnesses deliberately omit Word classes, styles, scripts, and other
presentation baggage. They are diagnostic geometry evidence, not approved
agreement text. See
[`pilots/html-table-probe-report.md`](pilots/html-table-probe-report.md) for
the validation findings and the proposed dual-source boundary.

## Geometry-Aware Pilot Generator

`tools/build_geometry_pilots.py` produces a deliberately small set of
review-only Markdown examples. RTF supplies wording and byte-offset provenance;
HTML supplies geometry only for strict unique matches, explicitly approved
hash-bound divergences, or clearly labeled competing alternatives. Unmatched
tables receive a geometry-free RTF token fallback.

Human geometry approvals live in [`geometry-approvals.json`](geometry-approvals.json)
and are keyed by both source hashes and both table IDs. They authorize a review
draft; they do not alter matcher diagnostics or promote an agreement.

```sh
python3 system/migration/tools/build_geometry_pilots.py \
  --output-dir system/migration/pilots/geometry-aware
python3 system/migration/tools/build_geometry_pilots.py \
  --output-dir system/migration/pilots/geometry-aware --check
```

The explicit output directory is mandatory. The generator refuses the legacy
and approved-agreement trees. See the checked-in
[`geometry-aware/`](pilots/geometry-aware/README.md) sample and manifest.

See [source-assessment.md](source-assessment.md) for the first reproducible
structural reading of the two documents and the proposed pilot areas.
The consolidated source-outline transition checklist is
[`transition-plan.md`](transition-plan.md).

Pilot sections and their review records live in [`pilots/`](pilots/README.md).
Build source baselines with `tools/build_pilot_notes.py`, always supplying an
explicit `--output-dir`. Approved notes are promoted to `system/agreements/`
and deliberately detached from regeneration. Their source ranges, generated
hashes, and review records are collected in
[`approved-manifest.json`](approved-manifest.json).

## Human Review

Source documents have no automatic precedence over one another. Record any
disagreement in [pending-updates/conflicts.md](pending-updates/conflicts.md).

When a source structure permits several genuinely plausible conversions,
review tooling may emit all useful alternatives. Each alternative must remain
clearly labeled, traceable to its source hashes and table IDs, and outside
`system/agreements/` until a human selects it. An unresolved alternative is not
an agreement and must not be chosen by heading, ordinal, or apparent
conventional wisdom.

The migration target is the partnership system's meaning, not a facsimile of
incidental Word formatting. Validated HTML geometry may clarify merged tables;
after enough surrounding text is understood, a table may instead be redrawn
for semantic clarity through an explicit review step.

Completed migration tickets are retained in [`history/`](history/README.md).
