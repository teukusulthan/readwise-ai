"""
Who is calling: the principal behind a request.

    BE_JWT_ACTIVE=false  → every caller is the fixed owner "local" (no login; today's local setup).
    BE_JWT_ACTIVE=true   → `X-Internal-Token` equal to BE_INTERNAL_TOKEN → the service principal
                           "service:internal"; otherwise a valid access token (bearer header or the
                           HttpOnly `token` cookie, see JWTBearer) → the user, keyed by its `user_id` claim.

`current_principal` is the router-level auth dependency (util/helper.router_param_builder) and can
also be declared by an endpoint to get the principal: FastAPI caches it per request, so it runs once.

The book catalog, search and /chat/ask are shared by every principal. Conversations (and their chat
sessions) are personal: `require_user` refuses the service principal (403), and the conversation
layer scopes rows with `Principal.can_see` / `owner_id`. Rows created before accounts existed have
owner NULL ("legacy"): only "local" sees them, so they stay visible while auth is off and become
invisible to real users once BE_JWT_ACTIVE is turned on.
"""

import hmac
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request

from auth.auth_bearer import JWTBearer
from auth.auth_handler import decode_jwt
from config.base import settings

INTERNAL_TOKEN_HEADER = "X-Internal-Token"
SERVICE_SUBJECT = "service:internal"
LOCAL_SUBJECT = "local"


@dataclass(frozen=True)
class Principal:
    subject: str  # user id, "local" or "service:internal"
    kind: str     # "user" | "local" | "service"

    @property
    def is_service(self) -> bool:
        return self.kind == "service"

    @property
    def owner_id(self) -> str:
        """Value stored in `conversations.owner_id` for rows this principal creates."""
        return self.subject

    @property
    def sees_legacy(self) -> bool:
        """Whether rows without an owner (created before accounts existed) belong to this principal."""
        return self.kind == "local"

    def can_see(self, owner_id: Optional[str]) -> bool:
        return owner_id == self.subject or (owner_id is None and self.sees_legacy)


LOCAL = Principal(subject=LOCAL_SUBJECT, kind="local")
SERVICE = Principal(subject=SERVICE_SUBJECT, kind="service")


def internal_token_status(request: Request) -> Optional[bool]:
    """None: no `X-Internal-Token` header. True/False: whether it equals BE_INTERNAL_TOKEN (constant-time).
    Always False while BE_INTERNAL_TOKEN is empty (disabled)."""
    presented = request.headers.get(INTERNAL_TOKEN_HEADER)
    if presented is None:
        return None
    expected = settings.INTERNAL_TOKEN or ""
    if not expected:
        return False
    return hmac.compare_digest(presented.encode("utf-8"), expected.encode("utf-8"))


async def current_principal(request: Request) -> Principal:
    if not settings.JWT_ACTIVE:
        return LOCAL
    internal = internal_token_status(request)
    if internal is not None:
        # A presented-but-wrong service token is refused outright, never silently downgraded.
        if not internal:
            raise HTTPException(status_code=403, detail="Invalid internal token.")
        return SERVICE
    token = await JWTBearer()(request)  # 401 missing/expired, 403 invalid, refresh tokens refused
    payload = decode_jwt(token)
    user_id = payload.get("user_id") if isinstance(payload, dict) else None
    if not user_id:
        raise HTTPException(status_code=403, detail="Invalid token.")
    return Principal(subject=str(user_id), kind="user")


async def require_user(principal: Principal = Depends(current_principal)) -> Principal:
    """For personal data (conversations, chat sessions): the service principal has none."""
    if principal.is_service:
        raise HTTPException(status_code=403, detail="Service tokens have no conversations.")
    return principal
