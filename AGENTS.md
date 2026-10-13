# Contributor and Agent Guide

Project: **RAG Book Library AI Assistant** - upload PDF books, extract, chunk, embed and index them, search semantically, ask questions with streaming cited answers, and expose the library to other agents over MCP.

This file is self-contained: everything a contributor (human or AI agent) needs to work in the repo is here or in the tracked files linked below. The `.claude/` folder (skills, rules, commands) is **optional local tooling** that is git-ignored and may be absent in your clone; nothing in this repo depends on it.

## Where to read

| Need | File |
|------|------|
| System architecture, runtime components, file map | [`docs/architecture.md`](docs/architecture.md) |
| REST endpoint registry | [`docs/api-spec.md`](docs/api-spec.md) |
| Database tables and collections | [`docs/database-schema.md`](docs/database-schema.md) |
| Backend conventions and commands | [`apps/backend/AI_GUIDE.md`](apps/backend/AI_GUIDE.md) |
| Web conventions and commands | [`apps/web/AI_GUIDE.md`](apps/web/AI_GUIDE.md), [`apps/web/README.md`](apps/web/README.md) |
| MCP server | [`apps/mcp/library/README.md`](apps/mcp/library/README.md) |
| Setup, ports, Docker | [`README.md`](README.md) |
| History of changes | [`changelog/`](changelog/) (`backend.md`, `web.md`, `mcp.md`) |

Read the relevant `AI_GUIDE.md` before writing code in an app. Skill files they mention (`skills/...`) are optional local tooling; the rules summarised below and in the guides are authoritative.

## Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Backend | Python 3.12 + FastAPI in `apps/backend/` | Entry `api.py`: `uv run python api.py --port 8020` (argparse runs at import, never `uvicorn api:app`) |
| Python deps | **uv** (`pyproject.toml`, `uv.lock`, `.python-version`) | `uv sync`, `uv add <pkg>`, `uv add --dev <pkg>`; no `requirements.txt`, no pip/venv |
| Relational DB | PostgreSQL 16 (`pgvector/pgvector:pg16`) | psycopg 3 + pool, `Services.postgres()`, raw SQL repositories, versioned migrations. All new domain data lives here |
| Legacy stores | MongoDB + Redis | Only the boilerplate auth/user/group/permission/role/upload modules, sessions, rate limiting. Do not use Mongo for new domains |
| Vector DB | Qdrant (`Services.qdrant()`) | pgvector is a later alternative behind a `VectorStore` interface |
| Embeddings | OpenAI-compatible embedding service (TEI serving `Qwen/Qwen3-Embedding-0.6B`) | URL from `BE_ENGINE_EMBEDDING_BASE_URL` (never commit it). 1024-dim, L2-normalised (cosine), max 32 inputs per request. Client: `Services.embedding()`. Changing model or dimensions requires re-indexing |
| LLM | LiteLLM, model chosen by env (`BE_LLM_*`) | OpenRouter is one allowed provider (`openrouter/<model>`) |
| RAG / agent | Agno, retrieve-then-generate in `service/rag.py` + `service/llm.py` | PDF parsing with Docling + `HybridChunker` (`util/document_parser.py`) |
| Streaming | Server-Sent Events (`EventSourceResponse`) | SSE responses are not wrapped in `BaseResponse` / the AES envelope |
| MCP | FastMCP in `apps/mcp/<name>/` (own pyproject + uv) | Calls the backend REST API with `X-Internal-Token`, never the databases; inbound bearer-token auth; read-only tools by default |
| File storage | Local disk `apps/backend/storage/books/<id>.pdf` (`BE_BOOK_STORAGE_DIR`) | S3 later (`util/s3_filesystem.py`) |
| Web | React 18 + TypeScript + Vite + Zustand + TanStack Query v5 + shadcn/ui in `apps/web/` | |
| Auth | JWT bearer (boilerplate auth module) + `X-Internal-Token` for system-to-system | |
| Deployment | Docker + docker compose (root `docker-compose.yml`, one Dockerfile per app) | |

Not used: Supabase, Rust/Axum, mobile apps, the be-python agent-management plane.

The stack is a guideline, not a hard gate. If a task needs something not listed, explain the trade-off, agree it, and record the change in `docs/architecture.md` in the same change. Additive libraries (parsers, test helpers) are fine when justified: add with `uv add` / `npm install` and mention them in the change summary.

## Commands

