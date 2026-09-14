"""Extract the Road to Solo Driving handbook into retrievable passages.

The handbook is a two-column InDesign layout, so naive text extraction
interleaves the columns and produces sentences that never appeared in the
document. This script reads text blocks with their coordinates, assigns each to
a column, and emits passages in true reading order.

Every passage carries the printed page number shown in the handbook footer,
not the PDF page index, so citations match what a reader sees on the page.

Run:  python extract_handbook.py <handbook.pdf> <out_dir>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pymupdf

# The PDF has two leading pages before the printed numbering starts, so
# printed page = PDF page index - PAGE_NUMBER_OFFSET. Verified by checking that
# "Strategy 5 - Driving safely at night" lands on printed p.63.
PAGE_NUMBER_OFFSET = 2

# Running headers repeat on every page of a chapter and are not body text.
CHAPTER_HEADERS = [
    "Contents",
    "Getting your learner permit",
    "Learning to drive",
    "Managing risk",
    "Rules and responsibilities",
    "Getting your probationary licence",
    "Keeping your licence",
    "Vehicle safety",
]

# Body text is 9pt Light; headings, "Tip" and "Fact" boxes are 10pt Medium.
HEADING_MIN_SIZE = 9.8

# The right column starts at roughly x=295 on a 595pt page, which is left of
# the true midpoint. Splitting on the midpoint misfiles every right-column
# block and interleaves the two columns.
COLUMN_SPLIT_RATIO = 0.45

MIN_PASSAGE_CHARS = 180
MAX_PASSAGE_CHARS = 1400


def block_text(block: dict) -> tuple[str, float]:
    """Flatten a text block into a string, returning it with its largest font size."""
    lines = []
    max_size = 0.0
    for line in block.get("lines", []):
        spans = line.get("spans", [])
        if not spans:
            continue
        lines.append("".join(span["text"] for span in spans))
        max_size = max(max_size, max(span["size"] for span in spans))
    text = " ".join(lines)
    # InDesign inserts word-joiner and non-breaking characters that survive
    # extraction and break keyword matching later.
    text = text.replace("\u2007", " ").replace("\u00a0", " ").replace("\ufeff", "")
    return re.sub(r"\s+", " ", text).strip(), max_size


def in_left_column(block_rect: tuple[float, ...], page_width: float) -> bool:
    """True when a block starts left of the column boundary."""
    return block_rect[0] < page_width * COLUMN_SPLIT_RATIO


def is_noise(text: str) -> bool:
    """Filter page furniture: folios, running headers, and stray fragments."""
    if not text or len(text) < 3:
        return True
    if text.isdigit():
        return True
    if text in CHAPTER_HEADERS:
        return True
    return False


def extract_pages(pdf_path: str) -> list[dict]:
    """Read every page into ordered blocks with column and heading information."""
    document = pymupdf.open(pdf_path)
    pages = []

    for page_index, page in enumerate(document, start=1):
        printed_page = page_index - PAGE_NUMBER_OFFSET
        if printed_page < 1:
            continue

        raw = page.get_text("dict")
        page_width = page.rect.width
        blocks = []

        for block in raw["blocks"]:
            if block.get("type") != 0:
                continue
            text, size = block_text(block)
            if is_noise(text):
                continue
            blocks.append(
                {
                    "text": text,
                    "size": size,
                    "left": in_left_column(block["bbox"], page_width),
                    "top": block["bbox"][1],
                    "x": block["bbox"][0],
                }
            )

        # Reading order: left column top-to-bottom, then right column.
        blocks.sort(key=lambda item: (not item["left"], item["top"], item["x"]))
        pages.append({"printedPage": printed_page, "blocks": blocks})

    document.close()
    return pages


def chapter_for_page(document: pymupdf.Document, page_index: int) -> str | None:
    """Read the running header to identify which chapter a page belongs to."""
    raw = document[page_index - 1].get_text("dict")
    for block in raw["blocks"]:
        if block.get("type") != 0:
            continue
        text, _ = block_text(block)
        if text in CHAPTER_HEADERS:
            return text
    return None


def build_passages(pdf_path: str) -> list[dict]:
    """Group blocks into passages of a size worth retrieving.

    A passage starts at a heading and accumulates the body blocks that follow
    it, splitting when it grows past the maximum length so no single retrieval
    hit swamps the model's context.
    """
    document = pymupdf.open(pdf_path)
    pages = extract_pages(pdf_path)
    passages: list[dict] = []

    last_chapter: str | None = None

    for page in pages:
        printed_page = page["printedPage"]
        # Chapter opener pages carry no running header, so the chapter carries
        # forward from the previous page rather than being recorded as unfiled.
        found = chapter_for_page(document, printed_page + PAGE_NUMBER_OFFSET)
        chapter = (None if found == "Contents" else found) or last_chapter
        last_chapter = chapter

        current_heading: str | None = None
        buffer: list[str] = []

        def flush() -> None:
            if not buffer:
                return
            body = " ".join(buffer).strip()
            if len(body) < MIN_PASSAGE_CHARS:
                buffer.clear()
                return
            passages.append(
                {
                    "id": f"RTSD_P{printed_page:03d}_{len(passages):04d}",
                    "chapter": chapter,
                    "heading": current_heading,
                    "printedPage": printed_page,
                    "text": body,
                    "sourceId": "SRC_001",
                }
            )
            buffer.clear()

        for block in page["blocks"]:
            if block["size"] >= HEADING_MIN_SIZE and len(block["text"]) < 90:
                flush()
                current_heading = block["text"]
                continue

            buffer.append(block["text"])
            if sum(len(part) for part in buffer) > MAX_PASSAGE_CHARS:
                flush()

        flush()

    document.close()
    return passages


def main(pdf_path: str, out_dir: str) -> None:
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)

    passages = build_passages(pdf_path)

    (output / "handbook-passages.json").write_text(
        json.dumps(
            {
                "source": {
                    "id": "SRC_001",
                    "title": "Road to Solo Driving",
                    "publisher": "Department of Transport and Planning, Victoria",
                    "edition": "April 2023",
                    "pageNumbering": "Printed page numbers as shown in the handbook footer.",
                },
                "passageCount": len(passages),
                "passages": passages,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Plain-text mirror, one file per chapter, for reading and diffing by hand.
    by_chapter: dict[str, list[dict]] = {}
    for passage in passages:
        by_chapter.setdefault(passage["chapter"] or "Unfiled", []).append(passage)

    text_dir = output / "chapters"
    text_dir.mkdir(exist_ok=True)
    for chapter, items in by_chapter.items():
        slug = re.sub(r"[^a-z0-9]+", "-", chapter.lower()).strip("-")
        lines = [f"# {chapter}", ""]
        for item in items:
            lines.append(f"## {item['heading'] or '(continued)'} — p.{item['printedPage']}")
            lines.append(f"[{item['id']}]")
            lines.append(item["text"])
            lines.append("")
        (text_dir / f"{slug}.txt").write_text("\n".join(lines), encoding="utf-8")

    print(f"passages: {len(passages)}")
    for chapter, items in sorted(by_chapter.items(), key=lambda pair: -len(pair[1])):
        print(f"  {len(items):4d}  {chapter}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
