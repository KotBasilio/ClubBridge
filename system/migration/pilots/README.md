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

## Second Reviewed Batch

The next three drafts were reviewed and promoted on 2026-10-16. Their
completed checklist is [`second-review.md`](second-review.md), and their source
evidence is in the canonical manifest. A new review queue will be created when
the next source-shaped batch is ready.

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

## Geometry-aware review drafts

Geometry-aware pilots remain review material even when their RTF↔HTML evidence
is strict. Merged tables use minimal HTML only when alignment is demonstrated;
simple rectangular tables may use GFM. Human-reviewed divergences retain that
diagnostic label, and genuine ambiguity may be presented as multiple competing
drafts. The current limited sample, report, and manifest are in
[`geometry-aware/`](geometry-aware/README.md). See the migration workspace
guidance for the alternatives rule.

## Section-workflow demonstration

[`section-workflow-demo/`](section-workflow-demo/REVIEW.md) is the first
deterministic section-runner example. It stages the narrow `ns` section
`Форспас`, including Archy's hash-keyed semantic-diagram presentation decision,
without promoting the draft into the approved agreements.
