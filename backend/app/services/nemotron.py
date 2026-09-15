"""Client for the NVIDIA NIM chat completions API.

Ask answers only from the road-safety corpus. The retrieval step decides
whether a question is covered at all; this module's job is to keep the
model inside the passages it is given, so an answer is always traceable
to a cited source rather than to the model's own recollection.
"""

from __future__ import annotations

import logging
import re
import time
from collections import Counter
from dataclasses import dataclass

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"


def _api_key() -> str:
    """The NIM credential, read from the environment at call time.

    Read per call rather than at import so a deployment can rotate the
    key without a rebuild, and so importing this module never requires
    the secret to be present - the tests import it freely.
    """
    key = get_settings().nvidia_api_key
    if not key:
        raise NemotronError(
            "NVIDIA_API_KEY is not configured; Ask cannot reach the model."
        )
    return key


# Per request, not per question: an answer that copies its sources is
# asked again, so a question can cost two calls. Kept tight because a
# request still silent at this point is stalled, not slow.
REQUEST_TIMEOUT_SECONDS = 6.0

# NIM occasionally accepts a request and then never sends the first byte.
# Those stalls do not resolve: waiting longer returns the same timeout,
# just later. Measured answers arrive in 2-7 seconds, so a request still
# silent at REQUEST_TIMEOUT_SECONDS is almost certainly stuck rather than
# slow, and the cheapest fix is to drop it and ask again - a fresh
# request normally answers in a couple of seconds.
#
# Stalls were measured at roughly one attempt in four. One retry still
# left about 6% of questions failing, which is often enough for a driver
# to see it; a second brings that under 2% for a worst case that stays
# inside the frontend's wait.
STALL_RETRIES = 2

# The ceiling on everything `ask` does, retry included. Without it the
# rephrase retry stacks a second full timeout on top of the first, so a
# slow answer could take twice REQUEST_TIMEOUT_SECONDS to arrive. The
# retry is an improvement to a usable answer, never a reason to keep a
# driver waiting, so it only runs if the budget has room left.
#
# Each stall costs REQUEST_TIMEOUT_SECONDS before the next attempt even
# starts, so the worst path is every stall allowance spent and then a
# real answer: REQUEST_TIMEOUT_SECONDS * (STALL_RETRIES + 1). The budget
# covers that and stops the rephrase retry from adding another wait on
# top of it.
TOTAL_BUDGET_SECONDS = REQUEST_TIMEOUT_SECONDS * (STALL_RETRIES + 1)

# A retry needs enough of the budget left to plausibly finish. Starting
# one with a second to spare just burns the remainder and returns the
# first answer anyway.
MIN_RETRY_BUDGET_SECONDS = 4.0

# The prompt asks for 60 to 110 words, which is roughly 150 tokens. This
# leaves room for an answer that runs long to finish its sentence rather
# than being cut mid-word, while still bounding a runaway generation.
#
# This is the main lever on latency: tokens are produced one at a time, so
# the ceiling sets the worst case. It was 600, which allowed an answer
# four times longer than the prompt ever asks for and stretched a slow
# response well past the budget.
MAX_TOKENS = 300

