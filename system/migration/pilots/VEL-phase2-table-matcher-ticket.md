# Phase 2 — RTF ↔ HTML table matching (Vel)

Owner: ⏩🐝 Vel · Review: 👁️ Iris team · Approval: Archy
Branch: `tools/rtf-html-table-matcher-vel`
Base: `e16518df285acbd3dbfff8d1e2cda0b1b7b9d817`

## Goal
Implement a **read-only diagnostic matcher** between RTF table regions obtained via
`rtf_inventory.py` and HTML tables extracted via `html_table_probe.py`.
Use matching to assess whether HTML geometry can safely be borrowed for
future Markdown generation. **Do not build the full converter in this phase.**

## Constraints
- Existing RTFs remain authoritative for wording and byte-offset provenance.
- HTML supplies geometry only after a **unique, evidence-supported** match.
- Start by matching within each corresponding source pair (Articles↔Articles;
  ns↔ns). Use ordered cell-text fingerprints with conservative Unicode/whitespace
  normalization; retain exact source text for final output.
- Do not use table ordinal or nearest heading *alone* to establish a match.
- Distinguish matched / ambiguous / unmatched / divergent / unsupported.
  If several candidate tables look similar, abstain rather than choose arbitrarily.
- Compare cell content and order, not only concatenated text. Handle source
  differences due to split paragraphs, RTF <br> markers and HTML entities.
- Record source hashes, table identifiers and match evidence for audit.
- Never modify `system/agreements/` or `system/legacy/`.
- The matcher must not auto-promote notes or edit reviewed materials.

## Suggested outputs
- `system/migration/tools/match_rtf_html_tables.py`
- Regression fixtures/tests under `system/migration/tests/`.
- `system/migration/pilots/rtf-html-matcher-report.md` summarizing coverage by
  source pair, confidence, collisions, mismatches, false-positive defenses,
  and a list of tables requiring human review.

## Tests / acceptance
1. Synthetic exact match, whitespace/entity variance, duplicate text, swapped
   content, missing table, repeated headings, multiline cell and suit symbols.
2. Verify a false positive is never silently accepted. Do not use
   approximate scores without documented thresholds and counterexamples.
3. Audit specific NS table #13 (`Развитие 2♠`); preserve its reported
   11 rows, 23 physical cells, 6 logical columns and 13 merges if matched.
4. Run existing test suite and all added tests locally.
5. Provide explicit commands for reproducible diagnostics.
6. Commit work to this branch and report SHA, test counts, results and concerns.
7. Leave merging into `main` to Archy after Iris review.

## Design freedom
Investigate and amend the proposed matching algorithm based on real source
evidence. Report if RTF inventory flattening loses enough cell boundaries
that stronger parsing is required. Do not force a match to satisfy the ticket.
