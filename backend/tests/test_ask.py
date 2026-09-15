"""Tests for the Ask retrieval and grounding layer.

The model call itself is not exercised here: it is a paid network
dependency and is not deterministic enough to assert on. What is tested
is everything that decides whether the model is called at all, and what
it is shown - which is where a grounding bug would actually hide.
"""

import asyncio

import httpx
import pytest

from app.services import conversation
from app.services import knowledge_base as kb
from app.services import nemotron


class TestRetrieval:
    @pytest.mark.parametrize(
        "question",
        [
            "What is the speed limit in a school zone?",
            "How many hours of supervised driving do I need?",
            "Who has right of way at a roundabout?",
            "How far should I stay behind the car in front?",
            "What is the blood alcohol limit for a learner?",
        ],
    )
    def test_road_questions_are_covered(self, question):
        assert kb.is_covered(kb.search(question)), question

    @pytest.mark.parametrize(
        "question",
        [
            "How do I bake sourdough bread?",
            "What is the capital of France?",
        ],
    )
    def test_unrelated_questions_are_not_covered(self, question):
        assert not kb.is_covered(kb.search(question)), question

    @pytest.mark.parametrize(
        "question",
        [
            "Write me a poem about cats",
            "Who won the 2022 AFL grand final?",
        ],
    )
    def test_incidental_word_overlap_still_reaches_the_model(self, question):
        """Retrieval is a coarse gate, not the whole defence.

        These score above the threshold on incidental words - "about",
        "won" - so lexical matching alone cannot reject them. They are
        caught by the model's OFF_TOPIC rule instead. Documented here so
        that a future tightening of MIN_SCORE is understood as a change
        to the first of two gates, not the only one.
        """
        assert kb.is_covered(kb.search(question)), question

    def test_handbook_keeps_a_slot(self):
        """Statutory text must not crowd out the plain-language source.

        "School zone" scores highest in the Rules, where rule 23 says only
        that the limit is on the signs. The answer - 40 km/h - is in the
        handbook, so the handbook has to survive into the results.
        """
        matches = kb.search("What is the speed limit in a school zone?")
        sources = {m.passage.source for m in matches}
        assert "Road to Solo Driving handbook" in sources

    def test_empty_question_retrieves_nothing(self):
        assert kb.search("") == []
        assert kb.search("   ") == []

    def test_stop_words_alone_retrieve_nothing(self):
        assert kb.search("the of and is") == []

    def test_context_names_every_source(self):
        matches = kb.search("roundabout")
        context = kb.build_context(matches)
        for match in matches:
            assert match.passage.source in context

    def test_scores_are_ordered(self):
        matches = kb.search("speed limit")
        scores = [m.score for m in matches]
        assert scores == sorted(scores, reverse=True)


class TestRefusalParsing:
    """The sentinel must be recognised without swallowing real answers."""

    def test_bare_sentinel_is_a_refusal(self):
        assert nemotron.strip_reasoning("NOT_IN_SOURCES") == "NOT_IN_SOURCES"

    def test_answer_mentioning_sentinel_is_not_refused(self):
        # A substring check would wrongly treat this as a refusal.
        answer = 'If unsure the assistant replies NOT_IN_SOURCES to the user.'
        bare = answer.strip().strip(".\"'`* ")
        assert bare != nemotron.NOT_IN_SOURCES


class TestDegenerateOutput:
    def test_repetition_loop_is_rejected(self):
        assert nemotron.is_degenerate(
            "NOT, 1999, 1999, 2000, 2001, 2002, 2003, 2004, NOT, 1999, 1999, 2000"
        )

    def test_real_answer_is_accepted(self):
        assert not nemotron.is_degenerate(
            "The speed limit in a school zone is 40 km/h unless signs say "
            "otherwise. These limits protect children near schools."
        )

    def test_short_answer_is_accepted(self):
        # Short replies repeat words by chance; they must not trip the check.
        assert not nemotron.is_degenerate("Zero. No alcohol at all.")