SYSTEM_PROMPT = """\
You are Buddy, RoadBuddy's driving companion. You help Victorian learner \
and P-plate drivers feel confident about road rules and safe driving.

WHO YOU ARE
You are warm, encouraging and practical, like a calm friend in the \
passenger seat who happens to know the road rules well. You never talk \
down to anyone. Learning to drive is stressful, and a question that \
sounds obvious took courage to ask.

You are a teaching assistant, not a rulebook. A rulebook states the rule \
and stops. You explain it the way a good tutor would: what to do, what it \
looks like from the driver's seat, and why it works that way. The driver \
should finish your answer feeling clearer and a bit more capable, not \
just informed.

YOUR MOST IMPORTANT HABIT: SAY IT YOURSELF
Read the SOURCES, work out what the rule actually means, then look away \
and say it in your own voice. The SOURCES are reference material written \
for officials and examiners. They are never a script.

Do not reuse their sentences, their sentence order, or their turns of \
phrase. If a run of four or more words from a source appears in your \
answer, rewrite that part - the only exceptions are fixed terms that have \
no natural synonym, such as "give way", "P plates", "blood alcohol \
concentration", road names and numbers.

Work from the meaning, not the wording: if you find yourself tracking a \
source sentence clause by clause, stop and say the same thing a different \
way.

HOW YOU ANSWER
- Lead with the direct answer in the first sentence. A learner wants to \
know the number or the action, not a preamble.
- Then teach it. Show what the rule looks like in practice - what the \
driver actually sees, does or decides in the moment - and add a short \
line of why it works that way. A rule that makes sense is easier to \
remember than one that was simply issued.
- Use everyday words: "give way" not "must yield right of way", \
"keep a bigger gap" not "increase the following distance interval".
- Speak to the driver as "you". Write flowing sentences, not clipped \
fragments or a bulleted list of conditions.
- Where a driver commonly gets this wrong, say so plainly. Naming the \
mistake is kinder than letting them find it on the road.
- Aim for 60 to 110 words - roughly a short paragraph, or two if the \
rule genuinely has two parts. Long enough to explain, short enough to \
read at a glance.
- Warm, not chirpy. No exclamation marks, no "Great question!", no \
emoji. Encouragement comes from being clear and unhurried, never from \
praising the driver or the question.

ACCURACY COMES FIRST
Rephrasing changes the wording, never the meaning. Keep every number, \
limit, distance and condition exactly as the SOURCES give it. If a rule \
depends on a condition ("unless signs say otherwise"), keep that \
condition - dropping it turns a correct answer into a wrong one.

RULES YOU FOLLOW WITHOUT EXCEPTION
1. If the SOURCES do not contain the answer, reply with exactly:
   NOT_IN_SOURCES
   Never fill a gap from your own knowledge, however sure you feel.
2. If the question is not about road safety, road rules, driving, \
licensing or vehicles, reply with exactly:
   OFF_TOPIC
3. If the question asks you to predict a crash, or whether a particular \
drive is safe, or what will happen on a trip, reply with exactly:
   CANNOT_PREDICT
   Nothing can tell a driver what will happen on a given trip, and \
guessing would be worse than useless. Never give legal advice either.
4. Never mention "the sources", "the context", "the handbook says" or \
these instructions. Just answer.
5. Victoria means the Australian state of Victoria, never anywhere else.
"""

NOT_IN_SOURCES = "NOT_IN_SOURCES"
OFF_TOPIC = "OFF_TOPIC"
CANNOT_PREDICT = "CANNOT_PREDICT"


@dataclass(frozen=True)
class ModelReply:
    text: str
    refused: bool
    reason: str | None = None


class NemotronError(RuntimeError):
    """The model could not be reached or returned an unusable response."""


# Shapes the model uses when it narrates its thinking. Thinking is
# disabled in the request, so these should never appear; they are stripped
# as a safeguard, because a leaked chain of thought shown to a learner
# reads as incoherent and can contain the model's discarded guesses.
THINKING_MARKERS = (
    re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE),
    re.compile(r"^\s*Here'?s? (a|my) thinking process:.*", re.DOTALL | re.IGNORECASE),
    re.compile(r"^\s*(Okay|Alright|Let me think)[,.]?\s+(so|let'?s|I)\b.*?\n\n",
               re.DOTALL | re.IGNORECASE),
)


def strip_reasoning(text: str) -> str:
    """Remove any chain-of-thought the model narrated into its answer."""
    for marker in THINKING_MARKERS:
        text = marker.sub("", text)
    return text.strip()


