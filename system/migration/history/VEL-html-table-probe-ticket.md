# Vel ticket — Validate and evolve HTML table probing

Owner: ⏩🐝 Vel (Codex, local ClubBridge checkout)
Status: ready for implementation
Branch: `tools/html-table-probe-vel`
Source baseline: commit `1ab11df`
Purpose: validate whether the Word-exported HTML documents preserve enough
layout information to support a conservative dual-source RTF+HTML converter.

## Scope

1. Read `AGENTS.md`, `system/migration/README.md`, and
   `system/migration/tools/html_table_probe.py`.
2. Run the existing migration test suite, then run the probe against BOTH
   `system/legacy/Articles_25_09.htm` and `system/legacy/ns25_09.htm`.
3. Inspect representative tables in the HTML and compare their geometry
   visually with the original RTF in an editor/Word, especially the
   `Развитие 2♠` → `1♣–1♦–2♠–??` table.
4. Confirm whether HTML exports represent row/column merges through normal
   `rowspan`/`colspan`, Word-specific styling, or a combination.
5. Improve the probe only where evidence warrants it. Add regression tests
   with small synthetic HTML fixtures including basic, merged, malformed,
   and nested tables; handle nesting explicitly or report it as unsupported
   without silently producing misleading fragments.
6. Produce a compact written report under
   `system/migration/pilots/html-table-probe-report.md` containing:
   source hashes, encoding, total tables by file, merged-table counts,
   exceptional cases, samples, and recommendation for the next converter stage.
7. If useful, add lightweight documentation showing exact invocation.

## Commands

```sh
python3 -m unittest discover -s system/migration/tests -v
python3 system/migration/tools/html_table_probe.py \
  --output /tmp/clubbridge-html-report.json \
  --samples-dir /tmp/clubbridge-html-samples \
  --sample-limit 12
```

## Acceptance criteria

- Never modify `system/agreements/` or overwrite existing reviewed notes.
- Never change the legacy RTF/HTML source bytes.
- The script remains read-only by default; optional output is explicit.
- Report/fixtures make merged-cell representation auditable.
- No Word `class`, `style`, `mso-*`, scripting, or unrelated HTML baggage in
  clean witness fragments.
- Clearly distinguish confirmed findings from speculative assumptions.
- Correct unexpected UTF-8 / Windows-1251 encoding issues and symbol loss.
- A source/table mismatch is flagged for human review; never silently infer
  partnership semantics.
- Commit tested changes on this branch and report SHA plus open questions.
- Do **not** implement full migration, update main, or open a PR unless Archy
  separately requests that step.

## Known initial-probe limitations to investigate

- Table indexing may include nested tables; nested cells must not be flattened
  ambiguously.
- A Word-exported file might express merges through styles rather than
  conventional span attributes.
- Source heading proximity is heuristic; it does not prove RTF/HTML alignment.
- Clean fragments are diagnostic witnesses, not approved system notes.
