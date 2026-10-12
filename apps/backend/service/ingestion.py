"""
Background indexing of uploaded PDFs.

    queued ──claim──► processing ──► indexed
                          └─────────► failed   (retry with POST /book/reindex)

Jobs run on daemon worker threads inside the API process (no queue infrastructure
needed for the MVP). Daemon threads never block shutdown or a dev auto-reload. Each claim
counts an attempt (ingestion_attempts); at the next startup a job cut off that way is
re-queued while it has fewer than INGESTION_MAX_ATTEMPTS attempts, else marked failed
(retry with reindex, which resets the count). This assumes one API process owns the queue.

Scanned PDFs: a parse with OCR off that yields no text is retried once with OCR on
(DOCLING_OCR_FALLBACK), if Docling has a usable OCR engine (probed once per process).

Retry safety:
- the status claim is an atomic UPDATE ... WHERE status = 'queued', so a job runs once;
- chunk point ids are deterministic, so re-indexing overwrites instead of duplicating;
- leftover points from a previous, longer run are deleted at the end;
- if the book row was deleted while the job ran, the job deletes the points it wrote.
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

# (pdf_path, ocr=False) -> (page_count, iterable of chunk dicts {text, embed_text, headings, page_start, page_end})
Parser = Callable[..., tuple[Optional[int], Iterable[dict]]]

NO_TEXT_MESSAGE = "No text could be extracted. The PDF may be scanned images (OCR is disabled) or empty."
NO_TEXT_WITH_OCR_MESSAGE = "No text could be extracted, even with OCR. The PDF may be empty or unreadable."
NO_OCR_ENGINE_WARNING = "OCR fallback enabled but no OCR engine is available; skipping"


class _NoOcrWarning:
    """The missing-engine warning is logged once per process, not once per scanned book."""

    logged = False
    _lock = threading.Lock()

    @classmethod
    def log_once(cls):
        with cls._lock:
            if cls.logged:
                return
            cls.logged = True
        logger.warning(NO_OCR_ENGINE_WARNING)


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
                 embedder=None, parser: Optional[Parser] = None, run_inline: bool = False,
                 ocr_available: Optional[Callable[[], bool]] = None):
        self.repository = repository or BookRepository()
        self.vector_store = vector_store or VectorStore()
        self._embedder = embedder
        self._parser = parser
        self._ocr_available = ocr_available
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

    @property
    def ocr_available(self) -> Callable[[], bool]:
        if self._ocr_available is None:
            from util.document_parser import ocr_available

            self._ocr_available = ocr_available
        return self._ocr_available

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
        book = self.repository.claim_queued(book_id)
        if not book:
            logger.info("Book {id} is no longer queued; skipping", id=book_id)
            return
        started = datetime.now(timezone.utc)
        try:
            page_count, chunk_count = self._index(book)
        except Exception as error:
            message = str(error) if isinstance(error, UserFacingError) else "Indexing failed. See server logs."
            logger.exception("Indexing failed for book {id}", id=book_id)
            if self._drop_points_if_book_deleted(book_id):
                return
            self._finish(book_id, "failed", ingestion_error=message[:1000])
            return

        if self._drop_points_if_book_deleted(book_id):
            return
        if self._finish(
            book_id, "indexed",
            ingestion_error=None, chunk_count=chunk_count, page_count=page_count,
            embedding_model=self.embedder.model, indexed_at=datetime.now(timezone.utc),
        ):
            logger.info("Indexed book {id}: {n} chunks in {s:.1f}s", id=book_id, n=chunk_count,
                        s=(datetime.now(timezone.utc) - started).total_seconds())

    def _finish(self, book_id, status: str, **fields) -> bool:
        """Record the job's outcome (`processing` -> `status`). Warns, never raises, if the row moved on."""
        if self.repository.transition_status(book_id, status, from_statuses=("processing",), **fields):
            return True
        logger.warning("Could not mark book {id} {status}: it was deleted or its status changed meanwhile",
                       id=book_id, status=status)
        return False

    def _drop_points_if_book_deleted(self, book_id) -> bool:
        """
        After upserting: if the book row is gone (deleted while this job ran), delete the points
        this job wrote so no orphan vectors stay in Qdrant. Returns True if the book was gone.
        """
        if self.repository.get(book_id) is not None:
            return False
        self.vector_store.delete_book(book_id)
        logger.info("Book {id} was deleted during indexing; removed its vectors", id=book_id)
        return True

    def _index(self, book: dict) -> tuple[Optional[int], int]:
        if not book["file_path"]:
            raise UserFacingError("The book has no stored document.")
        self.vector_store.ensure_collection()

        page_count, total = self._parse_and_store(book, self.parser(book["file_path"]))
        ocr_ran = False  # did a parse that found no text really run OCR? (picks the failure message)
        if total:
            logger.info("Book {id}: parsed {how}", id=book["id"],
                        how="with OCR" if settings.DOCLING_DO_OCR else "without OCR")
        elif settings.DOCLING_DO_OCR:
            ocr_ran = self.ocr_available()  # every parse already uses OCR, if an engine exists: no fallback
        elif settings.DOCLING_OCR_FALLBACK:
            if self.ocr_available():
                logger.info("Book {id}: no text without OCR, retrying with OCR", id=book["id"])
                ocr_ran = True
                page_count, total = self._parse_and_store(book, self.parser(book["file_path"], ocr=True))
                if total:
                    logger.info("Book {id}: parsed with OCR", id=book["id"])
                else:
                    logger.warning("Book {id}: OCR also found no text", id=book["id"])
            else:
                _NoOcrWarning.log_once()
                logger.info("Book {id}: no text without OCR; no OCR engine, not retrying", id=book["id"])

        if total == 0:
            raise UserFacingError(NO_TEXT_WITH_OCR_MESSAGE if ocr_ran else NO_TEXT_MESSAGE)
        self.vector_store.delete_stale_chunks(book["id"], keep_below=total)
        return page_count, total

    def _parse_and_store(self, book: dict, parsed: tuple[Optional[int], Iterable[dict]]) -> tuple[Optional[int], int]:
        """Embed + store a parser result's non-empty chunks. Returns (page_count, number of chunks stored)."""
        page_count, chunks = parsed
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

    def recover_interrupted(self) -> tuple[int, int]:
        """
        Startup: resume jobs a previous process left queued/processing (re-queued and handed to the
        worker while below INGESTION_MAX_ATTEMPTS, else failed). Not a new submission, so the
        INGESTION_MAX_QUEUED cap does not apply. Returns (requeued, failed).
        """
        requeued, failed = self.repository.recover_interrupted(settings.INGESTION_MAX_ATTEMPTS)
        for book_id in requeued:
            self.enqueue(book_id)
        if requeued or failed:
            logger.warning("Interrupted ingestion jobs: {requeued} re-queued, {failed} marked failed "
                           "(at {max} attempts)", requeued=len(requeued), failed=failed,
                           max=settings.INGESTION_MAX_ATTEMPTS)
        return len(requeued), failed
