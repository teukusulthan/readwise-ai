import json

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.datastructures import MutableHeaders
from .auth_handler import decode_jwt, replace_created_by, replace_user_id, add_user_filter, revoked_token_key
from loguru import logger

from util import redis

def verify_jwt(jwt_token: str):
    payload = decode_jwt(jwt_token)

    if payload != "Invalid":
        return "Valid"
    return payload

class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(JWTBearer, self).__init__(auto_error=False)

    async def __call__(self, request: Request):

        token = None

        try:
            credentials: HTTPAuthorizationCredentials = await super().__call__(request)
            if credentials:
                if credentials.scheme != "Bearer":
                    raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
                token = credentials.credentials
        except Exception:
            pass

        if not token:
            token = request.cookies.get("token")

        if not token:
            raise HTTPException(status_code=401, detail="Authentication required.")

        payload = decode_jwt(token)

        if payload == "Invalid":
            raise HTTPException(status_code=403, detail="Invalid token.")

        if payload == "Expired":
            raise HTTPException(status_code=401, detail="Expired token.")

        # Refresh tokens live longer and must only be accepted by JWTRefresh.
        if payload.get("type") == "refresh":
            raise HTTPException(status_code=403, detail="Invalid token.")

        multiLogin = payload.get("multiLogin")

        if multiLogin is not None and not multiLogin:
            redis_client = redis.RedisService()
            stored_token = redis_client.get(f"session:{payload['user_id']}")

            if str(stored_token) != token:
                raise HTTPException(status_code=403, detail="Access Denied: Invalid session.")

        return token
# used in router auth.py
class JWTRefresh(HTTPBearer): 
    def __init__(self, auto_error: bool = True):
        super(JWTRefresh, self).__init__(auto_error=False)

    async def __call__(self, request: Request):

        token = None

        try:
            credentials: HTTPAuthorizationCredentials = await super().__call__(request)
            if credentials:
                if credentials.scheme != "Bearer":
                    raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
                token = credentials.credentials
        except Exception:
            pass

        if not token:
            token = request.cookies.get("refresh_token")

        if not token:
            raise HTTPException(status_code=401, detail="Authentication required.")

        payload = decode_jwt(token)

        if payload == "Invalid":
            raise HTTPException(status_code=403, detail="Invalid token.")

        if payload == "Expired":
            raise HTTPException(status_code=401, detail="Expired token.")

        # Only refresh tokens: an access token must not mint new sessions or outlive its own expiry here.
        if payload.get("type") != "refresh" or 'user_id' not in payload:
            raise HTTPException(status_code=403, detail="Invalid token")

        if redis.RedisService().exists(revoked_token_key(token)):
            raise HTTPException(status_code=401, detail="Session ended.")

        if request.query_params.get("full_response", None):
            payload["full_response"] = request.query_params.get("full_response")

        request._query_params = payload
        request._query_params.pop('expire', None)

        return token

class JWTChangeUserId:  # Note: No HTTPBearer inheritance
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(self, request: Request, token: str = Depends(JWTBearer())):
        token = None

        try:
            credentials: HTTPAuthorizationCredentials = await super().__call__(request)
            if credentials:
                if credentials.scheme != "Bearer":
                    raise HTTPException(status_code=403, detail="Invalid authentication scheme.")
                token = credentials.credentials
        except Exception:
            pass

        if not token:
            token = request.cookies.get("token")

        if not token:
            raise HTTPException(status_code=401, detail="Authentication required.")
    
        # Decode token once
        payload = decode_jwt(token)

        # Handle body
        if request.method in ["POST", "PUT", "UPDATE"]:
            try:
                original_body = await request.json()
                modified_body = replace_user_id(original_body, payload)
                body_bytes = json.dumps(modified_body).encode()

                request._json = modified_body
                request._body = body_bytes

            except json.JSONDecodeError as e:
                logger.warning("JSON decode error: {error}", error=str(e))
                raise HTTPException(status_code=400, detail="Invalid JSON body")
            except Exception as e:
                logger.warning("Error processing body: {error}", error=str(e))
                raise
        else:
            # print(payload)
            new_headers = MutableHeaders(request._headers)
            new_headers["permissionId"] = (
                payload.get("permission_id", None)
                if payload.get("permission_id", None)
                else ""
            )
            new_headers["userId"] = (
                payload.get("user_id", None) if payload.get("user_id", None) else ""
            )
            new_headers["p_id"] = "p_id"
            request._headers = new_headers
            request.scope.update(headers=request.headers.raw)

        # Handle query parameters
        if not request.query_params:
            modified_query = replace_user_id(None, payload)
            request._query_params = modified_query

        return payload

class JWTChangeCreatedBy:  # Note: No HTTPBearer inheritance
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(self, request: Request, token: str = Depends(JWTBearer())):
        # Decode token once
        payload = decode_jwt(token)

        if "Expired" in payload:
            raise HTTPException(status_code=400, detail="Token Expired")

        # Handle body
        if request.method != "GET":
            try:
                original_body = await request.json()
                modified_body = replace_created_by(original_body, payload)
                body_bytes = json.dumps(modified_body).encode()

                request._json = modified_body
                request._body = body_bytes

            except json.JSONDecodeError as e:
                logger.warning("JSON decode error: {error}", error=str(e))
                raise HTTPException(status_code=400, detail="Invalid JSON body")
            except Exception as e:
                logger.warning("Error processing body: {error}", error=str(e))
                raise

        # Handle query parameters
        if not request.query_params:
            modified_query = replace_created_by(None, payload)
            request._query_params = modified_query

        return payload


class JWTFilterUserIdBody:
    def __init__(self, auto_error: bool = True):
        self.auto_error = auto_error

    async def __call__(
        self, 
        request: Request,
        token: str = Depends(JWTBearer())
    ):
        try:
            payload = decode_jwt(token)
            user_id = payload.get("user_id")

            if not user_id:
                raise HTTPException(
                    status_code=400, 
                    detail="User ID not found in token"
                )

            original_body = await request.json()
            modified_dto = add_user_filter(original_body, user_id)

            request.state.find_dto = modified_dto
        except json.JSONDecodeError as e:
            logger.warning("JSON decode error: {error}", error=str(e))
            raise HTTPException(status_code=400, detail="Invalid JSON body")
        except Exception as e:
            logger.warning("Error processing body: {error}", error=str(e))
            raise HTTPException(status_code=400, detail="Error processing body")

        return payload

