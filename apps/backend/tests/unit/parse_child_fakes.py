"""
Fakes run in the parse child by tests/unit/test_parse_process.py. Kept in their own light module:
a spawned child imports the module of every function it runs (pickled by reference), and the
test module itself pulls in the service layer.
"""

import os
import time


def child_pid():
    return os.getpid()


def child_raises():
    raise ValueError("bad page tree")


def child_exits():
    os._exit(1)  # as abrupt as a segfault in the native parser: no exception, no cleanup


def child_sleeps(seconds):
    time.sleep(seconds)
    return "finished"


def child_memory_limit():
    import resource

    return resource.getrlimit(resource.RLIMIT_AS)


def child_allocates(megabytes):
    return len(bytearray(megabytes * 1024 * 1024))


def child_parse(path, ocr):
    """Stands in for _parse_in_child: crashes on 'crash.pdf', else returns chunk dicts."""
    if path.endswith("crash.pdf"):
        os._exit(1)
    return 1, [{"text": f"chunk {i}", "embed_text": f"chunk {i}", "headings": [], "page_start": 1, "page_end": 1}
               for i in range(3)]
