"""Rank handbook passages against each RoadBuddy topic.

Produces the shortlist a content reviewer works from: for every topic, the
handbook passages most likely to contain the facts a knowledge item should
paraphrase, with the printed page number already attached.

Run:  python map_topics.py <passages.json> <out.json>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Terms that identify a topic in handbook wording, not RoadBuddy wording.
TOPIC_TERMS: dict[str, list[str]] = {
    "night_driving": ["night", "dark", "headlight", "high beam", "low beam", "dusk", "glare", "visibility"],
    "wet_weather": ["wet", "rain", "slippery", "aquaplan", "skid", "fog", "puddle", "grip", "wiper"],
    "speed_management": ["speed limit", "km/h", "stopping distance", "reaction", "speeding", "safe speed", "school zone"],
    "hazard_awareness": ["hazard", "scan", "observ", "anticipat", "blind spot", "head check", "mirror", "perception"],
    "following_distance": ["following distance", "two second", "three or four second", "safety margin", "gap", "tailgat"],
    "intersections": ["intersection", "give way", "roundabout", "traffic light", "stop sign", "turning right", "turning left", "yellow"],
    "signs_markings": ["sign", "line marking", "dividing line", "lane marking", "road marking", "regulatory", "warning sign"],
    "sharing_road": ["pedestrian", "cyclist", "bicycle", "motorcycl", "tram", "truck", "heavy vehicle", "vulnerable", "crossing"],
    "distraction": ["distract", "mobile phone", "device", "navigation", "passenger", "texting", "attention"],
    "p_plate_rules": ["probationary", "P1", "P2", "P plate", "zero BAC", "blood alcohol", "peer passenger", "licence condition", "demerit"],
    "fatigue": ["fatigue", "tired", "drowsy", "sleep", "rest break", "microsleep", "alert"],
    "vehicle_safety": ["roadworth", "tyre", "brake", "seatbelt", "restraint", "airbag", "ANCAP", "maintenance", "windscreen"],
}


def score(text: str, terms: list[str]) -> tuple[int, list[str]]:
    """Count how many topic terms appear in a passage, returning the matches."""
    lowered = text.lower()
    hits = [term for term in terms if re.search(re.escape(term.lower()), lowered)]
    return len(hits), hits


def main(passages_path: str, output_path: str) -> None:
    data = json.loads(Path(passages_path).read_text(encoding="utf-8"))
    passages = data["passages"]

    result = {}
    for topic_id, terms in TOPIC_TERMS.items():
        ranked = []
        for passage in passages:
            hit_count, hits = score(passage["text"], terms)
            if hit_count == 0:
                continue
            ranked.append(
                {
                    "passageId": passage["id"],
                    "printedPage": passage["printedPage"],
                    "chapter": passage["chapter"],
                    "heading": passage["heading"],
                    "matchedTerms": hits,
                    "score": hit_count,
                    "excerpt": passage["text"][:300],
                }
            )
        ranked.sort(key=lambda item: (-item["score"], item["printedPage"]))
        result[topic_id] = ranked[:12]

    Path(output_path).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    for topic_id, items in result.items():
        pages = sorted({item["printedPage"] for item in items})
        print(f"{topic_id:20s} {len(items):3d} candidates  pages {pages}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
