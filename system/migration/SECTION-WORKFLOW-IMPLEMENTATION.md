# Section-by-section migration runner — implementation contract

Status: ready for implementation · Owner: ⏩🐝 Vel · review: 👁️ Iris · final approval: Archy
Branch: `main` (turn-scoped sequential commits)

## Target workflow
Archy names **one source and one section**, or asks to re-convert it. Vel
generates a **review-only** Markdown draft plus manifest, presents it for
Archy's review, incorporates requested corrections, then commits only the
approved note and its review/provenance record. Repeat through both RTFs.

Existing approved notes are detached from automatic regeneration. A
re-conversion creates a new draft, never silently overwrites an approved note.

## Required changes to tooling

1. Evolve `build_geometry_pilots.py` and/or share its core table renderer in
   a reusable module. Avoid forking separate geometry algorithms.
2. Add a CLI accepting:
   - `--source` (Articles or ns);
   - `--section` (exact heading, not automatically inferred from page);
   - `--output-dir` (mandatory; staged draft destination);
   - `--check` (deterministic regeneration comparison).
   If headings are duplicated, fail with helpful candidates and source offsets.
   Offer an explicit heading occurrence or byte-range selector only if needed.
3. Extract whole sections: headings, paragraphs, tables, inline symbols, and
   source provenance—not tables alone. Preserve meaningful paragraph and table
   order. Define predictable section boundaries; page numbers are hints only.
4. Use existing Phase 2 fingerprints, HTML table geometry, and Phase 3 models:
   strict unique matches eligible; approved divergent only when source-hash-keyed;
   ambiguous pairings represented as clearly named alternative drafts;
   unmatched cells retained as conservative fallback, with a human-editable
   presentation choice.
5. Adopt the first approved **semantic-diagram** rule for ns
   `rtf-table-0003` (original tokens: `ограниченная рука`,
   `ФП<br>────→`, `неопределённая рука`):
   output one *single-row* three-cell centered GFM table. The review decision
   is about **presentation**, not evidence of an HTML match. Pin to the RTF
   source hash and table ID; when source hashes change, abstain/re-review.
6. Be conservative about Markdown formatting: merged hierarchies use minimal
   HTML; rectangular unmerged tables use GFM; a semantic diagram may use
   GFM despite having no HTML geometric match when expressly approved.
   Escape literal pipes; preserve bridge suit glyphs, bid punctuation and
   source wording.
7. Output a stable manifest: source hashes, heading, source byte range,
   generated draft hash, every table ID and classification, presentation
   overrides, warnings, competing variants, and unresolved issues.
8. Add a deliberate **review/promotion boundary**. Never auto-write into
   `system/agreements/`. Make it easy for Archy to review and then for Vel
   to commit an approved revision preserving traceability, without regenerating
   it in later runs.
9. Preserve the existing Phase 3 sample generator and reproducibility tests
   while adding the section workflow; preferably share logic, not duplication.
10. Add tests for section boundaries, duplicate headings, markdown escaping,
   ordering, symbols, approved diagrams, unmatched fallbacks, competing drafts,
   hash guard, re-conversion and no approved-file overwrites.

## Scope and success checkpoint
First build and test the runner on one narrowly chosen existing section.
Do not convert all source material in one pass. Demonstrate a full cycle:
run draft -> reviewable outputs -> manifest -> controlled human approval,
**without** making up an approval. Report CLI example, tests and caveats.

## Original user intent
The bridge partnership meaning matters more than Word's incidental layout.
Tables can later be redrawn explicitly after human review.
For unresolved table matching, show all plausible variants rather than
arbitrarily selecting one. The duplicate-spade Gazilli collision remains
unresolved. Keep source RTF/HTML immutable and approved notes stable.
