"""Build RoadBuddy's Learn content bundle from the question-bank workbook.

Reads the reviewed spreadsheet, applies the rewritten distractors, rebalances
the answer key across A/B/C/D, and emits a single JSON bundle the frontend can
import or the backend can serve.

Run:  python build_learn_json.py <workbook.xlsx> <out.json>
"""

from __future__ import annotations

import json
import random
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from rewrites import EXCLUDED, REWRITES

BUNDLE_VERSION = "1.0.0"
OPTION_KEYS = ["A", "B", "C", "D"]

# Workbook condition vocabulary -> the RiskFactor["type"] values the trip check
# actually returns. None means the app has no matching factor yet.
CONDITION_KEY_MAP = {
    "after_dark": "after_dark",
    "raining": "rain",
    "wet_surface": "rain",
    "historical_crash_context": "significant_crash_history",
    "future_speed_zone_context": "high_speed_zone",
    "future_fatigue_context": None,
}

MOCK_TOTAL_QUESTIONS = 32
MOCK_PASS_MARK_PERCENT = 78


def clean(value: object) -> str | None:
    """Return a trimmed string, or None for blank/NaN cells."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def as_iso_date(value: object) -> str | None:
    """Normalise a cell that may hold a datetime, a date, or a date string."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip() or None


def split_keys(value: object) -> list[str]:
    """Split a semicolon-delimited cell into a list of keys."""
    text = clean(value)
    return [part.strip() for part in text.split(";") if part.strip()] if text else []


def risk_factor_types(condition_keys: list[str]) -> list[str]:
    """Map workbook condition keys onto the app's RiskFactor types, deduped."""
    mapped = [CONDITION_KEY_MAP.get(key) for key in condition_keys]
    return sorted({value for value in mapped if value})


def build_options(row: pd.Series, rng: random.Random, position: int) -> tuple[list[dict], str]:
    """Assemble shuffled options and return them with the correct option key.

    The workbook stores the correct answer in a fixed column, and 87 of 100 rows
    have it in option_a. Placing the correct text at a caller-supplied position
    removes that pattern; the distractors are then shuffled among the remaining
    slots so their order is not a tell either.

    Args:
        row: A row from the Questions sheet.
        rng: Seeded RNG, so the same workbook always produces the same bundle.
        position: Index 0-3 at which the correct answer should sit.

    Returns:
        The four options as {key, text} dicts, and the key of the correct one.
    """
    question_id = row["question_id"]
    original_correct_column = f"option_{str(row['correct_option']).strip().lower()}"
    correct_text = clean(row[original_correct_column])

    if question_id in REWRITES:
        override_correct, distractors = REWRITES[question_id]
        correct_text = override_correct or correct_text
        distractors = list(distractors)
    else:
        distractors = [
            clean(row[f"option_{letter}"])
            for letter in "abcd"
            if f"option_{letter}" != original_correct_column
        ]

    rng.shuffle(distractors)
    texts = distractors[:position] + [correct_text] + distractors[position:]

    options = [{"key": key, "text": text} for key, text in zip(OPTION_KEYS, texts)]
    return options, OPTION_KEYS[position]


def build_scenario(row: pd.Series) -> dict | None:
    """Return the scenario block for scenario questions, or None for standard ones."""
    scenario_type = clean(row["scenario_type"])
    if not scenario_type or scenario_type == "standard":
        return None
    return {
        "type": scenario_type,
        "description": clean(row["scenario_description"]),
        "hazards": [item.strip() for item in (clean(row["scenario_hazards"]) or "").split(";") if item.strip()],
        "decisionPoint": clean(row["scenario_decision_point"]),
        "mediaNotice": clean(row["media_reference"]),
    }


