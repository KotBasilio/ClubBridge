# Migration Pilots

This directory records mechanically generated review drafts and their review
state. Drafts are not partnership-system notes until human review promotes
them into [`../../agreements/`](../../agreements/README.md).

## Reviewed and Promoted

Archy reviewed the first three pilots on 2026-10-16. They now live as ordinary,
human-maintained agreement notes. The canonical
[`../approved-manifest.json`](../approved-manifest.json) preserves each
approved source range and generated hash; the entry's `review_record` points
to its completed checklist.
[`review.md`](review.md) preserves the completed checklist.

## Reviewed `Вист` Pair

The paired `Вист` drafts were reviewed and consolidated into
[`../../agreements/vist.md`](../../agreements/vist.md). Their completed review
lives under [`vist/`](vist/README.md); their approval evidence is in the
canonical manifest.

## Reproducing a Source Baseline

The builder requires an explicit output directory so it cannot overwrite an
approved agreement accidentally. For example:

```sh
python3 system/migration/tools/build_pilot_notes.py \
  --output-dir /tmp/clubbridge-pilots \
  --pilot kosaya-sistema

python3 system/migration/tools/build_pilot_notes.py \
  --output-dir /tmp/clubbridge-pilots \
  --pilot kosaya-sistema \
  --check
```

Generated baselines remain migration evidence. Once promoted, agreement notes
are intentionally detached from regeneration and may evolve through normal,
reviewable Markdown edits.
