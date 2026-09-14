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






class MockTestQuestionResponse(BaseModel):
    id: str
    topic_id: str
    difficulty: str
    question_type: str
    prompt: str
    options: list[LearnOptionResponse]
    scenario: LearnScenarioResponse | None = None


class MockTestResponse(BaseModel):
    total_questions: int
    pass_mark_percent: int
    questions: list[MockTestQuestionResponse]


class MockTestAnswerRequest(BaseModel):
    question_id: str
    selected_option: str


class MockTestGradeRequest(BaseModel):
    answers: list[MockTestAnswerRequest]


class MockTestQuestionResult(BaseModel):
    question_id: str
    selected_option: str
    correct_option: str
    correct: bool
    explanation: str
    source: LearnSourceResponse


class MockTestGradeResponse(BaseModel):
    score: int
    total: int
    percentage: float
    pass_mark_percent: int
    passed: bool
    results: list[MockTestQuestionResult]


class TripLessonRequest(BaseModel):
    risk_factors: list[str]


class TripLessonResponse(BaseModel):
    available: bool
    matched_risk_factors: list[str]
    matched_topics: list[str]
    questions: list[LearnQuestionResponse]
