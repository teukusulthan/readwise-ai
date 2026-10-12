import asyncio
from types import SimpleNamespace

import pytest
from qdrant_client.http.exceptions import ResponseHandlingException

import service.llm as llm
from dto.chat import ChatAskDTO
from service.rag import Rag
from util.embedding import EmbeddingError
from util.http_errors import (ConflictError, NotFoundError, ServiceUnavailableError, to_http_exception)


def _status(error):
    exc = to_http_exception(error, 0.0)
    meta = exc.detail["metaData"]
    return exc.status_code, meta["message"]


# ── exception -> HTTP mapping ─────────────────────────────────────────

def test_not_found_is_404_with_its_message():
    assert _status(NotFoundError("Book x not found.")) == (404, "Book x not found.")


@pytest.mark.parametrize("error", [KeyError("k"), IndexError("i"), LookupError("l")])
def test_plain_lookup_errors_are_bugs_not_404(error):
    assert _status(error) == (500, "Internal server error.")


@pytest.mark.parametrize("error", [EmbeddingError("host down"), ResponseHandlingException(ConnectionError("refused"))])
def test_search_outages_are_503(error):
    assert _status(error) == (503, "Search service unavailable")


def test_other_mappings_still_hold():
    assert _status(ConflictError("busy"))[0] == 409
    assert _status(ValueError("bad"))[0] == 400
    assert _status(ServiceUnavailableError("down")) == (503, "down")


# ── SSE: retrieval outage becomes an error event ──────────────────────

class _BrokenSearch:
    def __init__(self, error):
        self.error = error

    def retrieve(self, *args, **kwargs):
        raise self.error


async def _events(rag):
    return [e async for e in rag.ask_stream(ChatAskDTO(question="Who rescued the crew?"))]


@pytest.mark.parametrize("error", [EmbeddingError("host down"), ResponseHandlingException(ConnectionError("refused"))])
async def test_stream_search_outage_is_a_503_error_event(error):
    async def never(system, user):
        yield "x"

    events = await _events(Rag(search=_BrokenSearch(error), streamer=never, allow_general_knowledge=True))
    assert events[-1] == ("error", {"message": "Search service unavailable", "code": 503})


async def test_stream_programming_errors_are_not_disguised():
    async def never(system, user):
        yield "x"

    with pytest.raises(KeyError):
        await _events(Rag(search=_BrokenSearch(KeyError("bug")), streamer=never, allow_general_knowledge=True))


def test_rest_ask_search_outage_maps_to_503():
    class Boom:
        def retrieve(self, *a, **k):
            raise EmbeddingError("down")

    rag = Rag(search=Boom(), generator=lambda s, u: "x", allow_general_knowledge=True)
    with pytest.raises(EmbeddingError) as raised:
        rag.ask(ChatAskDTO(question="Who rescued the crew?"))
    assert _status(raised.value) == (503, "Search service unavailable")


# ── LLM timeouts ──────────────────────────────────────────────────────

@pytest.fixture
def configured(settings, monkeypatch):
    monkeypatch.setattr(settings, "LLM_MODEL", "openai/test-model")
    monkeypatch.setattr(settings, "LLM_API_KEY", "test-key")


def test_timeout_and_retries_reach_the_litellm_request(settings, configured, monkeypatch):
    monkeypatch.setattr(settings, "LLM_TIMEOUT_SECONDS", 33)
    monkeypatch.setattr(settings, "LLM_NUM_RETRIES", 4)
    params = llm._model().get_request_params()
    assert params["timeout"] == 33 and params["num_retries"] == 4


def test_defaults(settings):
    assert (settings.LLM_TIMEOUT_SECONDS, settings.LLM_NUM_RETRIES, settings.LLM_FIRST_TOKEN_TIMEOUT_SECONDS) == (120, 2, 90)


def test_explicit_request_params_win(configured):
    assert llm._model({"timeout": 5}).get_request_params()["timeout"] == 5


def _fake_arun(monkeypatch, events, delay_first=0.0, closed=None):
    from agno.agent import Agent

    async def gen():
        try:
            await asyncio.sleep(delay_first)
            for event in events:
                yield event
        finally:
            if closed is not None:
                closed.append(True)

    monkeypatch.setattr(Agent, "arun", lambda self, prompt, **kw: gen())


def _content(text="", reasoning=None):
    class RunContentEvent(SimpleNamespace):
        pass

    return RunContentEvent(content=text, reasoning_content=reasoning)


async def test_first_token_timeout_ends_the_turn_with_a_safe_error_event(settings, configured, monkeypatch):
    monkeypatch.setattr(settings, "LLM_FIRST_TOKEN_TIMEOUT_SECONDS", 0.05)
    closed = []
    _fake_arun(monkeypatch, [_content("late")], delay_first=5, closed=closed)

    rag = Rag(search=SimpleNamespace(retrieve=lambda *a, **k: SimpleNamespace(
        hits=[], searched_book_ids=["b"], skipped=[], books=[])), streamer=llm.agno_streamer(),
        allow_general_knowledge=True)
    events = await _events(rag)
    assert events[-1] == ("error", {"message": "The model took too long to respond. Try again.", "code": 503})
    assert closed == [True]  # generation cancelled


async def test_reasoning_token_counts_as_first_token(settings, configured, monkeypatch):
    monkeypatch.setattr(settings, "LLM_FIRST_TOKEN_TIMEOUT_SECONDS", 0.3)

    async def slow_after_first():
        yield _content("", reasoning="thinking")
        await asyncio.sleep(0.5)  # longer than the first-token limit, which no longer applies
        yield _content("answer")

    from agno.agent import Agent

    monkeypatch.setattr(Agent, "arun", lambda self, prompt, **kw: slow_after_first())
    pieces = [p async for p in llm.agno_streamer()("system", "user")]
    assert pieces == ["answer"]


def test_provider_timeout_text_is_user_safe():
    assert llm._user_message("litellm.Timeout: request timed out") == llm.FIRST_TOKEN_TIMEOUT_MESSAGE
