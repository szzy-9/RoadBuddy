from __future__ import annotations

import random

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import (
    LearningMockTestConfig,
    LearningMockTestQuota,
    LearningQuestion,
    LearningQuestionOption,
    LearningSource,
    LearningTopic,
    QuestionTripCondition,
)
from app.schemas.learn import (
    LearnOptionResponse,
    LearnQuestionResponse,
    LearnQuestionsResponse,
    LearnScenarioResponse,
    LearnSourceResponse,
    LearnTopicResponse,
    LearnTopicsResponse,
    MockTestQuestionResponse,
    TripLessonRequest,
    TripLessonResponse,
)

DIFFICULTY_RANK = {
    "basic": 1,
    "applied": 2,
    "challenge": 3,
}



RISK_FACTOR_TO_CONDITION_KEYS = {
    "rain": {
        "raining",
        "wet_surface",
    },
    "after_dark": {
        "after_dark",
    },
    "high_speed_zone": {
        "future_speed_zone_context",
    },
    "significant_crash_history": {
        "historical_crash_context",
    },
}


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


def get_mock_test(
    session: Session,
    seed: int | None = None,
) -> MockTestResponse:
    config = session.get(
        LearningMockTestConfig,
        "default",
    )

    if config is None or not config.active:
        return MockTestResponse(
            total_questions=0,
            pass_mark_percent=0,
            questions=[],
        )

    quotas = session.execute(
        select(LearningMockTestQuota)
        .where(
            LearningMockTestQuota.blueprint_id == config.blueprint_id
        )
        .order_by(LearningMockTestQuota.topic_id)
    ).scalars().all()

    rng = random.Random(seed)

    selected_questions: list[LearningQuestion] = []

    for quota in quotas:
        minimum_rank = DIFFICULTY_RANK[quota.minimum_difficulty]

        candidates = session.execute(
            select(LearningQuestion)
            .where(
                LearningQuestion.topic_id == quota.topic_id,
                LearningQuestion.serve.is_(True),
            )
        ).scalars().all()

        eligible = [
            question
            for question in candidates
            if DIFFICULTY_RANK.get(
                question.difficulty,
                0,
            ) >= minimum_rank
        ]

        if len(eligible) < quota.question_count:
            raise ValueError(
                f"Not enough eligible questions for "
                f"{quota.topic_id}: "
                f"need {quota.question_count}, "
                f"found {len(eligible)}"
            )

        rng.shuffle(eligible)

        selected_questions.extend(
            eligible[: quota.question_count]
        )

    rng.shuffle(selected_questions)

    question_ids = [
        question.question_id
        for question in selected_questions
    ]

    option_rows = session.execute(
        select(LearningQuestionOption)
        .where(
            LearningQuestionOption.question_id.in_(
                question_ids
            )
        )
        .order_by(
            LearningQuestionOption.question_id,
            LearningQuestionOption.option_key,
        )
    ).scalars().all()

    options_by_question: dict[
        str,
        list[LearnOptionResponse],
    ] = defaultdict(list)

    for option in option_rows:
        options_by_question[
            option.question_id
        ].append(
            LearnOptionResponse(
                key=option.option_key,
                text=option.option_text,
            )
        )

    results: list[MockTestQuestionResponse] = []

    for question in selected_questions:
        scenario = None

        if question.scenario_type:
            scenario = LearnScenarioResponse(
                type=question.scenario_type,
                description=question.scenario_description,
                hazards=[
                    value.strip()
                    for value in (
                        question.scenario_hazards or ""
                    ).split(";")
                    if value.strip()
                ],
                decision_point=question.scenario_decision_point,
                media_reference=question.media_reference,
            )

        results.append(
            MockTestQuestionResponse(
                id=question.question_id,
                topic_id=question.topic_id,
                difficulty=question.difficulty,
                question_type=question.question_type,
                prompt=question.question_text,
                options=options_by_question[
                    question.question_id
                ],
                scenario=scenario,
            )
        )

    return MockTestResponse(
        total_questions=config.total_questions,
        pass_mark_percent=config.pass_mark_percent,
        questions=results,
    )

def grade_mock_test(
    session: Session,
    request: MockTestGradeRequest,
) -> MockTestGradeResponse:
    config = session.get(
        LearningMockTestConfig,
        "default",
    )

    if config is None or not config.active:
        return MockTestGradeResponse(
            score=0,
            total=0,
            percentage=0.0,
            pass_mark_percent=0,
            passed=False,
            results=[],
        )

    if len(request.answers) != config.total_questions:
        raise ValueError(
            f"Expected {config.total_questions} answers, "
            f"received {len(request.answers)}"
        )

    question_ids = [
        answer.question_id
        for answer in request.answers
    ]

    if len(set(question_ids)) != len(question_ids):
        raise ValueError(
            "Duplicate question IDs are not allowed"
    )



    questions = session.execute(
        select(LearningQuestion)
        .where(
            LearningQuestion.question_id.in_(question_ids),
            LearningQuestion.serve.is_(True),
        )
    ).scalars().all()

    questions_by_id = {
        question.question_id: question
        for question in questions
    }

    if len(questions_by_id) != config.total_questions:
        raise ValueError(
            "One or more question IDs are invalid or unavailable"
    )


    source_ids = {
        question.source_id
        for question in questions
    }

    sources = session.execute(
        select(LearningSource)
        .where(
            LearningSource.source_id.in_(source_ids)
        )
    ).scalars().all()

    sources_by_id = {
        source.source_id: source
        for source in sources
    }

    results: list[MockTestQuestionResult] = []
    score = 0

    for answer in request.answers:
        selected = answer.selected_option.strip().upper()
        
        if selected not in {"A", "B", "C", "D"}:
            raise ValueError(
                f"{answer.question_id}: invalid selected option"
            )

        question = questions_by_id.get(
            answer.question_id
        )

        if question is None:
            continue

        selected_option = (
            answer.selected_option
            .strip()
            .upper()
        )

        correct = (
            selected_option
            == question.correct_option
        )

        if correct:
            score += 1

        source = sources_by_id[
            question.source_id
        ]

        results.append(
            MockTestQuestionResult(
                question_id=question.question_id,
                selected_option=selected_option,
                correct_option=question.correct_option,
                correct=correct,
                explanation=question.explanation,
                source=LearnSourceResponse(
                    id=source.source_id,
                    name=source.source_title,
                    section=question.source_section,
                    url=source.source_url,
                ),
            )
        )

    total = len(results)

    percentage = (
        round(score * 100 / total, 2)
        if total
        else 0.0
    )

    passed = (
        total > 0
        and percentage >= config.pass_mark_percent
    )

    return MockTestGradeResponse(
        score=score,
        total=total,
        percentage=percentage,
        pass_mark_percent=config.pass_mark_percent,
        passed=passed,
        results=results,
    )

