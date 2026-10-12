"""
The parse child process (util/parse_process.py) with real spawned children running the
module-level fakes in parse_child_fakes.py.
"""

import os
import threading
import time
import uuid

import pytest
from qdrant_client import QdrantClient

from service.ingestion import Ingestion
from service.vector_store import VectorStore
from util.parse_process import (
    PARSE_TIMEOUT_MESSAGE,
    PARSER_CRASHED_MESSAGE,
    PARSER_OUT_OF_MEMORY_MESSAGE,
    ParseProcess,
    ParserCrashed,
    ParserOutOfMemory,
    ParserStopped,
    ParseTimedOut,
)

from parse_child_fakes import (  # tests/unit is on sys.path (pytest rootdir-relative import)
    child_allocates,
    child_exits,
    child_memory_limit,
    child_parse,
    child_pid,
    child_raises,
    child_sleeps,
)

# ── tests ────────────────────────────────────────────────────────────────


@pytest.fixture
def process():
    proc = ParseProcess(timeout_seconds=60, max_memory_mb=0, tasks_per_child=20)
    yield proc
    proc.shutdown()


def test_runs_in_a_separate_process_and_reuses_it(process):
    first = process.run(child_pid)
    assert first != os.getpid()
    assert process.run(child_pid) == first  # models loaded once stay loaded for the next book


def test_the_child_is_replaced_after_tasks_per_child_parses():
    proc = ParseProcess(timeout_seconds=60, max_memory_mb=0, tasks_per_child=2)
    try:
        pids = [proc.run(child_pid) for _ in range(3)]
    finally:
        proc.shutdown()
    assert pids[0] == pids[1] != pids[2]


def test_an_ordinary_error_propagates_and_keeps_the_child(process):
    pid = process.run(child_pid)
    with pytest.raises(ValueError, match="bad page tree"):
        process.run(child_raises)
    assert process.run(child_pid) == pid


def test_a_crashing_child_fails_with_a_safe_message_and_is_replaced(process):
    pid = process.run(child_pid)
    with pytest.raises(ParserCrashed) as error:
        process.run(child_exits)
    assert str(error.value) == PARSER_CRASHED_MESSAGE
    replacement = process.run(child_pid)
    assert replacement not in (pid, os.getpid())


def test_a_child_that_died_while_idle_is_replaced_without_failing_the_next_parse(process):
    import signal

    pid = process.run(child_pid)
    os.kill(pid, signal.SIGKILL)  # e.g. the kernel's OOM killer picked the idle child
    deadline = time.monotonic() + 10
    while not process._pool._broken and time.monotonic() < deadline:  # the pool notices asynchronously
        time.sleep(0.05)
    assert process._pool._broken
    assert process.run(child_pid) not in (pid, os.getpid())


def test_a_parse_past_the_timeout_is_killed_not_awaited():
    proc = ParseProcess(timeout_seconds=60, max_memory_mb=0, tasks_per_child=20)
    try:
        pid = proc.run(child_pid)  # child started (spawning takes longer than the tiny timeout below)
        proc.timeout_seconds = 1
        started = time.monotonic()
        with pytest.raises(ParseTimedOut) as error:
            proc.run(child_sleeps, 60)
        assert time.monotonic() - started < 10
        assert str(error.value) == PARSE_TIMEOUT_MESSAGE
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)  # the hung child is gone (killed and reaped)
        proc.timeout_seconds = 60
        assert proc.run(child_sleeps, 0) == "finished"  # a fresh child takes the next job
    finally:
        proc.shutdown()


def test_memory_cap_is_applied_in_the_child_only():
    import resource

    proc = ParseProcess(timeout_seconds=60, max_memory_mb=4096, tasks_per_child=20)
    try:
        assert proc.run(child_memory_limit) == (4096 * 1024 * 1024, 4096 * 1024 * 1024)
        with pytest.raises(ParserOutOfMemory) as error:
            proc.run(child_allocates, 8192)
        assert str(error.value) == PARSER_OUT_OF_MEMORY_MESSAGE
    finally:
        proc.shutdown()
    assert resource.getrlimit(resource.RLIMIT_AS)[0] == resource.RLIM_INFINITY  # the API process is not capped


def test_no_memory_cap_by_default(process):
    import resource

    assert process.run(child_memory_limit)[0] == resource.RLIM_INFINITY


def test_shutdown_kills_a_running_parse_and_refuses_new_ones():
    proc = ParseProcess(timeout_seconds=60, max_memory_mb=0, tasks_per_child=20)
    proc.run(child_pid)  # child started
    outcome = {}

    def parse():
        try:
            proc.run(child_sleeps, 60)
        except Exception as error:  # noqa: BLE001 - recorded for the assertion
            outcome["error"] = error

    worker = threading.Thread(target=parse)
    worker.start()
    time.sleep(0.5)
    started = time.monotonic()
    proc.shutdown()
    worker.join(10)
    assert not worker.is_alive() and time.monotonic() - started < 10
    assert isinstance(outcome["error"], ParserStopped)
    with pytest.raises(ParserStopped):
        proc.run(child_pid)


def test_ocr_probe_answer_is_cached_but_a_failed_probe_is_not(monkeypatch):
    proc = ParseProcess(timeout_seconds=60, max_memory_mb=0, tasks_per_child=20)
    calls = []

    def crashed(fn, *args):
        calls.append(fn)
        raise ParserCrashed(PARSER_CRASHED_MESSAGE)

    monkeypatch.setattr(proc, "run", crashed)
    assert proc.ocr_available() is False and proc.ocr_available() is False
    assert len(calls) == 2  # not cached: the next scanned book probes again

    monkeypatch.setattr(proc, "run", lambda fn, *args: calls.append(fn) or True)
    assert proc.ocr_available() is True and proc.ocr_available() is True
    assert len(calls) == 3


# ── the ingestion job survives a crashing child ──────────────────────────


class _Repository:
    def __init__(self, *books):
        self.books = {b["id"]: b for b in books}

    def get(self, book_id):
        return dict(self.books[book_id])

    def claim_queued(self, book_id):
        book = self.books[book_id]
        if book["ingestion_status"] != "queued":
            return None
        book["ingestion_status"] = "processing"
        return dict(book)

    def transition_status(self, book_id, to_status, from_statuses, **fields):
        book = self.books[book_id]
        if book["ingestion_status"] not in from_statuses:
            return None
        book.update(fields, ingestion_status=to_status)
        return dict(book)


class _Embedder:
    model = "fake-embedder"

    def embed_documents(self, texts):
        return [[1.0, 0.0, 0.0, 0.0] for _ in texts]


def test_a_crash_fails_only_that_book_and_the_next_one_is_indexed(process):
    crash = {"id": uuid.uuid4(), "title": "Crash", "file_path": "/tmp/crash.pdf", "ingestion_status": "queued"}
    good = {"id": uuid.uuid4(), "title": "Good", "file_path": "/tmp/good.pdf", "ingestion_status": "queued"}
    store = VectorStore(client=QdrantClient(":memory:"), collection="parse_child_test", dimensions=4)
    ingestion = Ingestion(repository=_Repository(crash, good), vector_store=store, embedder=_Embedder(),
                          parser=lambda path, ocr=False: process.run(child_parse, path, ocr),
                          run_inline=True, ocr_available=lambda: False)

    ingestion.enqueue(crash["id"])
    ingestion.enqueue(good["id"])

    assert crash["ingestion_status"] == "failed" and crash["ingestion_error"] == PARSER_CRASHED_MESSAGE
    assert good["ingestion_status"] == "indexed" and good["chunk_count"] == 3
    assert store.count(good["id"]) == 3
