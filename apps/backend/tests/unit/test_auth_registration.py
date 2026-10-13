"""Account creation and login gates: Google routes only when configured, BE_AUTH_REGISTRATION_OPEN, active-only login."""

import bcrypt
import httpx
import pytest
from fastapi import APIRouter, FastAPI

import router.auth as auth_router
from dto.auth import AuthDTO
from service.auth import Auth, AuthErrors

PASSWORD = "correct horse battery"


def _client(app):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


def test_google_routes_are_not_mounted_without_oauth_settings(app, settings):
    assert not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/auth/login" in paths
    assert not [path for path in paths if path.startswith("/auth/google")]


async def test_google_register_answers_404_without_oauth_settings(app):
    async with _client(app) as client:
        response = await client.post("/auth/google/register", json={"email": "x@example.test", "phone": "1"})
    assert response.status_code == 404


@pytest.mark.parametrize("client_id, secret, mounted", [
    ("client-id", "client-secret", True),
    ("client-id", None, False),
    (None, "client-secret", False),
])
def test_google_routes_mount_only_with_both_oauth_settings(settings, monkeypatch, client_id, secret, mounted):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", client_id)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", secret)
    target = APIRouter(prefix="/auth")
    assert auth_router.mount_google_routes(target) is mounted
    paths = {route.path for route in target.routes}
    expected = {"/auth/google", "/auth/google/callback", "/auth/google/token_exchange", "/auth/google/register"}
    assert (paths == expected) is mounted and (not paths) is (not mounted)


@pytest.fixture
def closed(settings, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_REGISTRATION_OPEN", False)


@pytest.mark.parametrize("path, kwargs", [
    ("/auth/register", {"json": {"username": "ada", "email": "ada@example.test", "password": PASSWORD, "phone": "1"}}),
    ("/auth/verification", {"params": {"otp": "123456"}}),
])
async def test_registration_endpoints_answer_403_when_closed(app, closed, path, kwargs):
    async with _client(app) as client:
        response = await client.post(path, **kwargs)
    assert response.status_code == 403
    assert response.json()["metaData"]["message"] == "Registration is closed."
    assert response.json()["metaData"]["responseCode"] == 403


async def test_google_register_answers_403_when_closed(settings, monkeypatch, closed):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "client-secret")
    google_app = FastAPI()
    target = APIRouter(prefix="/auth")
    auth_router.mount_google_routes(target)
    google_app.include_router(target)
    async with _client(google_app) as client:
        response = await client.post("/auth/google/register", json={"email": "x@example.test", "phone": "1"})
    assert response.status_code == 403
    assert response.json()["detail"]["metaData"]["message"] == "Registration is closed."


def test_registration_is_open_by_default(monkeypatch):
    from config.base import BaseSetting

    monkeypatch.delenv("BE_AUTH_REGISTRATION_OPEN", raising=False)
    assert BaseSetting().AUTH_REGISTRATION_OPEN is True
    monkeypatch.setenv("BE_AUTH_REGISTRATION_OPEN", "false")
    assert BaseSetting().AUTH_REGISTRATION_OPEN is False


# ── Login: only active accounts ──────────────────────────────────────


class _Collection:
    def __init__(self, account):
        self.account = account

    def find_one(self, query):
        return self.account

    def update_one(self, *args, **kwargs):
        pass


class _Redis:
    def __init__(self):
        self.failures = 0

    def get(self, key):
        return None

    def incr(self, key):
        self.failures += 1
        return self.failures

    def expire(self, *args):
        pass

    def set(self, *args, **kwargs):
        pass

    def delete(self, *args):
        pass


class _Stub:
    def get_by_id(self, _id):
        return {}

    def get_user_status_by_id(self, _id):
        return None


def _auth(status, password=PASSWORD):
    service = Auth.__new__(Auth)   # no Mongo/Redis connections
    service.collection = _Collection({
        "_id": "user-1", "email": "ada@example.test",
        "password": bcrypt.hashpw(password.encode(), bcrypt.gensalt(4)).decode(), "status": status,
    })
    service.redis = _Redis()
    service.permission_service = _Stub()
    service.user_service = _Stub()
    return service


def _login(service, password=PASSWORD):
    return service.get_user_properties(AuthDTO(email="ada@example.test", password=password), {})


def test_active_account_logs_in():
    account, _, _ = _login(_auth("active"))
    assert account["_id"] == "user-1"


@pytest.mark.parametrize("status, message", [
    (None, AuthErrors.NO_LOGIN_ACCESS),
    ("", AuthErrors.NO_LOGIN_ACCESS),
    ("inactive", AuthErrors.NO_LOGIN_ACCESS),
    ("pending", AuthErrors.NO_LOGIN_ACCESS),
    ("blocked", AuthErrors.ACCOUNT_BLOCKED),
    ("deleted", AuthErrors.ACCOUNT_DELETED),
])
def test_non_active_account_is_refused(status, message):
    with pytest.raises(Exception, match=message):
        _login(_auth(status))


def test_wrong_password_does_not_reveal_the_account_state():
    with pytest.raises(Exception, match=AuthErrors.INCORRECT_CREDENTIALS):
        _login(_auth("blocked"), password="wrong")


def test_refusal_messages_map_to_403():
    assert {AuthErrors.NO_LOGIN_ACCESS, AuthErrors.ACCOUNT_BLOCKED, AuthErrors.ACCOUNT_DELETED,
            AuthErrors.ACCOUNT_EXPIRED} <= set(auth_router._FORBIDDEN_MESSAGES)
