# AI Agent Guide — Backend (Python/FastAPI)

Quick start guide for AI agents working with this boilerplate.

## 🚀 First Time Setup

Read these files **every time before writing any code**, in order:

1. **This file** (`AI_GUIDE.md`) — Quick start and navigation
2. **`skills/fastapi-api-design/SKILL.md`** — Endpoint pattern, DTOs, BaseResponse, pagination, error handling
3. **`skills/fastapi-data/SKILL.md`** — Service layer, `BaseMongoRepository`, MongoDB/Redis access
4. **`skills/fastapi-file-naming/SKILL.md`** — File/module naming and new-module registration

Then load additional skill(s) per task (see Documentation Map below).

## 📖 Documentation Map
| File | Purpose | Load When |
|------|---------|-----------|
| **`skills/fastapi-api-design/SKILL.md`** | Endpoints, DTOs, BaseResponse envelope, pagination, error handling, AES encryption | Adding/changing an endpoint or response shape |
| **`skills/fastapi-auth/SKILL.md`** | JWT bearer auth, RBAC, password hashing, session/single-login, ownership scoping | Implementing auth, guarding routes, permissions |
| **`skills/fastapi-data/SKILL.md`** | Service layer, `BaseMongoRepository`, `Services` factory, `mongo_query_builder` | Creating services, querying MongoDB, business logic |
| **`skills/fastapi-config/SKILL.md`** | Settings (`BaseSetting`), app startup, middleware (decrypt, rate limit, CORS) | Adding env vars, changing startup, middleware |
| **`skills/fastapi-async-performance/SKILL.md`** | Async/blocking calls, `asyncio.to_thread`, threadpool | Slow endpoints, mixing `def`/`async def`, blocking I/O |
| **`skills/fastapi-logging/SKILL.md`** | `loguru` usage, PII masking (`censor_email`), forbidden `print()` | Adding logs, debugging with safe logging |
| **`skills/fastapi-file-naming/SKILL.md`** | File/module naming rules, new-module registration | Creating/renaming files or adding new modules |
| **`skills/fastapi-dependency-constraints/SKILL.md`** | Rules for adding dependencies in be-fastapi boilerplate | Adding a new Python dependency |
| **`skills/fastapi-virtual-environment/SKILL.md`** | Virtual environment setup + dependency installation | Setting up venv, installing packages |

### Project Docs

| File | Purpose | When to Read |
|------|---------|--------------|
| **`docs/api-spec.md`** | Endpoint registry | Any API work |
| **`docs/database-schema.md`** | Schema registry | DB / schema work |

## 🚨 Critical Rules Summary

### 🔴 MOST IMPORTANT: Layer Boundary

**NEVER access DB directly from a router — always go through service layer!**

- ✅ Router → Service → repository / `Services.*()` client (this order, always)
- ✅ Business logic in `service/` only
- ✅ Thin routers — no logic, just call service and return response
- ❌ **NEVER query MongoDB, PostgreSQL or Qdrant from `router/`**
- ❌ **NEVER put business logic in `router/`**
- ❌ **NEVER skip `BaseResponse` wrapper** (exceptions: SSE streams and `/health`)

### API Conventions
- ✅ List endpoints: `POST /{resource}/get-all` with `FindDTO` body
- ✅ Delete: `DELETE /{resource}/delete?id=` (query param, not path)
- ✅ Update: `PUT /{resource}/update` with full object in body (includes `id`)
- ✅ Wrap success: `BaseResponse(metaData=MetadataSuccess(execution_time=...))`
- ✅ Wrap failure: `HTTPException(detail=BaseResponseFailed(...).dict())`
- ✅ Paginate: `Pagination.count_total_pages(dto.size, count)`
- ⚠️ **NEVER use `GET` for list endpoints with filters**
- ⚠️ **NEVER put `id` in URL path for update/delete**

### Tech Stack
- 📦 Python 3.12 · FastAPI · Pydantic v2 · psycopg 3 (PostgreSQL) · qdrant-client · PyMongo + Redis (legacy modules) · Loguru · PyJWT · bcrypt · pycryptodome
- ✅ Dependencies are managed with **uv** (`pyproject.toml` + `uv.lock`): check `pyproject.toml` first, add with `uv add <pkg>` / `uv add --dev <pkg>`
- ✅ New domain data (books, chunks, status) → PostgreSQL; vectors → Qdrant; MongoDB is for the existing boilerplate modules only
- ✅ Full stack and policy: `.claude/rules/architecture.md`

### Logging
- ✅ Use `loguru.logger` for all logging
- ❌ **NEVER use `print()`** — not even for debugging

### Data Store Conventions
- ✅ PostgreSQL: `Services.postgres()` returns a psycopg `ConnectionPool` — `with Services.postgres().connection() as conn:`; parameterized SQL only, migrations in `migrations/*.sql`
- ✅ Qdrant: `Services.qdrant()` returns the shared `QdrantClient`
- ✅ Embeddings: `Services.embedding().embed_documents(texts)` / `.embed_query(text)` — never call the embedding HTTP API directly; vectors are 1024-dim, normalised (cosine)

