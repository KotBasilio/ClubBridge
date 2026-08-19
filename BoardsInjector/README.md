# BoardsInjector

Inject bridge deal and double-dummy information from a PBN file into the
**Travellers** section of an HTML report produced by EBU Pairs Scorer.

## Transformation

```text
Source.htm + boards.pbn -> Destination.htm
```

The PBN `[Board "..."]` field is the join key.

For each matching traveller board, BoardsInjector adds a compact 3x3 panel:

- deal (`Deal`) in compass layout;
- computed HCP around the deal;
- optimum score (`OptimumScore`);
- makeable-contract table derived from `OptimumResultTable`.

The score/traveller rows produced by EBU Pairs Scorer are left alone.

## Requirements

Python 3. No third-party packages are required.

## Run

From the repository root on Windows:

```bat
py BoardsInjector\BoardsInjector.py ^
  BoardsInjector\Example1\Source.htm ^
  BoardsInjector\Example1\boards.pbn ^
  BoardsInjector\Example1\Generated.htm
```

Or on Linux/macOS:

```sh
python3 BoardsInjector/BoardsInjector.py \
  BoardsInjector/Example1/Source.htm \
  BoardsInjector/Example1/boards.pbn \
  BoardsInjector/Example1/Generated.htm
```

General form:

```text
BoardsInjector.py <source.html> <boards.pbn> <destination.html>
```

By default both files are read/written as `iso-8859-1`, matching the example
EBU/PBN files. Override when needed:

```text
--html-encoding <encoding>
--pbn-encoding <encoding>
```

## Behavior

- Only the `Travellers` section is searched for board panels.
- Existing BoardsInjector-generated panels are replaced on a rerun, so the
  operation is idempotent on its own output.
- HTML boards with no matching PBN board are left unchanged and reported.
- PBN boards absent from the HTML report are reported.
- A recognized board with an unrecognized injection seam is reported as an
  error instead of silently modifying the wrong place.