class TestReasoningIsStripped:
    def test_think_tags_removed(self):
        assert nemotron.strip_reasoning(
            "<think>weighing options</think>The limit is 40 km/h."
        ) == "The limit is 40 km/h."

    def test_narrated_thinking_removed(self):
        assert nemotron.strip_reasoning(
            "Here's a thinking process:\n1. Consider the sources."
        ) == ""

    def test_ordinary_answer_untouched(self):
        answer = "The speed limit outside a school is 40 km/h when signs apply."
        assert nemotron.strip_reasoning(answer) == answer


class TestGroundingIsRequired:
    def test_model_is_not_called_without_context(self):
        """No context means nothing to ground against, so refuse to ask."""
        import asyncio

        with pytest.raises(ValueError):
            asyncio.run(nemotron.ask("What is the speed limit?", ""))


class TestSmallTalk:
    """Greetings are answered conversationally, before retrieval runs."""

    @pytest.mark.parametrize(
        "message",
        ["hi", "Hello", "hey there", "Good morning", "g'day", "Hi Buddy!", "yo"],
    )
    def test_greetings_are_recognised(self, message):
        assert conversation.small_talk_reply(message) == conversation.GREETING_REPLY

    @pytest.mark.parametrize(
        "message",
        ["What can you do?", "who are you", "help", "What is RoadBuddy?"],
    )
    def test_capability_questions_are_recognised(self, message):
        assert conversation.small_talk_reply(message) == conversation.CAPABILITY_REPLY

    @pytest.mark.parametrize("message", ["thanks", "Thank you!", "cheers", "bye"])
    def test_courtesy_is_recognised(self, message):
        assert conversation.small_talk_reply(message) == conversation.COURTESY_REPLY

    @pytest.mark.parametrize(
        "message",
        [
            "Hi, what is the speed limit in a school zone?",
            "hello how do I merge onto a freeway",
            "What is the speed limit?",
            "Good morning drivers must give way at a roundabout",
        ],
    )
    def test_a_real_question_is_not_small_talk(self, message):
        """A greeting attached to a question must still reach retrieval.

        This is the case that matters: treating "Hi, what is the speed
        limit?" as a greeting would swallow the question entirely.
        """
        assert conversation.small_talk_reply(message) is None

    def test_empty_message_is_not_small_talk(self):
        assert conversation.small_talk_reply("") is None
        assert conversation.small_talk_reply("   ") is None

    def test_examples_are_answerable(self):
        """The questions shown to a user must be ones Buddy can answer.

        Suggesting a question that then gets declined is worse than
        suggesting nothing.
        """
        for question in conversation.EXAMPLE_QUESTIONS:
            assert kb.is_covered(kb.search(question)), question


class TestPersonaPrompt:
    """The prompt must ask for rephrasing without loosening grounding.

    Telling a model to put things "in your own words" is a nudge toward
    invention, so the instructions that hold it to the sources have to
    survive alongside the persona.
    """

    def test_prompt_asks_for_rephrasing(self):
        prompt = nemotron.SYSTEM_PROMPT.lower()
        assert "your own voice" in prompt
        assert "do not reuse" in prompt
        assert "never a script" in prompt

    def test_prompt_still_forbids_outside_knowledge(self):
        prompt = nemotron.SYSTEM_PROMPT
        assert nemotron.NOT_IN_SOURCES in prompt
        assert nemotron.OFF_TOPIC in prompt
        assert "own knowledge" in prompt.lower()

    def test_prompt_protects_facts_from_rephrasing(self):
        """Wording may change; numbers and conditions may not."""
        prompt = nemotron.SYSTEM_PROMPT.lower()
        assert "never the meaning" in prompt
        assert "condition" in prompt

    def test_prompt_keeps_crash_prediction_refusal(self):
        assert "predict" in nemotron.SYSTEM_PROMPT.lower()

    def test_user_message_asks_for_rephrasing(self):
        message = nemotron._build_user_message("Q?", "some context")
        assert "own words" in message.lower()