### MongoDB Conventions (legacy modules)
- ✅ Services inherit `BaseMongoRepository` — never ad-hoc `pymongo.MongoClient()`
- ✅ Use `Services.mongo()` / `Services.redis()` factory — never create clients directly
- ✅ Collection names from `settings.MONGO_COLLECTION_*` — never hardcode
- ✅ Convert `_id` → `id` before returning to API consumers
- ✅ Mask sensitive fields: `data["password"] = "##########"`, `censor_email(data["email"])`

## 🎯 Quick Decision Guide

### What type of task is this?

```
New endpoint needed?
├─ Simple CRUD
│   ├─ Create   → POST /{resource}/add       + {Resource}DTO
│   ├─ Update   → PUT  /{resource}/update    + Update{Resource}DTO
│   ├─ Delete   → DELETE /{resource}/delete  + ?id=
│   ├─ Get one  → GET  /{resource}/get-one   + ?id=
│   └─ Get all  → POST /{resource}/get-all   + FindDTO body
│
└─ Custom action → POST/GET /{resource}/{action}
                   (e.g. /auth/refresh, /user/reset-password)
```

### New module or existing?

```
Adding feature to existing module?
├─ YES → modify dto/{module}.py, service/{module}.py, router/{module}.py
└─ NO  → create all 3 files + register in api.py (see checklist below)
```

## 📋 Code Generation Workflow

1. ✅ Check `docs/api-spec.md` — does the endpoint already exist?
2. ✅ Check `docs/database-schema.md` — does the collection exist?
3. ✅ Load `skills/orchestra.md` — pick relevant skill files
4. ✅ Create/update DTO in `dto/{module}.py`
5. ✅ Create/update service in `service/{module}.py` (extend `BaseMongoRepository`)
6. ✅ Create/update router in `router/{module}.py`
7. ✅ Register in `api.py` (`ROUTER_MODULES`) if new module; add it to `LIBRARY_ROUTERS` in `config/routers.py` if it should mount by default
8. ✅ Update `docs/api-spec.md` endpoint registry
9. ✅ Update `docs/database-schema.md` if schema changed

## 📁 File Locations

```
.
├── api.py                  → App entry point, ROUTER_MODULES, middleware, uvicorn
├── pyproject.toml          → Dependencies (uv) — check before adding anything
├── uv.lock                 → Locked dependency versions (commit it)
├── docker-compose.yml      → (repo root) PostgreSQL, Qdrant, MongoDB, Redis
├── auth/
│   ├── auth_bearer.py      → JWTBearer, JWTRefresh, JWTChangeUserId, etc.
│   └── auth_handler.py     → sign_jwt, decode_jwt, password hashing
├── config/
│   └── base.py             → BaseSetting (Pydantic v1), all env vars
├── dto/
│   ├── __init__.py         → BaseFindDTO, FindDTO (shared pagination/filter)
│   ├── auth.py
│   ├── user.py
│   └── {module}.py         → Add new DTOs here
├── exceptions/
│   └── fusion_exceptions.py → FusionBaseException hierarchy
├── middleware/
│   ├── body_limit.py       → Request body size cap (HTTP 413), pure ASGI
│   └── rate_limiter.py     → Redis-backed per-IP rate limit (fails open), pure ASGI
├── models/
│   ├── base_response.py    → BaseResponse, BaseResponseFailed (AES auto-encrypt)
│   ├── metadata.py         → MetadataSuccess, MetadataFailed
│   └── pagination.py       → Pagination (size, totalElements, totalPages)
├── router/
│   ├── auth.py
│   ├── health.py           → GET /health (liveness), GET /health/ready (dependency checks)
│   ├── middleware.py       → DecryptPayload (AES request decryption, pure ASGI)
│   ├── user.py
│   └── {module}.py         → Add new routers here
├── service/
│   ├── __init__.py         → BaseMongoRepository, Services factory, change_field_id
│   ├── auth.py
│   ├── user.py
│   └── {module}.py         → Add new services here
└── util/
    ├── aes_encryption.py   → encrypt_aes_data, decrypt_aes_data
    ├── helper.py           → mongo_query_builder, router_param_builder, censor_email
    ├── mongo.py            → MongoService (PyMongo singleton)
    ├── embedding.py        → EmbeddingClient + EmbeddingService singleton (company TEI, batching, retries, dim check)
    ├── document_parser.py  → Docling PDF conversion + HybridChunker → chunk dicts
    ├── storage.py          → Streaming local PDF storage (sha256, magic bytes, size cap)
    ├── migrate.py          → SQL migration runner (`uv run python -m util.migrate`)
    ├── http_errors.py      → Exception → HTTP status mapping (400/404/409/503/500)
    ├── postgres.py         → PostgresService (psycopg_pool ConnectionPool singleton)
    ├── qdrant.py           → QdrantService (QdrantClient singleton)
    └── redis.py            → RedisService, AsyncRedisService

migrations/               → Numbered PostgreSQL migrations (001_create_books.sql)
storage/books/           → Uploaded PDFs (git-ignored)

Book library modules (see docs/architecture.md §5):
  dto/book.py, dto/search.py, dto/chat.py
  router/book.py, router/search.py, router/chat.py
  service/book.py, book_repository.py, ingestion.py, vector_store.py, search.py, rag.py, llm.py, openlibrary.py

tests/
├── conftest.py             → Test env (BE_* values, isolated cwd), imports api
├── unit/                   → No external services needed
├── integration/            → `-m integration`, needs docker compose
└── external/               → `-m external`, calls the company embedding service
```

