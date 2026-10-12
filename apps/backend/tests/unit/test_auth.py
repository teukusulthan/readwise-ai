import time

import httpx
import jwt
import pytest
from fastapi import Depends, FastAPI

from auth.auth_bearer import JWTBearer
from auth.auth_handler import base_sign_jwt, create_otp

# The token that auth_bearer.py used to accept without verification.
FORMER_BYPASS_TOKEN = (
    "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9."
    "eyJ1c2VyX2lkIjoiN2ZjZGYwOTgyNDY0ZTIyNGRkZjc4YjE4NTE5ZjNjNTEiLCJleHBpcmUiOjE3NDA2MDcyOTEuMzY5NjE4NH0."
    "7RhnmP89eVgwbCx4BfhalzzzCPeXjmBRP5mE17CGvQY"
)


@pytest.fixture
def protected_client():
    app = FastAPI()

    @app.get("/protected", dependencies=[Depends(JWTBearer())])
    def protected():
        return {"ok": True}

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_missing_token_is_rejected(protected_client):
    resp = await protected_client.get("/protected")
    assert resp.status_code == 401


async def test_former_hardcoded_token_is_rejected(protected_client):
    resp = await protected_client.get("/protected", headers={"Authorization": f"Bearer {FORMER_BYPASS_TOKEN}"})
    assert resp.status_code == 403


async def test_forged_token_is_rejected(protected_client):
    forged = jwt.encode({"user_id": "x", "expire": time.time() + 60}, "wrong-secret", algorithm="HS256")
    resp = await protected_client.get("/protected", headers={"Authorization": f"Bearer {forged}"})
    assert resp.status_code == 403


async def test_valid_access_token_is_accepted(protected_client):
    tokens = base_sign_jwt({"user_id": "user-1"})
    resp = await protected_client.get("/protected", headers={"Authorization": f"Bearer {tokens['token']}"})
    assert resp.status_code == 200


async def test_refresh_token_is_not_an_access_token(protected_client):
    tokens = base_sign_jwt({"user_id": "user-1"})
    resp = await protected_client.get("/protected", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert resp.status_code == 403


async def test_token_without_expire_claim_is_rejected_not_500(protected_client, settings):
    token = jwt.encode({"user_id": "x"}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITH)
    resp = await protected_client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_otp_is_six_digits_and_not_predictable():
    codes = {create_otp() for _ in range(50)}
    assert all(len(code) == 6 and code.isdigit() for code in codes)
    # A fixed-seed TOTP would return one code for the whole 30 s window.
    assert len(codes) > 1