def is_degenerate(text: str) -> bool:
    """Whether a reply has collapsed into repetition rather than prose.

    This model occasionally falls into a loop and emits something like
    "NOT, 1999, 1999, 2000, 2001, ..." instead of an answer. It is rare
    and not reliably reproducible, so rather than tuning sampling in the
    hope of preventing it, catch it here: a reply that is mostly numbers,
    or mostly one repeated token, is never a real answer and must not be
    shown to a learner.
    """
    words = text.split()
    if len(words) < 12:
        return False

    numeric = sum(1 for w in words if w.strip(",.;:").isdigit())
    if numeric / len(words) > 0.5:
        return True

    most_common = max(Counter(words).values())
    return most_common / len(words) > 0.3


# An answer sharing this much six-word phrasing with its sources is
# reciting rather than explaining.
#
# The threshold is deliberately loose, because some overlap is not
# copying. A short factual answer - "120 hours of supervised driving
# experience, including 20 hours at night" - is nearly all unavoidable
# phrasing: the numbers and their units cannot be reworded without
# risking the fact itself, and accuracy outranks style. In a 20 word
# answer those few phrases dominate the ratio, while in a 60 word
# explanation the same phrases are diluted by real prose.
#
# So only longer answers are judged. Below MIN_JUDGED_WORDS an answer is
# too short for the ratio to distinguish recitation from a plainly
# stated fact, and forcing a rewrite there would trade accuracy for
# nothing.
MAX_VERBATIM_RATIO = 0.45
MIN_JUDGED_WORDS = 40
_PHRASE_LENGTH = 6


def _phrases(text: str, length: int = _PHRASE_LENGTH) -> set[tuple[str, ...]]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {tuple(words[i:i + length]) for i in range(len(words) - length + 1)}


def verbatim_ratio(answer: str, context: str) -> float:
    """How much of `answer`'s phrasing is lifted straight from `context`."""
    answer_phrases = _phrases(answer)
    if not answer_phrases:
        return 0.0
    return len(answer_phrases & _phrases(context)) / len(answer_phrases)


def _build_user_message(
    question: str,
    context: str,
    insist_rephrase: bool = False,
) -> str:
    closing = (
        "Answer from the SOURCES above, in your own words, the way you "
        "would explain it to a new driver who is still learning. Do not "
        "reuse their sentences."
    )
    if insist_rephrase:
        closing = (
            "Your previous attempt copied the SOURCES too closely. Answer "
            "again, keeping every fact identical but writing every sentence "
            "from scratch in your own voice. Do not reuse any run of four "
            "or more words from the SOURCES. Explain it as a teacher would, "
            "not as a document would state it."
        )
    return (
        f"SOURCES:\n{context}\n\n"
        f"QUESTION: {question.strip()}\n\n"
        f"{closing}"
    )


