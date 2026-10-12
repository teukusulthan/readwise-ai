import json

import httpx
import pytest

import router.chat as chat_router
from dto.chat import ChatAskDTO
from service.rag import INSUFFICIENT_MARKER, NO_CONTEXT_ANSWER, MarkerGate, Rag
from service.search import Retrieval
from service.vector_store import ChunkHit
from util.http_errors import ServiceUnavailableError


def _hit(n=1):
    return ChunkHit(score=0.8, book_id="b1", book_title="Saltmere", chunk_index=n, text=f"passage {n}",
                    headings=["Chapter 3"], page_start=3, page_end=3)


class FakeSearch:
    def __init__(self, retrieval):
        self.retrieval = retrieval

    def retrieve(self, question, book_ids=None, top_k=None, min_score=None, follow_up_of=None):
        return self.retrieval


def _streamer(pieces, fail_after=None):
    async def stream(system, user):
        for i, piece in enumerate(pieces):
            if fail_after is not None and i == fail_after:
                raise ServiceUnavailableError("The language model is rate-limited right now. Try again shortly.")
            yield piece
    return stream


async def _collect(rag, question="Who rescued the crew?"):
    return [event async for event in rag.ask_stream(ChatAskDTO(question=question))]


# ── MarkerGate ────────────────────────────────────────────────────────

def test_gate_releases_real_answer_with_buffered_start():
    gate = MarkerGate()
    assert gate.feed("  ") == "" and gate.feed("IN") == ""     # could still be the marker
    assert gate.feed("deed, the crew") == "INdeed, the crew"   # diverged → release buffer
    assert gate.feed(" was saved") == " was saved"


def test_gate_never_releases_marker():
    gate = MarkerGate()
    assert [gate.feed(p) for p in ["INSUFF", "ICIENT_", "CONTEXT"]] == ["", "", ""]
    assert gate.full == INSUFFICIENT_MARKER


# ── ask_stream ────────────────────────────────────────────────────────

async def test_stream_event_order_and_final_payload():
    rag = Rag(allow_general_knowledge=False, search=FakeSearch(Retrieval(hits=[_hit(1), _hit(2)], searched_book_ids=["b1"])),
              streamer=_streamer(["The Penhallow ", "lifeboat rescued ", "all seven [2]."]))
    events = await _collect(rag)
    names = [name for name, _ in events]
    assert names == ["status", "sources", "status", "delta", "delta", "delta", "done"]
    assert events[0][1] == {"stage": "retrieving"} and events[2][1] == {"stage": "generating"}
    assert [s["cited"] for s in events[1][1]["sources"]] == [False, False]
    assert "".join(d["text"] for n, d in events if n == "delta") == "The Penhallow lifeboat rescued all seven [2]."
    done = events[-1][1]
    assert done["mode"] == "llm" and done["grounded"] is True
    assert [s["cited"] for s in done["sources"]] == [False, True]


async def test_stream_insufficient_marker_is_not_streamed():
    rag = Rag(allow_general_knowledge=False, search=FakeSearch(Retrieval(hits=[_hit()], searched_book_ids=["b1"])),
              streamer=_streamer(["INSUFFICIENT", "_CONTEXT"]))
    events = await _collect(rag)
    assert not [e for e in events if e[0] == "delta"]
    assert events[-1][1]["mode"] == "insufficient_context" and events[-1][1]["answer"] == NO_CONTEXT_ANSWER


async def test_stream_without_relevant_passages_skips_llm():
    def must_not_run(system, user):
        raise AssertionError("LLM must not be called")

    rag = Rag(allow_general_knowledge=False, search=FakeSearch(Retrieval(hits=[], searched_book_ids=["b1"])), streamer=must_not_run)
    events = await _collect(rag)
    assert [n for n, _ in events] == ["status", "sources", "done"]
    assert events[-1][1]["mode"] == "no_context"


async def test_stream_provider_error_becomes_error_event():
    rag = Rag(allow_general_knowledge=False, search=FakeSearch(Retrieval(hits=[_hit()], searched_book_ids=["b1"])),
              streamer=_streamer(["Partial answer ", "more"], fail_after=1))
    events = await _collect(rag)
    assert events[-1] == ("error", {"message": "The language model is rate-limited right now. Try again shortly.",
                                    "code": 503})
    assert not [e for e in events if e[0] == "done"]


# ── HTTP endpoint (real SSE framing) ──────────────────────────────────

def _parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for frame in body.replace("\r\n", "\n").split("\n\n"):
        name, data = None, []
        for line in frame.split("\n"):
            if line.startswith("event:"):
                name = line[6:].strip()
            elif line.startswith("data:"):
                data.append(line[5:].strip())
        if name:
            events.append((name, json.loads("\n".join(data))))
    return events


async def test_stream_endpoint_sends_sse(app, monkeypatch):
    from auth.auth_handler import base_sign_jwt

    from service.chat_session import ChatSessions
    from service.conversation import Conversation
    from tests.unit.test_chat_session import MemorySessionStore
    from tests.unit.test_conversation import MemoryRepository

    rag = Rag(allow_general_knowledge=False, search=FakeSearch(Retrieval(hits=[_hit()], searched_book_ids=["b1"])),
              streamer=_streamer(["Saved by the lifeboat [1]."]))
    conversations = Conversation(repository=MemoryRepository(), rag=rag)
    monkeypatch.setattr(chat_router, "sessions", ChatSessions(conversations=conversations, store=MemorySessionStore()))
    token = base_sign_jwt({"user_id": "t"})["token"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/chat/stream", json={"question": "Who saved them?"},
                                     headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _parse_sse(response.text)
    assert [n for n, _ in events] == ["session", "conversation", "status", "sources", "status", "delta", "done"]
    assert events[-1][1]["conversationId"] == events[1][1]["id"]
    assert response.text.count("\nid: ") + response.text.startswith("id: ") == len(events)   # every event has an id
    assert events[-1][1]["grounded"] is True


async def test_stream_endpoint_validates_before_streaming(app):
    from auth.auth_handler import base_sign_jwt

    token = base_sign_jwt({"user_id": "t"})["token"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/chat/stream", json={"question": "   "}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 422


def test_final_answer_is_tidied():
    from service.rag import _tidy

    assert _tidy("First para. [1]  \n\n\n\nSecond para. [2]   \n") == "First para. [1]\n\nSecond para. [2]"
    assert _tidy("One. [1]\nTwo. [2]\n  \nThree. [3]") == "One. [1]\n\nTwo. [2]\n\nThree. [3]"