## ⚠️ Common Mistakes to Avoid

1. ❌ **DB access in router** — always via service layer
2. ❌ **Business logic in router** — belongs in service
3. ❌ **Raw `dict` return** — always use `BaseResponse`
4. ❌ **Missing `execution_time`** in response metadata
5. ❌ **`print()` for logging** — use `loguru.logger`
6. ❌ **Hardcoded secrets or connection strings** — use `config/base.py`
7. ❌ **`GET /{resource}/get-all`** — must be `POST` with `FindDTO`
8. ❌ **Returning `_id` field** — always convert to `id`
9. ❌ **Leaking password hashes** — mask with `"##########"`
10. ❌ **Ad-hoc MongoDB/Redis clients** — use `Services.mongo()` / `Services.redis()`
11. ❌ **New package without checking `pyproject.toml`** — add with `uv add`, never `pip install`
12. ❌ **Skip `docs/api-spec.md` update** — always update after adding endpoint

## 💡 Pro Tips

1. **Check `docs/api-spec.md` first** — endpoint may already exist
2. **Read `models/base_response.py`** — understand the response envelope before writing any endpoint
3. **Extend `BaseMongoRepository`** in service — don't write raw DB queries
4. **Use `mongo_query_builder(dto, text_type="...")`** for list queries
5. **Use `router_param_builder(tag)`** — consistent router setup with JWT protection
6. **Use `change_field_id(data)`** — converts `_id` → `id` on reads
7. **`config/base.py` is the single source of truth** for env config — env-file keys carry the `BE_` prefix (`BE_MONGO_URI`), `BaseSetting` fields and app code do not (`settings.MONGO_URI`)
8. **AES encryption is automatic** — `BaseResponse.model_dump()` handles it when `ENC_ACTIVE=True`

## 📞 Quick Commands

```bash
# Run the server (--reload = dev auto-restart on source changes; off by default because a
# restart kills running ingestions)
uv run python api.py --port 8020
uv run python api.py --port 8020 --reload

# Run with specific routers (an explicit list is how legacy routers are opted into)
uv run python api.py --routers auth,user[get-all:get-one]
# Empty BE_ENABLED_ROUTERS = safe default: health, auth, book, search, chat, conversation.
# user, role, group, permission, upload and "monitoring" (/monitoring/threadpool) mount only when listed.

# Run tests
uv run pytest
uv run pytest -m integration   # needs `docker compose up -d`
uv run pytest -m external      # needs the company embedding service

# Check existing API contracts
cat docs/api-spec.md

# Check DB schema
cat docs/database-schema.md

# Check installed dependencies
cat pyproject.toml

# Check existing DTOs
ls dto/

# Check existing services
ls service/

# Check router registration
cat api.py
```

## ✅ Success Checklist

Your generated code is good if:

- [ ] Router calls service — no DB access in router
- [ ] Service extends `BaseMongoRepository`
- [ ] DTO defined: `{Resource}DTO`, `Update{Resource}DTO`, `Find{Resource}DTO`
- [ ] `BaseResponse` used for all success responses
- [ ] `BaseResponseFailed` used for all error responses
- [ ] `execution_time` included in both success and failure metadata
- [ ] `loguru.logger` used — no `print()`
- [ ] Env vars via `config/base.py` — no hardcoded values
- [ ] New env keys added to `.env` / `.env.example` with the `BE_` prefix
- [ ] New router registered in `api.py` (`ROUTER_MODULES`)
- [ ] Collection name added to `config/base.py` (`MONGO_COLLECTION_*`)
- [ ] `_id` converted to `id` before returning
- [ ] Passwords masked with `"##########"` in responses
- [ ] `docs/api-spec.md` endpoint registry updated
- [ ] Auth: `JWTBearer` dependency on protected routes (default via `router_param_builder`)
- [ ] List endpoint uses `POST` + `FindDTO` body + `Pagination.count_total_pages()`
- [ ] Delete endpoint uses `?id=` query param
