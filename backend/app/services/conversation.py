"""Conversational turns that are not corpus questions.

A greeting is not a lookup. Sending "hi" through retrieval either finds
nothing and returns "I could not find that in the handbook", which reads
as a failure, or - for "good morning" - matches passages about morning
driving and wastes a model call on a question nobody asked.

These are matched before retrieval so Buddy can answer the way a person
would: say what it is for, and show what to ask.
"""

from __future__ import annotations

import re

# Whole-message greetings only. "Hi, what is the speed limit?" is a real
# question with a greeting attached and must reach retrieval, so these
# patterns anchor to the entire message rather than searching inside it.
GREETING = re.compile(
    r"^(hi|hey|hello|yo|hiya|howdy|sup"
    r"|good\s*(morning|afternoon|evening|day)"
    r"|g'?day"
    r"|greetings|morning|afternoon|evening)"
    r"[\s!.,?]*(buddy|roadbuddy|there|mate|all)?[\s!.,?]*$",
    re.IGNORECASE,
)

# "What can you do", "who are you" - a request for scope, not a road rule.
CAPABILITY = re.compile(
    r"^(what\s+(can|do)\s+you\s+(do|help\s+with|know)"
    r"|who\s+(are|r)\s+(you|u)"
    r"|what\s+(is|are)\s+(this|you|roadbuddy|buddy)"
    r"|help|start|menu|options)"
    r"[\s!.,?]*$",
    re.IGNORECASE,
)

# Thanks and sign-offs, so a polite close does not look like a failure.
COURTESY = re.compile(
    r"^(thanks?|thank\s*you|ta|cheers|ok|okay|cool|great|nice|bye|goodbye|see\s*ya)"
    r"[\s!.,?]*(buddy|mate)?[\s!.,?]*$",
    re.IGNORECASE,
)

GREETING_REPLY = "Hi, I'm Buddy. How can I help you?"
CAPABILITY_REPLY = (
    "I can answer questions about Victorian road rules and safe driving, "
    "using the Road to Solo Driving handbook and the road rules."
)
COURTESY_REPLY = "No worries. Ask me anything else about driving in Victoria."

# Shown alongside the reply so a new user can see what Buddy is for
# rather than having to guess what it will accept.
EXAMPLE_QUESTIONS = (
    "What is the speed limit in a school zone?",
    "Who has right of way at a roundabout?",
    "How many hours of supervised driving do I need?",
    "What should I do when driving at night?",
)


def small_talk_reply(question: str) -> str | None:
    """Return a conversational reply, or None if this is a real question."""
    text = question.strip()
    if not text:
        return None
    if GREETING.match(text):
        return GREETING_REPLY
    if CAPABILITY.match(text):
        return CAPABILITY_REPLY
    if COURTESY.match(text):
        return COURTESY_REPLY
    return None
