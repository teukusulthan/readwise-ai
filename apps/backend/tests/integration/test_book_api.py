"""
API-level tests against real PostgreSQL + Qdrant. PDF parsing and embeddings are
replaced with fast fakes here; tests/integration/test_full_pipeline.py uses the real ones.
"""

from pathlib import Path

import pytest

import router.book as book_router
import router.chat as chat_router
import router.search as search_router
from service.book_repository import BookRepository

pytestmark = pytest.mark.integration

SAMPLE = Path(__file__).resolve().parent.parent / "fixtures" / "sample_book.pdf"

FAKE_CHUNKS = [
    {"text": "Saltmere Light was built in 1847 by the engineer Agnes Morrow.", "headings": ["Chapter 1"],
     "page_start": 1, "page_end": 1},
    {"text": "The keeper climbed the 142 steps of the tower at sunset.", "headings": ["Chapter 2"],
     "page_start": 2, "page_end": 2},
]


@pytest.fixture(autouse=True)
def fast_pipeline(monkeypatch, hash_embedder):
    """Inline ingestion with a fake parser + deterministic embedder; same embedder for search."""
    ingestion = book_router.obj.ingestion
    monkeypatch.setattr(ingestion, "run_inline", True)
    monkeypatch.setattr(ingestion, "_parser", lambda path: (3, iter([dict(c) for c in FAKE_CHUNKS])))
    monkeypatch.setattr(ingestion, "_embedder", hash_embedder)
    monkeypatch.setattr(search_router.obj, "_embedder", hash_embedder)
    monkeypatch.setattr(chat_router.obj.search, "_embedder", hash_embedder)
    monkeypatch.setattr(chat_router.obj, "_generator", None)


async def _upload(client, title="The Keeper of Saltmere Light", content=None, **form):
    files = {"file": ("saltmere.pdf", content if content is not None else SAMPLE.read_bytes(), "application/pdf")}
    return await client.post("/book/upload", files=files, data={"title": title, **form})


async def test_catalog_crud_and_search(client):
    created = (await client.post("/book/add", json={"title": "Dune", "authors": ["Frank Herbert"],
                                                    "isbn": "978-0-441-01359-3"})).json()["data"]
    assert created["isbn"] == "9780441013593"
    assert created["searchable"] is False and created["ingestion"]["status"] == "none"

    found = (await client.post("/book/get-all", json={"search": "herbert"})).json()
    assert [b["title"] for b in found["data"]] == ["Dune"] and found["metaData"]["pagination"]["totalElements"] == 1

    metadata_only = (await client.post("/book/get-all", json={"status": ["none"]})).json()["data"]
    assert len(metadata_only) == 1

    duplicate = await client.post("/book/add", json={"title": "Dune again", "isbn": "9780441013593"})
    assert duplicate.status_code == 409

    assert (await client.get("/book/get-one", params={"id": "not-a-uuid"})).status_code == 400
    missing = await client.get("/book/get-one", params={"id": "00000000-0000-0000-0000-000000000000"})
    assert missing.status_code == 404
    assert "detail" not in missing.json() and missing.json()["metaData"]["responseCode"] == 404


async def test_upload_index_search_ask_delete(client):
    response = await _upload(client)
    assert response.status_code == 200, response.text
    book = response.json()["data"]
    book_id = book["id"]

    book = (await client.get("/book/get-one", params={"id": book_id})).json()["data"]
    assert book["ingestion"]["status"] == "indexed" and book["searchable"] is True
    assert book["ingestion"]["chunkCount"] == 2 and book["document"]["pageCount"] == 3
    assert "filePath" not in book and "file_path" not in book

    # Same file again → no duplicate book.
    again = await _upload(client, title="Copy")
    assert again.status_code == 409 and "already uploaded" in again.json()["metaData"]["message"]

    results = (await client.post("/search/query", json={"query": "who built Saltmere Light in 1847"})).json()["data"]
    assert results["results"][0]["pageStart"] == 1 and "Agnes Morrow" in results["results"][0]["text"]

    answer = (await client.post("/chat/ask", json={"question": "Who built Saltmere Light?"})).json()["data"]
    assert answer["mode"] == "retrieval_only" and answer["grounded"] is False and answer["sources"]

    # Reindex is idempotent: same chunk count, no duplicate vectors.
    reindexed = (await client.post("/book/reindex", params={"id": book_id})).json()["data"]
    assert reindexed["ingestion"]["status"] in ("queued", "indexed")
    assert book_router.obj.vector_store.count(book_id) == 2

    deleted = await client.delete("/book/delete", params={"id": book_id})
    assert deleted.status_code == 200
    assert book_router.obj.vector_store.count(book_id) == 0
    assert (await client.get("/book/get-one", params={"id": book_id})).status_code == 404


async def test_metadata_only_book_is_never_searched(client):
    book = (await client.post("/book/add", json={"title": "Moby-Dick"})).json()["data"]
    answer = (await client.post("/chat/ask", json={"question": "What is the whale called?",
                                                   "bookIds": [book["id"]]})).json()["data"]
    assert answer["mode"] == "no_indexed_books" and answer["sources"] == []
    assert answer["skippedBooks"][0]["reason"] == "not_indexed:none"


async def test_upload_attaches_pdf_to_existing_catalog_entry(client):
    book = (await client.post("/book/add", json={"title": "Saltmere (catalog entry)"})).json()["data"]
    attached = (await _upload(client, bookId=book["id"])).json()["data"]
    assert attached["id"] == book["id"] and attached["hasDocument"] is True
    second = await _upload(client, content=b"%PDF-1.4 different", bookId=book["id"])
    assert second.status_code == 409