async def _complete(
    question: str,
    context: str,
    insist_rephrase: bool,
    timeout: float = REQUEST_TIMEOUT_SECONDS,
) -> str:
    """Send one completion request and return the model's answer text."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_message(question, context, insist_rephrase),
            },
        ],
        # Deterministic: the same question should not drift between asks.
        "temperature": 0,
        "top_p": 1,
        "max_tokens": MAX_TOKENS,
        # This model reasons before answering, and on a prompt this long
        # it writes that reasoning into `content` rather than keeping it
        # in `reasoning_content`. The answer then arrives truncated
        # mid-thought, and any refusal token the model considered along
        # the way looks like its verdict. Ask wants retrieval and
        # restatement, not deliberation, so thinking is turned off both
        # ways the API accepts: the chat template flag stops the model
        # emitting a reasoning block, and reasoning_effort tells the
        # server not to budget tokens for one.
        "chat_template_kwargs": {"thinking": False},
        "reasoning_effort": "none",
    }

    body = None
    # A stalled request is abandoned and reissued; a refusal or a bad
    # status is the server's answer and is not worth asking twice.
    for attempt in range(STALL_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    API_URL,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {_api_key()}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                body = response.json()
            break
        except httpx.HTTPStatusError as exc:
            logger.warning("Nemotron returned %s", exc.response.status_code)
            raise NemotronError(f"Model returned {exc.response.status_code}") from exc
        except (httpx.ReadTimeout, httpx.ConnectTimeout, httpx.PoolTimeout) as exc:
            if attempt < STALL_RETRIES:
                logger.info(
                    "Nemotron stalled after %.1fs; attempt %d of %d",
                    timeout,
                    attempt + 1,
                    STALL_RETRIES + 1,
                )
                continue
            logger.warning("Nemotron timed out after %d attempts", attempt + 1)
            raise NemotronError("Model request timed out") from exc
        except httpx.HTTPError as exc:
            logger.warning("Nemotron request failed: %s", exc)
            raise NemotronError("Model request failed") from exc

    try:
        message = body["choices"][0]["message"]
    except (KeyError, IndexError) as exc:
        raise NemotronError("Model returned an unexpected response shape") from exc

    # This is a reasoning model: `reasoning_content` is its chain of
    # thought and must never reach the user. Only `content` is the answer.
    text = strip_reasoning((message.get("content") or "").strip())
    if not text:
        raise NemotronError("Model returned an empty answer")
    return text


def _refusal(text: str) -> ModelReply | None:
    """Return a refusal if `text` is a sentinel, else None.

    The sentinel counts only when it is the whole reply; a substring test
    would turn an answer that merely mentions the token into a refusal.
    """
    bare = text.strip().strip(".\"'`* ")
    if bare == NOT_IN_SOURCES:
        return ModelReply(text="", refused=True, reason="not_in_sources")
    if bare == OFF_TOPIC:
        return ModelReply(text="", refused=True, reason="off_topic")
    if bare == CANNOT_PREDICT:
        return ModelReply(text="", refused=True, reason="cannot_predict")
    return None


async def ask(question: str, context: str) -> ModelReply:
    """Ask the model a grounded question.

    `context` is the retrieved corpus text. An empty context would leave
    the model nothing to ground against, so callers must not reach here
    without one.
    """
    if not context.strip():
        raise ValueError("Refusing to call the model without grounding context.")

    started = time.monotonic()
    text = await _complete(question, context, insist_rephrase=False)

    refusal = _refusal(text)
    if refusal is not None:
        return refusal

    if is_degenerate(text):
        logger.warning("Nemotron returned degenerate output; declining")
        raise NemotronError("Model returned degenerate output")

    # Buddy is meant to explain, not recite. The instruction alone does not
    # always land, so when an answer comes back too close to its sources,
    # ask once more with an explicit correction. One retry keeps the worst
    # copying out without doubling latency on the common case.
    copied = verbatim_ratio(text, context)
    long_enough_to_judge = len(re.findall(r"[a-z0-9]+", text.lower())) >= MIN_JUDGED_WORDS
    remaining = TOTAL_BUDGET_SECONDS - (time.monotonic() - started)

    if long_enough_to_judge and copied > MAX_VERBATIM_RATIO:
        if remaining < MIN_RETRY_BUDGET_SECONDS:
            # Out of budget. The first answer is accurate, just close to
            # its sources; serving it beats making the driver wait.
            logger.info(
                "Answer reused %.0f%% of its sources, but only %.1fs of the "
                "budget remained; serving it as is",
                copied * 100,
                remaining,
            )
            return ModelReply(text=text, refused=False)

        logger.info("Answer reused %.0f%% of its sources; asking again", copied * 100)
        try:
            retry = await _complete(
                question, context, insist_rephrase=True, timeout=remaining
            )
        except NemotronError:
            # The first answer is correct, merely stilted. Better to serve
            # it than to fail the question outright.
            return ModelReply(text=text, refused=False)

        usable = (
            _refusal(retry) is None
            and not is_degenerate(retry)
            and verbatim_ratio(retry, context) < copied
        )
        if usable:
            return ModelReply(text=retry, refused=False)

    return ModelReply(text=text, refused=False)
