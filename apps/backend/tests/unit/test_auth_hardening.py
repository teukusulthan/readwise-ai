"""Account security: emailed codes bound to their email with an attempt limit, pending registrations without the
password, refresh/logout revocation, unknown-account lockout, the password policy and caller-safe error messages."""

import json
import time

import bcrypt
import fakeredis
import httpx
import pytest
from fastapi import Depends, FastAPI
from pydantic import ValidationError

import router.auth as auth_router
from auth import auth_bearer
from auth.auth_bearer import JWTRefresh
from auth.auth_handler import base_sign_jwt, revoked_token_key
from dto.auth import AuthDTO, ChangePasswordOTPDTO, EmailOtpDTO, RegisterDTO, password_problem
from service.auth import OTP_MAX_ATTEMPTS, Auth, AuthError, AuthErrors

PASSWORD = "correct horse battery"


class _Users:
    """Just enough of a Mongo collection: find_one by `_id` or by any identifier in an `$or` of `$in`/equals."""

    def __init__(self, *accounts):
        self.accounts = list(accounts)
        self.updates = []

    def find_one(self, query, collation=None):
        for account in self.accounts:
            if self._matches(account, query, collation):
                return account
        return None

    def _matches(self, account, query, collation):
        if "$or" in query:
            return any(self._matches(account, clause, collation) for clause in query["$or"])
        for field, condition in query.items():
            values = condition["$in"] if isinstance(condition, dict) else [condition]
            stored = account.get(field)
            if collation and isinstance(stored, str):
                if stored.lower() not in {str(v).lower() for v in values}:
                    return False
            elif stored not in values:
                return False
        return True

    def update_one(self, query, update):
        self.updates.append((query, update))
        for account in self.accounts:
            if account["_id"] == query["_id"]:
                account.update(update.get("$set", {}))


class _UserService:
    def __init__(self):
        self.added = []

    def add(self, dto, password_is_hash=False):
        self.added.append((dto, password_is_hash))
        return {"id": "new-user"}

    def get_by_id(self, _id):
        return {}

    def get_user_status_by_id(self, _id):
        return None


def _account(**fields):
    return {
        "_id": "user-1", "email": "ada@example.test", "username": "ada", "phone": "+15550001", "fullname": "Ada",
        "password": bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(4)).decode(), "status": "active",
        "emailVerified": True, **fields,
    }


@pytest.fixture
def redis():
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def service(redis):
    auth = Auth.__new__(Auth)   # no Mongo/Redis/SMTP connections
    auth.collection = _Users(_account())
    auth.redis = redis
    auth.user_service = _UserService()
    auth.permission_service = _UserService()
    auth.group_service = _UserService()
    auth.sent = []
    auth._send_mail = lambda to, subject, body: auth.sent.append((to, body))
    return auth


def _register_dto(**fields):
    values = {"fullname": "Grace", "username": "grace", "email": "grace@example.test", "password": PASSWORD,
              "phone": "+1 555 0002", **fields}
    return RegisterDTO(**values)


@pytest.fixture(autouse=True)
def no_mail_checks(settings, monkeypatch):
    # RegisterDTO would otherwise ask DNS and Proofy whether the address can receive mail.
    monkeypatch.setattr(settings, "AUTH_EMAIL_VERIFICATION", False)


# ── emailed codes ────────────────────────────────────────────────────


def test_a_code_only_works_for_its_own_email(service):
    service.store_otp("register-otp", "grace@example.test", "123456", {"user": {"username": "grace"}})
    with pytest.raises(AuthError, match=AuthErrors.OTP_INVALID):
        service.check_otp("register-otp", "other@example.test", "123456")
    # The email is matched case-insensitively.
    assert service.check_otp("register-otp", "GRACE@example.test", "123456")["user"] == {"username": "grace"}


def test_a_code_is_used_once(service):
    service.store_otp("register-otp", "grace@example.test", "123456", {"user": {"username": "grace"}})
    assert service.check_otp("register-otp", "grace@example.test", "123456")["user"] == {"username": "grace"}
    with pytest.raises(AuthError, match=AuthErrors.OTP_INVALID):
        service.check_otp("register-otp", "grace@example.test", "123456")


def test_wrong_guesses_burn_the_code(service):
    service.store_otp("reset-otp", "ada@example.test", "123456", {"userId": "user-1"})
    for guess in range(OTP_MAX_ATTEMPTS):
        with pytest.raises(AuthError, match=AuthErrors.OTP_INVALID):
            service.check_otp("reset-otp", "ada@example.test", f"{guess:06d}")
    # The right code no longer works: guessing is capped at OTP_MAX_ATTEMPTS tries per mailed code.
    with pytest.raises(AuthError, match=AuthErrors.OTP_INVALID):
        service.check_otp("reset-otp", "ada@example.test", "123456")


