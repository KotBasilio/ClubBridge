# Phase 3 — Geometry-aware Markdown pilot generator

Owner: ⏩🐝 Vel · Review: 👁️ Iris · Approval: 😺 Archy
Working branch: `main` (sequential turn-scoped coordination)
Baseline: `91316bbfa4843116f19536104f6991dae53ef87c`
Status: implemented; Iris review pending

## Goal
Extend the conservative migration pipeline to generate **review-only Markdown pilots**
using RTF for authoritative wording/provenance and HTML for validated table geometry.
Keep approved notes untouched. Minimize Word-export presentation baggage.

## Candidate categories
- **87 strict bilaterally unique matches**: use HTML `rowspan`/`colspan` geometry,
  but retain RTF wording and original source offsets; cross-check ordered cell text.
- **2 human-reviewed divergent pairs**: NS RTF 0005 ↔ HTML 0005, and Articles
  RTF 0019 ↔ HTML 0020, judged equivalent geometry/meaning by Archy in
  `system/migration/pilots/visual-review/review.md`. If incorporated, use explicit,
  reviewable *source-hash-keyed* approvals; retain their distinct `divergent`
  classification in the diagnostic evidence. Do not silently promote them.
- **Ambiguous case 3**: NS RTF 0039/0044 vs HTML 0042/0047 remains genuinely
  unresolved. Do not guess a pairing. At Archy's request, it is acceptable to
  generate **all plausible variants as clearly labeled competing drafts** so
  Archy can choose and delete incorrect variants. No automatic promotion,
  overwrite, or claim of semantic equivalence. Keep each variant traceable to
  both candidate IDs and source hashes.
- **Other unmatched/divergent**: report and abstain by default; don't invent.

## Conversion policy
- Preserve substantive text, suit symbols, auction ordering, and bridge meaning.
  Original RTFs remain immutable evidence and semantic authority.
- Use simple GFM tables for truly rectangular unmerged cases; use minimal
  HTML `<table>` with `rowspan`/`colspan` for merged/hierarchical tables.
  Strip Word `class`, `style`, `mso-*`, scripts and unrelated metadata.
- Where exact RTF cell-to-HTML geometry alignment cannot be demonstrated,
  **abstain**, retain source text as a reviewable fallback, or emit separately
  marked alternatives; never place text into guessed cells.
- Visual layout is not itself the goal. Archy may later choose to redraw tables
  for clearer semantics after enough source text has been reviewed.
- Do not automatically replace the current reviewed `system/agreements/*.md`
  or modify `system/legacy/`.
- Keep review outputs under `system/migration/pilots/`, deterministically
  regenerated into an explicit output directory (no silent destructive writes).

## Requested implementation
1. Read `AGENTS.md`, migration README, the Phase 2 matcher, Phase 2.5 human
   review, and existing pilot generator before modifying code.
2. Propose a minimal intermediate model for table rows, cells, spans, text
   alignment, IDs and provenance; reuse existing extraction logic where sensible.
3. Implement a **limited pilot** on representative selected sections/tables
   first, not mass re-conversion of the two entire documents.
4. Build a manifest classifying each generated table as strict, human-reviewed,
   competing-variant, or unresolved fallback, with source hashes, table IDs,
   and warning notes.
5. Add regression tests for merged and unmerged structures, text preservation,
   entity escaping, Unicode suits, determinism, ambiguous alternatives, and
   guarded writes.
6. Regenerate a small output sample and document the exact run/test commands
   and the number of tables in each evidence class.
7. Report blockers and design disagreements rather than weakening the matcher.
8. Commit to `main` **only after rechecking status and fetching/rebasing
   against current main**, because Iris also has write access. Do not force push.

## Human context
Archy initially suspected the 2×2 collision was confusion between 1♥ and 1♠
Gazilli siblings, but a raw-source recheck established both collided tables are
1♠. Archy accepts the correction. He confirms the Gazilli descriptions are
legible in both original documents (RTF pages approximately 33 and 39) and
allows the collision to remain unresolved. When multiple plausible conversions
exist, presenting all variants for human selection is preferable to silently
guessing one. `Reviewable alternatives` are not approved agreements.

## Deliverables
- Generator changes under `system/migration/tools/`
- Focused regression tests under `system/migration/tests/`
- Representative generated pilots + manifest under `system/migration/pilots/`
- Concise report documenting strict, reviewed, ambiguous and fallback cases
- Git commit SHA, test results, unresolved problems and proposed next step
