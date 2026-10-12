import httpx
import pytest

from service.openlibrary import OpenLibraryClient
from util.http_errors import NotFoundError, ServiceUnavailableError

SEARCH_DOC = {
    "key": "/works/OL893415W", "title": "Dune", "author_name": ["Frank Herbert"], "first_publish_year": 1965,
    "publisher": ["Chilton Books"], "language": ["eng"], "subject": ["Science fiction"], "cover_i": 11481354,
    "isbn": ["not-an-isbn", "0441172717", "9780441013593"],
}


def _client(handler):
    return OpenLibraryClient(base_url="https://openlibrary.test", transport=httpx.MockTransport(handler))


def test_get_by_isbn_maps_metadata_and_description():
    def handler(request):
        if request.url.path == "/search.json":
            assert request.url.params["isbn"] == "9780441013593"
            return httpx.Response(200, json={"docs": [SEARCH_DOC]})
        if request.url.path == "/works/OL893415W.json":
            return httpx.Response(200, json={"description": {"value": "Desert planet."}})
        return httpx.Response(404)

    meta = _client(handler).get_by_isbn("9780441013593")
    assert meta["title"] == "Dune" and meta["authors"] == ["Frank Herbert"]
    assert meta["published_year"] == 1965 and meta["description"] == "Desert planet."
    assert meta["cover_url"] == "https://covers.openlibrary.org/b/id/11481354-L.jpg"
    assert meta["metadata_source"] == "openlibrary" and meta["external_id"] == "/works/OL893415W"


def test_unknown_isbn_is_not_found():
    with pytest.raises(NotFoundError):
        _client(lambda r: httpx.Response(200, json={"docs": []})).get_by_isbn("9780441013593")


def test_network_failure_is_service_unavailable():
    def handler(request):
        raise httpx.ConnectError("down")

    with pytest.raises(ServiceUnavailableError):
        _client(handler).get_by_isbn("9780441013593")


def test_search_prefers_valid_isbn13_and_skips_results_without_isbn():
    docs = [SEARCH_DOC, {**SEARCH_DOC, "isbn": ["junk"], "title": "No ISBN"}]
    results = _client(lambda r: httpx.Response(200, json={"docs": docs})).search("dune")
    assert [r["title"] for r in results] == ["Dune"] and results[0]["isbn"] == "9780441013593"
