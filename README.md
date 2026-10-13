# RAG Book Library AI Assistant

An AI assistant for a personal/team book library: upload PDF books, extract → chunk → embed → index their content, search semantically across books, ask questions about one or many books, and receive **streaming answers with source citations**. Library capabilities are also exposed to other agents through an **MCP server**.

## Features

- **Catalog:** add books by hand, import metadata from Open Library, edit and delete them.
- **Upload and indexing:** upload one or several PDFs; they are parsed (Docling, in a separate process), chunked, embedded and indexed in the background, with retry, resume after a restart and an OCR fallback for scanned files when an OCR engine is available.
- **Semantic search:** a search page returns passages with book, section and page; each result opens the PDF at that page.
- **Ask:** streaming answers with numbered citations that open the PDF at the cited page, safe Markdown rendering, resumable and stoppable answers, and saved conversations. Facts from the model's own knowledge are labelled and never cited.
- **Accounts (optional):** login and registration, with conversations private per user (`BE_JWT_ACTIVE` + `VITE_AUTH_ENABLED`). Off by default for local use.
- **MCP server:** read-only library tools for other agents, over the backend REST API.
- **Docker and CI:** compose profile that builds and runs backend, web and MCP; a GitHub Actions workflow runs the tests.

Contributor and agent guidance lives in [`AGENTS.md`](AGENTS.md). How it works, where the code lives and what is still open: [`docs/architecture.md`](docs/architecture.md). Endpoints: [`docs/api-spec.md`](docs/api-spec.md).

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12 + FastAPI (`apps/backend`, be-fastapi template), dependencies via **uv** |
| Relational DB | PostgreSQL 16 (`pgvector/pgvector:pg16` image) — books, chunks, processing status |
| Vector DB | Qdrant (pgvector is a later alternative behind a `VectorStore` interface) |
| Legacy stores | MongoDB + Redis — only for the boilerplate auth/user/group/permission/role/upload modules |
| File storage | Local disk (`BE_BOOK_STORAGE_DIR`, default `apps/backend/storage/books/`); S3 later |
| Embeddings | Company TEI service — `Qwen3-Embedding-0.6B`, 1024-dim (`BE_ENGINE_EMBEDDING_*`) |
| LLM access | LiteLLM (provider/model via env) |
| Agent / RAG | Agno, running inside the backend service layer |
| Streaming | Server-Sent Events (FastAPI `EventSourceResponse`) |
| MCP | FastMCP (`apps/mcp/<name>/`), calls the backend REST API with `X-Internal-Token` |
| Web | React 18 + TypeScript + Vite + Zustand + TanStack Query + shadcn/ui (`apps/web`) |
| Deployment | Docker + docker compose |

Not used: Supabase, Rust/Axum, mobile (Flutter/React Native), the be-python `agent_mgmt` plane, mandatory MCPHub.

---

## Layout

```
readwise-ai/
├── apps/
│   ├── backend/      # FastAPI API (api.py entry, uv-managed)
│   ├── web/          # React + Vite web app
│   └── mcp/library/  # FastMCP server exposing the library to agents (stdio / HTTP)
├── docs/             # architecture, API spec, database schema
├── docker-compose.yml  # databases, plus the apps behind the `app` profile
├── .github/workflows/  # CI
├── sprint/           # Sprint planning (sprint-builder)
├── brief/            # Project brief (brief-builder) — optional
├── changelog/        # Per-stack changelogs
└── nx/               # Nx runner (`npm run dev` starts backend + web)
```

---

## Running locally

