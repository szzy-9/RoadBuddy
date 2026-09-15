"""Extract the Road Safety Road Rules 2017 PDF to plain text for retrieval.

Diagram-dependent content is omitted: the traffic-sign catalogues in
Schedules 2 to 4 carry their meaning in vector artwork that does not
survive text extraction, leaving only captions such as "End bus lane
sign (rule 154)". Answering from those captions would cite a rule
without its actual content, so they are dropped rather than indexed.

Running page furniture (the authorisation footer, the running heads and
the page numbers) is stripped as well, since it repeats on all 624 pages
and would otherwise dominate any similarity search.

Usage:
    python extract_road_rules.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PDF_PATH = HERE / "17-41sra026-authorised.pdf"
OUT_PATH = HERE / "road_rules_2017.txt"

# Page furniture repeated on every page of the authorised version.
FURNITURE = (
    re.compile(r"^\s*Authorised by the Chief Parliamentary Counsel\s*$"),
    re.compile(r"^\s*Road Safety Road Rules 2017\s*$"),
    re.compile(r"^\s*S\.R\. No\. 41/2017\s*$"),
    re.compile(r"^\s*Part \d+[A-Z]*—.*$"),
    re.compile(r"^\s*Division \d+[A-Z]*—.*$"),
    re.compile(r"^\s*Schedule \d+—.*$"),
    re.compile(r"^\s*\d{1,3}\s*$"),          # bare page number
    re.compile(r"^\s*═+\s*$"),
)

# Amendment history ("Rule 39(1) amended by S.R. No. 135/2021 rule 16.")
# is printed in a narrow margin, on the left of some pages and the right
# of others. With -layout that margin shares physical lines with the rule
# text, so it cannot be matched line-by-line: it is identified by column.
# Rule text is indented to at least TEXT_COLUMN; anything starting left of
# that is a left margin. RIGHT_MARGIN_COLUMN is where the right-hand
# margin band begins - a fragment there is dropped only when it also looks
# like provenance, so deeply indented real text is never lost.
TEXT_COLUMN = 16
RIGHT_MARGIN_COLUMN = 56

# A margin fragment is separated from the rule text by a run of spaces.
# The fragment itself is short (typically 7 to 15 characters) while the
# text it precedes resumes anywhere from roughly column 14 to 30, so the
# fragment's shape decides, not a fixed column.
MARGIN_SPLIT = re.compile(r"^(\S.{0,30}?)\s{2,}(\S.*)$")

# Margin fragments look like these; used to confirm a flush-left fragment
# really is amendment provenance rather than body text.
MARGIN_HINT = re.compile(
    r"^("
    r"(Rule|Sch\.|Pt|Div|Note to|Heading|Dictionary)\s*[\d(]"
    r"|S\.R\. No\.?"
    r"|No\. \d+"
    r"|\d+/\d{4}"
    r"|(amended|inserted|substituted|repealed|revoked|renumbered|new)\b"
    r"|rule\s+\d+[A-Z]*\.?$"
    r"|s\.\s*\d+"
    r")",
    re.IGNORECASE,
)

DIAGRAM_NOTE = re.compile(r"^\s*Note for diagrams\s*$")


def extract_pages(pdf: Path) -> list[str]:
    """Return the PDF's pages as layout-preserved text."""
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.split("\f")


def find_omitted_range(pages: list[str]) -> tuple[int, int]:
    """Return the half-open page range covering Schedules 2 to 4.

    These schedules are the traffic-sign and symbol catalogues. The range
    is located by content rather than hardcoded page numbers so that a
    reprint with different pagination still extracts correctly.

    The table of provisions near the front lists every schedule heading,
    so a naive search matches a contents page and collapses to an empty or
    wildly oversized range. Body pages are identified by their running
    head: the title and S.R. number appear in the first few lines, above
    the schedule heading. Contents pages carry neither.
    """
    start = None
    for index, page in enumerate(pages):
        head = "\n".join(page.split("\n")[:4])
        if ("Road Safety Road Rules 2017" in head
                and "Schedule 2—Standard or commonly" in head):
            start = index
            break
    if start is None:
        raise SystemExit("Could not locate Schedule 2; check the PDF edition.")

    end = None
    for index in range(start + 1, len(pages)):
        if "Schedule 5—Revocations" in pages[index]:
            end = index
            break
    if end is None:
        raise SystemExit("Could not locate Schedule 5; check the PDF edition.")
    return start, end


