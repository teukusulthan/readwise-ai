"""scripts/seed_gutenberg.py reads the API's failure message from the envelope it actually returns."""

import importlib.util
from pathlib import Path

import httpx
import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "seed_gutenberg.py"
_spec = importlib.util.spec_from_file_location("seed_gutenberg", _SCRIPT)
seed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(seed)


def _response(status, **kwargs):
    return httpx.Response(status, request=httpx.Request("POST", "http://test/book/add"), **kwargs)


@pytest.mark.parametrize("kwargs, message", [
    ({"json": {"metaData": {"message": "Book already exists", "responseCode": 409}, "data": None}}, "Book already exists"),
    ({"json": {"detail": {"metaData": {"message": "Legacy shape"}}}}, "Legacy shape"),
    ({"json": {"detail": "Too many requests"}}, "Too many requests"),
    ({"json": {"metaData": {"message": "Envelope wins"}, "detail": "plain"}}, "Envelope wins"),
    ({"text": "Bad gateway from proxy"}, "Bad gateway from proxy"),
])
def test_error_message_prefers_the_top_level_envelope(kwargs, message):
    assert seed.error_message(_response(409, **kwargs)) == message


def test_failed_call_raises_with_the_api_message():
    library = seed.Library("http://test", token=None)
    response = _response(409, json={"metaData": {"message": "Book already exists"}})
    with pytest.raises(RuntimeError, match="POST /book/add → 409: Book already exists"):
        library._data(response)