def main(workbook_path: str, output_path: str) -> None:
    sources_sheet = pd.read_excel(workbook_path, sheet_name="Sources")
    topics_sheet = pd.read_excel(workbook_path, sheet_name="Topics")
    knowledge_sheet = pd.read_excel(workbook_path, sheet_name="Knowledge Items")
    questions_sheet = pd.read_excel(workbook_path, sheet_name="Questions")
    blueprint_sheet = pd.read_excel(workbook_path, sheet_name="Mock Test Blueprint")

    sources = [
        {
            "id": clean(row["source_id"]),
            "publisher": clean(row["publisher"]),
            "title": clean(row["source_title"]),
            "type": clean(row["source_type"]),
            "jurisdiction": clean(row["jurisdiction"]),
            "url": clean(row["source_url"]),
            "licenceOrTerms": clean(row["licence_or_terms"]),
            "edition": clean(row["edition_or_version"]),
            "lastVerified": as_iso_date(row["last_verified"]),
            "status": clean(row["status"]),
        }
        for _, row in sources_sheet.iterrows()
    ]

    topics = []
    for _, row in topics_sheet.iterrows():
        condition_keys = split_keys(row["trip_condition_keys"])
        topics.append(
            {
                "id": clean(row["topic_id"]),
                "name": clean(row["topic_name"]),
                "description": clean(row["description"]),
                "tripMatchable": bool(row["trip_matchable"]),
                "conditionKeys": condition_keys,
                "riskFactorTypes": risk_factor_types(condition_keys),
                "active": bool(row["active"]),
            }
        )

    knowledge_items = [
        {
            "id": clean(row["knowledge_id"]),
            "topicId": clean(row["topic_id"]),
            "title": clean(row["title"]),
            "summary": clean(row["reviewed_summary"]),
            "sourceId": clean(row["source_id"]),
            "sourceSection": clean(row["source_section"]),
            "audience": split_keys(row["audience"]),
            "keywords": split_keys(row["keywords"]),
            "qualifiers": clean(row["exceptions_or_qualifiers"]),
            "status": clean(row["status"]),
            "reviewedAt": as_iso_date(row["reviewed_at"]),
        }
        for _, row in knowledge_sheet.iterrows()
    ]

    source_by_id = {source["id"]: source for source in sources}

    # A fixed seed keeps the bundle reproducible: rerunning the build on an
    # unchanged workbook produces a byte-identical file, so diffs show real
    # content edits rather than reshuffled options.
    rng = random.Random(20260913)

    # Cycle the correct answer's slot so the key lands close to 25% per letter
    # rather than 87% on A. The frontend should still shuffle at render time.
    served_index = 0
    questions = []
    for _, row in questions_sheet.iterrows():
        question_id = clean(row["question_id"])
        excluded_reason = EXCLUDED.get(question_id)

        options, correct_key = build_options(row, rng, served_index % 4)
        if not excluded_reason:
            served_index += 1

        condition_keys = split_keys(row["trip_match_keys"])
        source_id = clean(row["source_id"])

        questions.append(
            {
                "id": question_id,
                "knowledgeId": clean(row["knowledge_id"]),
                "topicId": clean(row["topic_id"]),
                "subtopic": clean(row["subtopic"]),
                "difficulty": clean(row["difficulty"]),
                "type": clean(row["question_type"]),
                "prompt": clean(row["question"]),
                "options": options,
                "correctOption": correct_key,
                "explanation": clean(row["explanation"]),
                "source": {
                    "id": source_id,
                    "name": (source_by_id.get(source_id) or {}).get("title"),
                    "section": clean(row["source_section"]),
                    "url": (source_by_id.get(source_id) or {}).get("url"),
                },
                "conditionKeys": condition_keys,
                "riskFactorTypes": risk_factor_types(condition_keys),
                "scenario": build_scenario(row),
                "reviewStatus": clean(row["status"]),
                "distractorsRewritten": question_id in REWRITES,
                "serve": excluded_reason is None,
                "excludeReason": excluded_reason,
            }
        )

    blueprint_quotas = [
        {
            "topicId": clean(row["topic_id"]),
            "questionCount": int(row["target_question_count"]),
            "minimumDifficulty": clean(row["minimum_difficulty"]),
        }
        for _, row in blueprint_sheet.iterrows()
        if bool(row["active"])
    ]

    served = [question for question in questions if question["serve"]]
    key_counts = {key: 0 for key in OPTION_KEYS}
    for question in served:
        key_counts[question["correctOption"]] += 1

    bundle = {
        "meta": {
            "bundleVersion": BUNDLE_VERSION,
            "generatedAt": datetime.now().date().isoformat(),
            "sourceWorkbook": Path(workbook_path).name,
            "counts": {
                "topics": len(topics),
                "knowledgeItems": len(knowledge_items),
                "questionsTotal": len(questions),
                "questionsServed": len(served),
                "questionsExcluded": len(questions) - len(served),
                "answerKeyDistribution": key_counts,
            },
            "notices": {
                "notOfficial": (
                    "Practice content only. RoadBuddy is a student project and is not "
                    "an official Victorian licence test."
                ),
                "sourceVerification": (
                    "Handbook sections and page numbers are taken from the Road to "
                    "Solo Driving edition named in sources[].edition and must be "
                    "re-checked against the current edition before release."
                ),
            },
        },
        "conditionKeyMap": CONDITION_KEY_MAP,
        "sources": sources,
        "topics": topics,
        "knowledgeItems": knowledge_items,
        "questions": questions,
        "mockBlueprint": {
            "totalQuestions": MOCK_TOTAL_QUESTIONS,
            "passMarkPercent": MOCK_PASS_MARK_PERCENT,
            "quotas": blueprint_quotas,
        },
    }

    Path(output_path).write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {output_path}")
    print(f"  questions served:   {len(served)} of {len(questions)}")
    print(f"  answer key:         {key_counts}")
    print(f"  blueprint quota:    {sum(q['questionCount'] for q in blueprint_quotas)} questions")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
