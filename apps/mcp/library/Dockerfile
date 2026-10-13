# syntax=docker/dockerfile:1.7
# Readwise AI library MCP server (HTTP transport). Build context: apps/mcp/library/
#   docker build -t readwise-mcp apps/mcp/library

FROM python:3.12.14-slim-bookworm AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM python:3.12.14-slim-bookworm AS runtime
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --create-home --home-dir /home/app app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8030

WORKDIR /app
COPY --from=build --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app server.py ./

USER 10001:10001
EXPOSE 8030

# The endpoint /mcp answers 401 without the bearer token, so probe the TCP port instead.
HEALTHCHECK --interval=15s --timeout=5s --start-period=15s --retries=5 \
    CMD ["python", "-c", "import socket,sys; socket.create_connection(('127.0.0.1', 8030), timeout=4).close()"]

# MCP_BEARER_TOKEN (>= 32 chars) is required: the server refuses to start without it.
CMD ["python", "server.py", "--transport", "http"]
