from loguru import logger
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from config.base import settings
from service import Services
from util.client_ip import client_ip

_EXEMPT_PATHS = {"/health"}


class RateLimitMiddleware:
    """
    Fixed-window, per-client-IP rate limit (client IP: util/client_ip.py) backed by Redis.

    Fails open: if Redis is unreachable the request is served and a warning is
    logged, so a Redis outage degrades protection instead of taking the API down.
    Pure ASGI so streaming responses (SSE) are not buffered.
    """

    def __init__(self, app: ASGIApp):
        self.app = app
        self.redis = Services.a_redis()
        self.rate_limit = settings.RATE_LIMIT
        self.window = settings.RATE_LIMIT_WINDOW

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http" or scope["path"] in _EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        key = f"rate_limit:{client_ip(scope)}"

        try:
            pipe = self.redis.pipeline()
            pipe.incr(key, 1)
            pipe.expire(key, self.window, nx=True)
            count, _ = await pipe.execute()
        except Exception as error:
            logger.warning("Rate limiter unavailable, failing open: {error}", error=type(error).__name__)
            await self.app(scope, receive, send)
            return

        if int(count) > self.rate_limit:
            response = JSONResponse(status_code=429, content={"detail": "Too many requests"})
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
