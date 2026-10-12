import uuid

import pytest
from qdrant_client import QdrantClient

from service.vector_store import VectorStore, point_id

DIM = 4


def _unit(*xs):
    norm = sum(x * x for x in xs) ** 0.5
    return [x / norm for x in xs]


@pytest.fixture
def store():
    # Qdrant "local mode": the real query engine, in memory, no server needed.
    return VectorStore(client=QdrantClient(":memory:"), collection="test_chunks", dimensions=DIM)


def _chunks(n, start=0):
    return [{"chunk_index": i, "text": f"chunk {i}", "headings": ["H"], "page_start": i + 1, "page_end": i + 1}
            for i in range(start, start + n)]


def test_point_ids_are_deterministic():
    book = uuid.uuid4()
    assert point_id(book, 3) == point_id(book, 3) != point_id(book, 4)


def test_reindexing_overwrites_instead_of_duplicating(store):
    book = uuid.uuid4()
    vectors = [_unit(1, 0, 0, 0)] * 3
    store.upsert_chunks(book, "Book", _chunks(3), vectors, "m")
    store.upsert_chunks(book, "Book", _chunks(3), vectors, "m")
    assert store.count(book) == 3


def test_delete_stale_chunks_after_shrinking(store):
    book = uuid.uuid4()
    store.upsert_chunks(book, "Book", _chunks(5), [_unit(1, 0, 0, 0)] * 5, "m")
    store.delete_stale_chunks(book, keep_below=2)
    assert store.count(book) == 2


def test_search_filters_by_book_and_threshold(store):
    a, b = uuid.uuid4(), uuid.uuid4()
    store.upsert_chunks(a, "A", _chunks(1), [_unit(1, 0, 0, 0)], "m")
    store.upsert_chunks(b, "B", _chunks(1), [_unit(0.9, 0.1, 0, 0)], "m")
    hits = store.search(_unit(1, 0, 0, 0), book_ids=[str(b)], limit=5, min_score=0.5)
    assert [h.book_title for h in hits] == ["B"]
    assert hits[0].headings == ["H"] and hits[0].page_start == 1
    assert store.search(_unit(0, 0, 0, 1), book_ids=None, limit=5, min_score=0.5) == []


def test_delete_book_removes_only_that_book(store):
    a, b = uuid.uuid4(), uuid.uuid4()
    store.upsert_chunks(a, "A", _chunks(2), [_unit(1, 0, 0, 0)] * 2, "m")
    store.upsert_chunks(b, "B", _chunks(1), [_unit(1, 0, 0, 0)], "m")
    store.delete_book(a)
    assert store.count(a) == 0 and store.count(b) == 1


def test_dimension_mismatch_detected(store):
    store.ensure_collection()
    other = VectorStore(client=store.client, collection="test_chunks", dimensions=DIM + 1)
    with pytest.raises(RuntimeError, match="re-index"):
        other.ensure_collection()