def test_codes_are_stored_hashed(service, redis):
    service.store_otp("register-otp", "grace@example.test", "123456", {})
    assert not any("123456" in (redis.get(key) or "") for key in redis.keys("*") if redis.type(key) == "string")


# ── registration ─────────────────────────────────────────────────────


def test_pending_registration_keeps_only_a_password_hash(service, settings, monkeypatch, redis):
    dto = _register_dto()   # built with the deliverability check off (no network in unit tests)
    monkeypatch.setattr(settings, "AUTH_EMAIL_VERIFICATION", True)

    assert service.register(dto) == {"message": "Email register sent", "verificationRequired": True}
    stored = "".join(redis.get(key) or "" for key in redis.keys("register-otp:*") if redis.type(key) == "string")
    assert PASSWORD not in stored and "passwordHash" in stored
    (to, body), = service.sent
    otp = next(word for word in body.split() if word.isdigit() and len(word) == 6)

    result = service.verify_register_otp(EmailOtpDTO(email="grace@example.test", otp=otp))
    assert result == {"message": "Account verified"}   # never the account (or its password) back
    (user, password_is_hash), = service.user_service.added
    assert password_is_hash and bcrypt.checkpw(PASSWORD.encode(), user.password.encode())
    assert user.phone == "+15550002" and user.emailVerified is True and user.status == "active"


def test_failed_mail_drops_the_pending_registration(service, settings, monkeypatch, redis):
    dto = _register_dto()
    monkeypatch.setattr(settings, "AUTH_EMAIL_VERIFICATION", True)

    def broken(*args):
        raise OSError("smtp down at 10.0.0.5")

    service._send_mail = broken
    with pytest.raises(AuthError, match=AuthErrors.MAIL_FAILED):
        service.register(dto)
    assert not redis.keys("register-otp:*")


@pytest.mark.parametrize("fields, message", [
    ({"email": "ADA@example.test"}, AuthErrors.EMAIL_TAKEN),
    ({"username": "Ada"}, AuthErrors.USERNAME_TAKEN),
    ({"phone": "+1 555 0001"}, AuthErrors.PHONE_TAKEN),
    # Another account's email or phone as a username would shadow that account at login.
    ({"phone": "+15550099", "username": "ada.alt", "email": "ada"}, None),
])
def test_identifiers_must_be_unused_by_any_account(service, fields, message):
    if message is None:
        with pytest.raises(ValidationError):
            _register_dto(**fields)
        return
    with pytest.raises(AuthError, match=message):
        service.register(_register_dto(**fields))


# ── login ────────────────────────────────────────────────────────────


def test_unknown_accounts_lock_like_real_ones(service, settings):
    for _ in range(settings.ACCOUNT_FAIL_LIMIT):
        with pytest.raises(AuthError, match=AuthErrors.INCORRECT_CREDENTIALS):
            service.login(AuthDTO(email="nobody@example.test", password="whatever-1"))
    with pytest.raises(AuthError, match="temporarily locked"):
        service.login(AuthDTO(email="nobody@example.test", password="whatever-1"))


def test_login_without_password_is_refused_not_a_crash(service):
    with pytest.raises(AuthError, match=AuthErrors.INCORRECT_CREDENTIALS):
        service.login(AuthDTO(email="ada@example.test"))


# ── refresh and logout ───────────────────────────────────────────────


def test_refresh_mints_a_new_pair_for_an_active_account(service):
    tokens = base_sign_jwt({"user_id": "user-1", "multiLogin": True})
    assert service.refresh(tokens["refresh_token"])["token"]


def test_refresh_refuses_an_access_token(service):
    tokens = base_sign_jwt({"user_id": "user-1", "multiLogin": True})
    with pytest.raises(AuthError, match=AuthErrors.SESSION_EXPIRED):
        service.refresh(tokens["token"])


@pytest.mark.parametrize("change", [{"status": "blocked"}, {"status": "deleted"}, {"passwordChangedAt": None}])
def test_refresh_rechecks_the_account(service, change):
    tokens = base_sign_jwt({"user_id": "user-1", "multiLogin": True})
    if "passwordChangedAt" in change:
        change = {"passwordChangedAt": time.time() + 1}   # password reset after the token was issued
    service.collection.accounts[0].update(change)
    with pytest.raises(AuthError):
        service.refresh(tokens["refresh_token"])


def test_refresh_refuses_a_deleted_account(service):
    tokens = base_sign_jwt({"user_id": "gone", "multiLogin": True})
    with pytest.raises(AuthError, match=AuthErrors.SESSION_EXPIRED):
        service.refresh(tokens["refresh_token"])


