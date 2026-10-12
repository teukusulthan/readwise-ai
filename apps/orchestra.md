# Orchestra — Apps

> AI: Read this file FIRST before any file operation. Do NOT scan the filesystem.
> Update immediately after every execution — append new files and mark features done.

## Features Implemented

- [x] Boilerplate hardening + stack migration (uv, PostgreSQL/Qdrant clients, health checks, web client fixes) — 2026-10-09
- [x] RAG Book Library MVP: catalog, Open Library import, PDF upload, Docling ingestion, Qdrant search, grounded answers, React UI — 2026-10-09 (see docs/architecture.md §5 for the file map)
- [x] Streaming answers (SSE), narrative prompt, cream light redesign, bounded-memory windowed Docling — 2026-10-09
- [ ] MCP server, app Docker images, login UI — not started

---

## File Index

### Infra (repo root)

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Local PostgreSQL (pgvector image), Qdrant, MongoDB, Redis — 127.0.0.1 only |

### Backend (`apps/backend/`)

| File | Purpose |
|------|---------|
| `api.py` | Entry point: settings, middleware stack, `ROUTER_MODULES`, uvicorn |
| `pyproject.toml` / `uv.lock` / `.python-version` | uv-managed dependencies, Python 3.12, pytest config |
| `config/base.py` | `BaseSetting` — all `BE_*` env settings |
| `middleware/body_limit.py` | Request body size cap (413) |
| `middleware/rate_limiter.py` | Redis per-IP rate limit, fails open |
| `router/middleware.py` | `DecryptPayload` (AES request envelope when `ENC_ACTIVE`) |
| `router/health.py` / `service/health.py` | `GET /health`, `GET /health/ready` |
| `util/postgres.py` | `PostgresService` — psycopg_pool singleton (`Services.postgres()`) |
| `util/qdrant.py` | `QdrantService` — QdrantClient singleton (`Services.qdrant()`) |
| `util/embedding.py` | `EmbeddingClient` for the company TEI service (`Services.embedding()`) |
| `service/__init__.py` | `Services` factory (mongo, postgres, qdrant, boto3, redis) |
| `tests/` | `conftest.py`, `unit/`, `integration/` (`-m integration`), `external/` (`-m external`) |

### Web (`apps/web/`)

| File | Purpose |
|------|---------|
| `src/config/env.ts` | Typed env accessor (`VITE_*`) |
| `src/config/query-client.ts` | Shared TanStack Query client |
| `src/services/api-client.ts` | Axios instance (cookie auth, refresh-on-401) |
| `src/services/api-factory.service.ts` | `apiRequests` — resolves to the `ApiResponse<T>` envelope |
| `src/services/api-endpoints.ts` | Endpoint constants (`/apps/...` via dev proxy) |
| `src/components/wrappers/PerfectScrollArea.tsx` | Mandated scroll-region wrapper |

### MCP (`apps/mcp/`)

| File | Purpose |
|------|---------|
| — | not created yet |
