import json

import httpx
import pytest
from fastmcp.exceptions import ToolError

from conftest import envelope, failure

BOOK = {
    "id": "b1",
    "title": "A Christmas Carol",
    "authors": ["Charles Dickens"],
    "description": "x" * 600,
    "language": "en",
    "publishedYear": 1843,
    "publisher": "Gutenberg",
    "isbn": None,
    "subjects": ["Ghost stories"],
    "document": {"fileName": "a.pdf", "pageCount": 80},
    "ingestion": {"status": "indexed", "error": None, "chunkCount": 42, "indexedAt": "2026-10-12T18:00:00+07:00"},
    "searchable": True,
}


def body(request: httpx.Request):
    return json.loads(request.content)


async def test_lists_the_four_read_only_tools(client):
    tools = {t.name: t for t in await client.list_tools()}
    assert set(tools) == {"list_books", "get_book", "search_passages", "ask_library"}
    assert all(t.annotations.read_only_hint for t in tools.values())


async def test_list_books_maps_request_and_shapes_output(client, backend):
    backend.response = httpx.Response(
        200, json=envelope([BOOK], pagination={"size": 5, "totalElements": 8, "totalPages": 2})
    )
    result = await client.call_tool(
        "list_books", {"query": " carol ", "indexed_only": True, "page": 2, "size": 5}
    )
    assert backend.last.method == "POST" and backend.last.url.path == "/book/get-all"
    assert body(backend.last) == {"page": 2, "size": 5, "search": "carol", "status": ["indexed"]}
    data = result.data
    assert (data.page, data.size, data.total, data.total_pages) == (2, 5, 8, 2)
    book = data.books[0]
    assert book.id == "b1" and book.status == "indexed" and book.searchable is True
    assert book.page_count == 80 and book.published_year == 1843
    assert len(book.description) <= 400  # concise, not the raw 600 chars


async def test_list_books_defaults_send_no_filters(client, backend):
    await client.call_tool("list_books", {})
    assert body(backend.last) == {"page": 1, "size": 20}


async def test_service_token_header_is_sent(client, backend, settings):
    await client.call_tool("list_books", {})
    assert backend.last.headers["x-internal-token"] == settings.internal_token


async def test_get_book_maps_request_and_detail(client, backend):
    backend.response = httpx.Response(200, json=envelope(BOOK))
    result = await client.call_tool("get_book", {"book_id": "b1"})
    assert backend.last.method == "GET" and backend.last.url.path == "/book/get-one"
    assert backend.last.url.params["id"] == "b1"
    book = result.data
    assert book.chunk_count == 42 and book.subjects == ["Ghost stories"] and book.publisher == "Gutenberg"
    assert book.error is None and len(book.description) == 600


async def test_get_book_404_is_a_tool_error(client, backend):
    backend.response = httpx.Response(404, json=failure("Book not found", 404))
    with pytest.raises(ToolError, match="Not found: Book not found"):
        await client.call_tool("get_book", {"book_id": "missing"})


async def test_search_passages_maps_request_and_output(client, backend):
    backend.response = httpx.Response(
        200,
        json=envelope(
            {
                "query": "whale",
                "results": [
                    {
                        "bookId": "b1", "bookTitle": "Moby", "chunkIndex": 3, "text": "y" * 3000,
                        "headings": ["Ch 1"], "pageStart": 4, "pageEnd": 5, "score": 0.61,
                    }
                ],
                "searchedBookCount": 3,
                "skippedBooks": [{"id": "b9", "title": "Draft", "reason": "not_indexed:none"}],
            }
        ),
    )
    result = await client.call_tool("search_passages", {"query": "whale", "book_ids": ["b1"], "top_k": 3})
    assert backend.last.url.path == "/search/query"
    assert body(backend.last) == {"query": "whale", "topK": 3, "bookIds": ["b1"]}
    data = result.data
    assert data.searched_book_count == 3
    passage = data.passages[0]
    assert (passage.book_title, passage.headings, passage.page_start, passage.page_end) == ("Moby", ["Ch 1"], 4, 5)
    assert passage.score == 0.61 and len(passage.text) <= 1500
    assert data.skipped_books[0].reason == "not_indexed:none"


