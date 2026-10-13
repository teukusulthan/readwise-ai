# syntax=docker/dockerfile:1.7
# Readwise AI backend (FastAPI + Docling). Build context: apps/backend/
#   docker build -t readwise-backend apps/backend

# ---- build: resolve the locked dependencies into /app/.venv ----------------
FROM python:3.12-slim-bookworm AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app

# Dependencies first so source edits do not invalidate this layer. pyproject.toml pins torch and
# torchvision to the CPU-only index, so no CUDA wheels end up in the image.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---- runtime ---------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

# libmagic1: python-magic (upload type sniffing). libgomp1 / libglib2.0-0: OpenMP and glib used by
# torch, onnxruntime and opencv (headless build, so no libGL).
# hadolint ignore=DL3008
RUN apt-get update \
    && apt-get install -y --no-install-recommends libmagic1 libgomp1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home --home-dir /home/app app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/home/app/.cache/huggingface

WORKDIR /app
COPY --from=build --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app . .

# Mount points owned by the app user, so named volumes start out writable:
#   /app/storage            uploaded PDFs (BE_BOOK_STORAGE_DIR, default storage/books)
#   /home/app/.cache/huggingface   tokenizer + Docling model downloads (first parse downloads them)
RUN mkdir -p /app/storage/books /home/app/.cache/huggingface \
    && chown -R app:app /app/storage /home/app/.cache
VOLUME ["/app/storage", "/home/app/.cache/huggingface"]

USER 10001:10001
EXPOSE 8020

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8020/health', timeout=4).status == 200 else 1)"]

# One worker only: startup recovery of interrupted ingestion jobs assumes a single process.
# No --reload (dev only). The venv is already synced, so run its python directly (api.py parses
# argparse at import; never start it as `uvicorn api:app`).
CMD ["python", "api.py", "--port", "8020", "--worker", "1"]
