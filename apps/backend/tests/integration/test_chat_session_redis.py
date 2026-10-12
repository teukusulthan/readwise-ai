"""Resumable chat sessions on the real Redis (docker compose, test DB 15)."""

import asyncio
import json

import httpx
import pytest

import router.chat as chat_router
from config.base import settings
from service.chat_session import ChatSessions, RedisSessionStore
from tests.unit.test_chat_session import CONVERSATION_ID, DTO, FakeConversations, _collect

pytestmark = pytest.mark.integration


async def test_store_round_trip_ids_after_and_ttl(redis_client):
    store = RedisSessionStore(client=redis_client)
    sid = "44444444-4444-4444-4444-444444444444"
    await store.create(sid)
    first = await store.append(sid, "delta", json.dumps({"text": "a"}))
    second = await store.append(sid, "done", json.dumps({"answer": "a"}))
    assert [e.id for e in await store.read(sid, "0", block_ms=None)] == [first, second]
    assert [e.event for e in await store.read(sid, first, block_ms=None)] == ["done"]   # strictly after
    assert await store.read(sid, second, block_ms=50) == []                            # waits, then nothing
    assert 0 < await redis_client.ttl(f"chat:session:{sid}:events") <= settings.CHAT_SESSION_TTL_SECONDS
    assert (await store.meta(sid))["status"] == "running"

    assert await store.claim_active(CONVERSATION_ID, sid)
    assert not await store.claim_active(CONVERSATION_ID, "someone-else")   # SET NX: already held
    await store.clear_active(CONVERSATION_ID, "someone-else")       # a different session: untouched
    assert await store.get_active(CONVERSATION_ID) == sid
    assert not await store.replace_active(CONVERSATION_ID, "someone-else", "x")
    assert await store.replace_active(CONVERSATION_ID, sid, "taker")   # compare-and-swap
    await store.clear_active(CONVERSATION_ID, sid)                  # no longer ours: untouched
    assert await store.get_active(CONVERSATION_ID) == "taker"
    await store.clear_active(CONVERSATION_ID, "taker")
    assert await store.get_active(CONVERSATION_ID) is None


async def test_answer_survives_disconnect_with_real_redis(redis_client):
    gate = asyncio.Event()
    fake = FakeConversations(gate=gate)
    sessions = ChatSessions(conversations=fake, store=RedisSessionStore(client=redis_client))
    session_id = await sessions.start(DTO)

    first = await asyncio.wait_for(_collect(sessions, session_id, stop_after=4), 10)   # then the client drops
    gate.set()
    await asyncio.wait_for(fake.finished.wait(), 10)
    rest = await asyncio.wait_for(_collect(sessions, session_id, after=first[-1].id), 10)
    assert [e.event for e in rest] == ["delta", "done"]


async def test_http_stream_resume_cancel_and_active(app, redis_client, monkeypatch):
    sessions = ChatSessions(conversations=FakeConversations(), store=RedisSessionStore(client=redis_client))
    monkeypatch.setattr(chat_router, "sessions", sessions)

    def frames(text):
        out = []
        for block in text.replace("\r\n", "\n").strip().split("\n\n"):
            fields = dict(line.split(": ", 1) for line in block.split("\n") if ": " in line and not line.startswith(":"))
            if "event" in fields:
                out.append(fields)
        return out

    from auth.auth_handler import base_sign_jwt

    token = base_sign_jwt({"user_id": "integration-test"})["token"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", timeout=30,
                                 headers={"Authorization": f"Bearer {token}"}) as client:
        live = frames((await client.post("/chat/stream", json={"question": "Who rescued the crew?"})).text)
        assert [f["event"] for f in live] == ["session", "conversation", "status", "delta", "delta", "done"]
        session_id = json.loads(live[0]["data"])["sessionId"]

        # Re-attach after the first delta: query parameter and Last-Event-ID header behave the same.
        by_query = frames((await client.get(f"/chat/stream/{session_id}", params={"after": live[3]["id"]})).text)
        by_header = frames((await client.get(f"/chat/stream/{session_id}", headers={"Last-Event-ID": live[3]["id"]})).text)
        assert [f["event"] for f in by_query] == [f["event"] for f in by_header] == ["delta", "done"]
        assert by_query[0]["id"] == live[4]["id"]

        finished = (await client.post(f"/chat/stream/{session_id}/cancel")).json()["data"]
        assert finished["cancelled"] is False and finished["status"] == "done"
        assert (await client.get("/chat/active", params={"conversationId": CONVERSATION_ID})).json()["data"]["active"] is False
        assert (await client.post("/chat/stream/55555555-5555-5555-5555-555555555555/cancel")).status_code == 404
        bad = frames((await client.get("/chat/stream/not-a-uuid")).text)
        assert bad[0]["event"] == "error" and json.loads(bad[0]["data"])["code"] == 400
