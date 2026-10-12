"""
Book catalog + document upload business logic.

A book is either:
  - metadata only   ingestion_status = 'none'  (catalog entry; NOT searchable by RAG)
  - has a document  queued → processing → indexed | failed
Only 'indexed' books are used for question answering.
"""

from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional

from loguru import logger

from config.base import settings
from dto.book import BookDTO, FindBookDTO, UpdateBookDTO
from service.book_repository import BookRepository, DuplicateBookError, parse_book_id
from service.ingestion import Ingestion
from service.openlibrary import OpenLibraryClient
from service.vector_store import VectorStore
from util import storage
from util.http_errors import ConflictError, NotFoundError, TooManyRequestsError

_BUSY_MESSAGE = "The book is being indexed. Wait until indexing finishes, then delete it."
_HAS_DOCUMENT_MESSAGE = "This book already has a document. Delete the book or use reindex."
QUEUE_FULL_MESSAGE = "Indexing queue is full, try again later."
QUEUE_RETRY_AFTER_SECONDS = 60


class BookNotFoundError(NotFoundError):
    pass


class Book:
    def __init__(self, repository: Optional[BookRepository] = None, vector_store: Optional[VectorStore] = None,
                 ingestion: Optional[Ingestion] = None, openlibrary: Optional[OpenLibraryClient] = None):
        self.repository = repository or BookRepository()
        self.vector_store = vector_store or VectorStore()
        self.ingestion = ingestion or Ingestion(repository=self.repository, vector_store=self.vector_store)
        self._openlibrary = openlibrary

    @property
    def openlibrary(self) -> OpenLibraryClient:
        if self._openlibrary is None:
            self._openlibrary = OpenLibraryClient()
        return self._openlibrary

    # ── catalog ───────────────────────────────────────────────────────

    def add(self, dto: BookDTO) -> dict:
        return to_api(self.repository.insert({**_dto_to_columns(dto), "metadata_source": "manual"}))

    def update(self, dto: UpdateBookDTO) -> dict:
        self._get_row(dto.id)
        return to_api(self.repository.update(dto.id, _dto_to_columns(dto)))

    def get_by_id(self, book_id) -> dict:
        return to_api(self._get_row(book_id))

    def get_all(self, dto: FindBookDTO) -> tuple[list[dict], int]:
        rows, total = self.repository.list(
            search=dto.search, statuses=dto.status, page=dto.page, size=dto.size,
            order_by=dto.orderBy, order=dto.order,
        )
        return [to_api(row) for row in rows], total

    def delete(self, book_id) -> dict:
        """
        Row first, in one guarded statement (refused while the worker owns the book), then its
        vectors and file. Search only uses books in the catalog, so points left behind by a failed
        cleanup are never returned; the worker also drops points of a book deleted under it.
        """
        row = self.repository.delete_if_idle(parse_book_id(book_id))
        if row is None:
            self._get_row(book_id)  # 404 if it doesn't exist
            raise ConflictError(_BUSY_MESSAGE)
        self.vector_store.delete_book(row["id"])
        if row["file_path"]:
            storage.discard(row["file_path"])
        return {"id": str(row["id"]), "deleted": True}

    # ── Open Library import ───────────────────────────────────────────

    def lookup_external(self, query: str) -> list[dict]:
        return [_metadata_to_api(item) for item in self.openlibrary.search(query)]

    def import_by_isbn(self, isbn: str) -> dict:
        existing = self.repository.find_by("isbn", isbn)
        if existing:
            raise DuplicateBookError(f"'{existing['title']}' with ISBN {isbn} is already in the catalog (id {existing['id']}).")
        metadata = self.openlibrary.get_by_isbn(isbn)
        if metadata.get("external_id"):
            same_work = self.repository.find_by("external_id", metadata["external_id"])
            if same_work:
                raise DuplicateBookError(
                    f"'{same_work['title']}' is already in the catalog (id {same_work['id']}) from another edition."
                )
        return to_api(self.repository.insert(metadata))

    # ── documents ─────────────────────────────────────────────────────

    def _ensure_queue_room(self):
        """Refuse new indexing work while the backlog is at BE_INGESTION_MAX_QUEUED (soft: check, then insert)."""
        cap = settings.INGESTION_MAX_QUEUED
        if cap > 0 and self.repository.count_queued() >= cap:
            raise TooManyRequestsError(QUEUE_FULL_MESSAGE, retry_after=QUEUE_RETRY_AFTER_SECONDS)

    def upload_document(self, file: BinaryIO, filename: Optional[str], book_id: Optional[str] = None,
                        title: Optional[str] = None) -> dict:
        """
        Store a PDF and queue it for indexing.
        - book_id given: attach the PDF to that catalog entry (must not already have a document).
        - otherwise: create a new book (title from the form, else the filename).
        The same file (sha256) can only exist once in the library.
        """
        target = self._get_row(book_id) if book_id else None
        if target and target["file_sha256"]:
            raise ConflictError(_HAS_DOCUMENT_MESSAGE)
        self._ensure_queue_room()

        stored = storage.save_pdf_upload(file, max_bytes=settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024)
        try:
            duplicate = self.repository.find_by("file_sha256", stored.sha256)
            if duplicate:
                raise DuplicateBookError(
                    f"This file was already uploaded as '{duplicate['title']}' (id {duplicate['id']})."
                )
            file_fields = {
                "file_name": _safe_display_name(filename),
                "file_sha256": stored.sha256,
                "file_size_bytes": stored.size_bytes,
                "ingestion_status": "queued",
                "ingestion_error": None,
            }
            if target:
                # The file goes to <book_id>.pdf, so claim the book before moving it there: the loser
                # of two concurrent attaches must not overwrite the winner's file.
                row = self._attach(target["id"], file_fields)
                storage.finalize(stored, row["id"])
            else:
                row = self.repository.insert({
                    "title": (title or "").strip() or _title_from_filename(filename),
                    "metadata_source": "upload",
                    **file_fields,
                })
                final_path = storage.finalize(stored, row["id"])
                row = self.repository.update(row["id"], {"file_path": str(final_path)})
        except BaseException:
            storage.discard(stored.path)
            raise

        self.ingestion.enqueue(row["id"])
        logger.info("Queued book {id} for indexing ({size} bytes)", id=row["id"], size=stored.size_bytes)
        return to_api(row)

    def reindex(self, book_id) -> dict:
        row = self._get_row(book_id)
        if not row["file_path"] or not Path(row["file_path"]).exists():
            raise ConflictError("This book has no stored document to index. Upload a PDF first.")
        self._ensure_queue_room()
        claimed = self.repository.transition_status(
            row["id"], "queued", from_statuses=("indexed", "failed"), ingestion_error=None, ingestion_attempts=0
        )
        if not claimed:
            raise ConflictError(f"The book is already {row['ingestion_status']}.")
        self.ingestion.enqueue(row["id"])
        return to_api(claimed)

    def _attach(self, book_id, file_fields: dict) -> dict:
        """Hash + path + queued status in one guarded write (only if the book has no document yet)."""
        row = self.repository.attach_document(
            book_id, {**file_fields, "file_path": str(storage.book_file_path(book_id))}
        )
        if row is None:
            self._get_row(book_id)  # 404 if it was deleted meanwhile
            raise ConflictError(_HAS_DOCUMENT_MESSAGE)
        return row

    def _get_row(self, book_id) -> dict:
        row = self.repository.get(parse_book_id(book_id))
        if not row:
            raise BookNotFoundError(f"Book {book_id} not found.")
        return row


