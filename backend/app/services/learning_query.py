from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import (
    LearningQuestion,
    LearningQuestionOption,
    LearningSource,
    LearningTopic,
)
from app.schemas.learn import (
    LearnOptionResponse,
    LearnQuestionResponse,
    LearnQuestionsResponse,
    LearnScenarioResponse,
    LearnSourceResponse,
    LearnTopicResponse,
    LearnTopicsResponse,
)


def get_topics(session: Session) -> LearnTopicsResponse:
    rows = session.execute(
        select(LearningTopic)
        .where(LearningTopic.active.is_(True))
        .order_by(LearningTopic.topic_name)
    ).scalars().all()

    return LearnTopicsResponse(
        topics=[
            LearnTopicResponse(
                id=row.topic_id,
                name=row.topic_name,
                description=row.description,
                trip_matchable=row.trip_matchable,
            )
            for row in rows
        ]
    )


def get_questions_by_topic(
    session: Session,
    topic_id: str,
) -> LearnQuestionsResponse:
    questions = session.execute(
        select(LearningQuestion)
        .where(
            LearningQuestion.topic_id == topic_id,
            LearningQuestion.serve.is_(True),
        )
        .order_by(
            LearningQuestion.difficulty,
            LearningQuestion.question_id,
        )
    ).scalars().all()

    if not questions:
        return LearnQuestionsResponse(questions=[])

    question_ids = [question.question_id for question in questions]

    option_rows = session.execute(
        select(LearningQuestionOption)
        .where(LearningQuestionOption.question_id.in_(question_ids))
        .order_by(
            LearningQuestionOption.question_id,
            LearningQuestionOption.option_key,
        )
    ).scalars().all()

    options_by_question: dict[str, list[LearnOptionResponse]] = defaultdict(list)

    for option in option_rows:
        options_by_question[option.question_id].append(
            LearnOptionResponse(
                key=option.option_key,
                text=option.option_text,
            )
        )

    source_ids = {question.source_id for question in questions}

    source_rows = session.execute(
        select(LearningSource)
        .where(LearningSource.source_id.in_(source_ids))
    ).scalars().all()

    sources_by_id = {
        source.source_id: source
        for source in source_rows
    }

    results = []

    for question in questions:
        source = sources_by_id[question.source_id]

        scenario = None
        if question.scenario_type:
            scenario = LearnScenarioResponse(
                type=question.scenario_type,
                description=question.scenario_description,
                hazards=[
                    value.strip()
                    for value in (question.scenario_hazards or "").split(";")
                    if value.strip()
                ],
                decision_point=question.scenario_decision_point,
                media_reference=question.media_reference,
            )

        results.append(
            LearnQuestionResponse(
                id=question.question_id,
                topic_id=question.topic_id,
                subtopic=question.subtopic,
                difficulty=question.difficulty,
                question_type=question.question_type,
                prompt=question.question_text,
                options=options_by_question[question.question_id],
                explanation=question.explanation,
                source=LearnSourceResponse(
                    id=source.source_id,
                    name=source.source_title,
                    section=question.source_section,
                    url=source.source_url,
                ),
                scenario=scenario,
            )
        )

    return LearnQuestionsResponse(questions=results)