```bash
docker compose up -d                     # PostgreSQL, Qdrant, MongoDB, Redis (needs docker group membership)

cd apps/backend
cp .env.example .env                     # every key carries the BE_ prefix
uv sync
uv run python api.py --port 8020         # add --reload for dev auto-restart
uv run python -m util.migrate            # apply SQL migrations
uv run pytest                            # unit tests
uv run pytest -m integration             # needs docker compose
uv run pytest -m external                # needs the embedding service

cd apps/web
npm install
npm run dev                              # http://localhost:3000
npm test && npm run typecheck && npm run lint

cd apps/mcp/library
uv sync && uv run pytest
```

Use free ports on shared machines; do not stop processes you did not start. Never run destructive operations against the dev databases; tests use `library_test` / `book_chunks_test`.

## Backend rules

- Layering: `router/*.py` (thin, no logic, no DB) -> `service/*.py` -> repository / `Services.*()` client. Never query PostgreSQL, Qdrant or MongoDB from a router.
- Responses go through `BaseResponse` / `BaseResponseFailed` with `execution_time` metadata (exceptions: SSE streams and `/health`).
- List endpoints are `POST /{resource}/get-all` with a `FindDTO` body; update is `PUT /{resource}/update` with `id` in the body; delete is `DELETE /{resource}/delete?id=`.
- SQL changes are versioned migrations in `apps/backend/migrations/NNN_*.sql` (next free number). Never edit an applied migration. Parameterised SQL only.
- Settings: add new keys to `config/base.py` (`BaseSetting`, accessed unprefixed as `settings.FIELD`) and to `.env.example` with the `BE_` prefix and a comment. No hardcoded secrets or connection strings.
- Logging with `loguru`; never `print()`. Use `Services.postgres()/qdrant()/embedding()/mongo()/redis()`; never create ad-hoc clients.
- New router modules register in `api.py` (`ROUTER_MODULES`); default-mounted ones are listed in `config/routers.py`.
- Update `docs/api-spec.md` when endpoints change and `docs/database-schema.md` when schema changes.

## Web rules

- Components never call the API directly: component -> hook (TanStack Query / Zustand) -> `src/services/` (`apiRequests`) -> API. Server data lives in the TanStack Query cache, not in Zustand.
- Placement decision tree for a new component:
  - shadcn/Radix primitive or design-system binding: `src/components/ui/`
  - app shell (layout, header, sidebar): `src/components/layouts/`
  - third-party adapter (scroll, map): `src/components/wrappers/`
  - generic, reused by 2+ features: `src/modules/{name}/`
  - domain-specific: `src/features/{domain}/{feature}/components/`
  - used by exactly one page: `src/pages/{page}/parts/`
  - never put domain components directly under `src/components/`.
- Navigation is config-driven: menu entries live in `src/config/menu/*` (`APP_MENU`, `ADMINISTRATOR_MENU`) and layouts render from those arrays. A user-facing route and its menu entry are wired in the same change (skip only for explicitly hidden or redirect-only routes).
- Bounded scroll regions use `PerfectScrollArea` (`src/components/wrappers/PerfectScrollArea.tsx`), not raw `overflow-auto`.
- Use shadcn/Radix for dialogs, forms and other behaviour; keep the existing "Mist & Ink" tokens and classes. Tailwind classes only, `@/` import alias, icons via `renderIcon` (Phosphor).
- App shell regions (header, sidebar, main) must not overlap; reserve layout space instead of relying on z-index.
- Handle loading and error states for every async operation.

## Scope and data

The project runs as an MVP: a web app plus a real backend. Use the real database for validated data; mock data (kept inside the web project) only where data is not yet validated. Ask before introducing new backend services or stores that the stack above does not list.

## Git and docs

- Commits use **Conventional Commits**: `<type>(<scope>): <subject>` with type in `feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert`, lowercase scope, imperative lowercase subject of at most 72 characters and no trailing period. Optional body wrapped at 72; `BREAKING CHANGE:` footer or `!` for breaking changes. No `Co-Authored-By` or AI attribution lines.
- Add an entry to `changelog/backend.md`, `changelog/web.md` or `changelog/mcp.md` (follow the format at the top of each file) for user-visible changes.
- Update `docs/architecture.md` and `docs/api-spec.md` when behaviour or endpoints change.
- Tests are required for new behaviour. Keep existing tests green.

## Public repository hygiene

This repository is public. Never commit secrets, internal IPs or hostnames, or company names. Real values (embedding host, API keys, tokens) belong in the git-ignored `apps/backend/.env`, `apps/web/env/.env` and `apps/mcp/library/.env`; the `.env.example` files hold placeholders only.

## Architecture mindset

- The backend is the single source of truth for business rules, auth and data access.
- The RAG agent lives in the backend service layer (Agno + LiteLLM) and streams answers over SSE.
- MCP servers are thin and read-only by default.
- Build incrementally: each change ends runnable and covered by tests.
