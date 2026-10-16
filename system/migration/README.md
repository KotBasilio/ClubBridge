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

See [source-assessment.md](source-assessment.md) for the first reproducible
structural reading of the two documents and the proposed pilot areas.

Pilot sections and their review records live in [`pilots/`](pilots/README.md).
Build source baselines with `tools/build_pilot_notes.py`, always supplying an
explicit `--output-dir`. Approved notes are promoted to `system/agreements/`
and deliberately detached from regeneration. Their source ranges, generated
hashes, and review records are collected in
[`approved-manifest.json`](approved-manifest.json).

## Human Review

Source documents have no automatic precedence over one another. Record any
disagreement in [pending-updates/conflicts.md](pending-updates/conflicts.md).
