# Vel ticket — Phase 2.5 visual review pack

Owner: ⏩🐝 Vel · Review: 👁️ Iris · Human decision: 😺 Archy
Branch: `tools/table-visual-review-vel`
Base: `025386569014f831613fbf6a04549155d2c0025f`

## Goal
Produce a **human-friendly, read-only visual review pack** for the first three
RTF↔HTML matching exceptions. Do not change match classifications, add overrides,
generate approved notes, or rewrite the legacy sources.

## Cases
1. Divergent: `ns` RTF `rtf-table-0005` ↔ HTML `html-table-0005`
   (RTF 31 rows / 78 tokens; HTML 32 rows / 112 physical cells).
2. Divergent: `Articles` RTF `rtf-table-0019` ↔ HTML `html-table-0020`
   (RTF 7 rows / 19 tokens; HTML 8 rows / 21 physical cells).
3. Genuine duplicate collision: `ns` RTF `0039`, `0044` ↔
   HTML `0042`, `0047`. Present *both possible pairings*; don't infer mapping.

## Deliverables
- Self-contained local HTML review page(s) under
  `system/migration/pilots/visual-review/`, suitable to open in a browser.
  Static only: no external resources, scripts, or links that require connectivity.
- A concise `README.md` in the same directory that points to each case and
  tells Archy how to inspect and report judgments.
- Optionally a small deterministic generation script under
  `system/migration/tools/`; avoid manually copying long source tables.
- Include both source hashes, table IDs, nearby headings/labels where available,
  and explicit `RTF-derived flattened interpretation` versus
  `HTML-exported geometry` labeling.
- Preserve exact meaningful wording and suit symbols. Escape untrusted text.
  Strip Word class/style/mso-* baggage. Inline CSS for side-by-side presentation
  is allowed in the generated review page **only**, not in agreement fragments.
- On the RTF side, show the current parser's grid/tokens *without inventing
  missing rowspan/colspan*. If rendering as a true table is misleading, use a
  row/cell token listing instead.
- For each divergent case, highlight or list structural discrepancies, and
  provide a plain review prompt:
  `Equivalent geometry / Different geometry / Uncertain`;
  `Same bidding meaning / Different meaning / Uncertain`.
- For the collision, ask which RTF table pairs with which HTML table, or whether
  the evidence is insufficient; include disambiguating local context but do
  not auto-pick by heading or ordinal.

## Acceptance criteria
- Full original test suite still passes; add focused tests for generated
  examples, text/suit preservation, HTML escaping, and determinism if a
  generator is implemented.
- Verify the output opens locally and is understandable without running code.
- RTF and HTML sources are not modified.
- `system/agreements/` stays untouched.
- No source-hash-keyed overrides are written; decisions belong to Archy later.
- Explain limitations, especially that a rendered HTML export is not an
  independent Word/RTF visual rendering.
- Commit and push on this branch; report SHA, tested commands, generated pages,
  and any findings.

## Context
Review the report at
`system/migration/pilots/rtf-html-matcher-report.md`, plus `AGENTS.md`.
This is deliberately a small sample before reviewing all exceptions.

## Human review response

Archy's decisions and the raw-source clarification for the duplicate collision
are recorded in [`visual-review/review.md`](visual-review/review.md). Cases 1
and 2 were judged geometrically equivalent with the same bidding meaning. Case
3 remains unresolved; no pairing override was approved.
