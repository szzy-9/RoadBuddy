from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from app.database.connection import SessionLocal
from app.database.models import (
    KnowledgeItem,
    LearningMockTestConfig,
    LearningMockTestQuota,
    LearningQuestion,
    LearningQuestionOption,
    LearningSource,
    LearningTopic,
    QuestionTripCondition,
)

CONTENT_PATH = Path(__file__).resolve().parents[1] / "content" / "learn_content.json"


def load_content() -> dict:
    with CONTENT_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def upsert_sources(session, sources: list[dict]) -> None:
    for source in sources:
        stmt = insert(LearningSource).values(
            source_id=source["id"],
            publisher=source["publisher"],
            source_title=source["title"],
            source_type=source.get("type"),
            jurisdiction=source.get("jurisdiction"),
            source_url=source.get("url"),
            licence_or_terms=source.get("licenceOrTerms"),
            edition_or_version=source.get("edition"),
            last_verified=source.get("lastVerified"),
            status=source.get("status") or "active",
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=[LearningSource.source_id],
            set_={
                "publisher": stmt.excluded.publisher,
                "source_title": stmt.excluded.source_title,
                "source_type": stmt.excluded.source_type,
                "jurisdiction": stmt.excluded.jurisdiction,
                "source_url": stmt.excluded.source_url,
                "licence_or_terms": stmt.excluded.licence_or_terms,
                "edition_or_version": stmt.excluded.edition_or_version,
                "last_verified": stmt.excluded.last_verified,
                "status": stmt.excluded.status,
            },
        )

        session.execute(stmt)


def upsert_topics(session, topics: list[dict]) -> None:
    for topic in topics:
        stmt = insert(LearningTopic).values(
            topic_id=topic["id"],
            topic_name=topic["name"],
            description=topic.get("description"),
            trip_matchable=topic.get("tripMatchable", False),
            active=topic.get("active", True),
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=[LearningTopic.topic_id],
            set_={
                "topic_name": stmt.excluded.topic_name,
                "description": stmt.excluded.description,
                "trip_matchable": stmt.excluded.trip_matchable,
                "active": stmt.excluded.active,
            },
        )

        session.execute(stmt)


def upsert_knowledge_items(session, items: list[dict]) -> None:
    for item in items:
        stmt = insert(KnowledgeItem).values(
            knowledge_id=item["id"],
            topic_id=item["topicId"],
            source_id=item["sourceId"],
            title=item["title"],
            reviewed_summary=item["summary"],
            source_section=item.get("sourceSection"),
            audience=";".join(item.get("audience", [])),
            keywords=";".join(item.get("keywords", [])),
            qualifiers=item.get("qualifiers"),
            status=item.get("status") or "review",
            reviewed_at=item.get("reviewedAt"),
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=[KnowledgeItem.knowledge_id],
            set_={
                "topic_id": stmt.excluded.topic_id,
                "source_id": stmt.excluded.source_id,
                "title": stmt.excluded.title,
                "reviewed_summary": stmt.excluded.reviewed_summary,
                "source_section": stmt.excluded.source_section,
                "audience": stmt.excluded.audience,
                "keywords": stmt.excluded.keywords,
                "qualifiers": stmt.excluded.qualifiers,
                "status": stmt.excluded.status,
                "reviewed_at": stmt.excluded.reviewed_at,
            },
        )

        session.execute(stmt)


