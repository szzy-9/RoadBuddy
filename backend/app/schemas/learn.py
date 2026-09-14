from __future__ import annotations

from pydantic import BaseModel


class LearnSourceResponse(BaseModel):
    id: str
    name: str
    section: str | None = None
    url: str | None = None


class LearnOptionResponse(BaseModel):
    key: str
    text: str


class LearnScenarioResponse(BaseModel):
    type: str
    description: str | None = None
    hazards: list[str] = []
    decision_point: str | None = None
    media_reference: str | None = None


class LearnQuestionResponse(BaseModel):
    id: str
    topic_id: str
    subtopic: str | None = None
    difficulty: str
    question_type: str
    prompt: str
    options: list[LearnOptionResponse]
    explanation: str
    source: LearnSourceResponse
    scenario: LearnScenarioResponse | None = None


class LearnTopicResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    trip_matchable: bool


class LearnTopicsResponse(BaseModel):
    topics: list[LearnTopicResponse]


class LearnQuestionsResponse(BaseModel):
    questions: list[LearnQuestionResponse]
