"""
Background indexing of uploaded PDFs.

    queued ──claim──► processing ──► indexed
                          └─────────► failed   (retry with POST /book/reindex)

Jobs run on daemon worker threads inside the API process (no queue infrastructure
needed for the MVP). Daemon threads never block shutdown or a dev auto-reload: a job
cut off that way is marked failed at the next startup and can be retried with reindex.

Retry safety:
- the status claim is an atomic UPDATE ... WHERE status = 'queued', so a job runs once;
- chunk point ids are deterministic, so re-indexing overwrites instead of duplicating;
- leftover points from a previous, longer run are deleted at the end.
"""

import queue
import threading
from datetime import datetime, timezone
from typing import Callable, Iterable, Optional

from loguru import logger

from config.base import settings
from service import Services
from service.book_repository import BookRepository
from service.vector_store import VectorStore

# (pdf_path) -> (page_count, iterable of chunk dicts {text, embed_text, headings, page_start, page_end})
Parser = Callable[[str], tuple[Optional[int], Iterable[dict]]]


class UserFacingError(Exception):
    """An ingestion failure whose message is safe and useful to show to the user."""


class _Workers:
    """Process-wide job queue drained by INGESTION_WORKERS daemon threads."""

    _queue: Optional[queue.Queue] = None
    _lock = threading.Lock()

    @classmethod
    def submit(cls, job: Callable[[], None]):
        with cls._lock:
            if cls._queue is None:
                cls._queue = queue.Queue()
                for i in range(max(1, settings.INGESTION_WORKERS)):
                    threading.Thread(target=cls._drain, name=f"ingest-{i}", daemon=True).start()
        cls._queue.put(job)

    @classmethod
    def _drain(cls):
        while True:
            job = cls._queue.get()
            try:
                job()
            finally:
                cls._queue.task_done()


class Ingestion:
    def __init__(self, repository: Optional[BookRepository] = None, vector_store: Optional[VectorStore] = None,
                 embedder=None, parser: Optional[Parser] = None, run_inline: bool = False):
        self.repository = repository or BookRepository()
        self.vector_store = vector_store or VectorStore()
        self._embedder = embedder
        self._parser = parser
        self.run_inline = run_inline  # tests: run synchronously instead of in the thread pool

    @property
    def embedder(self):
        return self._embedder or Services.embedding()

    @property
    def parser(self) -> Parser:
        if self._parser is None:
            # Imported lazily: Docling pulls in PyTorch and takes seconds to import.
            from util.document_parser import parse_pdf

            self._parser = parse_pdf
        return self._parser

    def enqueue(self, book_id):
        if self.run_inline:
            self.run(book_id)
        else:
            _Workers.submit(lambda: self._run_safely(book_id))

    def _run_safely(self, book_id):
        try:
            self.run(book_id)
        except Exception:
            logger.exception("Ingestion crashed for book {id}", id=book_id)

    def run(self, book_id):
        book = self.repository.transition_status(book_id, "processing", from_statuses=("queued",))
        if not book:
            logger.info("Book {id} is no longer queued; skipping", id=book_id)
            return
        started = datetime.now(timezone.utc)
        try:
            page_count, chunk_count = self._index(book)
        except Exception as error:
            message = str(error) if isinstance(error, UserFacingError) else "Indexing failed. See server logs."
            logger.exception("Indexing failed for book {id}", id=book_id)
            self.repository.transition_status(book_id, "failed", from_statuses=("processing",),
                                              ingestion_error=message[:1000])
            return

        self.repository.transition_status(
            book_id, "indexed", from_statuses=("processing",),
            ingestion_error=None, chunk_count=chunk_count, page_count=page_count,
            embedding_model=self.embedder.model, indexed_at=datetime.now(timezone.utc),
        )
        logger.info("Indexed book {id}: {n} chunks in {s:.1f}s", id=book_id, n=chunk_count,
                    s=(datetime.now(timezone.utc) - started).total_seconds())

    def _index(self, book: dict) -> tuple[Optional[int], int]:
        if not book["file_path"]:
            raise UserFacingError("The book has no stored document.")
        self.vector_store.ensure_collection()

        page_count, chunks = self.parser(book["file_path"])
        if page_count and page_count > settings.MAX_PDF_PAGES:
            raise UserFacingError(f"The document has {page_count} pages; the limit is {settings.MAX_PDF_PAGES}.")

        # Stream: embed + store one batch at a time instead of holding every vector in memory.
        batch_size = settings.ENGINE_EMBEDDING_BATCH_SIZE
        batch, total = [], 0
        for chunk in chunks:
            if not chunk["text"].strip():
                continue
            batch.append({**chunk, "chunk_index": total})
            total += 1
            if len(batch) == batch_size:
                self._store(book, batch)
                batch = []
        if batch:
            self._store(book, batch)

        if total == 0:
            raise UserFacingError(
                "No text could be extracted. The PDF may be scanned images (OCR is disabled) or empty."
            )
        self.vector_store.delete_stale_chunks(book["id"], keep_below=total)
        return page_count, total

    def _store(self, book: dict, batch: list[dict]):
        # Embed the contextualized text (headings + chunk); store the plain chunk text for display.
        vectors = self.embedder.embed_documents([c.get("embed_text") or c["text"] for c in batch])
        payload_chunks = [
            {
                "chunk_index": c["chunk_index"],
                "text": c["text"],
                "headings": c.get("headings") or [],
                "page_start": c.get("page_start"),
                "page_end": c.get("page_end"),
            }
            for c in batch
        ]
        self.vector_store.upsert_chunks(book["id"], book["title"], payload_chunks, vectors, self.embedder.model)

    def recover_interrupted(self) -> int:
        count = self.repository.fail_interrupted()
        if count:
            logger.warning("Marked {n} interrupted ingestion job(s) as failed", n=count)
        return count
