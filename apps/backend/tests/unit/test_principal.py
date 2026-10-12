"""Who is calling: JWT users, the X-Internal-Token service principal, and the no-login "local" owner."""

import hmac

import httpx
import pytest
from fastapi import Depends, FastAPI, Request
from pydantic.v1 import ValidationError

from auth import principal as principal_module
from auth.auth_handler import base_sign_jwt
from auth.principal import LOCAL, SERVICE, Principal, current_principal, require_user
from config.base import BaseSetting
from middleware.route_limits import client_key
from util.helper import router_param_builder

INTERNAL = "internal-token-for-tests-0123456789abcdef"


@pytest.fixture(autouse=True)
def auth_on(settings, monkeypatch):
    monkeypatch.setattr(settings, "JWT_ACTIVE", True)
    monkeypatch.setattr(settings, "INTERNAL_TOKEN", INTERNAL)


def _client():
    app = FastAPI()

    @app.get("/who")
    def who(principal: Principal = Depends(current_principal)):
        return {"subject": principal.subject, "kind": principal.kind}

    @app.get("/mine")
    def mine(principal: Principal = Depends(require_user)):
        return {"subject": principal.subject}

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def _bearer(user_id):
    return {"Authorization": f"Bearer {base_sign_jwt({'user_id': user_id})['token']}"}


async def test_internal_token_is_the_service_principal():
    async with _client() as client:
        response = await client.get("/who", headers={"X-Internal-Token": INTERNAL})
    assert response.status_code == 200
    assert response.json() == {"subject": "service:internal", "kind": "service"}


async def test_wrong_internal_token_is_refused_even_with_a_valid_jwt():
    async with _client() as client:
        assert (await client.get("/who", headers={"X-Internal-Token": INTERNAL[:-1] + "x"})).status_code == 403
        assert (await client.get("/who", headers={"X-Internal-Token": "", **_bearer("alice")})).status_code == 403


async def test_empty_internal_token_setting_disables_it(settings, monkeypatch):
    monkeypatch.setattr(settings, "INTERNAL_TOKEN", "")
    async with _client() as client:
        assert (await client.get("/who", headers={"X-Internal-Token": ""})).status_code == 403
        assert (await client.get("/who", headers={"X-Internal-Token": INTERNAL})).status_code == 403


async def test_internal_token_is_compared_in_constant_time(monkeypatch):
    calls, real = [], hmac.compare_digest

    def spy(a, b):
        calls.append((a, b))
        return real(a, b)

    monkeypatch.setattr(principal_module.hmac, "compare_digest", spy)
    async with _client() as client:
        assert (await client.get("/who", headers={"X-Internal-Token": "nope"})).status_code == 403
    assert calls == [(b"nope", INTERNAL.encode())]


async def test_jwt_bearer_and_cookie_still_identify_the_user():
    async with _client() as client:
        response = await client.get("/who", headers=_bearer("alice"))
        assert response.json() == {"subject": "alice", "kind": "user"}
        cookie = base_sign_jwt({"user_id": "bob"})["token"]
        client.cookies.set("token", cookie)
        assert (await client.get("/who")).json() == {"subject": "bob", "kind": "user"}


async def test_missing_or_refresh_token_is_refused():
    async with _client() as client:
        assert (await client.get("/who")).status_code == 401
        refresh = base_sign_jwt({"user_id": "alice"})["refresh_token"]
        assert (await client.get("/who", headers={"Authorization": f"Bearer {refresh}"})).status_code == 403


async def test_service_principal_has_no_personal_data():
    async with _client() as client:
        assert (await client.get("/mine", headers={"X-Internal-Token": INTERNAL})).status_code == 403
        assert (await client.get("/mine", headers=_bearer("alice"))).json() == {"subject": "alice"}


async def test_without_jwt_everyone_is_local(settings, monkeypatch):
    monkeypatch.setattr(settings, "JWT_ACTIVE", False)
    async with _client() as client:
        for headers in ({}, _bearer("alice"), {"X-Internal-Token": "wrong"}):
            assert (await client.get("/who", headers=headers)).json() == {"subject": "local", "kind": "local"}


def test_ownership_rules():
    alice = Principal(subject="alice", kind="user")
    assert alice.can_see("alice") and not alice.can_see("bob") and not alice.can_see(None)
    assert LOCAL.can_see("local") and LOCAL.can_see(None) and not LOCAL.can_see("alice")
    assert not SERVICE.can_see(None) and SERVICE.is_service


def test_router_auth_dependency_is_the_principal(settings):
    assert [d.dependency for d in router_param_builder("book")["dependencies"]] == [current_principal]


def _request(headers):
    return Request({"type": "http", "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
                    "client": ("203.0.113.9", 1234)})


def test_rate_limit_key_of_the_service_principal():
    assert client_key(_request({"X-Internal-Token": INTERNAL})) == "service:internal"
    assert client_key(_request({"X-Internal-Token": "wrong"})) == "ip:203.0.113.9"
    assert client_key(_request(_bearer("alice"))) == "user:alice"


def test_short_internal_token_is_rejected(monkeypatch):
    monkeypatch.setenv("BE_INTERNAL_TOKEN", "too-short")
    with pytest.raises(ValidationError, match="INTERNAL_TOKEN"):
        BaseSetting()
    monkeypatch.setenv("BE_INTERNAL_TOKEN", "")
    assert BaseSetting().INTERNAL_TOKEN == ""
