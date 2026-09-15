"""Retrieval over the extracted road-safety corpus.

The corpus is plain text on disk rather than a vector store: at roughly a
megabyte it fits in memory, and lexical scoring answers the kind of
question the Ask tab receives ("what is the speed limit in a school
zone") without an embedding service to run or pay for. Swapping in
embeddings later only means replacing `search`.

Retrieval decides whether Ask answers at all. When nothing scores above
MIN_SCORE the question is treated as outside the corpus and the caller
declines, so the model is never asked to answer from its own memory.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"

# Ordered by how directly each source answers a learner's question. The
# handbook is plain-language guidance written for new drivers; the Rules
# are statutory text, correct but phrased for lawyers.
#
# The weight tilts scoring toward the handbook. Without it the Rules win
# on size alone - they are more than twice as long, so they hold more
# passages containing any given term - and a learner asking "what is the
# speed limit in a school zone" gets rule 23, which says only that the
# limit is on the signs. The handbook gives the number.
SOURCES = (
    ("Road to Solo Driving handbook", "road_to_solo_driving.txt", 1.35),
    ("Road Safety Road Rules 2017", "road_rules_2017.txt", 1.0),
)

# Always keep room for the best handbook passage, so statutory text
# cannot fill every slot and hide the plain-language answer.
GUARANTEED_HANDBOOK_SLOTS = 1

# A passage is a few hundred words: large enough to carry a whole rule,
# small enough that an answer is not buried in unrelated text.
TARGET_WORDS = 220
OVERLAP_WORDS = 50

# Below this score the corpus is treated as not covering the question.
# Tuned against the sample questions in tests; raising it makes Ask
# decline more often, lowering it invites ungrounded answers.
MIN_SCORE = 0.045

STOP_WORDS = frozenset("""
a an the of in on at to for and or with by from is are was were be been being
do does did can could should would may might must shall will i you it its
this that these those there here what when where which who whom how why
if then than as but not no nor so such about into over under again further
my your his her their our me him them us we they he she
""".split())


@dataclass(frozen=True)
class Passage:
    """One retrievable chunk of the corpus."""

    source: str
    text: str
    weight: float = 1.0


@dataclass(frozen=True)
class Match:
    passage: Passage
    score: float


def tokenize(text: str) -> list[str]:
    """Lowercase word tokens with stop words removed."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]


def _split_passages(text: str, source: str, weight: float) -> list[Passage]:
    """Cut one document into overlapping word windows.

    Overlap keeps a rule that straddles a boundary retrievable from either
    side, which matters because the legislation runs one provision
    straight into the next.
    """
    words = text.split()
    if not words:
        return []

    passages: list[Passage] = []
    step = max(1, TARGET_WORDS - OVERLAP_WORDS)
    for start in range(0, len(words), step):
        window = words[start:start + TARGET_WORDS]
        if len(window) < 30 and passages:
            break
        passages.append(
            Passage(source=source, text=" ".join(window), weight=weight)
        )
    return passages


@lru_cache(maxsize=1)
def _index() -> tuple[list[Passage], list[Counter], Counter, int]:
    """Build the passage list and term statistics once per process."""
    passages: list[Passage] = []
    for label, filename, weight in SOURCES:
        path = KNOWLEDGE_DIR / filename
        if not path.exists():
            continue
        passages.extend(
            _split_passages(path.read_text(encoding="utf-8"), label, weight)
        )

    term_counts = [Counter(tokenize(p.text)) for p in passages]

    # Document frequency, for inverse-document-frequency weighting: a word
    # in every passage ("driver", "road") says far less about relevance
    # than a rare one ("roundabout", "tram").
    document_frequency: Counter = Counter()
    for counts in term_counts:
        document_frequency.update(counts.keys())

    return passages, term_counts, document_frequency, len(passages)


def search(question: str, limit: int = 4) -> list[Match]:
    """Return the passages most likely to answer `question`, best first."""
    passages, term_counts, document_frequency, total = _index()
    if not passages:
        return []

    query = Counter(tokenize(question))
    if not query:
        return []

    scored: list[Match] = []
    for passage, counts in zip(passages, term_counts):
        if not counts:
            continue

        overlap = 0.0
        for term, query_count in query.items():
            passage_count = counts.get(term)
            if not passage_count:
                continue
            idf = math.log((total + 1) / (document_frequency[term] + 1)) + 1
            overlap += query_count * math.log(1 + passage_count) * idf

        if overlap <= 0:
            continue

        # Normalise by passage length so a long passage does not win on
        # sheer size, and by query length so scores compare across
        # questions of different wording.
        score = overlap / (math.sqrt(sum(counts.values())) * len(query))
        scored.append(Match(passage=passage, score=score * passage.weight))

    scored.sort(key=lambda m: m.score, reverse=True)

    # Reserve a slot for the handbook. The statutory text can otherwise
    # take every slot and leave the plain-language answer unretrieved.
    chosen = scored[:limit]
    handbook = SOURCES[0][0]
    if limit > GUARANTEED_HANDBOOK_SLOTS and not any(
        m.passage.source == handbook for m in chosen
    ):
        best = next((m for m in scored if m.passage.source == handbook), None)
        if best is not None:
            chosen = chosen[:limit - GUARANTEED_HANDBOOK_SLOTS] + [best]

    return chosen


def build_context(matches: list[Match]) -> str:
    """Render matches as the grounding block given to the model."""
    blocks = []
    for index, match in enumerate(matches, start=1):
        blocks.append(f"[{index}] Source: {match.passage.source}\n{match.passage.text}")
    return "\n\n".join(blocks)


def is_covered(matches: list[Match]) -> bool:
    """Whether the corpus actually covers the question."""
    return bool(matches) and matches[0].score >= MIN_SCORE
