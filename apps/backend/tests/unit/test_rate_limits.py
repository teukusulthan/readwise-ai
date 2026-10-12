"""Per-route rate limits, trusted-proxy client IP, the ingestion queue cap and the chat concurrency cap."""

import io
import time

import fakeredis
import httpx
import pytest
from fastapi import Depends, FastAPI

from auth.auth_handler import base_sign_jwt
from auth.principal import LOCAL
from dto.chat import ChatAskDTO
from middleware import route_limits
from service import chat_session as chat_session_module
from service.chat_session import BUSY_MESSAGE, ChatSessions, RedisSessionStore
from tests.unit.test_book_consistency import FakeBooks, FakeIngestion, FakeVectors, PDF_A, _row
from tests.unit.test_chat_session import FakeConversations
from service.book import QUEUE_FULL_MESSAGE, Book
from util.client_ip import client_ip
from util.http_errors import TooManyRequestsError


@pytest.fixture
async def redis(monkeypatch):
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    monkeypatch.setattr(route_limits.Services, "a_redis", staticmethod(lambda: client))
    yield client
    await client.aclose()


def _app(group="search") -> FastAPI:
    from api import _envelope_http_exception_handler
    from starlette.exceptions import HTTPException as StarletteHTTPException

    app = FastAPI()
    app.add_exception_handler(StarletteHTTPException, _envelope_http_exception_handler)

    @app.post("/limited", dependencies=[Depends(route_limits.route_limit(group))])
    async def limited():
        return {"ok": True}

    return app


def _client(app, **kwargs):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app, **kwargs), base_url="http://test")


def _token(user_id):
    return base_sign_jwt({"user_id": user_id})["token"]


def test_uvicorn_does_not_rewrite_the_client_from_forwarded_headers():
    import api

    assert api.uvicorn_options()["proxy_headers"] is False


# ── per-route limits ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def jwt_on(settings, monkeypatch):
    monkeypatch.setattr(settings, "JWT_ACTIVE", True)


async def test_tokens_do_not_pick_a_budget_while_jwt_is_inactive(redis, settings, monkeypatch):
    monkeypatch.setattr(settings, "JWT_ACTIVE", False)
    monkeypatch.setattr(settings, "RATE_LIMIT_SEARCH_PER_MINUTE", 1)
    async with _client(_app()) as client:
        assert (await client.post("/limited", headers={"Authorization": f"Bearer {_token('forged-1')}"})).status_code == 200
        assert (await client.post("/limited", headers={"Authorization": f"Bearer {_token('forged-2')}"})).status_code == 429


