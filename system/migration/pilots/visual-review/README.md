# Phase 2.5 visual review pack

Open [`index.html`](index.html) in a browser. It links to:

1. [`case-1-ns-convention-card.html`](case-1-ns-convention-card.html) — large
   convention-card structural divergence;
2. [`case-2-articles-gazilli.html`](case-2-articles-gazilli.html) — compact
   Gazilli structural divergence;
3. [`case-3-ns-duplicate-collision.html`](case-3-ns-duplicate-collision.html) —
   the 2×2 duplicate collision with both possible pairings.

In the canonical repository pack, Archy's completed judgments and the remaining
unresolved collision are recorded in [`review.md`](review.md) for Iris review.

For cases 1 and 2, report one choice from each line:

- `Equivalent geometry / Different geometry / Uncertain`
- `Same bidding meaning / Different meaning / Uncertain`

For case 3, report `Mapping A`, `Mapping B`, or `Evidence insufficient`, plus
whether the paired tables have the same bidding meaning if you select a map.

The pages are static and self-contained. T-number badges connect identical
ordered non-empty wording across the RTF and HTML views. Empty RTF tokens do
not imply merge geometry. The rendered HTML export is geometry evidence, not
an independent rendering of the original Word/RTF document. Within-cell
whitespace and line breaks are normalized by the matcher; wording,
punctuation, and suit symbols are retained.

Regenerate from the repository root:

```bash
python3 system/migration/tools/build_table_visual_review.py
```
