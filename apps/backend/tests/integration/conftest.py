"""
Integration fixtures: a dedicated `library_test` database and `book_chunks_test`
Qdrant collection on the docker compose services (never the dev data).
"""

import hashlib
import math
import re

import httpx
import psycopg
import pytest
from redis.asyncio import Redis

from auth.auth_handler import base_sign_jwt
from config.base import settings
from service import Services
from util.migrate import migrate

ADMIN_URI = settings.POSTGRES_URI.rsplit("/", 1)[0] + "/library"


@pytest.fixture(scope="session", autouse=True)
def test_database():
    with psycopg.connect(ADMIN_URI, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = 'library_test'").fetchone()
        if not exists:
            conn.execute("CREATE DATABASE library_test")
    migrate(Services.postgres())
    qdrant = Services.qdrant()
    if qdrant.collection_exists(settings.QDRANT_COLLECTION):
        qdrant.delete_collection(settings.QDRANT_COLLECTION)
    yield
    if qdrant.collection_exists(settings.QDRANT_COLLECTION):
        qdrant.delete_collection(settings.QDRANT_COLLECTION)


@pytest.fixture(autouse=True)
def clean_books():
    with Services.postgres().connection() as conn:
        conn.execute("TRUNCATE books")
    yield


@pytest.fixture
def client(app):
    token = base_sign_jwt({"user_id": "integration-test"})["token"]
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test",
                             headers={"Authorization": f"Bearer {token}"}, timeout=120)


class HashEmbedder:
    """Deterministic bag-of-words vectors (no network). Shared words → higher cosine similarity."""

    model = "hash-embedder"

    def __init__(self, dimensions):
        self.dimensions = dimensions

    def _vector(self, text):
        vector = [0.0] * self.dimensions
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dimensions] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts):
        return [self._vector(t) for t in texts]

    def embed_query(self, text):
        return self._vector(text)


@pytest.fixture
def hash_embedder():
    return HashEmbedder(settings.ENGINE_EMBEDDING_DIMENSIONS)


# Chat sessions live in Redis (test DB from tests/conftest.py); keys are cleaned before and after.
@pytest.fixture
async def redis_client():
    client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, password=settings.REDIS_PASSWORD or None,
                   db=settings.REDIS_DB, decode_responses=True)
    async def clean():
        async for key in client.scan_iter("chat:*"):
            await client.delete(key)
    await clean()
    yield client
    await clean()
    await client.aclose()
