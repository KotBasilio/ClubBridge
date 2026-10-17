# Phase 2.5 human review response

Reviewer: Archy

Date: 2026-10-18

Review target: [`index.html`](index.html)

Iris review target: confirm that this record accurately preserves Archy's
judgments and the remaining uncertainty. This response records decisions only;
it does not change matcher classifications, create overrides, or approve
agreement text.

## Case 1 — NS convention card

Tables: `rtf-table-0005` ↔ `html-table-0005`

- Geometry: **Equivalent geometry**
- Meaning: **Same bidding meaning**

Archy's observations:

- the HTML export has extra empty perimeter cells, shown in the review page as
  `∅ empty physical cell`; they carry no meaning;
- the HTML export merges several cells and represents those merges properly.

Human-review disposition: the structural divergence is understood as an
export/representation difference, not a semantic disagreement.

## Case 2 — Articles Gazilli

Tables: `rtf-table-0019` ↔ `html-table-0020`

- Geometry: **Equivalent geometry**
- Meaning: **Same bidding meaning**

Archy's observations:

- the HTML export has extra empty cells in its bottom row; they carry no
  meaning;
- the HTML export merges several cells and represents those merges properly.

Human-review disposition: the structural divergence is understood as an
export/representation difference, not a semantic disagreement.

## Case 3 — NS duplicate collision

RTF candidates: `rtf-table-0039`, `rtf-table-0044`

HTML candidates: `html-table-0042`, `html-table-0047`

- Pairing judgment: **Evidence insufficient; unresolved**
- No mapping override is approved.

Archy initially proposed Mapping A because the two candidates appeared to be
the sibling 1♥ and 1♠ Gazilli conventions. A raw-source recheck established
that all four collision candidates contain the 1♠ auction:

- RTF tables `0039` and `0044` both encode `1♠` as `\u9824`;
- HTML tables `0042` and `0047` both encode `1♠` as `&#9824;`.

The separate 1♥ sibling is `rtf-table-0031` ↔ `html-table-0031`; it encodes the
heart as `\u9829` / `&#9829;` and was already a unique strict match. After this
clarification, Archy left the duplicate-spade collision unresolved.

## Forward-looking note

Archy confirmed that the system's meaning is the important target. Once enough
surrounding material has been converted and reviewed, some tables may be
redrawn for semantic clarity rather than mechanically imitating incidental
Word layout. Such redrawing remains future reviewed conversion work, not an
outcome of this diagnostic phase.

## Phase disposition

- Cases 1 and 2 now have positive human geometry and meaning judgments.
- Case 3 remains ambiguous and must not be guessed.
- The matcher rules and Phase 2 classifications remain unchanged in this
  response.
- No legacy source, approved agreement, or source-hash-keyed override was
  modified or created.