async def test_over_budget_is_429_with_envelope_and_retry_after(redis, settings, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_SEARCH_PER_MINUTE", 2)
    async with _client(_app()) as client:
        assert (await client.post("/limited")).status_code == 200
        assert (await client.post("/limited")).status_code == 200
        blocked = await client.post("/limited")
    assert blocked.status_code == 429
    assert blocked.json()["metaData"]["responseCode"] == 429
    assert 1 <= int(blocked.headers["Retry-After"]) <= 60


async def test_budget_is_per_user_not_shared_by_a_common_ip(redis, settings, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_SEARCH_PER_MINUTE", 1)
    async with _client(_app()) as client:
        alice, bob = {"Authorization": f"Bearer {_token('alice')}"}, {"Authorization": f"Bearer {_token('bob')}"}
        assert (await client.post("/limited", headers=alice)).status_code == 200
        assert (await client.post("/limited", headers=alice)).status_code == 429
        assert (await client.post("/limited", headers=bob)).status_code == 200


async def test_anonymous_clients_are_limited_per_ip(redis, settings, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_SEARCH_PER_MINUTE", 1)
    app = _app()
    async with _client(app, client=("10.0.0.1", 1)) as first, _client(app, client=("10.0.0.2", 1)) as second:
        assert (await first.post("/limited")).status_code == 200
        assert (await first.post("/limited")).status_code == 429
        assert (await second.post("/limited")).status_code == 200


async def test_invalid_token_falls_back_to_ip(redis, settings, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_SEARCH_PER_MINUTE", 1)
    async with _client(_app()) as client:
        junk = {"Authorization": "Bearer not-a-jwt"}
        assert (await client.post("/limited", headers=junk)).status_code == 200
        assert (await client.post("/limited", headers={"Authorization": "Bearer other-junk"})).status_code == 429


async def test_groups_have_separate_budgets_and_zero_disables(redis, settings, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_SEARCH_PER_MINUTE", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_CHAT_PER_MINUTE", 0)
    async with _client(_app("search")) as search, _client(_app("chat")) as chat:
        assert (await search.post("/limited")).status_code == 200
        assert (await search.post("/limited")).status_code == 429
        for _ in range(5):
            assert (await chat.post("/limited")).status_code == 200


async def test_window_expiry_resets_the_budget(redis, settings, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_SEARCH_PER_MINUTE", 1)
    async with _client(_app()) as client:
        assert (await client.post("/limited")).status_code == 200
        assert (await client.post("/limited")).status_code == 429
        for key in await redis.keys("rate_limit:route:*"):
            await redis.delete(key)   # what the 60 s TTL does
        assert (await client.post("/limited")).status_code == 200


async def test_redis_outage_fails_open(settings, monkeypatch):
    class Broken:
        def pipeline(self):
            raise ConnectionError("down")

    monkeypatch.setattr(route_limits.Services, "a_redis", staticmethod(lambda: Broken()))
    monkeypatch.setattr(settings, "RATE_LIMIT_SEARCH_PER_MINUTE", 1)
    async with _client(_app()) as client:
        for _ in range(3):
            assert (await client.post("/limited")).status_code == 200


def test_default_budgets(settings):
    assert (settings.RATE_LIMIT_UPLOAD_PER_MINUTE, settings.RATE_LIMIT_CHAT_PER_MINUTE,
            settings.RATE_LIMIT_SEARCH_PER_MINUTE) == (20, 30, 60)
    assert settings.INGESTION_MAX_QUEUED == 50 and settings.CHAT_MAX_CONCURRENT_SESSIONS == 20


# ── client IP / trusted proxies ───────────────────────────────────────

def _scope(peer, forwarded=None):
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return {"type": "http", "client": (peer, 1234), "headers": headers}


def test_forwarded_for_is_ignored_without_trusted_proxies(settings, monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "")
    assert client_ip(_scope("203.0.113.9", "1.2.3.4")) == "203.0.113.9"


def test_forwarded_for_is_ignored_from_an_untrusted_peer(settings, monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "10.0.0.0/8")
    assert client_ip(_scope("203.0.113.9", "1.2.3.4")) == "203.0.113.9"


def test_rightmost_untrusted_address_is_the_client(settings, monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "10.0.0.0/8, 192.168.1.5")
    # 6.6.6.6 is client-supplied spoofing to the left of the real client 198.51.100.7
    assert client_ip(_scope("10.0.0.2", "6.6.6.6, 198.51.100.7, 10.0.0.9, 192.168.1.5")) == "198.51.100.7"


def test_all_trusted_or_malformed_chain_falls_back_to_peer(settings, monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "10.0.0.0/8")
    assert client_ip(_scope("10.0.0.2", "10.0.0.3")) == "10.0.0.2"
    assert client_ip(_scope("10.0.0.2", "1.2.3.4, garbage")) == "10.0.0.2"
    assert client_ip(_scope("10.0.0.2")) == "10.0.0.2"


def test_invalid_trusted_proxies_setting_is_rejected(settings):
    from config.base import BaseSetting

    with pytest.raises(ValueError, match="TRUSTED_PROXIES"):
        BaseSetting.trusted_proxies_are_cidrs("10.0.0.0/8,not-a-cidr")


# ── ingestion queue cap ───────────────────────────────────────────────

def _service(*rows):
    repo = FakeBooks(*rows)
    return Book(repository=repo, vector_store=FakeVectors(), ingestion=FakeIngestion()), repo


def test_upload_is_refused_when_the_queue_is_full(settings, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_MAX_QUEUED", 2)
    service, repo = _service(_row(title="a", status="queued", sha="1"), _row(title="b", status="queued", sha="2"))
    with pytest.raises(TooManyRequestsError, match=QUEUE_FULL_MESSAGE):
        service.upload_document(io.BytesIO(PDF_A), "x.pdf")
    assert len(repo.rows) == 2 and service.ingestion.queued == []


def test_upload_is_accepted_below_the_cap_and_processing_does_not_count(settings, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_MAX_QUEUED", 2)
    service, repo = _service(_row(title="a", status="queued", sha="1"), _row(title="b", status="processing", sha="2"))
    service.repository.insert = lambda fields: {**_row(title=fields["title"], status="queued", sha="n"), **fields}
    service.repository.update = lambda book_id, fields: {**_row(status="queued", sha="n"), **fields}
    service.upload_document(io.BytesIO(PDF_A), "x.pdf")
    assert len(service.ingestion.queued) == 1


def test_reindex_counts_against_the_queue_cap(settings, monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "INGESTION_MAX_QUEUED", 1)
    pdf = tmp_path / "b.pdf"
    pdf.write_bytes(PDF_A)
    target = _row(title="t", status="indexed", sha="3", file_path=str(pdf))
    service, repo = _service(_row(title="a", status="queued", sha="1"), target)
    with pytest.raises(TooManyRequestsError):
        service.reindex(str(target["id"]))
    assert service.ingestion.queued == []


def test_queue_cap_zero_means_unlimited(settings, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_MAX_QUEUED", 0)
    service, _ = _service(*[_row(title=str(i), status="queued", sha=str(i)) for i in range(5)])
    service._ensure_queue_room()


def test_too_many_requests_maps_to_429_with_retry_after():
    from util.http_errors import to_http_exception

    error = to_http_exception(TooManyRequestsError("slow down", retry_after=7), time.time())
    assert error.status_code == 429 and error.headers == {"Retry-After": "7"}
    assert error.detail["metaData"]["message"] == "slow down"


# ── concurrent chat sessions cap ──────────────────────────────────────

@pytest.fixture
async def chat(settings, monkeypatch):
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    clock = {"now": 1_000_000.0}
    monkeypatch.setattr(chat_session_module.time, "time", lambda: clock["now"])
    monkeypatch.setattr(settings, "CHAT_MAX_CONCURRENT_SESSIONS", 2)
    monkeypatch.setattr(settings, "CHAT_SESSION_STALE_SECONDS", 30)
    sessions = ChatSessions(conversations=FakeConversations(), store=RedisSessionStore(client=client))
    yield sessions, clock
    await client.aclose()


DTO = ChatAskDTO(question="q")


async def test_claim_beyond_the_cap_is_429(chat):
    sessions, _ = chat
    await sessions.claim(DTO, LOCAL)
    await sessions.claim(DTO, LOCAL)
    with pytest.raises(TooManyRequestsError, match=BUSY_MESSAGE) as caught:
        await sessions.claim(DTO, LOCAL)
    assert caught.value.retry_after >= 1


async def test_finished_session_frees_a_slot(chat):
    sessions, _ = chat
    first = await sessions.claim(DTO, LOCAL)
    await sessions.claim(DTO, LOCAL)
    await sessions.store.update(first, status="done")
    await sessions.claim(DTO, LOCAL)   # counting prunes the finished session


async def test_dead_session_stops_counting_after_the_stale_window(chat):
    sessions, clock = chat
    await sessions.claim(DTO, LOCAL)
    await sessions.claim(DTO, LOCAL)
    clock["now"] += 31          # heartbeats stale: both runners died
    await sessions.claim(DTO, LOCAL)
    assert await sessions.store.count_running() == 1


async def test_refused_second_turn_on_a_conversation_does_not_hold_a_slot(chat):
    from service.chat_session import TURN_RUNNING_MESSAGE
    from util.http_errors import ConflictError

    sessions, _ = chat
    cid = ChatAskDTO(question="q", conversationId="11111111-1111-1111-1111-111111111111")
    await sessions.claim(cid, LOCAL)
    with pytest.raises(ConflictError, match=TURN_RUNNING_MESSAGE):
        await sessions.claim(cid, LOCAL)
    assert await sessions.store.count_running() == 1


async def test_cap_zero_means_unlimited(chat, settings, monkeypatch):
    sessions, _ = chat
    monkeypatch.setattr(settings, "CHAT_MAX_CONCURRENT_SESSIONS", 0)
    for _ in range(5):
        await sessions.claim(DTO, LOCAL)


async def test_slot_is_released_when_the_answer_ends(chat):
    import asyncio

    sessions, _ = chat
    session_id = await sessions.start(DTO, LOCAL)
    await asyncio.wait_for(sessions.conversations.finished.wait(), 5)
    for _ in range(100):
        if await sessions.store.client.zcard("chat:sessions:running") == 0:
            break
        await asyncio.sleep(0.01)
    assert await sessions.store.client.zcard("chat:sessions:running") == 0
    assert (await sessions.store.meta(session_id))["status"] == "done"
