# HTML Table Probe — Diagnostic Report

Date: 2026-10-17

Branch: `tools/html-table-probe-vel`

## Scope and Boundary

This pass tested whether the Word-exported HTML companions preserve table
geometry well enough to support a conservative dual-source converter. The RTF
remains authoritative for agreement text and provenance. HTML is evaluated as
a possible source of table shape only. No approved agreement or legacy source
was changed.

The probe was run with:

```sh
python3 system/migration/tools/html_table_probe.py \
  --output /tmp/clubbridge-html-report.json \
  --samples-dir /tmp/clubbridge-html-samples \
  --sample-limit 13
```

## Source Inventory

| Source | SHA-256 | Declared encoding | Tables | Tables with merges |
| --- | --- | --- | ---: | ---: |
| `Articles_25_09.htm` | `63028359317a08b80b2c38fb6c804e82c1a16749124fa54a98a8db67b14b7502` | `windows-1252` | 60 | 30 |
| `ns25_09.htm` | `b9c6be73a5023e25c349fb9aa9c331ecbb498caeaca90f7041a5c93c625797b7` | `windows-1252` | 60 | 47 |

Both files declare their encoding in a `Content-Type` meta element. Russian
text and bridge suits are predominantly numeric character references, which
`HTMLParser` resolves after strict byte decoding.

## Confirmed Geometry Findings

The exports use conventional HTML span attributes for their merged cells:

| Source | Merged cells | `rowspan` cells | `colspan` cells | Tables with `rowspan` | Tables with `colspan` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `Articles_25_09.htm` | 113 | 33 | 80 | 17 | 25 |
| `ns25_09.htm` | 361 | 91 | 273 | 40 | 43 |

Across all 120 tables:

- every table is top-level; the real exports contain no nested tables;
- expanding `rowspan` and `colspan` produces a complete rectangular grid for
  every row;
- there are no invalid span values, malformed table structures, or rowspans
  extending beyond the final row;
- there are no `vmerge`, `hmerge`, or merge-specific `mso-*` hints;
- generic Word `mso-*` presentation styles are therefore not needed to recover
  merge geometry.

The old probe counted any `mso-*` style as a possible merge hint, which made
almost every Word cell look exceptional. The revised metric checks only
merge-specific tokens and reports zero in both real documents.

## Representative Tables

| Source / index | Nearby heading | Rows | Physical cells | Logical columns | Merged cells |
| --- | --- | ---: | ---: | ---: | ---: |
| Articles #1 | `«Косая система»` | 5 | 13 | 3 | 2 |
| Articles #22 | `Their strong club` | 2 | 4 | 2 | 0 |
| NS #2 | `Эволюция` | 11 | 44 | 4 | 0 |
| NS #5 | `Конвенционка` | 32 | 112 | 7 | 51 |
| NS #13 | `Минорные неравномеры` | 11 | 23 | 6 | 13 |

NS table #13 is the requested `Развитие 2♠` witness beginning
`1♣-1♦-2♠-??`. Its HTML uses a conventional six-column grid with four
`rowspan` cells and nine `colspan` cells. Every one of its eleven rows covers
all six logical columns. The cell wording and row order agree with the RTF
inventory, while the spans recover the hierarchy that the flattened RTF rows
cannot express. Its geometry also agrees with Archy's reviewed HTML table in
`system/agreements/otvety-na-1-trefu.md`.

This environment did not provide an interactive Word renderer. The finding
above is therefore a structural comparison of the raw Word export, the RTF
inventory, and the already human-reviewed agreement—not a new independent
visual verdict about Word's display.

## Encoding and Bridge Symbols

Strict `windows-1252` decoding succeeds for both sources. Within table text,
the probe found:

| Source | ♣ | ♦ | ♥ | ♠ | Replacement characters |
| --- | ---: | ---: | ---: | ---: | ---: |
| `Articles_25_09.htm` | 106 | 112 | 109 | 116 | 0 |
| `ns25_09.htm` | 161 | 160 | 152 | 156 | 0 |

A regression test also covers raw Windows-1251 Russian text combined with a
numeric club-suit reference. UTF-8, UTF-8 BOM, declared legacy encodings, and
unknown or undecodable declarations are handled without a silent replacement
fallback.

## Exceptional and Unsupported Cases

No exceptional table structure occurs in the two real exports. Synthetic
fixtures cover the risks that remain possible in later sources:

- malformed or missing span values are reported and treated as span `1`;
- cells outside rows create an explicit diagnostic rather than disappearing;
- nested tables become separate source-order records with parent/depth data;
- nested content is not flattened into the parent cell; its clean parent
  witness contains an explicit `nested table omitted` marker;
- paragraph and `<br>` boundaries inside cells survive as `<br>` in witnesses.

The nearest-heading field remains heuristic. For example, NS table #13 is
reported under the outline heading `Минорные неравномеры`, while its immediate
plain-paragraph label is `Развитие 2♠:`. Heading proximity must not be used as
proof of RTF/HTML alignment. Also, an HTML `<table>` may be a one-cell layout
device rather than a semantic agreement table.

Clean-witness inspection found no Word `class`, `style`, `mso-*`, scripting,
`head`, or XML baggage in the emitted fragments.

## Recommendation

Proceed with a second diagnostic stage: build an RTF-table to HTML-table
matcher, not the full converter yet.

The matcher should:

1. normalize cell text conservatively and match within the same source section
   using ordered text fingerprints;
2. require a unique, high-confidence match before borrowing HTML spans;
3. retain both source hashes and both table identifiers in its evidence;
4. emit clean HTML for tables with merges, because Markdown pipe tables cannot
   represent `rowspan` or `colspan` losslessly;
5. continue using Markdown pipe tables for simple rectangular tables when no
   span is present;
6. flag unmatched, multiply matched, nested, malformed, or text-divergent
   tables for human review rather than inferring geometry.

The current exports provide strong evidence that this approach is viable: HTML
has reliable conventional geometry, while RTF remains the correct authority
for wording and provenance. The unresolved engineering problem is safe
cross-source alignment, not table parsing.
