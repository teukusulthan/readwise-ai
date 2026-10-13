# Backend (FastAPI)

FastAPI service for the RAG Book Library. Entry point: `api.py`.

## Requirements

- [uv](https://docs.astral.sh/uv/) — manages Python 3.12, the virtualenv and dependencies
- `libmagic` system library (used by `python-magic` for upload MIME detection; `apt install libmagic1`)
- Backing services from the root `docker-compose.yml` (PostgreSQL, Qdrant, MongoDB, Redis)
- Network access to the company embedding service (`BE_ENGINE_EMBEDDING_BASE_URL`, TEI serving Qwen3-Embedding-0.6B; ask the team for the host)

## 1) Start backing services

From the repo root:

```bash
docker compose up -d
docker compose ps     # wait until every service is "healthy"
```

Postgres and Redis are published on host ports **5433** and **6380** (see the compose file) to avoid clashing with locally installed instances.

## 2) Install dependencies

```bash
cd apps/backend
uv sync               # creates .venv with Python 3.12 and installs pyproject.toml + uv.lock
```

Add a dependency with `uv add <package>` (or `uv add --dev <package>` for test tooling). Never `pip install` into the venv by hand — `pyproject.toml` + `uv.lock` are the source of truth.

## 3) Environment configuration (`.env`)

```bash
cp .env.example .env
```

- **Every key must carry the `BE_` prefix** (`BE_MONGO_URI`, `BE_JWT_SECRET`, …). Unprefixed keys are ignored with a warning.
- Code reads them unprefixed: `BE_MONGO_URI` → `settings.MONGO_URI` (`config/base.py`).
- Empty values for optional settings mean "unset".
- Accounts are off by default (`BE_JWT_ACTIVE=false`: no login, every caller is the owner "local"). To turn them on, set `BE_JWT_ACTIVE=true` with a `BE_JWT_SECRET` of at least 32 characters, together with the web's `VITE_AUTH_ENABLED=true`. Fill `BE_SESSION_SECRET` (`openssl rand -hex 32`, different from the JWT secret). `BE_ENC_SECRET` must be 16/24/32 characters if `BE_ENC_ACTIVE=true`.
- The `.env.example` defaults match the compose stack.

## 4) Run the API

Run through `api.py` — it parses CLI arguments and builds settings at import time, so don't use the `uvicorn api:app` CLI.

```bash
uv run python api.py --port 8020          # dev, auto-reload (single worker)
uv run python api.py --port 8020 --worker 4   # multi-worker, reload off
```

- Swagger UI: http://localhost:8020/docs
- Liveness: http://localhost:8020/health
- Readiness (pings every configured backing service): http://localhost:8020/health/ready

## 5) Tests

```bash
uv run pytest                    # unit tests (no services needed)
uv run pytest -m integration     # needs `docker compose up -d`
uv run pytest -m external        # calls the company embedding service (internal network)
```

`tests/conftest.py` sets throwaway `BE_*` values and runs from an empty temp dir, so your real `.env` is never loaded by tests.

## 6) CLI options

| Option | Default | Description |
|--------|---------|-------------|
| `-p`, `--port` | `8020` | HTTP port |
| `-worker`, `--worker` | `1` | Uvicorn worker count (reload auto-off when `> 1`) |
| `--routers` | `None` | Include specific routers (comma-separated) |
| `-uenv`, `--update_env` | `None` | Override env values: `"BE_KEY=VAL BE_KEY2=VAL2"` (the `BE_` prefix is optional here) |
| `-fenv`, `--file_env` | `.env` | Env file to load |

### Routers

`health` (always mounted), `auth`, `group`, `permission`, `role`, `upload`, `user`.

```bash
uv run python api.py --routers auth,user --port 8020
```

`BE_ENABLED_ROUTERS` (comma-separated) does the same from `.env`; empty = all.

## 7) HTTP hardening (settings)

| Setting | Default | Purpose |
|---------|---------|---------|
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed browser origins; credentials are allowed only for explicit origins |
| `SESSION_SECRET` | random per process (warns) | Session cookie secret for the Google OAuth flow |
| `MAX_REQUEST_BODY_MB` | `100` | Requests above this get HTTP 413 (checked on Content-Length and on streamed bytes) |
| `MAX_UPLOAD_SIZE_MB` | `100` | Per-file cap in the upload service |
| `RATE_LIMIT_ACTIVE` / `RATE_LIMIT` / `RATE_LIMIT_WINDOW` | `true` / `100000` / `60` | Per-IP fixed window in Redis; fails open if Redis is down |
| `ENC_ACTIVE` | `false` | AES request/response envelope (`hashedPayload`); applies to JSON bodies only |

## Troubleshooting

- `ValidationError` on start: a required `BE_*` key is missing or malformed in `.env`.
- `ModuleNotFoundError`: run `uv sync`.
- `.env` not applied: run from `apps/backend/` (the loader reads `.env` from the working directory).
- `Address already in use`: change `--port` or stop the other process.
- `/health/ready` returns 503: check `docker compose ps`; the response names the failing service.
