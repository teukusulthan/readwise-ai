import uuid

import pytest
from qdrant_client import QdrantClient

from service.ingestion import Ingestion
from service.vector_store import VectorStore

DIM = 4


class FakeRepository:
    """In-memory stand-in for BookRepository's status methods."""

    def __init__(self, book):
        self.book = book
        self.history = [book["ingestion_status"]]

    def transition_status(self, book_id, to_status, from_statuses, **fields):
        if self.book["ingestion_status"] not in from_statuses:
            return None
        self.book.update(fields, ingestion_status=to_status)
        self.history.append(to_status)
        return dict(self.book)


class FakeEmbedder:
    model = "fake-embedder"

    def __init__(self):
        self.batches = []

    def embed_documents(self, texts):
        self.batches.append(list(texts))
        return [[1.0, 0.0, 0.0, 0.0] for _ in texts]


def _book(status="queued"):
    return {"id": uuid.uuid4(), "title": "Sample", "file_path": "/tmp/sample.pdf", "ingestion_status": status,
            "ingestion_error": None}


def _parser(chunks, pages=3):
    return lambda path: (pages, iter(chunks))


def _chunks(n):
    return [{"text": f"text {i}", "embed_text": f"Heading\ntext {i}", "headings": ["Heading"],
             "page_start": 1, "page_end": 1} for i in range(n)]


@pytest.fixture
def store():
    return VectorStore(client=QdrantClient(":memory:"), collection="ingest_test", dimensions=DIM)


def _ingestion(book, store, parser, embedder=None):
    return Ingestion(repository=FakeRepository(book), vector_store=store, embedder=embedder or FakeEmbedder(),
                     parser=parser, run_inline=True)


def test_indexes_in_embedding_batches_and_records_result(store, settings, monkeypatch):
    monkeypatch.setattr(settings, "ENGINE_EMBEDDING_BATCH_SIZE", 32)
    book, embedder = _book(), FakeEmbedder()
    ingestion = _ingestion(book, store, _parser(_chunks(70)), embedder)
    ingestion.enqueue(book["id"])

    assert ingestion.repository.history == ["queued", "processing", "indexed"]
    assert book["chunk_count"] == 70 and book["page_count"] == 3 and book["embedding_model"] == "fake-embedder"
    assert [len(b) for b in embedder.batches] == [32, 32, 6]
    assert embedder.batches[0][0] == "Heading\ntext 0"  # contextualized text is what gets embedded
    assert store.count(book["id"]) == 70


def test_reindex_with_fewer_chunks_leaves_no_stale_points(store):
    book = _book()
    _ingestion(book, store, _parser(_chunks(10))).enqueue(book["id"])
    book["ingestion_status"] = "queued"
    _ingestion(book, store, _parser(_chunks(4))).enqueue(book["id"])
    assert store.count(book["id"]) == 4 and book["chunk_count"] == 4


def test_runs_only_when_queued(store):
    book = _book(status="indexed")
    ingestion = _ingestion(book, store, _parser(_chunks(3)))
    ingestion.enqueue(book["id"])
    assert ingestion.repository.history == ["indexed"]


def test_no_text_fails_with_helpful_message(store):
    book = _book()
    _ingestion(book, store, _parser([{"text": "  "}])).enqueue(book["id"])
    assert book["ingestion_status"] == "failed"
    assert "No text could be extracted" in book["ingestion_error"]


def test_unexpected_error_fails_without_leaking_details(store):
    def broken_parser(path):
        raise RuntimeError("/secret/internal/path exploded")

    book = _book()
    _ingestion(book, store, broken_parser).enqueue(book["id"])
    assert book["ingestion_status"] == "failed"
    assert "secret" not in book["ingestion_error"]


def test_too_many_pages_rejected(store, settings, monkeypatch):
    monkeypatch.setattr(settings, "MAX_PDF_PAGES", 2)
    book = _book()
    _ingestion(book, store, _parser(_chunks(1), pages=3)).enqueue(book["id"])
    assert book["ingestion_status"] == "failed" and "limit is 2" in book["ingestion_error"]


def test_worker_threads_are_daemons_so_shutdown_never_waits():
    import threading

    from service.ingestion import _Workers

    done = threading.Event()
    _Workers.submit(done.set)
    assert done.wait(5)
    workers = [t for t in threading.enumerate() if t.name.startswith("ingest-")]
    assert workers and all(t.daemon for t in workers)
