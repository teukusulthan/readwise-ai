"""
Calls the real company embedding service (internal network).
Run explicitly: `uv run pytest -m external` (service URL from EMBEDDING_TEST_BASE_URL or
apps/backend/.env — see the `embedding_base_url` fixture — and network access to the service).
"""

import math
import os

import pytest

from util.embedding import EmbeddingClient

pytestmark = pytest.mark.external

MODEL = os.environ.get("BE_ENGINE_EMBEDDING_MODEL", "Qwen3-Embedding-0.6B")
DIMENSIONS = int(os.environ.get("BE_ENGINE_EMBEDDING_DIMENSIONS", "1024"))


@pytest.fixture(scope="module")
def client(embedding_base_url):
    client = EmbeddingClient(base_url=embedding_base_url, model=MODEL, dimensions=DIMENSIONS)
    yield client
    client.close()


def _cos(a, b):
    return sum(x * y for x, y in zip(a, b))  # vectors are L2-normalised by the service


def test_service_is_up(client):
    client.ping()


def test_vectors_have_configured_size_and_unit_norm(client):
    (vector,) = client.embed_documents(["A library holds books."])
    assert len(vector) == DIMENSIONS
    assert math.isclose(math.sqrt(sum(x * x for x in vector)), 1.0, rel_tol=1e-3)


def test_more_than_one_server_batch(client):
    vectors = client.embed_documents([f"passage number {i}" for i in range(40)])
    assert len(vectors) == 40


def test_relevant_passage_ranks_first(client):
    passages = [
        "Photosynthesis converts light energy into chemical energy inside chloroplasts.",
        "The French Revolution began in 1789 and ended the monarchy in France.",
        "A binary search tree keeps keys ordered so lookups take logarithmic time.",
    ]
    passage_vectors = client.embed_documents(passages)
    query = client.embed_query("When did the French monarchy end?")
    scores = [_cos(query, vector) for vector in passage_vectors]
    assert max(range(len(scores)), key=scores.__getitem__) == 1
