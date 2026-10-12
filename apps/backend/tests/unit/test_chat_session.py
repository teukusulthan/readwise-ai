"""Resumable chat sessions: the answer outlives the client connection (no Redis needed here)."""

import asyncio
import json
import time

import pytest

from dto.chat import ChatAskDTO
from service.chat_session import ChatSessions, StoredEvent, parse_event_id


class MemorySessionStore:
    """In-memory stand-in for RedisSessionStore (same methods, blocking reads included)."""

    def __init__(self):
        self.events: dict[str, list[StoredEvent]] = {}
        self.metas: dict[str, dict] = {}
        self.cancels: set[str] = set()
        self.active: dict[str, str] = {}
        self._seq = 0
        self._changed = asyncio.Event()

    async def create(self, session_id):
        now = time.time()
        self.metas[session_id] = {"status": "running", "created_at": now, "heartbeat": now}

    async def append(self, session_id, event, data):
        self._seq += 1
        entry_id = f"{1_000 + self._seq}-0"
        self.events.setdefault(session_id, []).append(StoredEvent(id=entry_id, event=event, data=data))
        self._changed.set()
        return entry_id

    def _after(self, session_id, after):
        key = tuple(int(p) for p in after.split("-")) if after != "0" else (0, 0)
        return [e for e in self.events.get(session_id, []) if tuple(int(p) for p in e.id.split("-")) > key]

    async def read(self, session_id, after, block_ms):
        found = self._after(session_id, after)
        if found or not block_ms:
            return found
        self._changed.clear()
        try:
            await asyncio.wait_for(self._changed.wait(), block_ms / 1000)
        except asyncio.TimeoutError:
            return []
        return self._after(session_id, after)

    async def meta(self, session_id):
        return dict(self.metas.get(session_id, {}))

    async def update(self, session_id, **fields):
        self.metas.setdefault(session_id, {}).update({k: str(v) if not isinstance(v, str) else v for k, v in fields.items()})

    async def request_cancel(self, session_id):
        self.cancels.add(session_id)

    async def cancel_requested(self, session_id):
        return session_id in self.cancels

    async def set_active(self, conversation_id, session_id):
        self.active[conversation_id] = session_id

    async def get_active(self, conversation_id):
        return self.active.get(conversation_id)

    async def clear_active(self, conversation_id, session_id):
        if self.active.get(conversation_id) == session_id:
            del self.active[conversation_id]


CONVERSATION_ID = "11111111-1111-1111-1111-111111111111"


class FakeConversations:
    """stream_turn() that emits a scripted turn; `gate` lets a test pause it mid-answer."""

    def __init__(self, deltas=("The lifeboat ", "saved them [1]."), gate: asyncio.Event = None, fail=False):
        self.deltas, self.gate, self.fail = deltas, gate, fail
        self.finished = asyncio.Event()
        self.stopped = False

    async def stream_turn(self, dto):
        try:
            yield "conversation", {"id": CONVERSATION_ID, "title": dto.question}
            yield "status", {"stage": "generating"}
            for i, text in enumerate(self.deltas):
                if i == 1 and self.gate is not None:
                    await self.gate.wait()
                yield "delta", {"text": text}
            if self.fail:
                raise RuntimeError("boom")
            yield "done", {"answer": "".join(self.deltas), "mode": "llm", "conversationId": CONVERSATION_ID}
        except (asyncio.CancelledError, GeneratorExit):
            self.stopped = True  # the real Conversation saves the partial answer as "stopped" here
            raise
        finally:
            self.finished.set()


def _sessions(**kwargs):
    store = MemorySessionStore()
    fake = FakeConversations(**kwargs)
    return ChatSessions(conversations=fake, store=store), store, fake


async def _collect(sessions, session_id, after="0", stop_after=None):
    out = []
    async for item in sessions.events(session_id, after):
        out.append(item)
        if stop_after and len(out) >= stop_after:
            break
    return out


DTO = ChatAskDTO(question="Who rescued the crew?")


async def _until(condition, timeout=5.0):
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "condition not reached"
        await asyncio.sleep(0.01)


async def test_events_are_stored_with_ids_in_order():
    sessions, store, _ = _sessions()
    session_id = await sessions.start(DTO)
    events = await asyncio.wait_for(_collect(sessions, session_id), 5)
    assert [e.event for e in events] == ["session", "conversation", "status", "delta", "delta", "done"]
    assert json.loads(events[0].data) == {"sessionId": session_id}
    assert all(e.id for e in events) and len({e.id for e in events}) == len(events)
    await _until(lambda: store.metas[session_id]["status"] == "done")


