from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.learn import (
    LearnQuestionsResponse,
    LearnTopicsResponse,
    MockTestResponse,
    MockTestGradeRequest,
    MockTestGradeResponse,
)

from app.services.learning_query import (
    get_mock_test,
    get_questions_by_topic,
    get_topics,
    grade_mock_test,
)

router = APIRouter(prefix="/learn", tags=["learn"])


@router.get("/topics", response_model=LearnTopicsResponse)
def topics(
    session: Annotated[Session, Depends(get_db)],
) -> LearnTopicsResponse:
    return get_topics(session)


@router.get("/questions", response_model=LearnQuestionsResponse)
def questions(
    topic: Annotated[str, Query(min_length=1, max_length=80)],
    session: Annotated[Session, Depends(get_db)],
) -> LearnQuestionsResponse:
    return get_questions_by_topic(session, topic)

@router.get(
    "/mock-test",
    response_model=MockTestResponse,
)
def mock_test(
    session: Annotated[Session, Depends(get_db)],
    seed: Annotated[int | None, Query()] = None,
) -> MockTestResponse:
    return get_mock_test(
        session,
        seed=seed,
    )

@router.post(
    "/mock-test/grade",
    response_model=MockTestGradeResponse,
)
def grade_test(
    request: MockTestGradeRequest,
    session: Annotated[Session, Depends(get_db)],
) -> MockTestGradeResponse:
    try:
        return grade_mock_test(
            session,
            request,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc













