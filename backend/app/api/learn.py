from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.schemas.learn import (
    LearnQuestionsResponse,
    LearnTopicsResponse,
)
from app.services.learning_query import (
    get_questions_by_topic,
    get_topics,
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
