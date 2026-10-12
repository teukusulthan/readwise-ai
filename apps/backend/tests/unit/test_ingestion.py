import uuid

import pytest
from qdrant_client import QdrantClient

import service.ingestion as ingestion_module
from service.ingestion import NO_OCR_ENGINE_WARNING, NO_TEXT_MESSAGE, NO_TEXT_WITH_OCR_MESSAGE, Ingestion
from service.book_repository import INTERRUPTED_MESSAGE
from service.vector_store import VectorStore
from util.parse_process import (
    PARSE_TIMEOUT_MESSAGE,
    PARSER_CRASHED_MESSAGE,
    PARSER_OUT_OF_MEMORY_MESSAGE,
    ParserCrashed,
    ParserOutOfMemory,
    ParserStopped,
    ParseTimedOut,
)

DIM = 4


class FakeRepository:
    """In-memory stand-in for BookRepository's status methods."""

    def __init__(self, book):
        self.book = book
        self.history = [book["ingestion_status"]]
        self.deleted = False  # the row was deleted (DELETE /book/delete) while the job ran

    def get(self, book_id):
        return None if self.deleted else dict(self.book)

    def claim_queued(self, book_id):
        if self.deleted or self.book["ingestion_status"] != "queued":
            return None
        self.book.update(ingestion_status="processing", ingestion_attempts=self.book["ingestion_attempts"] + 1)
        self.history.append("processing")
        return dict(self.book)

    def transition_status(self, book_id, to_status, from_statuses, **fields):
        if self.deleted or self.book["ingestion_status"] not in from_statuses:
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


def _book(status="queued", attempts=0):
    return {"id": uuid.uuid4(), "title": "Sample", "file_path": "/tmp/sample.pdf", "ingestion_status": status,
            "ingestion_error": None, "ingestion_attempts": attempts}


def _parser(chunks, pages=3):
    return lambda path, ocr=False: (pages, iter(chunks))


def _chunks(n):
    return [{"text": f"text {i}", "embed_text": f"Heading\ntext {i}", "headings": ["Heading"],
             "page_start": 1, "page_end": 1} for i in range(n)]


@pytest.fixture
def caplog_loguru():
    """Messages loguru logs during the test."""
    from loguru import logger

    messages = []
    handler = logger.add(lambda message: messages.append(message.record["message"]), level="DEBUG")
    yield messages
    logger.remove(handler)


@pytest.fixture
def store():
    return VectorStore(client=QdrantClient(":memory:"), collection="ingest_test", dimensions=DIM)


def _ingestion(book, store, parser, embedder=None, ocr_available=True):
    return Ingestion(repository=FakeRepository(book), vector_store=store, embedder=embedder or FakeEmbedder(),
                     parser=parser, run_inline=True, ocr_available=lambda: ocr_available)


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


def test_no_text_fails_with_helpful_message(store, settings, monkeypatch):
    monkeypatch.setattr(settings, "DOCLING_OCR_FALLBACK", False)
    book = _book()
    _ingestion(book, store, _parser([{"text": "  "}])).enqueue(book["id"])
    assert book["ingestion_status"] == "failed"
    assert book["ingestion_error"] == NO_TEXT_MESSAGE


def test_unexpected_error_fails_without_leaking_details(store):
    def broken_parser(path):
        raise RuntimeError("/secret/internal/path exploded")

    book = _book()
    _ingestion(book, store, broken_parser).enqueue(book["id"])
    assert book["ingestion_status"] == "failed"
    assert "secret" not in book["ingestion_error"]


