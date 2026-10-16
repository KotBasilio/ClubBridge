# `Вист` Review Pair

These two drafts extract the `Вист` section from each legacy document.
Neither source has precedence. Keeping them separate makes overlap and disagreement
visible before any human-approved consolidation.

- [`vist-articles.md`](vist-articles.md) contains the longer explanations and
  examples from `Articles_25_09.rtf`.
- [`vist-system-map.md`](vist-system-map.md) contains the compact system map,
  convention-card table, detailed opening leads, and Lavinthal notes from
  `ns25_09.rtf`.
- [`review.md`](review.md) is the human review surface.
- [`manifest.json`](manifest.json) records source ranges, fingerprints, and
  generated-file hashes.

These files are migration drafts, not yet partnership authority. If they are
accepted, promote them into [`../../../agreements/`](../../../agreements/README.md)
as one or more coherent notes; do not silently merge wording where the sources
differ.

## Rebuild and Check

From the repository root:

```sh
python3 system/migration/tools/build_pilot_notes.py \
  --output-dir system/migration/pilots/vist \
  --pilot vist-articles \
  --pilot vist-system-map

python3 system/migration/tools/build_pilot_notes.py \
  --output-dir system/migration/pilots/vist \
  --pilot vist-articles \
  --pilot vist-system-map \
  --check
```
