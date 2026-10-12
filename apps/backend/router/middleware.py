import json

from loguru import logger
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from config.base import settings
from util.aes_encryption import decrypt_aes_data

_ENCRYPTED_METHODS = {"POST", "PUT", "PATCH"}


class DecryptPayload:
    """
    When ENC_ACTIVE is on, JSON bodies of POST/PUT/PATCH requests must be
    `{"hashedPayload": "<AES ciphertext>"}`. The body is decrypted and replayed
    to the app as plain JSON. Non-JSON bodies (multipart uploads) and other
    methods pass through unchanged.

    Pure ASGI so streaming responses (SSE) are not buffered.
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if (
            scope["type"] != "http"
            or not settings.ENC_ACTIVE
            or scope["method"] not in _ENCRYPTED_METHODS
            or not self._is_json(scope)
        ):
            await self.app(scope, receive, send)
            return

        body = await self._read_body(receive)
        try:
            payload = json.loads(body or b"{}")
            if not isinstance(payload, dict) or "hashedPayload" not in payload:
                raise ValueError("invalid requests")
            decrypted = decrypt_aes_data(payload["hashedPayload"])
            if decrypted is None:
                raise ValueError("Failed to decrypt payload")
            decrypted_bytes = decrypted.encode("utf-8")
        except Exception as error:
            logger.warning("Rejected encrypted payload: {error}", error=type(error).__name__)
            response = JSONResponse(status_code=400, content={"error": "Failed to decrypt payload"})
            await response(scope, receive, send)
            return

        headers = [(k, v) for k, v in scope["headers"] if k != b"content-length"]
        headers.append((b"content-length", str(len(decrypted_bytes)).encode()))
        scope = {**scope, "headers": headers}

        sent = False

        async def replay_receive() -> Message:
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": decrypted_bytes, "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send)

    @staticmethod
    def _is_json(scope: Scope) -> bool:
        content_type = dict(scope.get("headers") or []).get(b"content-type", b"")
        return content_type.split(b";")[0].strip().lower() == b"application/json"

    @staticmethod
    async def _read_body(receive: Receive) -> bytes:
        chunks = []
        while True:
            message = await receive()
            if message["type"] != "http.request":
                break
            chunks.append(message.get("body", b""))
            if not message.get("more_body", False):
                break
        return b"".join(chunks)
