#!/usr/bin/env python3
"""
BoardsInjector

Merge deal and double-dummy information from a PBN file into the
Travellers board panels of an EBU Pairs Scorer HTML report.

Usage:
    python BoardsInjector.py Source.htm boards.pbn Destination.htm
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


TAG_RE = re.compile(r'^\[([^\s]+)\s+"(.*)"\]\s*$')
BOARD_HEADER_RE = re.compile(
    r'<TH\b[^>]*>\s*Board\s+(\d+)\b.*?</TH>',
    re.IGNORECASE | re.DOTALL,
)
INJECTION_TH_RE = re.compile(
    r'<TH\b(?=[^>]*\bcolSpan\s*=\s*["\']?8["\']?)[^>]*>',
    re.IGNORECASE,
)
EXISTING_INJECTION_RE = re.compile(
    r'\s*<!--\s*BoardsInjector:begin\s+board=\d+\s*-->.*?'
    r'<!--\s*BoardsInjector:end\s+board=\d+\s*-->\s*',
    re.IGNORECASE | re.DOTALL,
)
TRAVELLERS_ANCHOR_RE = re.compile(
    r'<A\b[^>]*\bname\s*=\s*["\']?Travellers["\']?[^>]*>',
    re.IGNORECASE,
)
SCORECARDS_ANCHOR_RE = re.compile(
    r'<A\b[^>]*\bname\s*=\s*["\']?ScoreCards["\']?[^>]*>',
    re.IGNORECASE,
)

SEATS = ("N", "E", "S", "W")
DENOMS = ("NT", "S", "H", "D", "C")
HCP_VALUE = {"A": 4, "K": 3, "Q": 2, "J": 1}


class BoardsInjectorError(RuntimeError):
    pass


@dataclass
class BoardData:
    board: int
    deal: Optional[str] = None
    optimum_score: Optional[str] = None
    optimum_rows: List[str] = field(default_factory=list)


@dataclass
class InjectionReport:
    injected: List[int] = field(default_factory=list)
    html_without_pbn: List[int] = field(default_factory=list)
    pbn_not_in_html: List[int] = field(default_factory=list)
    no_injection_seam: List[int] = field(default_factory=list)


def parse_pbn(text: str) -> Dict[int, BoardData]:
    """Parse the Board/Deal/OptimumResultTable/OptimumScore subset we need."""
    lines = text.splitlines()
    result: Dict[int, BoardData] = {}
    current: Optional[BoardData] = None
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        match = TAG_RE.match(stripped)

        if not match:
            i += 1
            continue

        key, value = match.group(1), match.group(2)
        key_lower = key.lower()

        if key_lower == "board":
            try:
                board_no = int(value.strip())
            except ValueError as exc:
                raise BoardsInjectorError(f"Invalid PBN Board value: {value!r}") from exc

            if board_no in result:
                raise BoardsInjectorError(f"Duplicate PBN board number: {board_no}")

            current = BoardData(board=board_no)
            result[board_no] = current

        elif current is not None and key_lower == "deal":
            current.deal = value.strip()

        elif current is not None and key_lower == "optimumscore":
            current.optimum_score = value.strip()

        elif current is not None and key_lower == "optimumresulttable":
            rows: List[str] = []
            j = i + 1
            while j < len(lines):
                next_stripped = lines[j].strip()
                if TAG_RE.match(next_stripped):
                    break
                if next_stripped:
                    rows.append(next_stripped)
                j += 1
            current.optimum_rows = rows
            i = j - 1

        i += 1

    return result


def parse_deal(deal: str) -> Dict[str, Tuple[str, str, str, str]]:
    """
    Return N/E/S/W hands as (spades, hearts, diamonds, clubs).

    PBN Deal format is:
        <first-seat>:<hand> <hand> <hand> <hand>
    and hands proceed clockwise from first-seat.
    """
    try:
        first_seat, hands_part = deal.split(":", 1)
    except ValueError as exc:
        raise BoardsInjectorError(f"Malformed Deal: {deal!r}") from exc

    first_seat = first_seat.strip().upper()
    if first_seat not in SEATS:
        raise BoardsInjectorError(f"Malformed Deal starting seat: {first_seat!r}")

    raw_hands = hands_part.split()
    if len(raw_hands) != 4:
        raise BoardsInjectorError(
            f"Malformed Deal: expected 4 hands, got {len(raw_hands)}: {deal!r}"
        )

    start = SEATS.index(first_seat)
    by_seat: Dict[str, Tuple[str, str, str, str]] = {}

    for offset, raw_hand in enumerate(raw_hands):
        suits = raw_hand.split(".")
        if len(suits) != 4:
            raise BoardsInjectorError(
                f"Malformed hand {raw_hand!r} in Deal {deal!r}: expected S.H.D.C"
            )
        seat = SEATS[(start + offset) % 4]
        by_seat[seat] = tuple(suits)  # type: ignore[assignment]

    return by_seat


def hand_hcp(hand: Iterable[str]) -> int:
    return sum(HCP_VALUE.get(rank.upper(), 0) for suit in hand for rank in suit)


def parse_optimum_rows(rows: Iterable[str]) -> Dict[str, Dict[str, int]]:
    table: Dict[str, Dict[str, int]] = {seat: {} for seat in SEATS}

    for row in rows:
        parts = row.split()
        if len(parts) < 3:
            continue

        declarer = parts[0].upper()
        denomination = parts[1].upper()
        result_text = parts[2]

        if declarer not in table or denomination not in DENOMS:
            continue

        try:
            tricks = int(result_text)
        except ValueError:
            continue

        table[declarer][denomination] = tricks

    return table


def render_hand(hand: Tuple[str, str, str, str]) -> str:
    spades, hearts, diamonds, clubs = (s if s else "-" for s in hand)
    return (
        f"&#9824;{html.escape(spades)}<BR>"
        f"<FONT color=red>&#9829;</FONT>{html.escape(hearts)}<BR>"
        f"<FONT color=red>&#9830;</FONT>{html.escape(diamonds)}<BR>"
        f"&#9827;{html.escape(clubs)}<BR>"
    )


def _dd_cell(tricks: Optional[int]) -> str:
    if tricks is None or tricks <= 6:
        return "-"
    return str(tricks - 6)


def render_dd_table(optimum_rows: Iterable[str]) -> str:
    table = parse_optimum_rows(optimum_rows)

    header = (
        "&nbsp;&nbsp;N&nbsp;&#9824;&nbsp;"
        "<FONT color=red>&#9829;</FONT>&nbsp;"
        "<FONT color=red>&#9830;</FONT>&nbsp;&#9827;"
    )
    lines = [header]

    for seat in ("N", "S", "E", "W"):
        values = [_dd_cell(table[seat].get(denom)) for denom in DENOMS]
        lines.append(
            html.escape(seat)
            + "&nbsp;"
            + "&nbsp;".join(html.escape(value) for value in values)
        )

    return "<BR>".join(lines)


def render_hcp(hands: Dict[str, Tuple[str, str, str, str]]) -> str:
    n = hand_hcp(hands["N"])
    e = hand_hcp(hands["E"])
    s = hand_hcp(hands["S"])
    w = hand_hcp(hands["W"])

    # Keep the compass placement legible without creating another nested TABLE.
    line1 = f"{n:>2}".center(12).replace(" ", "&nbsp;")
    line2 = f"{w:>2} HCP {e:<2}".center(12).replace(" ", "&nbsp;")
    line3 = f"{s:>2}".center(12).replace(" ", "&nbsp;")
    return f"{line1}<BR>{line2}<BR>{line3}"


def render_board_panel(board: BoardData) -> str:
    if not board.deal:
        raise BoardsInjectorError(f"Board {board.board}: PBN has no Deal field")

    hands = parse_deal(board.deal)
    optimum = html.escape(board.optimum_score or "-")

    style_table = (
        "FONT-SIZE:11pt; FONT-FAMILY:Times New Roman; FONT-WEIGHT:normal; "
        "WIDTH:100%; BORDER-COLLAPSE:collapse; BACKGROUND-COLOR:#fdf0d9"
    )
    style_cell = "WIDTH:33.33%; VERTICAL-ALIGN:top; TEXT-ALIGN:left"
    style_mono = (
        "FONT-SIZE:10pt; FONT-FAMILY:Courier New,Courier,monospace; "
        "FONT-WEIGHT:normal"
    )

    return f"""
            <!-- BoardsInjector:begin board={board.board} -->
            <TABLE style="{style_table}" cellPadding=4 align=center>
              <TBODY>
              <TR>
                <TD style="{style_cell}">Opt<BR>{optimum}<BR></TD>
                <TD style="{style_cell}">{render_hand(hands["N"])}</TD>
                <TD style="{style_cell}">&nbsp;</TD>
              </TR>
              <TR>
                <TD style="{style_cell}">{render_hand(hands["W"])}</TD>
                <TD style="{style_cell}">&nbsp;</TD>
                <TD style="{style_cell}">{render_hand(hands["E"])}</TD>
              </TR>
              <TR>
                <TD style="{style_cell}; {style_mono}">{render_hcp(hands)}</TD>
                <TD style="{style_cell}">{render_hand(hands["S"])}</TD>
                <TD style="{style_cell}; {style_mono}">{render_dd_table(board.optimum_rows)}</TD>
              </TR>
              </TBODY>
            </TABLE>
            <!-- BoardsInjector:end board={board.board} -->
