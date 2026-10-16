# Migration Pilots

This directory records mechanically generated review drafts and their review
state. Drafts are not partnership-system notes until human review promotes
them into [`../../agreements/`](../../agreements/README.md).

## Reviewed and Promoted

Archy reviewed the first three pilots on 2026-10-16. They now live as ordinary,
human-maintained agreement notes. [`approved-manifest.json`](approved-manifest.json)
preserves their source ranges and generated hashes at approval;
[`review.md`](review.md) preserves the completed checklist.

## Active Review

The paired `Вист` drafts live under [`vist/`](vist/README.md). They deliberately
keep the two sources separate while we test cross-document comparison.

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
