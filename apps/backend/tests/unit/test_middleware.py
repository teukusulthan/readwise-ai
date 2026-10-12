import json

import httpx
import pytest
from fastapi import FastAPI, Request

from middleware.body_limit import BodySizeLimitMiddleware
from middleware.rate_limiter import RateLimitMiddleware
from router.middleware import DecryptPayload
from util.aes_encryption import encrypt_aes_data


def _echo_app() -> FastAPI:
    app = FastAPI()

    @app.post("/echo")
    async def echo(request: Request):
        return {"body": (await request.body()).decode()}

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    return app


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


# ── Body size limit ───────────────────────────────────────────────────

@pytest.fixture
def limited_client():
    app = _echo_app()
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=10)
    return _client(app)


async def test_body_within_limit_passes(limited_client):
    resp = await limited_client.post("/echo", content=b"0123456789")
    assert resp.status_code == 200


async def test_declared_oversized_body_is_rejected(limited_client):
    resp = await limited_client.post("/echo", content=b"x" * 11)
    assert resp.status_code == 413


async def test_streamed_oversized_body_without_length_is_rejected(limited_client):
    async def chunks():
        for _ in range(5):
            yield b"xxxx"

    resp = await limited_client.post("/echo", content=chunks())
    assert resp.status_code == 413


# ── DecryptPayload ────────────────────────────────────────────────────

@pytest.fixture
def enc_on(settings, monkeypatch):
    monkeypatch.setattr(settings, "ENC_ACTIVE", True)


@pytest.fixture
def decrypt_client():
    app = _echo_app()
    app.add_middleware(DecryptPayload)
    return _client(app)


async def test_encrypted_json_is_decrypted(enc_on, decrypt_client):
    payload = {"title": "Dune"}
    resp = await decrypt_client.post("/echo", json={"hashedPayload": encrypt_aes_data(payload)})
    assert resp.status_code == 200
    assert json.loads(resp.json()["body"]) == payload


async def test_plain_json_is_rejected_when_encryption_on(enc_on, decrypt_client):
    resp = await decrypt_client.post("/echo", json={"title": "Dune"})
    assert resp.status_code == 400


async def test_multipart_passes_through_when_encryption_on(enc_on, decrypt_client):
    resp = await decrypt_client.post("/echo", files={"file": ("a.txt", b"hello")})
    assert resp.status_code == 200


async def test_payload_untouched_when_encryption_off(settings, decrypt_client):
    assert settings.ENC_ACTIVE is False
    resp = await decrypt_client.post("/echo", json={"title": "Dune"})
    assert json.loads(resp.json()["body"]) == {"title": "Dune"}


# ── Rate limiter ──────────────────────────────────────────────────────

class _FakePipeline:
    def __init__(self, count=None, error=None):
        self.count, self.error = count, error

    def incr(self, *args, **kwargs):
        pass

    def expire(self, *args, **kwargs):
        pass

    async def execute(self):
        if self.error:
            raise self.error
        return [self.count, True]


class _FakeRedis:
    def __init__(self, pipeline):
        self._pipeline = pipeline

    def pipeline(self):
        return self._pipeline


def _rate_limited_client(monkeypatch, pipeline, limit=5):
    import middleware.rate_limiter as rate_limiter

    monkeypatch.setattr(rate_limiter.Services, "a_redis", staticmethod(lambda: _FakeRedis(pipeline)))
    monkeypatch.setattr(rate_limiter.settings, "RATE_LIMIT", limit)
    app = _echo_app()
    app.add_middleware(RateLimitMiddleware)
    return _client(app)


async def test_rate_limit_allows_under_limit(monkeypatch):
    client = _rate_limited_client(monkeypatch, _FakePipeline(count=5))
    assert (await client.get("/ping")).status_code == 200


async def test_rate_limit_blocks_over_limit(monkeypatch):
    client = _rate_limited_client(monkeypatch, _FakePipeline(count=6))
    assert (await client.get("/ping")).status_code == 429


async def test_rate_limit_fails_open_when_redis_down(monkeypatch):
    client = _rate_limited_client(monkeypatch, _FakePipeline(error=ConnectionError("redis down")))
    assert (await client.get("/ping")).status_code == 200