async def test_search_passages_omits_book_ids_when_not_given(client, backend):
    backend.response = httpx.Response(200, json=envelope({"query": "q", "results": [], "searchedBookCount": 0}))
    result = await client.call_tool("search_passages", {"query": "q"})
    assert body(backend.last) == {"query": "q", "topK": 8}
    assert result.data.passages == []


@pytest.mark.parametrize("args", [{"query": ""}, {"query": "q", "top_k": 99}, {"query": "q", "top_k": 0}])
async def test_search_passages_rejects_bad_input_before_calling_the_backend(client, backend, args):
    with pytest.raises(ToolError):
        await client.call_tool("search_passages", args)
    assert backend.requests == []


async def test_ask_library_maps_request_and_sources(client, backend):
    backend.response = httpx.Response(
        200,
        json=envelope(
            {
                "question": "Who?",
                "answer": "The lifeboat [1].",
                "grounded": True,
                "mode": "llm",
                "usedGeneralKnowledge": False,
                "model": "m",
                "sources": [
                    {"n": 1, "bookId": "b1", "bookTitle": "Marigold", "headings": ["Ch 3"],
                     "pageStart": 3, "pageEnd": 3, "score": 0.7, "text": "z" * 900, "cited": True}
                ],
                "skippedBooks": [],
            }
        ),
    )
    result = await client.call_tool("ask_library", {"question": "Who?", "book_ids": ["b1"]})
    assert backend.last.url.path == "/chat/ask"
    assert body(backend.last) == {"question": "Who?", "bookIds": ["b1"]}
    data = result.data
    assert data.answer == "The lifeboat [1]." and data.mode == "llm" and data.grounded is True
    src = data.sources[0]
    assert (src.n, src.book_title, src.headings, src.page_start, src.cited) == (1, "Marigold", ["Ch 3"], 3, True)
    assert len(src.snippet) <= 600


@pytest.mark.parametrize(
    ("response", "needle"),
    [
        (httpx.Response(401, json=failure("Not authenticated", 401)), "rejected the credentials (401"),
        (httpx.Response(403, json=failure("Forbidden", 403)), "LIBRARY_INTERNAL_TOKEN"),
        (httpx.Response(429, json=failure("Too many requests", 429), headers={"Retry-After": "17"}), "retry in 17 seconds"),
        (httpx.Response(429, json=failure("Too many requests", 429)), "retry shortly"),
        (httpx.Response(503, json=failure("Search service unavailable", 503)), "temporarily unavailable: Search service unavailable"),
        (httpx.Response(400, json=failure("Invalid book id: 'x'", 400)), "Invalid book id: 'x'"),
        (httpx.Response(422, json={"detail": [{"loc": ["body", "query"], "msg": "too short"}]}), "query: too short"),
        (httpx.Response(500, text="boom"), "failed (500): HTTP 500"),
    ],
)
async def test_backend_errors_become_tool_errors(client, backend, response, needle):
    backend.response = response
    with pytest.raises(ToolError) as exc:
        await client.call_tool("ask_library", {"question": "q"})
    assert needle in str(exc.value)


@pytest.mark.parametrize(
    "error", [httpx.ConnectError("refused"), httpx.ReadTimeout("slow")], ids=["down", "timeout"]
)
async def test_backend_down_is_a_tool_error_without_leaking_the_token(client, backend, settings, error):
    backend.response = error
    with pytest.raises(ToolError) as exc:
        await client.call_tool("list_books", {})
    assert "http://backend.test" in str(exc.value)
    assert settings.internal_token not in str(exc.value)
