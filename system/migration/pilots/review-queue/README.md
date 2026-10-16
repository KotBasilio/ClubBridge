# Active Review Queue

This directory holds the next three source-shaped conversion drafts. They are
review material, not partnership-system notes. Their source sections remain
unchecked in the [transition plan](../../transition-plan.md) until Archy and
Nessy approve promotion.

- [`soobrazheniya.md`](soobrazheniya.md) — `Соображения` from `ns25_09.rtf`.
- [`vkhody-articles.md`](vkhody-articles.md) — `Входы` from
  `Articles_25_09.rtf`; it is distinct from the `ns25_09.rtf` section of the
  same name.
- [`review.md`](review.md) records the review state.
- [`manifest.json`](manifest.json) records the generated baseline.

Rebuild a draft into this directory only while it is active review material:

```sh
python3 system/migration/tools/build_pilot_notes.py \
  --output-dir system/migration/pilots/review-queue \
  --pilot soobrazheniya \
  --pilot vkhody-articles
```
