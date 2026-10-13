"""Accounts on the real stores: per-user conversations (Postgres), register + login (Mongo/Redis), service token."""

import httpx
import pytest

import router.chat as chat_router
from auth.auth_handler import base_sign_jwt
from auth.principal import LOCAL
from config.base import settings
from service import Services
from service.chat_session import ChatSessions, RedisSessionStore
from service.conversation import Conversation
from service.conversation_repository import ConversationRepository
from service.rag import Rag
from tests.integration.test_conversation_api import OneHitSearch

pytestmark = pytest.mark.integration

INTERNAL = "internal-token-for-tests-0123456789abcdef"


@pytest.fixture(autouse=True)
def clean_conversations():
    with Services.postgres().connection() as conn:
        conn.execute("TRUNCATE conversations CASCADE")
    yield


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch):
    monkeypatch.setattr(settings, "JWT_ACTIVE", True)
    monkeypatch.setattr(settings, "INTERNAL_TOKEN", INTERNAL)


@pytest.fixture
def chat(redis_client, monkeypatch):
    async def stream(system, user):
        yield "The lifeboat came [1]."

    service = Conversation(rag=Rag(search=OneHitSearch(), streamer=stream))
    monkeypatch.setattr(chat_router, "sessions",
                        ChatSessions(conversations=service, store=RedisSessionStore(client=redis_client)))


def _client(app, **headers):
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", headers=headers, timeout=60)


def _user(app, user_id):
    return _client(app, Authorization=f"Bearer {base_sign_jwt({'user_id': user_id})['token']}")


async def test_conversations_are_isolated_between_users(app, chat):
    async with _user(app, "alice") as alice, _user(app, "bob") as bob:
        response = await alice.post("/chat/stream", json={"question": "Who came to the rescue?"})
        assert response.status_code == 200 and "event: done" in response.text
        mine = (await alice.get("/conversation/get-all")).json()
        assert mine["metaData"]["pagination"]["totalElements"] == 1
        conversation_id = mine["data"][0]["id"]

        theirs = (await bob.get("/conversation/get-all")).json()
        assert theirs["data"] == [] and theirs["metaData"]["pagination"]["totalElements"] == 0
        # Someone else's conversation is "not found" (its existence is not revealed).
        assert (await bob.get("/conversation/get-one", params={"id": conversation_id})).status_code == 404
        assert (await bob.put("/conversation/rename", json={"id": conversation_id, "title": "Mine"})).status_code == 404
        assert (await bob.delete("/conversation/delete", params={"id": conversation_id})).status_code == 404
        assert (await bob.get("/chat/active", params={"conversationId": conversation_id})).status_code == 404
        hijack = await bob.post("/chat/stream", json={"question": "And then?", "conversationId": conversation_id})
        assert hijack.status_code == 404 and hijack.headers["content-type"].startswith("application/json")

        detail = (await alice.get("/conversation/get-one", params={"id": conversation_id})).json()["data"]
        assert detail["title"] == "Who came to the rescue?" and len(detail["messages"]) == 2


async def test_local_owner_sees_legacy_rows_and_users_do_not(app, chat, monkeypatch):
    repo = ConversationRepository()
    legacy = repo.create("Before accounts", owner_id=None)   # rows from before migration 004
    users_row = repo.create("Alice's", owner_id="alice")

    monkeypatch.setattr(settings, "JWT_ACTIVE", False)
    async with _client(app) as anyone:
        listing = (await anyone.get("/conversation/get-all")).json()["data"]
        assert [c["title"] for c in listing] == ["Before accounts"]
        assert (await anyone.get("/conversation/get-one", params={"id": str(legacy["id"])})).status_code == 200
        assert (await anyone.get("/conversation/get-one", params={"id": str(users_row["id"])})).status_code == 404
        response = await anyone.post("/chat/stream", json={"question": "Who came?"})
        assert "event: done" in response.text
    with Services.postgres().connection() as conn:
        owners = {r["title"]: r["owner_id"] for r in conn.execute("SELECT title, owner_id FROM conversations")}
    assert owners == {"Before accounts": None, "Alice's": "alice", "Who came?": "local"}

    monkeypatch.setattr(settings, "JWT_ACTIVE", True)
    async with _user(app, "alice") as alice:
        assert [c["title"] for c in (await alice.get("/conversation/get-all")).json()["data"]] == ["Alice's"]
        assert (await alice.get("/conversation/get-one", params={"id": str(legacy["id"])})).status_code == 404
    assert repo.get(legacy["id"], LOCAL) is not None