async def test_answer_continues_after_the_client_disconnects_and_resumes_from_last_id():
    gate = asyncio.Event()
    sessions, store, fake = _sessions(gate=gate)
    session_id = await sessions.start(DTO)

    # The client reads until the first delta, then its connection drops.
    first = await asyncio.wait_for(_collect(sessions, session_id, stop_after=4), 5)
    assert first[-1].event == "delta"
    gate.set()
    await asyncio.wait_for(fake.finished.wait(), 5)       # generation finished without any reader
    assert fake.stopped is False

    rest = await asyncio.wait_for(_collect(sessions, session_id, after=first[-1].id), 5)
    assert [e.event for e in rest] == ["delta", "done"]   # exactly what was missed, nothing twice


async def test_cancel_stops_generation_and_ends_the_stream():
    gate = asyncio.Event()
    sessions, store, fake = _sessions(gate=gate)
    session_id = await sessions.start(DTO)
    await asyncio.wait_for(_collect(sessions, session_id, stop_after=4), 5)

    result = await sessions.cancel(session_id)
    assert result["cancelled"] is True
    await asyncio.wait_for(fake.finished.wait(), 5)
    assert fake.stopped is True

    events = await asyncio.wait_for(_collect(sessions, session_id), 5)
    assert events[-1].event == "cancelled"
    await _until(lambda: store.metas[session_id]["status"] == "cancelled")
    assert CONVERSATION_ID not in store.active


async def test_active_session_of_a_conversation_until_it_finishes():
    gate = asyncio.Event()
    sessions, store, fake = _sessions(gate=gate)
    session_id = await sessions.start(DTO)
    await asyncio.wait_for(_collect(sessions, session_id, stop_after=3), 5)
    assert await sessions.active(CONVERSATION_ID) == {"active": True, "sessionId": session_id,
                                                      "conversationId": CONVERSATION_ID}
    gate.set()
    await _until(lambda: CONVERSATION_ID not in store.active)
    assert (await sessions.active(CONVERSATION_ID))["active"] is False


async def test_crash_in_the_turn_becomes_an_error_event():
    sessions, store, _ = _sessions(fail=True)
    session_id = await sessions.start(DTO)
    events = await asyncio.wait_for(_collect(sessions, session_id), 5)
    assert events[-1].event == "error" and json.loads(events[-1].data)["code"] == 500


async def test_unknown_or_invalid_sessions_are_error_events():
    sessions, _, _ = _sessions()
    missing = await _collect(sessions, "22222222-2222-2222-2222-222222222222")
    assert [e.event for e in missing] == ["error"] and json.loads(missing[0].data)["code"] == 404
    invalid = await _collect(sessions, "../../etc")
    assert json.loads(invalid[0].data)["code"] == 400
    with pytest.raises(LookupError):
        await sessions.cancel("22222222-2222-2222-2222-222222222222")


async def test_dead_session_is_reported_as_interrupted(settings, monkeypatch):
    sessions, store, _ = _sessions()
    session_id = "33333333-3333-3333-3333-333333333333"
    await store.create(session_id)
    await store.append(session_id, "session", json.dumps({"sessionId": session_id}))
    store.metas[session_id]["heartbeat"] = time.time() - 120   # its process stopped two minutes ago
    monkeypatch.setattr("service.chat_session.READ_BLOCK_MS", 10)
    events = await asyncio.wait_for(_collect(sessions, session_id), 5)
    assert [e.event for e in events] == ["session", "error"]
    assert "interrupted" in json.loads(events[-1].data)["message"]


async def test_shutdown_stops_running_answers():
    gate = asyncio.Event()
    sessions, store, fake = _sessions(gate=gate)
    session_id = await sessions.start(DTO)
    await asyncio.wait_for(_collect(sessions, session_id, stop_after=4), 5)
    await sessions.shutdown(timeout=5)
    assert fake.stopped is True and store.metas[session_id]["status"] == "cancelled"


def test_event_id_validation():
    assert parse_event_id(None) == "0" and parse_event_id("1760000000000-3") == "1760000000000-3"
    for bad in ("abc", "1-2-3", "$", "+"):
        with pytest.raises(ValueError):
            parse_event_id(bad)
