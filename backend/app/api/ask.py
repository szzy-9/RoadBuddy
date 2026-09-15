"""Ask endpoint: grounded question answering over the road-safety corpus."""

import logging

from fastapi import APIRouter

from app.schemas.ask import AskRequest, AskResponse, AskSource
from app.services import conversation, knowledge_base, nemotron

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ask", tags=["ask"])

# Shown when the corpus does not cover a question. Ask declines rather
# than guessing, and points at the handbook the app already cites.
NOT_COVERED = (
    "I could not find that in the Road to Solo Driving handbook or the "
    "Victorian road rules. Check the Road to Solo Driving handbook for "
    "anything I do not cover."
)
OFF_TOPIC = (
    "I can only help with road safety, road rules and driving in Victoria."
)
# RoadBuddy never predicts crashes. The app's whole premise is recorded
# history, not prophecy, so Ask points at what is actually known.
CANNOT_PREDICT = (
    "I cannot tell you what will happen on a drive, and I would not guess. "
    "What I can show you is the recorded crash history for a route - run a "
    "trip check, or open the Radar map."
)
UNAVAILABLE = (
    "I could not reach the answer service just now. Please try again."
)

# How much of a passage to show as a citation.
EXCERPT_CHARS = 240


@router.post("/", response_model=AskResponse)
async def ask_question(request: AskRequest) -> AskResponse:
    question = request.question.strip()

    # A greeting is a conversational turn, not a lookup. Answer it before
    # retrieval so "hi" does not come back as "not in the handbook".
    small_talk = conversation.small_talk_reply(question)
    if small_talk is not None:
        return AskResponse(
            answered=True,
            answer=small_talk,
            sources=[],
            reason="greeting",
            examples=list(conversation.EXAMPLE_QUESTIONS),
        )

    matches = knowledge_base.search(question)

    # Retrieval is the gate: if the corpus does not cover the question,
    # the model is never called, so it cannot answer from its own memory.
    if not knowledge_base.is_covered(matches):
        return AskResponse(
            answered=False,
            answer=NOT_COVERED,
            sources=[],
            reason="not_in_sources",
        )

    context = knowledge_base.build_context(matches)

    try:
        reply = await nemotron.ask(question, context)
    except nemotron.NemotronError:
        logger.exception("Ask could not reach the model")
        return AskResponse(
            answered=False,
            answer=UNAVAILABLE,
            sources=[],
            reason="unavailable",
        )

    if reply.refused:
        answer = {
            "off_topic": OFF_TOPIC,
            "cannot_predict": CANNOT_PREDICT,
        }.get(reply.reason, NOT_COVERED)
        return AskResponse(
            answered=False,
            answer=answer,
            sources=[],
            reason=reply.reason,
        )

    # Cite only the distinct documents that were actually given to the
    # model, so a reader can check the answer against its source.
    seen: set[str] = set()
    sources: list[AskSource] = []
    for match in matches:
        name = match.passage.source
        if name in seen:
            continue
        seen.add(name)
        sources.append(
            AskSource(name=name, excerpt=match.passage.text[:EXCERPT_CHARS].strip())
        )

    return AskResponse(answered=True, answer=reply.text, sources=sources)