@pytest.mark.parametrize("error, message", [
    (ParseTimedOut(PARSE_TIMEOUT_MESSAGE), PARSE_TIMEOUT_MESSAGE),
    (ParserCrashed(PARSER_CRASHED_MESSAGE), PARSER_CRASHED_MESSAGE),
    (ParserOutOfMemory(PARSER_OUT_OF_MEMORY_MESSAGE), PARSER_OUT_OF_MEMORY_MESSAGE),
])
def test_a_failed_parse_child_fails_the_book_with_its_safe_message(store, error, message):
    def failing_parser(path, ocr=False):
        raise error

    book = _book()
    _ingestion(book, store, failing_parser).enqueue(book["id"])
    assert book["ingestion_status"] == "failed" and book["ingestion_error"] == message


def test_a_parse_stopped_by_shutdown_leaves_the_book_processing_for_startup_recovery(store):
    def stopped_parser(path, ocr=False):
        raise ParserStopped("parse stopped by shutdown")

    book = _book()
    ingestion = _ingestion(book, store, stopped_parser)
    ingestion.enqueue(book["id"])
    assert ingestion.repository.history == ["queued", "processing"] and book["ingestion_error"] is None


def test_too_many_pages_rejected(store, settings, monkeypatch):
    monkeypatch.setattr(settings, "MAX_PDF_PAGES", 2)
    book = _book()
    _ingestion(book, store, _parser(_chunks(1), pages=3)).enqueue(book["id"])
    assert book["ingestion_status"] == "failed" and "limit is 2" in book["ingestion_error"]


def _deleting_parser(repository, chunks, fail=False):
    """Yields the chunks, then the book row disappears (deleted while indexing ran)."""
    def parse(path):
        def generate():
            yield from chunks
            repository.deleted = True
            if fail:
                raise RuntimeError("parser crashed after the book was deleted")
        return 3, generate()
    return parse


def test_points_of_a_book_deleted_during_indexing_are_removed(store):
    book = _book()
    ingestion = _ingestion(book, store, None)
    ingestion._parser = _deleting_parser(ingestion.repository, _chunks(5))
    ingestion.enqueue(book["id"])
    assert store.count(book["id"]) == 0
    assert ingestion.repository.history == ["queued", "processing"]  # never marked indexed


def test_partial_points_of_a_deleted_book_are_removed_when_indexing_fails(store, settings, monkeypatch):
    monkeypatch.setattr(settings, "ENGINE_EMBEDDING_BATCH_SIZE", 2)
    book = _book()
    ingestion = _ingestion(book, store, None)
    ingestion._parser = _deleting_parser(ingestion.repository, _chunks(5), fail=True)
    ingestion.enqueue(book["id"])
    assert store.count(book["id"]) == 0 and ingestion.repository.history == ["queued", "processing"]


def test_points_are_kept_when_the_book_still_exists(store):
    book = _book()
    _ingestion(book, store, _parser(_chunks(3))).enqueue(book["id"])
    assert store.count(book["id"]) == 3 and book["ingestion_status"] == "indexed"


def test_worker_threads_are_daemons_so_shutdown_never_waits():
    import threading

    from service.ingestion import _Workers

    done = threading.Event()
    _Workers.submit(done.set)
    assert done.wait(5)
    workers = [t for t in threading.enumerate() if t.name.startswith("ingest-")]
    assert workers and all(t.daemon for t in workers)


def test_shutdown_leaves_waiting_jobs_queued_and_stops_the_parse_child(monkeypatch):
    import threading

    from service.ingestion import _Workers

    stopped = []
    monkeypatch.setattr(_Workers, "_stopped", False)
    monkeypatch.setattr(ingestion_module.parse_process, "shutdown", lambda: stopped.append(True))
    ingestion_module.shutdown()
    assert stopped == [True]

    ran, drained = [], threading.Event()
    _Workers.submit(lambda: ran.append(True))
    _Workers.submit(drained.set)  # never runs either: shows the worker went past both jobs
    _Workers._queue.join()
    assert ran == [] and not drained.is_set()


# ── attempts + startup recovery ───────────────────────────────────────