def get_trip_lesson(
    session: Session,
    request: TripLessonRequest,
    limit: int = 4,
) -> TripLessonResponse:
    supported_factors = [
        factor
        for factor in request.risk_factors
        if factor in RISK_FACTOR_TO_CONDITION_KEYS
    ]

    if not supported_factors:
        return TripLessonResponse(
            available=False,
            matched_risk_factors=[],
            matched_topics=[],
            questions=[],
        )

    condition_keys = {
        key
        for factor in supported_factors
        for key in RISK_FACTOR_TO_CONDITION_KEYS[factor]
    }

    selected_questions: list[LearningQuestion] = []
    selected_ids: set[str] = set()

    # First, select at least one question for each supported risk factor.
    for factor in supported_factors:
        factor_condition_keys = RISK_FACTOR_TO_CONDITION_KEYS[factor]

        factor_question_ids = session.execute(
            select(QuestionTripCondition.question_id)
            .where(
                QuestionTripCondition.condition_key.in_(
                    factor_condition_keys
                )
            )  
            .distinct()
        ).scalars().all()

        if not factor_question_ids:
            continue

        query = (
            select(LearningQuestion)
            .where(
                LearningQuestion.question_id.in_(
                    factor_question_ids
                ),
                LearningQuestion.serve.is_(True),
            )
        )

        if selected_ids:
            query = query.where(
                ~LearningQuestion.question_id.in_(
                    selected_ids
                )
            )

        question = session.execute(
            query
            .order_by(
                LearningQuestion.difficulty,
                LearningQuestion.question_id,
            )
            .limit(1)
        ).scalar_one_or_none()

        if question is not None:
            selected_questions.append(question)
            selected_ids.add(question.question_id)


    # Then fill any remaining slots with other matching questions.
    all_question_ids = session.execute(
        select(QuestionTripCondition.question_id)
        .where(
            QuestionTripCondition.condition_key.in_(
                condition_keys
            )
        )
        .distinct()
    ).scalars().all()

    remaining = limit - len(selected_questions)

    if remaining > 0:
        extra_query = (
            select(LearningQuestion)
            .where(
                LearningQuestion.question_id.in_(
                    all_question_ids
                ),
                LearningQuestion.serve.is_(True),
            )
        )

        if selected_ids:
            extra_query = extra_query.where(
                ~LearningQuestion.question_id.in_(
                    selected_ids
                )
            )

        extra_questions = session.execute(
            extra_query
            .order_by(
                LearningQuestion.difficulty,
                LearningQuestion.question_id,
            )
            .limit(remaining)
        ).scalars().all()

        selected_questions.extend(extra_questions)

    questions = selected_questions


    if not questions:
        return TripLessonResponse(
            available=False,
            matched_risk_factors=supported_factors,
            matched_topics=[],
            questions=[],
        )

    ids = [
        question.question_id
        for question in questions
    ]

    option_rows = session.execute(
        select(LearningQuestionOption)
        .where(
            LearningQuestionOption.question_id.in_(ids)
        )
        .order_by(
            LearningQuestionOption.question_id,
            LearningQuestionOption.option_key,
        )
    ).scalars().all()

    options_by_question: dict[
        str,
        list[LearnOptionResponse],
    ] = defaultdict(list)

    for option in option_rows:
        options_by_question[
            option.question_id
        ].append(
            LearnOptionResponse(
                key=option.option_key,
                text=option.option_text,
            )
        )

    source_ids = {
        question.source_id
        for question in questions
    }

    sources = session.execute(
        select(LearningSource)
        .where(
            LearningSource.source_id.in_(
                source_ids
            )
        )
    ).scalars().all()

    sources_by_id = {
        source.source_id: source
        for source in sources
    }

    results: list[LearnQuestionResponse] = []

    for question in questions:
        source = sources_by_id[
            question.source_id
        ]

        scenario = None

        if question.scenario_type:
            scenario = LearnScenarioResponse(
                type=question.scenario_type,
                description=question.scenario_description,
                hazards=[
                    value.strip()
                    for value in (
                        question.scenario_hazards or ""
                    ).split(";")
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
                options=options_by_question[
                    question.question_id
                ],
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

    matched_topics = sorted(
        {
            question.topic_id
            for question in questions
        }
    )

    return TripLessonResponse(
        available=True,
        matched_risk_factors=supported_factors,
        matched_topics=matched_topics,
        questions=results,
    )