async def test_service_token_reads_the_shared_catalog_but_has_no_conversations(app, chat):
    async with _client(app, **{"X-Internal-Token": INTERNAL}) as service:
        assert (await service.post("/book/get-all", json={"page": 1, "size": 5})).status_code == 200
        assert (await service.get("/conversation/get-all")).status_code == 403
        assert (await service.post("/chat/stream", json={"question": "Who came?"})).status_code == 403
    async with _client(app, **{"X-Internal-Token": "wrong"}) as forged:
        assert (await forged.post("/book/get-all", json={"page": 1, "size": 5})).status_code == 403
    async with _client(app) as anonymous:
        assert (await anonymous.post("/book/get-all", json={"page": 1, "size": 5})).status_code == 401


@pytest.fixture
def users():
    collection = Services.mongo().get_database(settings.MONGO_DB)[settings.MONGO_COLLECTION_USER]
    collection.delete_many({"email": {"$regex": "@accounts\\.test$"}})
    yield collection
    collection.delete_many({"email": {"$regex": "@accounts\\.test$"}})


async def test_register_without_verification_then_login_owns_conversations(app, chat, users, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_EMAIL_VERIFICATION", False)
    account = {"fullname": "Ada Reader", "username": "ada", "email": "ada@accounts.test",
               "password": "correct horse battery", "phone": "+15550001"}
    async with _client(app) as client:
        registered = await client.post("/auth/register", json=account)
        assert registered.status_code == 200, registered.text
        assert registered.json()["data"]["verificationRequired"] is False
        stored = users.find_one({"email": "ada@accounts.test"})
        assert stored["status"] == "active" and stored["password"] != account["password"]   # hashed
        assert (await client.post("/auth/register", json=account)).status_code == 400        # duplicate

        assert (await client.post("/auth/login", json={"email": "ada@accounts.test", "password": "wrong"})).status_code == 400
        login = await client.post("/auth/login", json={"email": "ada", "password": account["password"]})
        assert login.status_code == 200, login.text
        user = login.json()["data"]["user"]
        assert user["id"] == stored["_id"] and user["email"] == "ada@accounts.test"
        assert "token" not in login.json()["data"]                                            # cookies only
        assert all("secure" in h.lower() for h in login.headers.get_list("set-cookie"))      # default: Secure
        token = login.cookies["token"]

        # Plain-HTTP development (BE_AUTH_COOKIE_SECURE=false): the same cookies without `Secure`.
        monkeypatch.setattr(settings, "AUTH_COOKIE_SECURE", False)
        insecure = await client.post("/auth/login", json={"email": "ada", "password": account["password"]})
        assert insecure.status_code == 200
        assert not any("secure" in h.lower() for h in insecure.headers.get_list("set-cookie"))
        monkeypatch.setattr(settings, "AUTH_COOKIE_SECURE", True)

        # The web's post-login check (GET /auth/validate): 401 when the browser did not keep the cookies.
        client.cookies.clear()
        assert (await client.get("/auth/validate")).status_code == 401
        # The web client's 401 path: /auth/refresh with the refresh cookie mints a new access cookie.
        client.cookies.set("refresh_token", login.cookies["refresh_token"])
        assert (await client.get("/auth/validate")).json()["data"] == {"status": "active"}
        refreshed = await client.get("/auth/refresh")
        assert refreshed.status_code == 200 and refreshed.cookies.get("token")

        # Sign out works even when the access cookie has already expired (only the refresh cookie is sent).
        client.cookies.delete("token")
        logout = await client.delete("/auth/logout")
        assert logout.status_code == 200 and 'token=""' in logout.headers.get("set-cookie", "")

    # The HttpOnly cookie identifies the user; the conversation is stored under its user id.
    async with _client(app) as browser:
        browser.cookies.set("token", token)
        assert "event: done" in (await browser.post("/chat/stream", json={"question": "Who came?"})).text
        assert (await browser.get("/conversation/get-all")).json()["metaData"]["pagination"]["totalElements"] == 1
    with Services.postgres().connection() as conn:
        assert conn.execute("SELECT owner_id FROM conversations").fetchone()["owner_id"] == stored["_id"]
