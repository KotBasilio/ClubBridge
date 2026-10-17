# RTF ↔ HTML table matcher — Phase 2 report

Date: 2026-10-17

Branch: `tools/rtf-html-table-matcher-vel`

Scope: read-only diagnostics; no agreement or legacy source was changed

## Outcome

The matcher found **87 bilaterally unique structural matches** among 115 RTF
table regions and 120 HTML tables. These matches are safe candidates for a
later geometry-borrowing phase; the matcher itself does not borrow geometry or
generate Markdown.

| Source pair | RTF regions | HTML tables | Matched | Ambiguous | Divergent | Unmatched | Unsupported |
|---|---:|---:|---:|---:|---:|---:|---:|
| Articles | 59 | 60 | 48 | 0 | 2 | 9 | 0 |
| ns | 56 | 60 | 39 | 2 | 4 | 11 | 0 |
| **Total** | **115** | **120** | **87** | **2** | **6** | **20** | **0** |

The corresponding HTML side has 10 unreferenced Articles tables and 15
unreferenced ns tables. “Unreferenced” means that no RTF result names the table
as an exact, ambiguous, divergent, or unsupported candidate; it does not imply
that the source table is unimportant.

## Matching rule

Each RTF table is a consecutive region of `table-row` paragraphs emitted by
`rtf_inventory.py`. Each row is split into its ordered cell tokens. On the HTML
side, every physical cell contributes one token. A continuing `rowspan`
contributes one empty token in each later row, matching the representation
observed in Word's RTF; a `colspan` remains one token rather than being expanded
into synthetic empty cells.

Cell text normalization is deliberately narrow:

- Unicode NFC;
- non-breaking space converted to ordinary space;
- RTF `<br>` markers and HTML paragraph/line breaks treated as whitespace;
- runs of whitespace collapsed.

Case, punctuation, bridge symbols, wording, cell order, and row boundaries are
not normalized away. The matcher does not use headings or ordinals as match
evidence and has no approximate similarity score.

A table is `matched` only when its complete ordered row/cell fingerprint occurs
exactly once on the RTF side and exactly once on the supported HTML side.
`divergent` means the ordered sequence of non-empty cells is bilaterally unique,
but row/cell structure differs. Geometry is **not** approved for divergent
tables. Any collision at either evidence tier is `ambiguous`; the matcher
abstains.

Every JSON result records both source SHA-256 hashes, stable per-source table
identifiers, normalized fingerprint hashes, evidence text, RTF byte offsets,
nearby headings for navigation only, and HTML geometry facts.

| Source | SHA-256 |
|---|---|
| `Articles_25_09.rtf` | `8416e9315db61c689b7be737a3b740577b47f91729e63137634d1592665e8054` |
| `Articles_25_09.htm` | `63028359317a08b80b2c38fb6c804e82c1a16749124fa54a98a8db67b14b7502` |
| `ns25_09.rtf` | `146d7c77baf0d1bf57af5df662ba7fa22543411e26d402b23bf99276fc48da8b` |
| `ns25_09.htm` | `b9c6be73a5023e25c349fb9aa9c331ecbb498caeaca90f7041a5c93c625797b7` |

There is intentionally no numeric “confidence” score. `matched` is the sole
auto-eligible evidence class; every other status requires review or abstention.

## Target-table audit

NS RTF table `rtf-table-0013` uniquely matches `html-table-0013`, headed by
content beginning `1♣-1♦-2♠-??`. The HTML geometry remains:

- 11 rows;
- 23 physical cells;
- 6 logical columns;
- 13 merged cells.

This is a strict structural/content match, not an ordinal-based match.

## Tables requiring review

### Ambiguous collision

The same normalized structured content occurs twice in each ns source:

- `rtf-table-0039` and `rtf-table-0044`;
- `html-table-0042` and `html-table-0047`.

This creates a genuine 2×2 collision. Neither heading nor source order is used
to break the tie. Both RTF results are therefore `ambiguous`.

### Unique content, divergent structure

These pairs retain the same bilaterally unique ordered non-empty cell content,
but disagree on row/cell boundaries. They require visual or source-level review
before any HTML geometry can be trusted:

| Source | RTF table | HTML candidate | RTF rows / tokens | HTML rows / physical cells |
|---|---|---|---:|---:|
| Articles | `rtf-table-0019` | `html-table-0020` | 7 / 19 | 8 / 21 |
| Articles | `rtf-table-0047` | `html-table-0048` | 6 / 12 | 6 / 14 |
| ns | `rtf-table-0005` | `html-table-0005` | 31 / 78 | 32 / 112 |
| ns | `rtf-table-0017` | `html-table-0017` | 26 / 78 | 27 / 65 |
| ns | `rtf-table-0033` | `html-table-0033` | 6 / 14 | 7 / 17 |
| ns | `rtf-table-0042` | `html-table-0045` | 6 / 14 | 7 / 17 |

### No deterministic candidate

Articles RTF tables:

`0010`, `0014`, `0025`, `0026`, `0028`, `0032`, `0034`, `0056`, `0057`.

Articles HTML tables:

`0010`, `0014`, `0015`, `0026`, `0027`, `0029`, `0033`, `0035`, `0057`,
`0058`.

ns RTF tables:

`0003`, `0004`, `0021`, `0030`, `0034`, `0038`, `0041`, `0043`, `0045`,
`0046`, `0050`.

ns HTML tables:

`0003`, `0004`, `0021`, `0030`, `0034`, `0035`, `0036`, `0037`, `0041`,
`0044`, `0046`, `0048`, `0049`, `0053`, `0054`.

Spot checks show several reasons why “nearly equal” would be unsafe: Symbol and
Wingdings glyphs decode differently in the two exports, some bullet glyphs
differ, and some tables appear to contain substantive or structural source
differences. Those observations are navigation hints, not match evidence.

## False-positive defenses

Regression tests cover exact matching, whitespace and entity variation,
duplicate content, swapped cells, missing tables, repeated headings, multiline
cells, suit symbols, rowspan/colspan flattening, unsupported HTML, and the real
NS target table. In particular:

- a match must be unique on **both** source sides;
- swapped cells cannot match merely because they contain the same words;
- repeated headings have no effect on matching;
- same content with different row boundaries is reported as divergent;
- malformed or nested HTML is unsupported rather than promoted;
- no fuzzy threshold or source-order fallback exists.

## Reproduction

From the repository root:

```bash
python3 -m unittest discover -s system/migration/tests -v
python3 system/migration/tools/match_rtf_html_tables.py \
  --output /tmp/clubbridge-table-matches.json
```

The first command runs 32 tests. The second writes the complete auditable JSON
diagnostic. Omitting `--output` prints the same JSON to standard output.

## Remaining questions and recommendation

The present RTF inventory represents cells using inserted pipe delimiters and
groups consecutive table rows. It cannot prove whether a literal pipe occurred
inside original cell text, and adjacent Word tables without an intervening
non-table paragraph could be grouped as one region. Neither issue was observed
as a false match here, but both are limitations of the intermediate model.

Recommended next step: have Iris and Archy review the two ambiguous source
locations and a small representative sample of the six divergent pairs. If the
rendered originals confirm their correspondence, add explicit, reviewed
overrides keyed by source hashes and table IDs; do not weaken the automatic
matcher. Separately investigate the 20 unmatched RTF regions as parser/export
differences or genuine document drift. The 87 strict matches can proceed to a
later, still review-gated geometry application phase.