**Prerequisites:** Docker (your user must be in the `docker` group, or prefix the Docker commands with `sudo`), [uv](https://docs.astral.sh/uv/), Node 22+.

```bash
# 1. Infrastructure (PostgreSQL, Qdrant, MongoDB, Redis)
docker compose up -d

# 2. Backend — http://localhost:8020 (Swagger at /docs)
cd apps/backend
cp .env.example .env        # fill in values; every key carries the BE_ prefix
uv sync
uv run python api.py --port 8020 --reload   # --reload = dev auto-restart; omit it for anything long-running

# 3. Web — http://localhost:3000
cd apps/web
npm install
npm run dev
```

The databases can also be run without Docker: install PostgreSQL 16 (with the pgvector extension), Qdrant, MongoDB and Redis yourself and point the `BE_*` connection settings in `apps/backend/.env` at them.

Tests: `uv run pytest` (backend, and in `apps/mcp/library`), `npm test` (web).

**MCP server (optional)** — lets agents search and question the library (read-only tools over the backend REST API):

```bash
cd apps/mcp/library
uv sync && uv run python server.py      # stdio; HTTP + bearer token: see apps/mcp/library/README.md
```

| Service | Default URL |
|---------|-------------|
| Web (Vite dev) | http://localhost:3000 |
| Backend API | http://localhost:8020 |
| PostgreSQL | localhost:5433 |
| Qdrant | http://localhost:6333 |
| MongoDB | localhost:27017 |
| Redis | localhost:6380 |

**Changing ports.** The defaults are backend 8020 and web 3000. If one is taken, start the backend with another `--port` (for example `uv run python api.py --port 8021`) and set, in `apps/web/env/.env` (git-ignored; copy `env/.env.example`), `PORT=<web port>` and `BACKEND_PROXY_TARGET=http://localhost:<backend port>`. For Docker use `WEB_PORT` / `BACKEND_PORT`.

All ports bind to 127.0.0.1. Postgres and Redis use 5433/6380 on the host to avoid clashing with local installs (override with `POSTGRES_PORT` / `REDIS_PORT`).

**File storage:** uploaded PDFs are kept on local disk (`apps/backend/storage/books/<book_id>.pdf`, set by `BE_BOOK_STORAGE_DIR`; the Docker setup uses the `book-storage` volume). S3-compatible storage is a later option.

---

## Running with Docker

Besides the databases, compose can build and run the three apps behind the `app` profile (plain `docker compose up -d` still starts only the databases).

```bash
cp apps/backend/.env.example apps/backend/.env            # BE_SESSION_SECRET, BE_LLM_*, BE_ENGINE_EMBEDDING_BASE_URL ... (accounts off)
cp apps/web/env/.env.example apps/web/env/.env            # ICON_CDN_PROXY_TARGET (icon CDN host; empty = no icons)
cp apps/mcp/library/.env.example apps/mcp/library/.env    # MCP_BEARER_TOKEN (>= 32 chars), LIBRARY_INTERNAL_TOKEN
docker compose --profile app up -d --build
docker compose --profile app ps                           # backend, web, mcp should become "healthy"
```

| Service | Host URL | Notes |
|---------|----------|-------|
| web | http://localhost:3000 (`WEB_PORT`) | nginx: serves the build, proxies `/api/v1/apps/` to the backend (SSE unbuffered; `/chat/ask` gets a 420 s read timeout, other API calls 300 s), `/cdn-assets/` to `ICON_CDN_PROXY_TARGET` (resolved per request, so an unreachable CDN never stops nginx from starting) |
| backend | http://localhost:8020 (`BACKEND_PORT`) | one worker; `BE_POSTGRES_URI`, `BE_QDRANT_URL`, `BE_MONGO_URI`, `BE_REDIS_HOST/PORT` are set by compose to the service names, overriding the localhost values in `.env` |
| mcp | http://localhost:8030/mcp (`MCP_PORT`) | HTTP transport with bearer token; `LIBRARY_API_URL` points at the backend service |

- Client IPs behind nginx: web and backend share a dedicated `edge` network with a fixed subnet (`EDGE_SUBNET`, default `172.29.250.0/28`), and compose sets the backend's `BE_TRUSTED_PROXIES` to that subnet. nginx overwrites `X-Forwarded-For` with the browser's address, so per-route rate limits count each client separately instead of sharing nginx's IP. If the subnet clashes with another network on the host, set `EDGE_SUBNET` (shell or root `.env`) — both values follow it. The web container is only on `edge`; the MCP container reaches the backend over the default network and is keyed by its service token.
- Volumes: `book-storage` (uploaded PDFs) and `hf-cache` (tokenizer and Docling models, downloaded on the first parse) survive rebuilds.
- `VITE_API_BASE_URL` and `VITE_AUTH_ENABLED` are compiled into the web bundle: set them in the shell or a root `.env` (compose reads that, not `apps/web/env/.env`) and rebuild. Accounts are off by default (`BE_JWT_ACTIVE=false` in `apps/backend/.env.example`, `VITE_AUTH_ENABLED=false`); turn `VITE_AUTH_ENABLED=true` on together with `BE_JWT_ACTIVE=true` and a `BE_JWT_SECRET` of at least 32 characters (the backend refuses to start otherwise).
- The backend `.env` is not copied into the image (`.dockerignore`); it is passed as environment variables. The embedding service host (`BE_ENGINE_EMBEDDING_BASE_URL`) must be reachable from the container.
- Ports bind to 127.0.0.1. Put TLS in front before exposing them.

---

## AI Agent System

Start with [`AGENTS.md`](AGENTS.md) (`CLAUDE.md` points to it), then the app `AI_GUIDE.md` for the area you are changing (`apps/backend/AI_GUIDE.md`, `apps/web/AI_GUIDE.md`). The `.claude/` folder (skills, rules) is optional local tooling that is git-ignored and may be absent.

---

## License

MIT
