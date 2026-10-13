import hashlib
import time
from datetime import datetime
from typing import Dict
import jwt
from jwt import InvalidTokenError

from dto import FindDTO
import secrets
from config.base import settings


def token_response(token: str, refresh_token: str, expired):
    return {
        "token": token,
        "refresh_token" : refresh_token,
        "expire": datetime.fromtimestamp(expired).strftime("%Y-%m-%dT%H:%M:%S.%f%z"),
    }


def sign_jwt(user_id: str, permissionID, multiLogin, **additional_payloads) -> Dict[str, str]:
    expired = time.time() + settings.JWT_EXPIRED
    payload = {"user_id": user_id, "permission_id": permissionID,"multiLogin" : multiLogin, "expire": expired}
    if len(additional_payloads) > 0:
        payload.update(additional_payloads)
    return base_sign_jwt(payload)

def base_sign_jwt(payload:dict):
    payload = payload.copy()
    # When the pair was minted: refresh tokens issued before a password change are refused (service/auth.py).
    payload["issued"] = time.time()

    # ACCESS TOKEN
    access_payload = payload.copy()
    access_payload["type"] = "access"
    access_payload["expire"] = time.time() + settings.JWT_EXPIRED

    access_token = jwt.encode(
        access_payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITH
    )

    # REFRESH TOKEN
    refresh_payload = payload.copy()
    refresh_payload["type"] = "refresh"
    refresh_payload["expire"] = time.time() + settings.JWT_REFRESH

    refresh_token = jwt.encode(
        refresh_payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITH
    )

    return token_response(
        access_token,
        refresh_token,
        access_payload["expire"]
    )   

def add_payload(token:str ,payload:dict)->str:
    decoded_payload = jwt.decode(token, settings.JWT_SECRET, algorithms=settings.JWT_ALGORITH)
    for key , value in payload.items():
        decoded_payload[key] = value

    token = jwt.encode(decoded_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITH)
    return token

def remove_payload(token:str , keys:list)->str:
    decoded_payload = jwt.decode(token, settings.JWT_SECRET, algorithms=settings.JWT_ALGORITH)
    for key in keys:
        decoded_payload.pop(key)

    token = jwt.encode(decoded_payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITH)
    return token

def create_otp() -> str:
    # Random per-request code. A TOTP derived from a fixed, source-visible seed
    # made every emailed OTP predictable.
    return f"{secrets.randbelow(1_000_000):06d}"

def create_token() -> str:
    return secrets.token_urlsafe(32)

def create_email_link_verification(domain: str, token: str) -> str:
    return f"https://{domain}/api/v1/apps/auth/verify-email?token={token}"


def revoked_token_key(token: str) -> str:
    """Redis key that marks a signed-out refresh token (set by /auth/logout, checked by JWTRefresh)."""
    return f"revoked-token:{hashlib.sha256(token.encode('utf-8')).hexdigest()}"


def decode_jwt(token: str, ignoreExpired: bool = False):
    try:
        decoded_token = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITH]
        )
        return decoded_token if decoded_token.get("expire", 0) >= time.time() or ignoreExpired == True else "Expired"
    except InvalidTokenError:
        return "Invalid"


def refresh():
    expired = time.time() + settings.JWT_EXPIRED
    payload = {"expire": expired}
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITH)

    return token_response(token, expired)

def replace_user_id(data, token):
    if data:
        data["id"] = token.get("user_id")
        if "userId" not in data:
            data["userId"] = token.get("user_id")
            data["permissionId"] = token.get("permission_id")
        return data        
    elif data is None:
        data = {
            "userId": token.get("user_id"),
            "permissionId": token.get("permission_id")
        }
        return data
    
def replace_created_by(data, token):
    if data:
        data["id"] = token.get("user_id")
        if "createdBy" not in data:
            data["createdBy"] = token.get("user_id")
        return data        
    elif data is None:
        data = {
            "createdBy": token.get("user_id")
        }
        
        return data

def add_user_filter(dto: dict, user_id: str):
    user_filter = {    
        "field": "userId",
        "operator": "is",
        "value": {
            "is": user_id
        }
    }
    filters = dto.get("filters", [])
    filters.append(user_filter)

    dto["filters"] = filters

    return dto


    
