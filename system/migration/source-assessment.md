# Initial Source Assessment

This is a provisional structural reading, not a claim about bridge meaning or
document precedence. Counts come from `tools/rtf_inventory.py`; rendered-source
verification has not happened yet.

## Inventory

| Source | Explicit page regions | Paragraphs | Outline headings | Table rows | Internal links outside the TOC |
| --- | ---: | ---: | ---: | ---: | ---: |
| `Articles_25_09.rtf` | 35 | 1,611 | 79 | 368 | 20 |
| `ns25_09.rtf` | 52 | 2,125 | 106 | 448 | 56 |

Neither source contains an embedded picture or object. Both rely substantially
on tables, list markers, fields, bookmarks, and hyperlinks.

## Working Reading

`ns25_09.rtf` appears to be the broad map of the current system. Its top-level
sections are:

- Соображения
- Шлемовая торговля
- Вист
- Входы
- Односторонка
- Заключение

`Articles_25_09.rtf` appears to hold extended rationale, theory, examples, and
some system developments. Its top-level sections are:

- Односторонка
- Входы
- Вист
- HUM-версия
- Реакция на помехи

These are useful source roles, not an authority hierarchy. A disagreement must
be preserved and recorded in
[`pending-updates/conflicts.md`](pending-updates/conflicts.md).

## Suggested Pilots

Before attempting all 250–300 semantic notes, convert and verify a few
deliberately different sections:

1. `«Косая система»` — prose, examples, and a small table;
2. `Ответы на 1♣` — dense tables and internal cross-references;
3. `Шлемовая торговля` — nested headings, lists, and mixed Russian/English text.

Together they should expose whether the inventory contains enough evidence for
safe note boundaries and cross-links. If not, change the tooling before bulk
generation.

## Known Review Risks

- A table's visual geometry may carry meaning not present in flattened rows.
- Font, color, emphasis, indentation, and merged cells are not yet represented.
- RTF table-of-contents entries duplicate real section names and must not become
  notes.
- Internal hyperlinks and bookmarks need to become stable Markdown links only
  after semantic note boundaries are chosen.
- Source byte offsets aid traceability, but they do not replace a visual check
  against the original document.