def test_logout_revokes_the_refresh_token(service, redis):
    tokens = base_sign_jwt({"user_id": "user-1", "multiLogin": True})
    service.logout(tokens["refresh_token"])
    assert 0 < redis.ttl(revoked_token_key(tokens["refresh_token"])) <= 604800
    with pytest.raises(AuthError, match=AuthErrors.SESSION_EXPIRED):
        service.refresh(tokens["refresh_token"])


@pytest.fixture
def refresh_client(redis, monkeypatch):
    monkeypatch.setattr(auth_bearer.redis, "RedisService", lambda: redis)
    app = FastAPI()

    @app.get("/refresh-only", dependencies=[Depends(JWTRefresh())])
    def refresh_only():
        return {"ok": True}

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_jwt_refresh_dependency_accepts_only_live_refresh_tokens(refresh_client, redis):
    tokens = base_sign_jwt({"user_id": "user-1"})
    async with refresh_client as client:
        ok = await client.get("/refresh-only", cookies={"refresh_token": tokens["refresh_token"]})
        assert ok.status_code == 200
        access = await client.get("/refresh-only", headers={"Authorization": f"Bearer {tokens['token']}"})
        assert access.status_code == 403
        redis.set(revoked_token_key(tokens["refresh_token"]), "1", ex=60)
        revoked = await client.get("/refresh-only", cookies={"refresh_token": tokens["refresh_token"]})
        assert revoked.status_code == 401


# ── password reset ───────────────────────────────────────────────────


def test_reset_answer_does_not_reveal_whether_the_account_exists(service):
    from dto.auth import RequestChangeDTO

    unknown = service.request_change(RequestChangeDTO.model_construct(email="nobody@example.test"))
    known = service.request_change(RequestChangeDTO.model_construct(email="ada@example.test"))
    throttled = service.request_change(RequestChangeDTO.model_construct(email="ada@example.test"))
    assert unknown == known == throttled == {"message": AuthErrors.RESET_REQUESTED}
    assert len(service.sent) == 1


def test_reset_changes_the_password_and_ends_old_sessions(service):
    from dto.auth import RequestChangeDTO

    old_tokens = base_sign_jwt({"user_id": "user-1", "multiLogin": True})
    time.sleep(0.01)
    service.request_change(RequestChangeDTO.model_construct(email="ada@example.test"))
    otp = next(word for word in service.sent[0][1].split() if word.isdigit() and len(word) == 6)
    new_password = "a brand new passphrase"
    assert service.change_password_by_otp(
        ChangePasswordOTPDTO(email="ada@example.test", otp=otp, newPassword=new_password)
    ) == {"message": "Password changed"}
    assert bcrypt.checkpw(new_password.encode(), service.collection.accounts[0]["password"].encode())
    with pytest.raises(AuthError, match=AuthErrors.SESSION_EXPIRED):
        service.refresh(old_tokens["refresh_token"])


# ── input rules ──────────────────────────────────────────────────────


@pytest.mark.parametrize("password, refused", [
    ("short1!", True),
    ("password123", True),
    ("grace", True),
    ("ä" * 37, True),            # 74 bytes: bcrypt would ignore the end
    ("correct horse battery", False),
])
def test_password_policy(password, refused):
    assert (password_problem(password, username="grace", email="grace@example.test") is not None) is refused


@pytest.mark.parametrize("fields", [
    {"username": "ab"},
    {"username": "12345678"},                 # could equal a phone number
    {"username": "ada@example.test"},         # could equal an email
    {"email": "grace@example.test\nBcc: x@example.test"},
    {"phone": "call me"},
    {"fullname": "Grace\r\nBcc: x@example.test"},
    {"password": "grace@example.test"},
])
def test_register_input_is_validated(fields):
    with pytest.raises(ValidationError):
        _register_dto(**fields)


def test_register_input_is_normalised():
    dto = _register_dto(email="  Grace@Example.TEST ", phone="+1 (555) 000-2", username=" grace ")
    assert (dto.email, dto.phone, dto.username) == ("grace@example.test", "+15550002", "grace")


# ── router ───────────────────────────────────────────────────────────


def test_only_auth_errors_reach_the_caller():
    assert auth_router.public_message(AuthError(AuthErrors.OTP_INVALID)) == AuthErrors.OTP_INVALID
    assert auth_router.public_message(KeyError("password")) == auth_router.GENERIC_ERROR_MESSAGE


async def test_unexpected_login_errors_are_generic(app, monkeypatch):
    def boom(dto):
        raise RuntimeError("mongo at 10.0.0.7 refused the connection")

    monkeypatch.setattr(auth_router.obj, "login", boom)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/auth/login", json={"email": "ada", "password": PASSWORD})
    assert response.status_code == 400
    assert response.json()["metaData"]["message"] == auth_router.GENERIC_ERROR_MESSAGE
    assert "10.0.0.7" not in response.text