class TestVerbatimDetection:
    """Copying is measured, not assumed, so the retry has a real trigger."""

    CONTEXT = (
        "Slow down a little when you see potential hazards like pedestrians "
        "or turning vehicles, and move your foot near the brake so you can "
        "stop if needed. Create a buffer of space to give yourself more time."
    )

    def test_copied_answer_scores_high(self):
        copied = (
            "Slow down a little when you see potential hazards like "
            "pedestrians or turning vehicles, and move your foot near the "
            "brake so you can stop if needed."
        )
        assert nemotron.verbatim_ratio(copied, self.CONTEXT) > nemotron.MAX_VERBATIM_RATIO

    def test_short_factual_answers_are_not_judged(self):
        """A short fact is mostly unavoidable phrasing, not recitation.

        "120 hours of supervised driving experience" cannot be reworded
        without risking the number, so answers below the word floor are
        exempt from the copying check rather than rewritten.
        """
        answer = (
            "You need a minimum of 120 hours of supervised driving "
            "experience, including 20 hours of driving at night."
        )
        word_count = len(answer.split())
        assert word_count < nemotron.MIN_JUDGED_WORDS

    def test_reworded_answer_scores_low(self):
        reworded = (
            "Ease off the accelerator when you spot something that might "
            "become a problem, and cover the brake so you are ready. Extra "
            "space buys you the second you need on a slippery road."
        )
        assert nemotron.verbatim_ratio(reworded, self.CONTEXT) <= nemotron.MAX_VERBATIM_RATIO

    def test_short_answer_does_not_divide_by_zero(self):
        # Shorter than the phrase window, so there are no phrases to compare.
        assert nemotron.verbatim_ratio("Zero.", self.CONTEXT) == 0.0

    def test_empty_answer_is_zero(self):
        assert nemotron.verbatim_ratio("", self.CONTEXT) == 0.0


class TestRephraseRetryPrompt:
    def test_retry_message_names_the_problem(self):
        message = nemotron._build_user_message("Q?", "ctx", insist_rephrase=True)
        assert "copied" in message.lower()
        assert "own voice" in message.lower()

    def test_first_attempt_does_not_mention_a_previous_try(self):
        message = nemotron._build_user_message("Q?", "ctx", insist_rephrase=False)
        assert "previous attempt" not in message.lower()


class TestCrashPredictionRefusal:
    """AC 4.2e: Buddy declines to predict crashes, every time.

    The persona rewrite made the model answer this in prose rather than
    with a sentinel, which left the endpoint unable to tell a refusal
    from an answer. The dedicated sentinel restores a signal the caller
    can act on.
    """

    def test_prompt_defines_the_sentinel(self):
        assert nemotron.CANNOT_PREDICT in nemotron.SYSTEM_PROMPT

    def test_sentinel_is_parsed_as_a_refusal(self):
        reply = nemotron._refusal(nemotron.CANNOT_PREDICT)
        assert reply is not None
        assert reply.refused
        assert reply.reason == "cannot_predict"

    def test_an_answer_mentioning_prediction_is_not_a_refusal(self):
        assert nemotron._refusal("Nobody can predict a crash, so leave more space.") is None


class TestLatencyBudget:
    """Ask answers inside a bounded time, retry included.

    The rephrase retry used to start a second request with a fresh
    timeout, so a slow answer could take twice the per-request limit to
    arrive. A driver waiting on a spinner has no way to tell that from a
    hang, so the budget now covers both attempts.
    """

    CONTEXT = "Night driving reduces visibility. Keep a bigger gap."

    def test_retry_cannot_outlast_the_total_budget(self):
        assert nemotron.REQUEST_TIMEOUT_SECONDS <= nemotron.TOTAL_BUDGET_SECONDS

    def test_budget_covers_every_stall_allowance(self):
        """The budget must fit the worst path it permits.

        Set it below REQUEST_TIMEOUT_SECONDS * (STALL_RETRIES + 1) and a
        question that uses its full stall allowance is cut off partway,
        making the retries it was granted unusable.
        """
        worst_case = nemotron.REQUEST_TIMEOUT_SECONDS * (nemotron.STALL_RETRIES + 1)
        assert nemotron.TOTAL_BUDGET_SECONDS >= worst_case

    def test_budget_stays_inside_the_frontend_wait(self):
        """The frontend gives up at 22s; the server must fail first.

        If the server outlasts it the user sees a generic client-side
        timeout rather than Buddy's own "could not reach" message.
        """
        assert nemotron.TOTAL_BUDGET_SECONDS <= 20.0

    def test_retry_is_skipped_when_the_budget_is_spent(self, monkeypatch):
        """A slow first answer is served as is rather than retried."""
        calls = []
        start = nemotron.time.monotonic()

        async def slow_complete(question, context, insist_rephrase, timeout=None):
            calls.append(insist_rephrase)
            # Simulate a first attempt that consumed the whole budget.
            monkeypatch.setattr(
                nemotron.time,
                "monotonic",
                lambda: start + nemotron.TOTAL_BUDGET_SECONDS,
            )
            return self.CONTEXT

        monkeypatch.setattr(nemotron, "_complete", slow_complete)
        monkeypatch.setattr(nemotron, "MIN_JUDGED_WORDS", 1)

        reply = asyncio.run(nemotron.ask("Why is night driving harder?", self.CONTEXT))

        assert calls == [False], "a spent budget must not start a retry"
        assert reply.text == self.CONTEXT
        assert reply.refused is False

    def test_retry_gets_only_the_remaining_budget(self, monkeypatch):
        """The retry's timeout is what is left, not a fresh full one."""
        timeouts = []

        async def complete(question, context, insist_rephrase, timeout=None):
            timeouts.append(timeout)
            return self.CONTEXT if not insist_rephrase else "Rewritten freely."

        monkeypatch.setattr(nemotron, "_complete", complete)
        monkeypatch.setattr(nemotron, "MIN_JUDGED_WORDS", 1)

        asyncio.run(nemotron.ask("Why is night driving harder?", self.CONTEXT))

        assert len(timeouts) == 2, "expected a retry"
        assert timeouts[1] is not None
        assert timeouts[1] <= nemotron.TOTAL_BUDGET_SECONDS


