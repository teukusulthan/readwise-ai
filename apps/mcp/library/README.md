# library MCP server

Read-only [MCP](https://modelcontextprotocol.io) server (FastMCP) that lets agents and MCP clients browse, search and question the Readwise AI book library. It calls **only the backend REST API**; it never touches PostgreSQL, Qdrant or the PDF storage.

## Tools

| Tool | Backend call | Returns |
|------|--------------|---------|
| `list_books(query?, indexed_only?, page?, size?)` | `POST /book/get-all` | `{books[{id,title,authors,status,searchable,...}], page, size, total, total_pages}` |
| `get_book(book_id)` | `GET /book/get-one` | one book with `status`, `chunk_count`, `error`, subjects, ... |
| `search_passages(query, book_ids?, top_k?)` | `POST /search/query` | `{passages[{book_title,headings,page_start,page_end,score,text}], searched_book_count, skipped_books}` |
| `ask_library(question, book_ids?)` | `POST /chat/ask` | `{answer, mode, grounded, used_general_knowledge, sources[{n,book_title,headings,page_start,page_end,cited,snippet}]}` |

Only `indexed` books are searchable. Passage and source text is quoted book content: clients must treat it as data, not instructions. Failures (backend down, 401/403, 404, 429 with the retry delay, 503, bad input) come back as MCP tool errors.

## Configuration

Copy `.env.example`; values are read from the process environment.

| Variable | Default | Notes |
|----------|---------|-------|
| `LIBRARY_API_URL` | `http://localhost:8020` | Backend base URL |
| `LIBRARY_INTERNAL_TOKEN` | empty | Sent as `X-Internal-Token`; must equal the backend's `BE_INTERNAL_TOKEN`. Empty only works when the backend runs with `BE_JWT_ACTIVE=false` |
| `LIBRARY_TIMEOUT_SECONDS` | `420` | `ask_library` waits for a full LLM answer: keep it above the backend's worst case, `BE_LLM_TIMEOUT_SECONDS` × (1 + `BE_LLM_NUM_RETRIES`) = 120 × 3 = 360 s plus retrieval |
| `MCP_BEARER_TOKEN` | none | **Required for HTTP**, at least 32 characters (`openssl rand -hex 32`) |
| `MCP_HOST` / `MCP_PORT` | `127.0.0.1` / `8030` | HTTP bind address |

## Run

```bash
cd apps/mcp/library
uv sync

# stdio: local clients (Claude Desktop / Claude Code); no inbound token
uv run python server.py

# HTTP (streamable, endpoint /mcp): requires Authorization: Bearer $MCP_BEARER_TOKEN
MCP_BEARER_TOKEN=$(openssl rand -hex 32) uv run python server.py --transport http
```

The HTTP transport refuses to start without `MCP_BEARER_TOKEN`; a missing or wrong bearer gets `401` (constant-time comparison). Bind beyond localhost only behind TLS.

Client config example (stdio):

```json
{ "mcpServers": { "library": {
  "command": "uv",
  "args": ["run", "--project", "/path/to/apps/mcp/library", "python", "/path/to/apps/mcp/library/server.py"],
  "env": { "LIBRARY_API_URL": "http://localhost:8020", "LIBRARY_INTERNAL_TOKEN": "<BE_INTERNAL_TOKEN>" }
} } }
```

## Tests

`uv run pytest` (no backend needed: the backend is mocked with `httpx.MockTransport`).
