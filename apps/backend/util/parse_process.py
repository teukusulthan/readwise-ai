"""
Docling parsing in a child process, so a PDF that crashes the native parser, exhausts memory
or never finishes takes down only that child — never the API process and its live chat sessions.

    ingestion worker thread (API process)            child process (spawn, one at a time)
      ParseProcess.parse_pdf(path, ocr) ──submit──►  _parse_in_child: util.document_parser.parse_pdf
                                       ◄─(pages, [chunk dicts])─┘     (converters cached per child)

- One child (ProcessPoolExecutor, max_workers=1, spawn). It is replaced after
  INGESTION_PARSE_TASKS_PER_CHILD tasks (bounds leaks while amortising the model load).
- Wall-clock limit per parse: INGESTION_PARSE_TIMEOUT_SECONDS. On timeout the child is killed
  (not waited for) and a fresh one is started for the next job.
- Optional address-space cap in the child: INGESTION_PARSE_MAX_MEMORY_MB (RLIMIT_AS, 0 = off).
- Crash / timeout / out of memory raise ParseFailed subclasses whose message is safe to show users.
- The OCR engine probe runs in the child too (it must run where the OCR converter would run);
  its answer is cached in this process.
- App shutdown (lifespan) calls shutdown(): the child is killed and a parse in progress raises
  ParserStopped, so its job stays `processing` and is re-queued at the next startup.

Spawned children re-import the main module as `__mp_main__` (standard `spawn` behaviour); `api.py`
is import-safe (uvicorn only starts under `__main__`), it just adds a few seconds per new child.
"""

import multiprocessing
import threading
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from concurrent.futures.process import BrokenProcessPool
from typing import Callable, Optional

from loguru import logger

from config.base import settings

PARSE_TIMEOUT_MESSAGE = "Parsing this PDF took too long and was stopped."
PARSER_CRASHED_MESSAGE = "The PDF parser crashed on this file."
PARSER_OUT_OF_MEMORY_MESSAGE = "Parsing this PDF needed more memory than the server allows."


class ParseFailed(Exception):
    """The child could not parse the PDF; str(error) is safe to show to users."""


class ParseTimedOut(ParseFailed):
    pass


class ParserCrashed(ParseFailed):
    pass


class ParserOutOfMemory(ParseFailed):
    pass


class ParserStopped(Exception):
    """The app is shutting down: the parse was cut off (the job is resumed at the next startup)."""


# ── runs in the child ────────────────────────────────────────────────────

def _init_child(max_memory_mb: int, parent_settings):
    # Parse with the API process's settings: the child's main module need not have built them
    # (the settings singleton is created by api.py), and runtime overrides carry over.
    global settings
    import config.base as config_base

    config_base.Setting.instance = config_base.settings = settings = parent_settings

    if max_memory_mb > 0:
        import resource

        limit = max_memory_mb * 1024 * 1024
        _, hard = resource.getrlimit(resource.RLIMIT_AS)
        if hard != resource.RLIM_INFINITY:
            limit = min(limit, hard)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def _parse_in_child(pdf_path: str, ocr: bool) -> tuple[Optional[int], list[dict]]:
    from util.document_parser import parse_pdf

    page_count, chunks = parse_pdf(pdf_path, ocr=ocr)
    if page_count and page_count > settings.MAX_PDF_PAGES:
        return page_count, []  # nothing parsed: the job rejects the book on its page count
    return page_count, list(chunks)


def _ocr_available_in_child() -> bool:
    from util.document_parser import ocr_available

    return ocr_available()


# ── runs in the API process ──────────────────────────────────────────────