def drop_trailing_margin(line: str) -> str:
    """Remove a right-hand margin fragment appended to a line of rule text.

    On right-margin pages a line reads
    "(b) driving a motor vehicle and engaged in speed     Rule 310(3)(b)",
    where the tail is provenance, not part of the rule.
    """
    match = re.match(r"^(.*?\S)\s{3,}(\S.*)$", line)
    if not match:
        return line
    text, tail = match.groups()
    start_of_tail = len(line) - len(tail)
    if start_of_tail >= RIGHT_MARGIN_COLUMN - 2 and MARGIN_HINT.search(tail.strip()):
        return text
    return line


def strip_margin(line: str) -> str | None:
    """Remove the amendment-history margin from one physical line.

    Returns the rule text, or None when the line was margin only.
    """
    if not line.strip():
        return ""

    indent = len(line) - len(line.lstrip())

    # Right-hand margin: a short provenance fragment sitting far right.
    if indent >= RIGHT_MARGIN_COLUMN and MARGIN_HINT.search(line.strip()):
        return None

    # A right-hand margin fragment can also trail a line of rule text at
    # any indent, so remove it before the left-margin handling below.
    line = drop_trailing_margin(line)

    if indent >= TEXT_COLUMN:
        return line.rstrip()

    # Starts in the margin band: either margin plus rule text on the same
    # line, or a margin-only line.
    split = MARGIN_SPLIT.match(line)
    if split:
        margin, text = split.groups()
        if MARGIN_HINT.search(margin.strip()):
            # Preserve the text's original column so indentation-based
            # structure (sub-paragraphs) survives.
            return " " * (len(line) - len(text)) + text.rstrip()
        return line.rstrip()

    return None if MARGIN_HINT.search(line.strip()) else line.rstrip()


def clean_page(page: str) -> list[str]:
    """Drop page furniture and amendment margins from one page."""
    kept: list[str] = []

    for line in page.split("\n"):
        if any(pattern.match(line) for pattern in FURNITURE):
            continue
        if DIAGRAM_NOTE.match(line):
            continue

        cleaned = strip_margin(line)
        if cleaned is None:
            continue

        kept.append(cleaned)

    return kept


def collapse_blanks(lines: list[str]) -> list[str]:
    """Reduce runs of blank lines to a single separator."""
    out: list[str] = []
    for line in lines:
        if not line.strip():
            if out and not out[-1].strip():
                continue
            out.append("")
        else:
            out.append(line)
    return out


def main() -> None:
    if not PDF_PATH.exists():
        raise SystemExit(f"Missing PDF: {PDF_PATH}")

    pages = extract_pages(PDF_PATH)
    omit_start, omit_end = find_omitted_range(pages)

    lines: list[str] = []
    for index, page in enumerate(pages):
        if omit_start <= index < omit_end:
            continue
        lines.extend(clean_page(page))

    lines = collapse_blanks(lines)
    text = "\n".join(lines).strip() + "\n"

    OUT_PATH.write_text(text, encoding="utf-8")

    omitted = omit_end - omit_start
    print(f"Pages in PDF:      {len(pages)}")
    print(f"Pages omitted:     {omitted} (Schedules 2-4, sign catalogues)")
    print(f"Lines written:     {len(lines)}")
    print(f"Characters:        {len(text)}")
    print(f"Output:            {OUT_PATH}")


if __name__ == "__main__":
    main()
