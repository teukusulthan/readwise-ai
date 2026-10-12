"""Conversation history on the real Postgres test database (repository SQL + HTTP endpoints)."""

import pytest

import router.chat as chat_router
from auth.principal import LOCAL
from service import Services
from service.chat_session import ChatSessions, RedisSessionStore
from service.conversation import Conversation
from service.conversation_repository import ConversationRepository
from service.rag import Rag
from service.search import Retrieval
from service.vector_store import ChunkHit

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def clean_conversations():
    with Services.postgres().connection() as conn:
        conn.execute("TRUNCATE conversations CASCADE")
    yield


class OneHitSearch:
    def retrieve(self, question, book_ids=None, top_k=None, min_score=None, follow_up_of=None):
        hit = ChunkHit(score=0.8, book_id="b1", book_title="Saltmere", chunk_index=0, text="The lifeboat came.",
                       headings=[], page_start=1, page_end=1)
        return Retrieval(hits=[hit], searched_book_ids=["b1"])


def test_repository_round_trip_keeps_order_and_json():
    repo = ConversationRepository()
    conversation = repo.create("Lifeboat", book_ids=[], owner_id="local")
    repo.add_message(conversation["id"], {"role": "user", "content": "Who came?", "book_ids": []})
    repo.add_message(conversation["id"], {"role": "assistant", "content": "The lifeboat [1].", "mode": "llm",
                                          "grounded": True, "sources": [{"n": 1, "cited": True}]})
    messages = repo.messages(conversation["id"])
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["sources"] == [{"n": 1, "cited": True}]
    assert [m["role"] for m in repo.recent_messages(conversation["id"], 1)] == ["assistant"]
    rows, total = repo.list_recent(LOCAL)
    assert total == 1 and rows[0]["message_count"] == 2
    assert repo.delete(conversation["id"], LOCAL) and repo.messages(conversation["id"]) == []  # cascade


async def test_stream_then_list_rename_delete(client, redis_client, monkeypatch):
    async def stream(system, user):
        yield "The lifeboat came [1]."

    service = Conversation(rag=Rag(search=OneHitSearch(), streamer=stream))
    monkeypatch.setattr(chat_router, "sessions", ChatSessions(conversations=service, store=RedisSessionStore(client=redis_client)))

    async with client:
        response = await client.post("/chat/stream", json={"question": "Who came to the rescue?"})
        assert response.status_code == 200 and "event: done" in response.text

        listing = (await client.get("/conversation/get-all")).json()
        assert listing["metaData"]["pagination"]["totalElements"] == 1
        conversation_id = listing["data"][0]["id"]
        assert listing["data"][0]["title"] == "Who came to the rescue?"

        detail = (await client.get("/conversation/get-one", params={"id": conversation_id})).json()["data"]
        assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
        assert detail["messages"][1]["mode"] == "llm" and detail["messages"][1]["sources"][0]["cited"] is True

        renamed = await client.put("/conversation/rename", json={"id": conversation_id, "title": "  Rescue  "})
        assert renamed.json()["data"]["title"] == "Rescue"

        assert (await client.delete("/conversation/delete", params={"id": conversation_id})).status_code == 200
        assert (await client.get("/conversation/get-one", params={"id": conversation_id})).status_code == 404
        assert (await client.get("/conversation/get-one", params={"id": "not-a-uuid"})).status_code == 400
