# Reviewed `Вист` Pair

These two generated drafts extracted the `Вист` section from each legacy
document. Archy reviewed and accepted both on 2026-10-16. Their material now
lives in the consolidated [`../../../agreements/vist.md`](../../../agreements/vist.md).

The reviewed agreement keeps both sources' provenance and combines the source
sections `“Flipping Kiev” explained` and `Лавинталь` as
`Flipping Odd Suit Preference`, following Archy's semantic ruling. Neither
source received precedence.

- [`review.md`](review.md) records the completed review.
- [`approved-manifest.json`](approved-manifest.json) preserves source ranges,
  fingerprints, and hashes of both generated inputs.

## Reproduce the Generated Inputs

Approved agreement notes are detached from regeneration. To reproduce the two
source-shaped inputs without overwriting the agreement, build them into a
temporary directory from the repository root:

```sh
python3 system/migration/tools/build_pilot_notes.py \
  --output-dir /tmp/clubbridge-vist-pilots \
  --pilot vist-articles \
  --pilot vist-system-map
```
