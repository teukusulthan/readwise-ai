
import uvicorn
from fastapi import FastAPI
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from config.base import Setting
from config.routers import select_routers
import argparse
import os
import sys
import secrets

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import threading
import asyncio
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from loguru import logger

load_dotenv()

ROUTER_MODULES = {
    "health": "health",
    "auth": "auth",
    "group": "group",
    "permission": "permission",
    "role": "role",
    "upload": "upload",
    "user": "user",
    "book": "book",
    "search": "search",
    "chat": "chat",
    "conversation": "conversation",
}

# Source packages watched by the dev auto-reload (see uvicorn.run below).
RELOAD_DIRS = ["auth", "config", "dto", "exceptions", "middleware", "models", "router", "service", "util"]

def build_argument_parser():
    parser = argparse.ArgumentParser(
        description="Issue Cluster", formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-p", "--port", help="Port", metavar="", default="8020")
    parser.add_argument("-worker", "--worker", type=int, default=1)
    parser.add_argument(
        "-routers", "--routers", help="Include Routers", default=None
    )
    parser.add_argument("-uenv", "--update_env", default=None)
    parser.add_argument("-fenv", "--file_env", default=".env")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Dev only: restart on source changes (a restart kills running indexing jobs)",
    )
    return parser


argument_parser = build_argument_parser()
# parse_known_args: importing this module from pytest/uvicorn workers must not
# fail on their own CLI arguments.
args, _unknown_args = argument_parser.parse_known_args()

settings = Setting(file=args.file_env, update_env=args.update_env, routers=args.routers)

threadpool = ThreadPoolExecutor(
    thread_name_prefix="syncpool", max_workers=settings.MAX_THREADS_WORKERS
)


def _prepare_book_library():
    """Apply database migrations, then resume (or, at the attempt cap, fail) jobs a previous process left unfinished."""
    if not settings.POSTGRES_URI:
        logger.warning("BE_POSTGRES_URI is not set — book library endpoints are unavailable.")
        return
    try:
        from service import Services
        from service.ingestion import Ingestion
        from util.migrate import migrate

        migrate(Services.postgres())
        Ingestion().recover_interrupted()
    except Exception:
        logger.exception("Book library startup failed (is PostgreSQL running?)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.debug(
        f"setting up thread pool with {settings.MAX_THREADS_WORKERS} max threads workers"
    )
    loop = asyncio.get_running_loop()
    loop.set_default_executor(threadpool)
    await asyncio.to_thread(_prepare_book_library)
    yield
    # Stop answers still being generated so their partial text is saved as "stopped"
    # (readers see a "cancelled" event instead of waiting for a dead session).
    chat = sys.modules.get("router.chat")
    if chat is not None:
        await chat.sessions.shutdown()
    # Kill the Docling parse child without waiting for it (an interrupted job resumes at startup).
    ingestion = sys.modules.get("service.ingestion")
    if ingestion is not None:
        ingestion.shutdown()


    # logger.debug(f"Application Closed")
    # for producer in _producer_pool.values():
    #     producer.close()


from router.middleware import DecryptPayload
from middleware.body_limit import BodySizeLimitMiddleware
from middleware.rate_limiter import RateLimitMiddleware

app_args = {
    "title": "Readwise AI API",
    "description": "REST API for Readwise AI — book catalog, PDF indexing, semantic search and cited answers",
    "lifespan": lifespan,
}
app = FastAPI(**app_args)


def _session_secret() -> str:
    if settings.SESSION_SECRET:
        return settings.SESSION_SECRET
    logger.warning(
        "BE_SESSION_SECRET is not set — using a random per-process secret. "
        "OAuth sessions will not survive restarts or span multiple workers."
    )
    return secrets.token_hex(32)


def _cors_origins() -> list:
    return [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]


# Starlette runs the last-added middleware first, so the request passes through:
# CORS -> rate limit -> body size limit -> session -> decrypt -> routers.
app.add_middleware(DecryptPayload)
app.add_middleware(SessionMiddleware, secret_key=_session_secret())
app.add_middleware(
    BodySizeLimitMiddleware, max_bytes=settings.MAX_REQUEST_BODY_MB * 1024 * 1024
)
if settings.RATE_LIMIT_ACTIVE:
    app.add_middleware(RateLimitMiddleware)

_origins = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    # Browsers reject credentialed requests to a wildcard origin, and the web
    # app authenticates with cookies — so credentials only for explicit origins.
    allow_credentials="*" not in _origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def _envelope_http_exception_handler(request, exc):
    """Return envelope failures (`detail` = {metaData, ...}) as the top-level body.

    Plain-string/other details keep FastAPI's default `{"detail": ...}` shape.
    Covers FastAPI's HTTPException too (it subclasses Starlette's).
    """
    detail = exc.detail
    if isinstance(detail, dict) and "metaData" in detail:
        return JSONResponse(detail, status_code=exc.status_code, headers=getattr(exc, "headers", None))
    return await default_http_exception_handler(request, exc)


def _pool_threads(prefix="syncpool"):
    return [t for t in threading.enumerate() if t.name.startswith(prefix)]


def _queue_size(executor):
    # CPython detail: ThreadPoolExecutor._work_queue is a queue.SimpleQueue
    # Not guaranteed public API, but widely used for ops introspection
    q = getattr(executor, "_work_queue", None)
    try:
        return q.qsize() if q is not None else None
    except Exception:
        return None


def threadpool_stats():
    threads = _pool_threads()
    return {
        "max_workers": getattr(threadpool, "_max_workers", None),
        "current_threads": len(threads),
        # “active” is an estimate; see section 3 for precise tracking
        "active_threads_estimate": sum(1 for t in threads if t.is_alive()),
        "queue_size_best_effort": _queue_size(threadpool),
    }


selected_routers = select_routers(settings.ENABLED_ROUTERS, args.routers)
if "monitoring" in selected_routers:
    app.add_api_route("/monitoring/threadpool", threadpool_stats, methods=["GET"], tags=["monitoring"])
for router_name, module_name in ROUTER_MODULES.items():
    if router_name in selected_routers:
        module = __import__(f"router.{module_name}", fromlist=["router"])
        app.include_router(module.router)


def uvicorn_options() -> dict:
    return dict(
        host="0.0.0.0",
        port=int(args.port),
        workers=args.worker,
        # Off by default: the reloader kills running ingestions on any file change.
        reload=args.reload and args.worker == 1,
        # Watch app code only: a reload kills running indexing jobs, so editing tests/,
        # scripts/ or writing to storage/ must not restart the server.
        # (api.py itself is not watched — restart by hand after editing it.)
        reload_dirs=[d for d in RELOAD_DIRS if os.path.isdir(d)],
        # util/client_ip.py is the only reader of X-Forwarded-For (and only from BE_TRUSTED_PROXIES);
        # uvicorn's own proxy-header rewrite would let any loopback peer pick the client IP.
        proxy_headers=False,
    )


if __name__ == "__main__":
    uvicorn.run("api:app", **uvicorn_options())
