"""RedisSessionStore's atomic claim primitives against fakeredis (SET NX EX and the Lua scripts really run)."""

import fakeredis
import pytest

from service.chat_session import RedisSessionStore

CID = "11111111-1111-1111-1111-111111111111"
KEY = f"chat:conversation:{CID}:active"


@pytest.fixture
async def store():
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    yield RedisSessionStore(client=client)
    await client.aclose()


async def test_claim_active_is_nx_and_sets_a_ttl(store):
    assert await store.claim_active(CID, "a")
    assert not await store.claim_active(CID, "b")
    assert await store.get_active(CID) == "a"
    assert 0 < await store.client.ttl(KEY) <= store.ttl


async def test_clear_active_only_deletes_its_own_claim(store):
    await store.claim_active(CID, "a")
    await store.clear_active(CID, "b")
    assert await store.get_active(CID) == "a"
    await store.clear_active(CID, "a")
    assert await store.get_active(CID) is None
    await store.clear_active(CID, "a")   # already gone: no error


async def test_replace_active_is_compare_and_swap_and_resets_ttl(store):
    await store.claim_active(CID, "a")
    assert not await store.replace_active(CID, "wrong", "b")
    assert await store.get_active(CID) == "a"
    await store.client.expire(KEY, 5)
    assert await store.replace_active(CID, "a", "b")
    assert await store.get_active(CID) == "b"
    assert 5 < await store.client.ttl(KEY) <= store.ttl
    assert not await store.replace_active("22222222-2222-2222-2222-222222222222", "a", "b")   # absent key
