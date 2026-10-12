from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class _BodyTooLarge(Exception):
    pass


class BodySizeLimitMiddleware:
    """
    Reject request bodies larger than `max_bytes` with HTTP 413.

    Checks the declared Content-Length up front and also counts streamed
    bytes, so chunked uploads without a Content-Length are capped too.
    Pure ASGI (not BaseHTTPMiddleware) so streaming responses such as SSE
    pass through untouched.
    """

    def __init__(self, app: ASGIApp, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        content_length = dict(scope.get("headers") or []).get(b"content-length")
        if content_length is not None:
            try:
                declared = int(content_length)
            except ValueError:
                await self._reject(scope, receive, send, 400, "Invalid Content-Length header.")
                return
            if declared > self.max_bytes:
                await self._reject(scope, receive, send, 413, "Request body too large.")
                return

        received = 0
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _BodyTooLarge()
            return message

        async def tracking_send(message: Message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _BodyTooLarge:
            if response_started:
                raise
            await self._reject(scope, receive, send, 413, "Request body too large.")

    @staticmethod
    async def _reject(scope: Scope, receive: Receive, send: Send, status: int, message: str):
        response = JSONResponse(status_code=status, content={"detail": message})
        await response(scope, receive, send)