class TestStallRetry:
    """NIM sometimes accepts a request and never sends a first byte.

    Those stalls do not resolve on their own - waiting returns the same
    timeout, only later - but a fresh request usually answers in a couple
    of seconds. So a timeout is retried once, while a real HTTP error is
    the server's answer and is taken at face value.
    """

    PAYLOAD = {"choices": [{"message": {"content": "A clear answer."}}]}

    @pytest.fixture(autouse=True)
    def _configured_key(self, monkeypatch):
        """These tests exercise transport, not credentials."""
        monkeypatch.setattr(nemotron, "_api_key", lambda: "test-key")

    def _client(self, responses):
        """An AsyncClient stub that yields `responses` in order."""
        calls = []

        class FakeResponse:
            def __init__(self, payload):
                self._payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self._payload

        class FakeClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            async def post(self, *args, **kwargs):
                outcome = responses[len(calls)]
                calls.append(outcome)
                if isinstance(outcome, Exception):
                    raise outcome
                return FakeResponse(outcome)

        return FakeClient, calls

    def test_a_stall_is_retried_once_and_can_succeed(self, monkeypatch):
        client, calls = self._client(
            [httpx.ReadTimeout("stalled"), self.PAYLOAD]
        )
        monkeypatch.setattr(nemotron.httpx, "AsyncClient", client)

        text = asyncio.run(nemotron._complete("Q?", "ctx", insist_rephrase=False))

        assert len(calls) == 2, "the stall should have been retried"
        assert text == "A clear answer."

    def test_repeated_stalls_give_up_rather_than_hang(self, monkeypatch):
        stalls = [
            httpx.ReadTimeout("stalled") for _ in range(nemotron.STALL_RETRIES + 1)
        ]
        client, calls = self._client(stalls)
        monkeypatch.setattr(nemotron.httpx, "AsyncClient", client)

        with pytest.raises(nemotron.NemotronError):
            asyncio.run(nemotron._complete("Q?", "ctx", insist_rephrase=False))

        assert len(calls) == nemotron.STALL_RETRIES + 1

    def test_an_http_error_is_not_retried(self, monkeypatch):
        """A 400 is the server's verdict; asking again just wastes time."""
        error = httpx.HTTPStatusError(
            "bad request",
            request=httpx.Request("POST", nemotron.API_URL),
            response=httpx.Response(400),
        )
        client, calls = self._client([error, self.PAYLOAD])
        monkeypatch.setattr(nemotron.httpx, "AsyncClient", client)

        with pytest.raises(nemotron.NemotronError):
            asyncio.run(nemotron._complete("Q?", "ctx", insist_rephrase=False))

        assert len(calls) == 1, "an HTTP error must not be retried"