class ParseProcess:
    """Owns the parse child. Thread-safe; one parse at a time (the timeout covers only that parse)."""

    def __init__(self, timeout_seconds: Optional[float] = None, max_memory_mb: Optional[int] = None,
                 tasks_per_child: Optional[int] = None):
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.INGESTION_PARSE_TIMEOUT_SECONDS
        self.max_memory_mb = max_memory_mb if max_memory_mb is not None else settings.INGESTION_PARSE_MAX_MEMORY_MB
        self.tasks_per_child = tasks_per_child or settings.INGESTION_PARSE_TASKS_PER_CHILD
        self._run_lock = threading.Lock()    # serialises run()
        self._state_lock = threading.Lock()  # guards _pool / _stopped (shutdown() must not wait for a run)
        self._pool: Optional[ProcessPoolExecutor] = None
        self._stopped = False
        self._ocr_available: Optional[bool] = None

    def parse_pdf(self, pdf_path: str, ocr: bool = False) -> tuple[Optional[int], list[dict]]:
        """Same contract as util.document_parser.parse_pdf, but the chunks arrive as a list."""
        return self.run(_parse_in_child, pdf_path, ocr)

    def ocr_available(self) -> bool:
        """The child's OCR engine probe, cached here. A probe that crashed or timed out counts as 'no' (not cached)."""
        if self._ocr_available is None:
            try:
                self._ocr_available = self.run(_ocr_available_in_child)
            except ParseFailed:
                logger.exception("The Docling OCR probe failed in the parse process")
                return False
        return self._ocr_available

    def run(self, fn: Callable, *args):
        """Run a module-level (picklable) function in the child, within the timeout."""
        with self._run_lock:
            pool, future = self._submit(fn, *args)
            try:
                return future.result(timeout=self.timeout_seconds)
            except FuturesTimeout:
                self._discard(pool)
                logger.error("Parse process timed out after {s}s; killed it", s=self.timeout_seconds)
                raise ParseTimedOut(PARSE_TIMEOUT_MESSAGE) from None
            except BrokenProcessPool as error:
                self._discard(pool)
                if self._stopped:
                    raise ParserStopped("parse stopped by shutdown") from None
                logger.error("Parse process crashed: {error}", error=error)
                raise ParserCrashed(PARSER_CRASHED_MESSAGE) from error
            except MemoryError as error:  # raised in the child (e.g. under the RLIMIT_AS cap)
                self._discard(pool)
                raise ParserOutOfMemory(PARSER_OUT_OF_MEMORY_MESSAGE) from error

    def shutdown(self):
        """Kill the child without waiting for a parse in progress; later runs raise ParserStopped."""
        with self._state_lock:
            self._stopped = True
            pool, self._pool = self._pool, None
        if pool is not None:
            _kill(pool)
            logger.info("Parse process stopped")

    def _submit(self, fn: Callable, *args):
        pool = self._current_pool()
        try:
            return pool, pool.submit(fn, *args)
        except RuntimeError:  # incl. BrokenProcessPool: the idle child died, or shutdown() just ran
            self._discard(pool)
            pool = self._current_pool()  # raises ParserStopped after shutdown()
            return pool, pool.submit(fn, *args)

    def _current_pool(self) -> ProcessPoolExecutor:
        with self._state_lock:
            if self._stopped:
                raise ParserStopped("the parse process is shut down")
            if self._pool is None:
                self._pool = ProcessPoolExecutor(
                    max_workers=1,
                    mp_context=multiprocessing.get_context("spawn"),
                    max_tasks_per_child=max(1, self.tasks_per_child),
                    initializer=_init_child,
                    initargs=(self.max_memory_mb, settings),
                )
            return self._pool

    def _discard(self, pool: ProcessPoolExecutor):
        """Drop a broken or hung pool (killing its child); the next run starts a fresh one."""
        with self._state_lock:
            if self._pool is pool:
                self._pool = None
        _kill(pool)


def _kill(pool: ProcessPoolExecutor):
    # CPython detail: ProcessPoolExecutor._processes maps pid -> Process (no public kill before 3.14).
    processes = list((getattr(pool, "_processes", None) or {}).values())
    for process in processes:
        if process.is_alive():
            process.kill()
    for process in processes:
        process.join(timeout=5)
    pool.shutdown(wait=False, cancel_futures=True)


_default: Optional[ParseProcess] = None
_default_lock = threading.Lock()


def default() -> ParseProcess:
    """The API process's parse child (created on first use, from settings)."""
    global _default
    with _default_lock:
        if _default is None:
            _default = ParseProcess()
        return _default


def parse_pdf(pdf_path: str, ocr: bool = False) -> tuple[Optional[int], list[dict]]:
    return default().parse_pdf(pdf_path, ocr=ocr)


def ocr_available() -> bool:
    return default().ocr_available()


def shutdown():
    """App shutdown: kill the parse child if one is running; no new one is started afterwards."""
    default().shutdown()
