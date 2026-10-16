# Migration Pilots

These files are mechanically generated review drafts, not yet approved
partnership-system notes. They test three structurally different source
sections before we choose final semantic boundaries or perform bulk migration.

- [`kosaya-sistema.md`](kosaya-sistema.md) comes from `«Косая система»` in
  `Articles_25_09.rtf`.
- [`otvety-na-1-trefu.md`](otvety-na-1-trefu.md) comes from `Ответы на 1♣` in
  `ns25_09.rtf`.
- [`shlemovaya-torgovlya.md`](shlemovaya-torgovlya.md) comes from
  `Шлемовая торговля` in `ns25_09.rtf`.

`manifest.json` records source hashes, byte ranges, structural counts, and
generated-file hashes. Rebuild or verify the pilots from the repository root:

```sh
python3 system/migration/tools/build_pilot_notes.py
python3 system/migration/tools/build_pilot_notes.py --check
```

Table regions remain in fenced source-shaped text and carry review markers.
This avoids inventing cell geometry that the current extractor cannot prove.
See [`review.md`](review.md) for the automated findings and human checklist.
