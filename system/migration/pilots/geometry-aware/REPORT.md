# Phase 3 geometry-aware pilot report

This limited pilot uses RTF wording and provenance with HTML geometry only at
the evidence levels stated in `manifest.json`. Nothing here is an approved
partnership agreement.

## Generated evidence classes

| Evidence class | Generated tables |
|---|---:|
| Strict | 2 |
| Human-reviewed divergent | 1 |
| Competing variant | 4 |
| Unresolved fallback | 1 |

The sample demonstrates GFM for a rectangular unmerged table, minimal HTML for
merged geometry, a hash-keyed human approval that does not erase the original
`divergent` diagnosis, both complete mappings for the unresolved 2×2 collision,
and abstention from HTML geometry for an unmatched RTF table.

## Review boundaries

- RTF supplies the displayed wording and byte-offset provenance.
- HTML supplies only validated `rowspan`/`colspan` geometry.
- The reviewed Gazilli draft omits its fully empty bottom HTML row, which Archy
  explicitly judged non-meaningful; the manifest records that adjustment.
- Competing drafts are alternatives, not agreements; neither mapping is chosen.
- The fallback is a row/cell token list because its geometry is unresolved.
- Minimal HTML contains no Word classes, styles, scripts, or `mso-*` baggage.
- A later human review may redraw tables for clearer bridge meaning.

## Reproduction

```bash
python3 system/migration/tools/build_geometry_pilots.py \
  --output-dir system/migration/pilots/geometry-aware
python3 system/migration/tools/build_geometry_pilots.py \
  --output-dir system/migration/pilots/geometry-aware --check
python3 -m unittest discover -s system/migration/tests -v
```

## Open issue

The duplicate-spade Gazilli pairing remains unresolved. The two generated
mapping documents are intentionally textually similar because the duplicated
source tables are themselves identical; their distinct value is provenance,
not invented semantic difference.