def test_each_claim_counts_an_attempt(store):
    book = _book(attempts=1)
    ingestion = _ingestion(book, store, _parser(_chunks(2)))
    ingestion.enqueue(book["id"])
    assert book["ingestion_attempts"] == 2 and book["ingestion_status"] == "indexed"
    ingestion.enqueue(book["id"])  # not queued any more: no claim, no attempt
    assert book["ingestion_attempts"] == 2


class FakeLibrary:
    """Books table for startup recovery; recover_interrupted models the repository's single UPDATE."""

    def __init__(self, *books):
        self.books = {str(b["id"]): b for b in books}

    def recover_interrupted(self, max_attempts):
        requeued, failed = [], 0
        for book in self.books.values():
            if book["ingestion_status"] not in ("queued", "processing"):
                continue
            if book["ingestion_attempts"] < max_attempts:
                book.update(ingestion_status="queued", ingestion_error=None)
                requeued.append(book["id"])
            else:
                book.update(ingestion_status="failed", ingestion_error=INTERRUPTED_MESSAGE)
                failed += 1
        return requeued, failed

    def claim_queued(self, book_id):
        book = self.books[str(book_id)]
        if book["ingestion_status"] != "queued":
            return None
        book.update(ingestion_status="processing", ingestion_attempts=book["ingestion_attempts"] + 1)
        return dict(book)


class RecordingIngestion(Ingestion):
    def __init__(self, repository):
        super().__init__(repository=repository, vector_store=object(), embedder=FakeEmbedder(), parser=_parser([]))
        self.enqueued = []

    def enqueue(self, book_id):
        self.enqueued.append(book_id)