"""


def _travellers_slice(html_text: str) -> Tuple[int, int]:
    travellers = TRAVELLERS_ANCHOR_RE.search(html_text)
    if not travellers:
        raise BoardsInjectorError("Could not find the Travellers section in HTML")

    scorecards = SCORECARDS_ANCHOR_RE.search(html_text, travellers.end())
    end = scorecards.start() if scorecards else len(html_text)
    return travellers.start(), end


def inject_boards(html_text: str, boards: Dict[int, BoardData]) -> Tuple[str, InjectionReport]:
    # This makes rerunning the tool on its own output safe.
    clean_html = EXISTING_INJECTION_RE.sub("\n", html_text)

    section_start, section_end = _travellers_slice(clean_html)
    section = clean_html[section_start:section_end]
    matches = list(BOARD_HEADER_RE.finditer(section))

    if not matches:
        raise BoardsInjectorError("No traveller Board headers found in HTML")

    report = InjectionReport()
    html_board_numbers = {int(match.group(1)) for match in matches}

    insertions: List[Tuple[int, str]] = []

    for index, match in enumerate(matches):
        board_no = int(match.group(1))
        next_board_start = matches[index + 1].start() if index + 1 < len(matches) else len(section)

        board = boards.get(board_no)
        if board is None:
            report.html_without_pbn.append(board_no)
            continue

        seam = INJECTION_TH_RE.search(section, match.end(), next_board_start)
        if seam is None:
            report.no_injection_seam.append(board_no)
            continue

        panel = render_board_panel(board)
        insertions.append((seam.end(), panel))
        report.injected.append(board_no)

    # Apply from the end so earlier offsets remain valid.
    for position, panel in reversed(insertions):
        section = section[:position] + panel + section[position:]

    report.pbn_not_in_html = sorted(set(boards) - html_board_numbers)
    report.injected.sort()
    report.html_without_pbn = sorted(set(report.html_without_pbn))
    report.no_injection_seam = sorted(set(report.no_injection_seam))

    output = clean_html[:section_start] + section + clean_html[section_end:]
    return output, report


def _format_numbers(values: Iterable[int]) -> str:
    return ", ".join(str(value) for value in values)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Inject PBN deals and double-dummy analysis into an EBU Pairs Scorer HTML report."
    )
    parser.add_argument("source_html", type=Path, help="EBU Pairs Scorer HTML input")
    parser.add_argument("boards_pbn", type=Path, help="PBN file containing board data")
    parser.add_argument("destination_html", type=Path, help="HTML file to write")
    parser.add_argument(
        "--html-encoding",
        default="iso-8859-1",
        help="HTML input/output encoding (default: iso-8859-1)",
    )
    parser.add_argument(
        "--pbn-encoding",
        default="iso-8859-1",
        help="PBN encoding (default: iso-8859-1)",
    )
    args = parser.parse_args(argv)

    try:
        source = args.source_html.read_text(encoding=args.html_encoding)
        pbn_text = args.boards_pbn.read_text(encoding=args.pbn_encoding)
        boards = parse_pbn(pbn_text)
        if not boards:
            raise BoardsInjectorError("No [Board \"...\"] records found in PBN")

        output, report = inject_boards(source, boards)
        args.destination_html.write_text(output, encoding=args.html_encoding)

    except (BoardsInjectorError, OSError, UnicodeError) as exc:
        print(f"BoardsInjector: error: {exc}", file=sys.stderr)
        return 2

    print(
        f"BoardsInjector: injected {len(report.injected)} board(s)"
        + (f": {_format_numbers(report.injected)}" if report.injected else "")
    )

    if report.html_without_pbn:
        print(
            "BoardsInjector: HTML board(s) without PBN data: "
            + _format_numbers(report.html_without_pbn)
        )

    if report.pbn_not_in_html:
        print(
            "BoardsInjector: PBN board(s) not present in HTML Travellers: "
            + _format_numbers(report.pbn_not_in_html)
        )

    if report.no_injection_seam:
        print(
            "BoardsInjector: board(s) found but injection seam was not recognized: "
            + _format_numbers(report.no_injection_seam),
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