@pytest.mark.parametrize("content, filename", [(b"not a pdf", "notes.pdf"), (b"%PDF-1.4", "notes.txt")])
async def test_upload_rejects_non_pdf(client, content, filename):
    response = await client.post("/book/upload", files={"file": (filename, content, "application/pdf")})
    assert response.status_code == 400
    rows, total = BookRepository().list()
    assert total == 0


async def test_import_from_open_library(client, monkeypatch):
    class FakeOpenLibrary:
        def get_by_isbn(self, isbn):
            return {"title": "Dune", "authors": ["Frank Herbert"], "isbn": isbn, "description": "Desert planet.",
                    "cover_url": None, "publisher": None, "published_year": 1965, "language": "eng",
                    "subjects": [], "metadata_source": "openlibrary", "external_id": "/works/OL893415W"}

    monkeypatch.setattr(book_router.obj, "_openlibrary", FakeOpenLibrary())
    imported = (await client.post("/book/import", json={"isbn": "9780441013593"})).json()["data"]
    assert imported["metadataSource"] == "openlibrary" and imported["searchable"] is False
    assert (await client.post("/book/import", json={"isbn": "9780441013593"})).status_code == 409


# ── edits, deletes and attaches stay consistent with the index ────────

async def test_renamed_book_is_cited_under_its_new_title(client):
    book = (await _upload(client)).json()["data"]
    renamed = await client.put("/book/update", json={"id": book["id"], "title": "Saltmere, Revised"})
    assert renamed.status_code == 200
    # The points still carry the old title in their payload; results use the catalog title.
    results = (await client.post("/search/query", json={"query": "who built Saltmere Light in 1847"})).json()["data"]
    assert results["results"] and {r["bookTitle"] for r in results["results"]} == {"Saltmere, Revised"}


async def test_delete_is_refused_while_indexing_and_404_when_missing(client):
    book = (await _upload(client)).json()["data"]
    repo = BookRepository()
    assert repo.transition_status(book["id"], "processing", from_statuses=("indexed",))

    busy = await client.delete("/book/delete", params={"id": book["id"]})
    assert busy.status_code == 409
    assert busy.json()["metaData"]["message"] == "The book is being indexed. Wait until indexing finishes, then delete it."
    assert repo.get(book["id"]) and book_router.obj.vector_store.count(book["id"]) == 2

    missing = await client.delete("/book/delete", params={"id": "00000000-0000-0000-0000-000000000000"})
    assert missing.status_code == 404


def test_delete_if_idle_guard():
    repo = BookRepository()
    for status in ("queued", "processing"):
        row = repo.insert({"title": f"Busy {status}", "ingestion_status": status})
        assert repo.delete_if_idle(row["id"]) is None and repo.get(row["id"])
    idle = repo.insert({"title": "Idle"})
    assert repo.delete_if_idle(idle["id"])["id"] == idle["id"] and repo.get(idle["id"]) is None
    assert repo.delete_if_idle(idle["id"]) is None


def test_attach_document_guard():
    repo = BookRepository()
    book = repo.insert({"title": "Catalog entry"})
    fields = {"file_name": "a.pdf", "file_sha256": "a" * 64, "file_size_bytes": 10, "file_path": "/books/x.pdf",
              "ingestion_status": "queued", "ingestion_error": None}
    attached = repo.attach_document(book["id"], fields)
    assert attached["file_sha256"] == "a" * 64 and attached["ingestion_status"] == "queued"
    assert attached["file_path"] == "/books/x.pdf"
    # A second attach (the loser of a race) changes nothing.
    assert repo.attach_document(book["id"], {**fields, "file_sha256": "b" * 64}) is None
    assert repo.get(book["id"])["file_sha256"] == "a" * 64


async def test_worker_removes_points_of_a_book_deleted_while_indexing(client, monkeypatch):
    from service import Services

    def parse_then_delete(path):
        def chunks():
            yield from (dict(c) for c in FAKE_CHUNKS)
            with Services.postgres().connection() as conn:   # the row disappears mid-job
                conn.execute("DELETE FROM books WHERE file_path = %s", (path,))
        return 3, chunks()

    monkeypatch.setattr(book_router.obj.ingestion, "_parser", parse_then_delete)
    response = await _upload(client)
    assert response.status_code == 200, response.text
    book_id = response.json()["data"]["id"]
    assert BookRepository().get(book_id) is None
    assert book_router.obj.vector_store.count(book_id) == 0


async def test_file_streams_the_stored_pdf_inline_and_404s_when_missing(client):
    content = SAMPLE.read_bytes()
    book = (await _upload(client, title="Saltmere", content=content)).json()["data"]

    response = await client.get("/book/file", params={"id": book["id"]})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == 'inline; filename="saltmere.pdf"'
    assert response.content == content

    no_document = (await client.post("/book/add", json={"title": "Dune"})).json()["data"]
    assert (await client.get("/book/file", params={"id": no_document["id"]})).status_code == 404
    assert (await client.get("/book/file", params={"id": "00000000-0000-0000-0000-000000000000"})).status_code == 404
    assert (await client.get("/book/file", params={"id": "../../etc/passwd"})).status_code == 400

    Path(BookRepository().get(book["id"])["file_path"]).unlink()
    assert (await client.get("/book/file", params={"id": book["id"]})).status_code == 404
