"""Extract the Road to Solo Driving handbook to plain text for retrieval.

The handbook is the plain-language source a learner actually asks about,
so it is the primary corpus for the Ask tab; the Road Safety Road Rules
supply the statutory detail behind it.

Image-dependent content is omitted. The handbook illustrates signs and
manoeuvres heavily, and those illustrations leave behind bare captions
such as "Children crossing sign" with no picture attached. A caption on
its own tells a reader nothing and, worse, looks like an answer to a
retrieval system, so captions are dropped.

Usage:
    python extract_handbook.py
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
PDF_PATH = HERE / "English - Road to solo driving handbook.pdf"
OUT_PATH = HERE / "road_to_solo_driving.txt"

# Running heads naming the handbook's part, repeated on every page.
RUNNING_HEADS = (
    "Learning to drive",
    "Managing risk",
    "Rules and responsibilities",
    "Getting your licence",
    "Resources",
    "On the road",
)

# A caption orphaned by an omitted illustration: a short line naming a
# sign, signal or marking, with no sentence structure around it.
CAPTION = re.compile(
    r"^\s*[A-Z][A-Za-z0-9''\-/() ]{2,60}"
    r"(sign|signs|signal|signals|marking|markings|line|lines|arrow|light|lights)"
    r"\s*$"
)

# Page numbers and other bare numeric furniture.
BARE_NUMBER = re.compile(r"^\s*\d{1,3}\s*$")

# Sentence-like text is kept even if it ends in one of the caption words.
SENTENCE_HINT = re.compile(r"[.:;?!]|\b(you|your|the|a|an|is|are|must|can|when|if)\b",
                           re.IGNORECASE)


def extract_pages(pdf: Path) -> list[str]:
    # Reading order, not visual layout. The handbook is multi-column with
    # a narrow caption column beside the prose; -layout interleaves the
    # two, splitting sentences and stranding values such as "40 km/h"
    # away from the text they belong to. -nolayout reads each column
    # through, which is what a retrieval system needs.
    result = subprocess.run(
        ["pdftotext", str(pdf), "-"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.split("\f")


def is_caption(line: str) -> bool:
    """Whether a line is a caption left behind by an omitted image."""
    if not CAPTION.match(line):
        return False
    # "Give way signs tell you to slow down" is prose, not a caption.
    return not SENTENCE_HINT.search(line.strip()[:-4])


def clean_page(page: str) -> list[str]:
    kept: list[str] = []
    for raw in page.split("\n"):
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped:
            kept.append("")
            continue
        if stripped in RUNNING_HEADS:
            continue
        if BARE_NUMBER.match(line):
            continue
        if is_caption(line):
            continue

        kept.append(line)
    return kept


def collapse_blanks(lines: list[str]) -> list[str]:
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

    lines: list[str] = []
    captions_dropped = 0
    for page in pages:
        before = sum(1 for line in page.split("\n") if is_caption(line.rstrip()))
        captions_dropped += before
        lines.extend(clean_page(page))

    lines = collapse_blanks(lines)
    text = "\n".join(lines).strip() + "\n"
    OUT_PATH.write_text(text, encoding="utf-8")

    print(f"Pages:             {len(pages)}")
    print(f"Captions omitted:  {captions_dropped} (illustrations not in text)")
    print(f"Lines written:     {len(lines)}")
    print(f"Characters:        {len(text)}")
    print(f"Output:            {OUT_PATH}")


if __name__ == "__main__":
    main()
