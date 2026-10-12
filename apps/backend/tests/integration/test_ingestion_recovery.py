"""
Self-healing indexing against real PostgreSQL + Qdrant (library_test / book_chunks_test):
migration 003 (ingestion_attempts), the counting claim, and startup recovery.
"""

import pytest

from service import Services
from service.book import Book
from service.book_repository import INTERRUPTED_MESSAGE, BookRepository
from service.ingestion import Ingestion

pytestmark = pytest.mark.integration

CHUNKS = [{"text": "Saltmere Light was built in 1847.", "headings": ["Chapter 1"], "page_start": 1, "page_end": 1}]


def _book(repo, title, status, attempts):
    row = repo.insert({"title": title, "file_path": f"/books/{title}.pdf", "ingestion_status": status})
    with Services.postgres().connection() as conn:  # attempts are only written by claims / recovery
        conn.execute("UPDATE books SET ingestion_attempts = %s WHERE id = %s", (attempts, row["id"]))
    return row["id"]


def test_migration_adds_attempts_column_defaulting_to_zero():
    with Services.postgres().connection() as conn:
        column = conn.execute(
            "SELECT data_type, is_nullable, column_default FROM information_schema.columns "
            "WHERE table_name = 'books' AND column_name = 'ingestion_attempts'"
        ).fetchone()
        applied = conn.execute("SELECT 1 FROM schema_migrations WHERE name = '003_ingestion_attempts.sql'").fetchone()
    assert applied and column["data_type"] == "integer" and column["is_nullable"] == "NO"
    assert column["column_default"] == "0"
    assert BookRepository().insert({"title": "Fresh"})["ingestion_attempts"] == 0


def test_claim_counts_attempts_and_runs_once():
    repo = BookRepository()
    book_id = _book(repo, "claimed", "queued", 0)
    claimed = repo.claim_queued(book_id)
    assert claimed["ingestion_status"] == "processing" and claimed["ingestion_attempts"] == 1
    assert repo.claim_queued(book_id) is None and repo.get(book_id)["ingestion_attempts"] == 1


def test_startup_recovery_resumes_below_the_cap_and_fails_at_it(settings, monkeypatch, hash_embedder):
    monkeypatch.setattr(settings, "INGESTION_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(settings, "INGESTION_MAX_QUEUED", 1)  # not a new submission: the cap must not refuse it
    repo = BookRepository()
    waiting = _book(repo, "waiting", "queued", 0)
    running = _book(repo, "running", "processing", 2)
    exhausted = _book(repo, "exhausted", "processing", 3)
    done = _book(repo, "done", "indexed", 1)

    ingestion = Ingestion(repository=repo, embedder=hash_embedder, run_inline=True,
                          parser=lambda path, ocr=False: (1, iter([dict(c) for c in CHUNKS])))
    assert ingestion.recover_interrupted() == (2, 1)

    for book_id, attempts in ((waiting, 1), (running, 3)):
        row = repo.get(book_id)
        assert row["ingestion_status"] == "indexed" and row["ingestion_attempts"] == attempts
        assert row["chunk_count"] == 1 and ingestion.vector_store.count(book_id) == 1
    failed = repo.get(exhausted)
    assert failed["ingestion_status"] == "failed" and failed["ingestion_error"] == INTERRUPTED_MESSAGE
    assert repo.get(done)["ingestion_status"] == "indexed" and repo.get(done)["ingestion_attempts"] == 1


def test_recovery_orders_the_interrupted_job_first():
    repo = BookRepository()
    first_queued = _book(repo, "first", "queued", 0)
    second_queued = _book(repo, "second", "queued", 0)
    running = _book(repo, "running", "processing", 1)
    requeued, failed = repo.recover_interrupted(max_attempts=3)
    assert requeued == [running, first_queued, second_queued] and failed == 0
    assert {repo.get(b)["ingestion_status"] for b in requeued} == {"queued"}


def test_reindex_resets_attempts(tmp_path):
    class RecordingIngestion:  # not a list subclass: an empty list is falsy and Book() would replace it
        def __init__(self):
            self.queued = []

        def enqueue(self, book_id):
            self.queued.append(book_id)

    repo, ingestion = BookRepository(), RecordingIngestion()
    pdf = tmp_path / "retry.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    book_id = _book(repo, "retry", "failed", 3)
    repo.update(book_id, {"file_path": str(pdf), "file_sha256": "f" * 64})

    result = Book(repository=repo, ingestion=ingestion).reindex(str(book_id))
    assert result["ingestion"]["status"] == "queued" and result["ingestion"]["attempts"] == 0
    assert repo.get(book_id)["ingestion_attempts"] == 0 and ingestion.queued == [book_id]
