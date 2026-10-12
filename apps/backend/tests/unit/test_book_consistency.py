"""
Book delete / PDF attach under concurrency, with an in-memory repository that models the
guarded SQL statements of BookRepository (delete_if_idle, attach_document).

Each race is replayed deterministically: a "stale" read stands for a request that looked at
the row before a concurrent request changed it.
"""

import hashlib
import io
import uuid

import pytest

from service.book import Book, BookNotFoundError
from util.http_errors import ConflictError

PDF_A = b"%PDF-1.4\nfirst upload\n"
PDF_B = b"%PDF-1.4\nsecond upload, a different file\n"


def _row(status="indexed", sha=None, file_path=None, title="Saltmere"):
    row = {column: None for column in (
        "authors", "description", "isbn", "cover_url", "publisher", "published_year", "language", "subjects",
        "metadata_source", "file_name", "file_size_bytes", "page_count", "chunk_count", "embedding_model",
        "indexed_at", "created_at", "updated_at",
    )}
    return {**row, "id": uuid.uuid4(), "title": title, "ingestion_status": status, "file_sha256": sha,
            "file_path": file_path, "ingestion_error": None}


class FakeBooks:
    """In-memory books table. `stale[id]` queues snapshots that get() returns (one per read) before the
    real row: each stands for a request that read the row before a concurrent write."""

    def __init__(self, *rows):
        self.rows = {str(r["id"]): r for r in rows}
        self.stale: dict[str, list[dict]] = {}
        self.attach_calls: list[dict] = []

    def get(self, book_id):
        key = str(book_id)
        row = self.stale[key].pop(0) if self.stale.get(key) else self.rows.get(key)
        return dict(row) if row else None

    def find_by(self, column, value):
        return next((dict(r) for r in self.rows.values() if r.get(column) == value), None)

    def delete_if_idle(self, book_id):
        row = self.rows.get(str(book_id))
        if row is None or row["ingestion_status"] in ("queued", "processing"):
            return None
        return self.rows.pop(str(book_id))

    def count_queued(self):
        return sum(1 for row in self.rows.values() if row.get("ingestion_status") == "queued")

    def attach_document(self, book_id, fields):
        self.attach_calls.append(dict(fields))
        row = self.rows.get(str(book_id))
        if row is None or row["file_sha256"] is not None:
            return None
        row.update(fields)
        return dict(row)


class FakeVectors:
    def __init__(self):
        self.deleted: list[str] = []

    def delete_book(self, book_id):
        self.deleted.append(str(book_id))


class FakeIngestion:
    def __init__(self):
        self.queued: list[str] = []

    def enqueue(self, book_id):
        self.queued.append(str(book_id))


@pytest.fixture(autouse=True)
def storage_dir(tmp_path, settings, monkeypatch):
    monkeypatch.setattr(settings, "BOOK_STORAGE_DIR", str(tmp_path))
    return tmp_path


def _service(*rows):
    repo = FakeBooks(*rows)
    return Book(repository=repo, vector_store=FakeVectors(), ingestion=FakeIngestion()), repo


# ── delete ────────────────────────────────────────────────────────────

def test_delete_removes_row_then_vectors_and_file(storage_dir):
    pdf = storage_dir / "book.pdf"
    pdf.write_bytes(PDF_A)
    row = _row(sha="abc", file_path=str(pdf))
    service, repo = _service(row)

    assert service.delete(str(row["id"])) == {"id": str(row["id"]), "deleted": True}
    assert repo.rows == {} and service.vector_store.deleted == [str(row["id"])] and not pdf.exists()


@pytest.mark.parametrize("status", ["queued", "processing"])
def test_delete_while_indexing_is_409_and_touches_nothing(storage_dir, status):
    pdf = storage_dir / "book.pdf"
    pdf.write_bytes(PDF_A)
    row = _row(status=status, sha="abc", file_path=str(pdf))
    service, repo = _service(row)

    with pytest.raises(ConflictError, match="The book is being indexed. Wait until indexing finishes, then delete it."):
        service.delete(str(row["id"]))
    assert str(row["id"]) in repo.rows and service.vector_store.deleted == [] and pdf.exists()


def test_delete_racing_a_reindex_claim_is_409(storage_dir):
    # The user saw 'indexed', but a reindex claimed the book ('queued') before the delete ran.
    # The old check-then-delete passed the check and deleted the row under the worker.
    row = _row(status="queued", sha="abc", file_path=str(storage_dir / "book.pdf"))
    service, repo = _service(row)
    repo.stale[str(row["id"])] = [{**row, "ingestion_status": "indexed"}]

    with pytest.raises(ConflictError):
        service.delete(str(row["id"]))
    assert str(row["id"]) in repo.rows and service.vector_store.deleted == []


def test_delete_missing_book_is_404():
    service, _ = _service()
    with pytest.raises(BookNotFoundError):
        service.delete(str(uuid.uuid4()))
    assert service.vector_store.deleted == []


# ── attach a PDF to an existing catalog entry ─────────────────────────

def test_attach_sets_hash_path_and_queued_status_in_one_guarded_write(storage_dir):
    row = _row(status="none")
    service, repo = _service(row)

    result = service.upload_document(io.BytesIO(PDF_A), "saltmere.pdf", book_id=str(row["id"]))

    final = storage_dir / f"{row['id']}.pdf"
    assert repo.attach_calls == [{
        "file_name": "saltmere.pdf", "file_sha256": hashlib.sha256(PDF_A).hexdigest(),
        "file_size_bytes": len(PDF_A), "ingestion_status": "queued", "ingestion_error": None,
        "file_path": str(final),
    }]
    assert final.read_bytes() == PDF_A and result["hasDocument"] is True
    assert service.ingestion.queued == [str(row["id"])]


def test_concurrent_attach_loser_gets_409_and_its_file_is_removed(storage_dir):
    row = _row(status="none")
    service, repo = _service(row)
    book_id = str(row["id"])
    repo.stale[book_id] = [dict(row), dict(row)]  # both requests read the row before either attached a PDF

    service.upload_document(io.BytesIO(PDF_A), "a.pdf", book_id=book_id)
    with pytest.raises(ConflictError, match="This book already has a document. Delete the book or use reindex."):
        service.upload_document(io.BytesIO(PDF_B), "b.pdf", book_id=book_id)

    assert repo.rows[book_id]["file_sha256"] == hashlib.sha256(PDF_A).hexdigest()
    assert sorted(p.name for p in storage_dir.iterdir()) == [f"{book_id}.pdf"]  # no leftover temp upload
    assert (storage_dir / f"{book_id}.pdf").read_bytes() == PDF_A              # winner's file untouched
    assert service.ingestion.queued == [book_id]


def test_attach_to_a_book_deleted_meanwhile_is_404_and_leaves_no_file(storage_dir):
    row = _row(status="none")
    service, repo = _service(row)
    book_id = str(row["id"])
    repo.stale[book_id] = [dict(row)]
    del repo.rows[book_id]  # deleted after the request looked it up

    with pytest.raises(BookNotFoundError):
        service.upload_document(io.BytesIO(PDF_A), "a.pdf", book_id=book_id)
    assert list(storage_dir.iterdir()) == [] and service.ingestion.queued == []
