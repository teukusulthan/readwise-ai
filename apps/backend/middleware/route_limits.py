"""
Per-route rate limits (FastAPI dependencies), on top of the global per-IP limiter.

    @router.post("/query", dependencies=[Depends(route_limit("search"))])

A fixed one-minute window per (route group, client) in Redis. The client is the service principal when a
valid `X-Internal-Token` is present, else the authenticated user when a valid access token is present (so
users behind one proxy or NAT do not share a budget), else the client IP (util/client_ip.py). A budget of 0 disables the group. Over budget -> TooManyRequestsError -> HTTP 429 with
the error envelope and a Retry-After header. Fails open when Redis is unreachable, like the global limiter.
"""

import time
from typing import Callable

from fastapi import Request
from loguru import logger

from auth.auth_handler import decode_jwt
from auth.principal import SERVICE_SUBJECT, internal_token_status
from config.base import settings
from service import Services
from util.client_ip import client_ip
from util.http_errors import TooManyRequestsError, to_http_exception

WINDOW_SECONDS = 60

# route group -> name of the per-minute budget setting
BUDGETS = {
    "upload": "RATE_LIMIT_UPLOAD_PER_MINUTE",
    "chat": "RATE_LIMIT_CHAT_PER_MINUTE",
    "search": "RATE_LIMIT_SEARCH_PER_MINUTE",
}


def _token(request: Request):
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get("token")


def client_key(request: Request) -> str:
    """`service:internal` for a valid internal token, `user:<id>` for a valid access token (only while
    BE_JWT_ACTIVE), else `ip:<address>`. An invalid internal token is ignored here (the auth dependency
    refuses the request)."""
    if internal_token_status(request):
        return SERVICE_SUBJECT
    token = _token(request) if settings.JWT_ACTIVE else None  # unsigned-key tokens are forgeable when JWT is off
    if token:
        try:
            payload = decode_jwt(token)
        except Exception:
            payload = None
        if isinstance(payload, dict) and payload.get("type") != "refresh" and payload.get("user_id"):
            return f"user:{payload['user_id']}"
    return f"ip:{client_ip(request.scope)}"


def route_limit(group: str) -> Callable:
    setting_name = BUDGETS[group]

    async def dependency(request: Request):
        limit = int(getattr(settings, setting_name))
        if limit <= 0:
            return
        start_time = time.time()
        key = f"rate_limit:route:{group}:{client_key(request)}"
        try:
            pipe = Services.a_redis().pipeline()
            pipe.incr(key, 1)
            pipe.expire(key, WINDOW_SECONDS, nx=True)
            pipe.ttl(key)
            count, _, ttl = await pipe.execute()
        except Exception as error:
            logger.warning("Route rate limiter unavailable, failing open: {error}", error=type(error).__name__)
            return
        if int(count) > limit:
            raise to_http_exception(
                TooManyRequestsError("Too many requests, try again in a moment.",
                                     retry_after=ttl if ttl and ttl > 0 else WINDOW_SECONDS),
                start_time,
            )

    dependency.__name__ = f"route_limit_{group}"
    return dependency