def test_recovery_requeues_jobs_below_the_attempt_cap_and_fails_the_rest(settings, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(settings, "INGESTION_MAX_QUEUED", 1)  # recovery is not a new submission: no cap
    waiting, running = _book("queued", attempts=0), _book("processing", attempts=2)
    exhausted, done = _book("processing", attempts=3), _book("indexed", attempts=1)
    library = FakeLibrary(waiting, running, exhausted, done)
    ingestion = RecordingIngestion(library)

    assert ingestion.recover_interrupted() == (2, 1)
    assert set(ingestion.enqueued) == {waiting["id"], running["id"]}
    assert waiting["ingestion_status"] == running["ingestion_status"] == "queued"
    assert exhausted["ingestion_status"] == "failed" and exhausted["ingestion_error"] == INTERRUPTED_MESSAGE
    assert done["ingestion_status"] == "indexed"


def test_recovery_with_nothing_interrupted_enqueues_nothing():
    ingestion = RecordingIngestion(FakeLibrary(_book("indexed"), _book("failed")))
    assert ingestion.recover_interrupted() == (0, 0) and ingestion.enqueued == []


def test_a_resumed_job_runs_to_completion_and_counts_its_attempt(store, settings, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_MAX_ATTEMPTS", 3)
    book = _book("processing", attempts=1)
    repository = FakeRepository(book)
    repository.recover_interrupted = FakeLibrary(book).recover_interrupted
    ingestion = Ingestion(repository=repository, vector_store=store, embedder=FakeEmbedder(),
                          parser=_parser(_chunks(2)), run_inline=True)
    assert ingestion.recover_interrupted() == (1, 0)
    assert book["ingestion_status"] == "indexed" and book["ingestion_attempts"] == 2


# ── final status writes ───────────────────────────────────────────────

def test_a_lost_final_status_write_is_logged_not_raised(store, caplog_loguru):
    book = _book()
    ingestion = _ingestion(book, store, _parser(_chunks(1)))
    ingestion.repository.transition_status = lambda *a, **k: None  # status changed underneath the job
    ingestion.enqueue(book["id"])
    assert any("Could not mark book" in m and "indexed" in m for m in caplog_loguru)


# ── OCR fallback ──────────────────────────────────────────────────────

class FakeParser:
    """Records each call's `ocr` flag; returns `without_ocr` / `with_ocr` chunks."""

    def __init__(self, without_ocr, with_ocr):
        self.results = {False: without_ocr, True: with_ocr}
        self.calls = []

    def __call__(self, path, ocr=False):
        self.calls.append(ocr)
        return 3, iter([dict(c) for c in self.results[ocr]])


def test_text_pdf_is_parsed_once_without_ocr(store):
    book, parser = _book(), FakeParser(_chunks(2), _chunks(5))
    _ingestion(book, store, parser).enqueue(book["id"])
    assert parser.calls == [False] and book["chunk_count"] == 2


def test_scanned_pdf_is_retried_once_with_ocr(store, caplog_loguru):
    book, parser = _book(), FakeParser([{"text": " "}], _chunks(3))
    _ingestion(book, store, parser).enqueue(book["id"])
    assert parser.calls == [False, True]
    assert book["ingestion_status"] == "indexed" and book["chunk_count"] == 3 and store.count(book["id"]) == 3
    assert any("no text without OCR, retrying with OCR" in m for m in caplog_loguru)


def test_ocr_also_empty_fails_with_the_no_text_message(store, caplog_loguru):
    book, parser = _book(), FakeParser([], [{"text": "  "}])
    _ingestion(book, store, parser).enqueue(book["id"])
    assert parser.calls == [False, True]
    assert book["ingestion_status"] == "failed" and book["ingestion_error"] == NO_TEXT_WITH_OCR_MESSAGE
    assert book["ingestion_error"].startswith("No text could be extracted")
    assert any("OCR also found no text" in m for m in caplog_loguru)


def test_no_ocr_retry_when_fallback_disabled_or_ocr_already_on(store, settings, monkeypatch):
    monkeypatch.setattr(settings, "DOCLING_OCR_FALLBACK", False)
    book, parser = _book(), FakeParser([], _chunks(3))
    _ingestion(book, store, parser).enqueue(book["id"])
    assert parser.calls == [False] and book["ingestion_error"] == NO_TEXT_MESSAGE

    monkeypatch.setattr(settings, "DOCLING_OCR_FALLBACK", True)
    monkeypatch.setattr(settings, "DOCLING_DO_OCR", True)
    book, parser = _book(), FakeParser([], _chunks(3))
    _ingestion(book, store, parser).enqueue(book["id"])
    assert parser.calls == [False] and book["ingestion_error"] == NO_TEXT_WITH_OCR_MESSAGE


def test_without_an_ocr_engine_the_ocr_pass_is_skipped_and_warned_once(store, caplog_loguru, monkeypatch):
    monkeypatch.setattr(ingestion_module._NoOcrWarning, "logged", False)
    for _ in range(2):  # two scanned books: one warning
        book, parser = _book(), FakeParser([], _chunks(3))
        _ingestion(book, store, parser, ocr_available=False).enqueue(book["id"])
        assert parser.calls == [False]
        assert book["ingestion_status"] == "failed" and book["ingestion_error"] == NO_TEXT_MESSAGE
    assert caplog_loguru.count(NO_OCR_ENGINE_WARNING) == 1


def test_ocr_always_on_without_an_engine_keeps_the_original_message(store, settings, monkeypatch):
    monkeypatch.setattr(settings, "DOCLING_DO_OCR", True)
    book, parser = _book(), FakeParser([], _chunks(3))
    _ingestion(book, store, parser, ocr_available=False).enqueue(book["id"])
    assert parser.calls == [False] and book["ingestion_error"] == NO_TEXT_MESSAGE


def test_the_engine_probe_is_not_consulted_for_text_pdfs(store):
    def probe():
        raise AssertionError("probed although the PDF had text")

    book = _book()
    Ingestion(repository=FakeRepository(book), vector_store=store, embedder=FakeEmbedder(),
              parser=FakeParser(_chunks(2), []), run_inline=True, ocr_available=probe).enqueue(book["id"])
    assert book["ingestion_status"] == "indexed"