def upsert_questions(session, questions: list[dict]) -> None:
    for question in questions:
        scenario = question.get("scenario") or {}

        stmt = insert(LearningQuestion).values(
            question_id=question["id"],
            knowledge_id=question["knowledgeId"],
            topic_id=question["topicId"],
            source_id=question["source"]["id"],
            subtopic=question.get("subtopic"),
            difficulty=question["difficulty"],
            question_type=question["type"],
            question_text=question["prompt"],
            correct_option=question["correctOption"],
            explanation=question["explanation"],
            source_section=question["source"].get("section"),
            review_status=question["reviewStatus"],
            serve=question["serve"],
            scenario_type=scenario.get("type"),
            scenario_description=scenario.get("description"),
            scenario_hazards=";".join(scenario.get("hazards", [])),
            scenario_decision_point=scenario.get("decisionPoint"),
            media_reference=scenario.get("mediaNotice"),
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=[LearningQuestion.question_id],
            set_={
                "knowledge_id": stmt.excluded.knowledge_id,
                "topic_id": stmt.excluded.topic_id,
                "source_id": stmt.excluded.source_id,
                "subtopic": stmt.excluded.subtopic,
                "difficulty": stmt.excluded.difficulty,
                "question_type": stmt.excluded.question_type,
                "question_text": stmt.excluded.question_text,
                "correct_option": stmt.excluded.correct_option,
                "explanation": stmt.excluded.explanation,
                "source_section": stmt.excluded.source_section,
                "review_status": stmt.excluded.review_status,
                "serve": stmt.excluded.serve,
                "scenario_type": stmt.excluded.scenario_type,
                "scenario_description": stmt.excluded.scenario_description,
                "scenario_hazards": stmt.excluded.scenario_hazards,
                "scenario_decision_point": stmt.excluded.scenario_decision_point,
                "media_reference": stmt.excluded.media_reference,
            },
        )

        session.execute(stmt)

        session.execute(
            delete(LearningQuestionOption).where(
                LearningQuestionOption.question_id == question["id"]
            )
        )

        for option in question["options"]:
            session.add(
                LearningQuestionOption(
                    question_id=question["id"],
                    option_key=option["key"],
                    option_text=option["text"],
                )
            )

        session.execute(
            delete(QuestionTripCondition).where(
                QuestionTripCondition.question_id == question["id"]
            )
        )

        for condition_key in question.get("conditionKeys", []):
            session.add(
                QuestionTripCondition(
                    question_id=question["id"],
                    condition_key=condition_key,
                )
            )

def upsert_mock_blueprint(session, blueprint: dict) -> None:
    blueprint_id = "default"

    config_stmt = insert(LearningMockTestConfig).values(
        blueprint_id=blueprint_id,
        total_questions=blueprint["totalQuestions"],
        pass_mark_percent=blueprint["passMarkPercent"],
        active=True,
    )

    config_stmt = config_stmt.on_conflict_do_update(
        index_elements=[
            LearningMockTestConfig.blueprint_id
        ],
        set_={
            "total_questions": config_stmt.excluded.total_questions,
            "pass_mark_percent": config_stmt.excluded.pass_mark_percent,
            "active": config_stmt.excluded.active,
        },
    )

    session.execute(config_stmt)

    session.execute(
        delete(LearningMockTestQuota).where(
            LearningMockTestQuota.blueprint_id == blueprint_id
        )
    )

    for quota in blueprint["quotas"]:
        session.add(
            LearningMockTestQuota(
                blueprint_id=blueprint_id,
                topic_id=quota["topicId"],
                question_count=quota["questionCount"],
                minimum_difficulty=quota["minimumDifficulty"],
            )
        )



def main() -> None:
    content = load_content()

    with SessionLocal() as session:
        try:
            upsert_sources(session, content["sources"])
            upsert_topics(session, content["topics"])
            upsert_knowledge_items(session, content["knowledgeItems"])
            upsert_questions(session, content["questions"])
            upsert_mock_blueprint(
                session,
                content["mockBlueprint"],
            )

            session.commit()
        except Exception:
            session.rollback()
            raise

    counts = content["meta"]["counts"]

    print("Learn content loaded successfully.")
    print(f"Sources: {len(content['sources'])}")
    print(f"Topics: {len(content['topics'])}")
    print(f"Knowledge items: {len(content['knowledgeItems'])}")
    print(f"Questions: {counts['questionsTotal']}")
    print(f"Served: {counts['questionsServed']}")


if __name__ == "__main__":
    main()
