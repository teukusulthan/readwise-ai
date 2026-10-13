# RAG Book Library AI Assistant

An AI assistant for a personal/team book library: upload PDF books, extract → chunk → embed → index their content, search semantically across books, ask questions about one or many books, and receive **streaming answers with source citations**. Library capabilities are also exposed to other agents through an **MCP server**.

Built on the company's "Vibe Coding Base" boilerplate. The boilerplate's rules and skills (`.claude/`) are **guidelines** — this project adapts them to its own stack (see [`.claude/rules/architecture.md`](.claude/rules/architecture.md)).

---

## Stack

| Layer | Tech |
|-------|------|
| Backend | Python 3.12 + FastAPI (`apps/backend`, be-fastapi template), dependencies via **uv** |
| Relational DB | PostgreSQL 16 (`pgvector/pgvector:pg16` image) — books, chunks, processing status |
| Vector DB | Qdrant (pgvector is a later alternative behind a `VectorStore` interface) |
| Legacy stores | MongoDB + Redis — only for the boilerplate auth/user/group/permission/role/upload modules |
| Object storage | S3-compatible (local server TBD) |
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
library-rag/
├── .claude/          # Agent rules, skills, commands (guidelines for AI-assisted work)
├── apps/
│   ├── backend/      # FastAPI API (api.py entry, uv-managed)
│   ├── web/          # React + Vite web app
│   └── mcp/library/  # FastMCP server exposing the library to agents (stdio / HTTP)
├── docs/             # API spec + database schema registries
├── sprint/           # Sprint planning (sprint-builder)
├── brief/            # Project brief (brief-builder) — optional
├── changelog/        # Per-stack changelogs
└── nx/               # Nx runner (`npm run dev` starts backend + web)
```

The `.ai/` scaffolder and `design/` folder referenced by some generic skills are **not present** in this project.

---

## Running locally

**Prerequisites:** Docker, [uv](https://docs.astral.sh/uv/), Node 20+.

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

All ports bind to 127.0.0.1. Postgres and Redis use 5433/6380 on the host to avoid clashing with local installs (override with `POSTGRES_PORT` / `REDIS_PORT`).

**Object storage:** not in compose yet. MinIO stopped publishing community Docker images, so pick an S3-compatible store (or a local volume) before the book-upload phase. The backend already talks S3 through `util/s3_filesystem.py`.

---

## AI Agent System

Rules and skills are loaded on demand via `orchestra.md` files. Load order: `CLAUDE.md` / `AGENTS.md` → `.claude/rules/architecture.md` → domain orchestra (`.claude/skills/orchestra/`) → app `AI_GUIDE.md` → specific skills.

---

## License

MIT