# ── mapping helpers ───────────────────────────────────────────────────

def _dto_to_columns(dto: BookDTO) -> dict:
    return {
        "title": dto.title,
        "authors": dto.authors,
        "description": dto.description,
        "isbn": dto.isbn,
        "cover_url": dto.coverUrl,
        "publisher": dto.publisher,
        "published_year": dto.publishedYear,
        "language": dto.language,
        "subjects": dto.subjects,
    }


def _iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def to_api(row: dict) -> dict:
    """Database row -> API shape (camelCase). Never exposes the server file path or hash."""
    status = row["ingestion_status"]
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "authors": row["authors"] or [],
        "description": row["description"],
        "isbn": row["isbn"],
        "coverUrl": row["cover_url"],
        "publisher": row["publisher"],
        "publishedYear": row["published_year"],
        "language": row["language"],
        "subjects": row["subjects"] or [],
        "metadataSource": row["metadata_source"],
        "hasDocument": bool(row["file_sha256"]),
        "document": {
            "fileName": row["file_name"],
            "sizeBytes": row["file_size_bytes"],
            "pageCount": row["page_count"],
        } if row["file_sha256"] else None,
        "ingestion": {
            "status": status,
            "error": row["ingestion_error"],
            # Worker claims since the last upload/reindex (startup recovery resumes below the cap).
            "attempts": row["ingestion_attempts"],
            "chunkCount": row["chunk_count"],
            "embeddingModel": row["embedding_model"],
            "indexedAt": _iso(row["indexed_at"]),
        },
        # The one flag the UI and chat rely on: only indexed books can answer questions.
        "searchable": status == "indexed",
        "createdAt": _iso(row["created_at"]),
        "updatedAt": _iso(row["updated_at"]),
    }


def _metadata_to_api(item: dict) -> dict:
    return {
        "title": item["title"],
        "authors": item["authors"],
        "isbn": item["isbn"],
        "coverUrl": item["cover_url"],
        "publishedYear": item["published_year"],
        "externalId": item["external_id"],
    }


def _safe_display_name(filename: Optional[str]) -> str:
    name = Path((filename or "document.pdf").replace("\\", "/")).name
    return name[:255] or "document.pdf"


def _title_from_filename(filename: Optional[str]) -> str:
    stem = Path(_safe_display_name(filename)).stem.replace("_", " ").replace("-", " ").strip()
    return stem[:500] or "Untitled document"
