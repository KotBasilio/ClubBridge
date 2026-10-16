# First Pilot Review — Completed

Archy reviewed all three pilots in detail and accepted them on 2026-10-16.
They have been promoted to `system/agreements/` with status `reviewed`.

## Automated Inventory

| Pilot | Extracted blocks | Headings | Table regions | Source hyperlinks | TOC backlinks |
| --- | ---: | ---: | ---: | ---: | ---: |
| `«Косая система»` | 77 | 5 | 4 | 4 | 2 |
| `Ответы на 1♣` | 365 | 15 | 13 | 21 | 7 |
| `Шлемовая торговля` | 170 | 9 | 2 | 2 | 2 |

The hyperlink counts include the TOC backlinks. Content links retain their
visible source wording, but do not yet have Markdown targets because the final
semantic note paths do not exist.

## Review Checklist

### `«Косая система»`

- [x] Wording agrees with the rendered RTF.
- [x] Table geometry and multiline cells are represented correctly.
- [x] The section should remain one note, or its child headings should become
  separate semantic notes.
- [x] The two source hyperlinks described as `по этой ссылке` retain their
  visible wording; stable cross-link targets remain future work.

### `Ответы на 1♣`

- [x] Wording agrees with the rendered RTF.
- [x] Dense tables, multiline auctions, and merged cells are represented
  correctly.
- [x] Child headings identify sensible semantic note boundaries.
- [x] Internal source hyperlinks retain their visible wording; stable
  cross-link targets remain future work.

### `Шлемовая торговля`

- [x] Wording agrees with the rendered RTF.
- [x] Lists and mixed Russian/English passages retain their intended grouping.
- [x] Tables and auction layouts are represented correctly.
- [x] Child headings identify sensible semantic note boundaries.
- [x] Internal source hyperlinks retain their visible wording; stable
  cross-link targets remain future work.

## Conversion Properties Retained

- The RTF outline hierarchy is usable, but it skips numerical levels. The
  pilots compress those gaps into ordinary Markdown heading levels.
- Adobe Symbol suits, arrows, and notation are converted to visible Unicode;
  the private-use horizontal arrow extender is represented as `─`.
- `TOC` backlink text is retained as an HTML source-navigation comment rather
  than partnership content.
- Table text is preserved, but cell geometry is intentionally not guessed.
- Font weight, italics, color, indentation, and merged cells are not yet
  represented.
- Approved notes are detached from mechanical regeneration. Their original
  generated hashes remain in `approved-manifest.json` as migration evidence.
