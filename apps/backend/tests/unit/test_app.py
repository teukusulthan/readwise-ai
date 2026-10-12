import httpx
import pytest

import router.health as health_router


@pytest.fixture
def client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_liveness_is_public(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_readiness_reports_each_dependency(client, monkeypatch):
    monkeypatch.setattr(
        health_router.obj,
        "check_all",
        lambda: {"mongo": {"status": "ok"}, "redis": {"status": "error", "error": "ConnectionError"},
                 "postgres": {"status": "not_configured"}, "qdrant": {"status": "ok"}},
    )
    resp = await client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json()["checks"]["redis"]["status"] == "error"


async def test_readiness_ok_when_unconfigured_services_skipped(client, monkeypatch):
    monkeypatch.setattr(
        health_router.obj,
        "check_all",
        lambda: {"mongo": {"status": "ok"}, "postgres": {"status": "not_configured"}},
    )
    resp = await client.get("/health/ready")
    assert resp.status_code == 200


async def test_cors_allows_configured_origin_with_credentials(client):
    resp = await client.options(
        "/health",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert resp.headers.get("access-control-allow-credentials") == "true"


async def test_cors_rejects_unknown_origin(client):
    resp = await client.options(
        "/health",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in resp.headers


async def test_oversized_request_rejected_by_app(client, settings):
    too_big = b"x" * (settings.MAX_REQUEST_BODY_MB * 1024 * 1024 + 1)
    resp = await client.post("/auth/login", content=too_big, headers={"Content-Type": "application/json"})
    assert resp.status_code == 413


async def test_protected_route_requires_auth(client):
    resp = await client.post("/group/get-all", json={})
    assert resp.status_code == 401


def test_expected_routers_are_mounted(app):
    paths = {route.path for route in app.routes}
    for path in ("/health", "/health/ready", "/auth/login", "/role/get-all", "/upload/upload-file"):
        assert path in paths


def _handler_client():
    import api
    from fastapi import FastAPI, HTTPException
    from starlette.exceptions import HTTPException as StarletteHTTPException

    mini = FastAPI()
    mini.add_exception_handler(StarletteHTTPException, api._envelope_http_exception_handler)
    envelope = {"metaData": {"status": False, "responseCode": 404, "message": "nope"}, "data": None}

    @mini.get("/envelope")
    def _envelope():
        raise HTTPException(404, detail=envelope, headers={"WWW-Authenticate": "Bearer"})

    @mini.get("/plain")
    def _plain():
        raise HTTPException(400, detail="plain message")

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=mini), base_url="http://test")


async def test_envelope_http_exception_is_top_level_and_keeps_headers():
    async with _handler_client() as c:
        resp = await c.get("/envelope")
    assert resp.status_code == 404
    assert resp.json()["metaData"]["responseCode"] == 404 and "detail" not in resp.json()
    assert resp.headers["www-authenticate"] == "Bearer"


async def test_plain_http_exception_keeps_detail_shape():
    async with _handler_client() as c:
        resp = await c.get("/plain")
    assert resp.status_code == 400 and resp.json() == {"detail": "plain message"}


async def test_real_app_auth_failure_keeps_plain_detail(client):
    # The JWT guard raises a plain-string HTTPException by design; the envelope
    # handler must leave it alone. (The 404 envelope is proven in integration tests.)
    resp = await client.get("/book/get-one", params={"id": "00000000-0000-0000-0000-000000000000"})
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Authentication required."}


def test_cors_default_origins_include_dev_port_3001():
    from config.base import BaseSetting

    default = BaseSetting.__fields__["CORS_ORIGINS"].default
    assert "http://localhost:3001" in default.split(",")
