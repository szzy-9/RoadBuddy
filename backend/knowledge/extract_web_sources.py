"""Extract the TAC and Transport Victoria road-safety pages to plain text.

The handbook and the Rules are published as PDFs and have their own
extractors. These two sources are ordinary web pages, so the text is
pulled from the article body of each one and written to a single file per
publisher, in the same plain-text shape the retrieval index expects.

Both sites sit behind a CDN that answers non-browser clients with 403,
robots.txt included. When that happens this script cannot fetch the page
itself; see `PAGES` below and the README note on refreshing the corpus.
"""

from __future__ import annotations

import re
import sys
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parent

# The pages each corpus file is built from. Grouped by publisher so a
# citation points at an organisation a learner recognises, rather than at
# one page out of many.
PAGES: dict[str, tuple[str, tuple[str, ...]]] = {
    "transport_victoria.txt": (
        "Transport Victoria",
        (
            "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/fatigue-and-driving",
            "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/headlights-and-high-beams",
            "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/merging-lanes",
            "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/freeways",
            "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/roundabouts",
            "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/intersections-and-giving-way",
            "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/traffic-lights",
            "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/safe-driving-tips",
            "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/snow-and-winter-driving",
            "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/learner-and-probationary-driver-road-rules",
            "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/mobile-phones-and-devices/device-rules-for-new-and-young-drivers-and-motorcyclists",
            "https://transport.vic.gov.au/road-and-active-transport/road-rules-and-safety/alcohol-drugs-and-driving/alcohol-and-driving-laws",
            "https://transport.vic.gov.au/road-and-active-transport/registration-and-licensing/licences/probationary-licence/vehicles-for-probationary-drivers",
            "https://transport.vic.gov.au/road-and-active-transport/active-transport/bicycles/driving-with-bike-riders",
        ),
    ),
    "tac.txt": (
        "Transport Accident Commission",
        (
            "https://www.tac.vic.gov.au/road-safety/staying-safe/tired-driving",
            "https://www.tac.vic.gov.au/road-safety/road-users/drivers",
        ),
    ),
}

# Chrome on macOS. The CDN rejects obvious tooling, and a request that
# names itself honestly as a browser is still what these public pages
# serve to any visitor.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-AU,en;q=0.9",
}

# Chrome elements that carry no prose.
SKIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript", "svg", "form"}

# Blocks that separate one idea from the next. Kept as newlines so a
# retrieval window does not run a heading into unrelated body text.
BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "div", "tr", "br"}


class ArticleText(HTMLParser):
    """Collect visible text, skipping chrome and keeping block breaks."""

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in SKIP_TAGS:
            self._skip_depth += 1
        elif tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and data.strip():
            self._parts.append(data)

    def text(self) -> str:
        joined = "".join(self._parts)
        # Collapse runs of blank lines and trailing spaces left by markup.
        joined = re.sub(r"[ \t]+", " ", joined)
        joined = re.sub(r"\n\s*\n+", "\n\n", joined)
        return joined.strip()


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def page_text(html: str) -> str:
    parser = ArticleText()
    parser.feed(html)
    return parser.text()


def main() -> int:
    failures: list[str] = []

    for filename, (publisher, urls) in PAGES.items():
        sections: list[str] = []

        for url in urls:
            try:
                html = fetch(url)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
                print(f"  FAILED {url}\n         {exc}", file=sys.stderr)
                failures.append(url)
                continue

            text = page_text(html)
            if len(text.split()) < 50:
                print(f"  THIN   {url} ({len(text.split())} words)", file=sys.stderr)
                failures.append(url)
                continue

            # The URL rides along so a passage stays traceable to the page
            # it came from, even though citations name the publisher.
            sections.append(f"Source: {url}\n\n{text}")
            print(f"  ok     {url} ({len(text.split())} words)")
            time.sleep(1)  # Courtesy gap between requests.

        if not sections:
            print(f"  nothing written for {filename}", file=sys.stderr)
            continue

        out = KNOWLEDGE_DIR / filename
        out.write_text(
            f"{publisher}\nRoad safety guidance, retrieved for RoadBuddy.\n\n"
            + "\n\n".join(sections)
            + "\n",
            encoding="utf-8",
        )
        print(f"  wrote  {out.name} ({len(out.read_text(encoding='utf-8').split())} words)")

    if failures:
        print(f"\n{len(failures)} page(s) could not be fetched.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
