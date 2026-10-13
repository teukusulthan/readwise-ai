# MCP Changelog

Tracks changes to the MCP servers under `apps/mcp/`.

Append-only. Newest entries at the top. Same entry format as [`backend.md`](./backend.md).

---

### 2026-10-13 · Docker image for the MCP server (no sprint) · ✅ Done

**Event:** Task completed
**Files:** `apps/mcp/library/Dockerfile`, `apps/mcp/library/.dockerignore`, `docker-compose.yml`
> Image for the HTTP transport (`MCP_TRANSPORT=http`, 0.0.0.0:8030, non-root, TCP healthcheck); compose service `mcp` (profile `app`) calls the backend service via `LIBRARY_API_URL`. Image build not yet verified (no Docker daemon available).

### 2026-10-13 · Library MCP server (no sprint) · ✅ Done

**Event:** Task completed
**Files:** `apps/mcp/library/{server.py,pyproject.toml,uv.lock,.python-version,.env.example,README.md}`, `apps/mcp/library/tests/{conftest,test_tools,test_auth}.py`, `docs/architecture.md`, `README.md`
> New FastMCP server `library` with four read-only tools (`list_books`, `get_book`, `search_passages`, `ask_library`) that call only the backend REST API with `X-Internal-Token` (`LIBRARY_INTERNAL_TOKEN`). Typed trimmed outputs; backend down / 401 / 403 / 404 / 429 (retry delay) / 503 become tool errors. stdio needs no inbound token; the HTTP transport refuses to start without `MCP_BEARER_TOKEN` (>= 32 chars) and checks `Authorization: Bearer` in constant time (401 otherwise). 31 unit tests with a mocked backend.
