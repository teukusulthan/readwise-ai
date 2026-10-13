import os
from loguru import logger
from time import time
from fastapi import APIRouter, HTTPException, Request, Depends, Query, Response
from auth.auth_bearer import JWTRefresh
from config.base import settings
from middleware.route_limits import route_limit
from util.helper import get_execution_time, is_include_schema, router_param_builder
from models.base_response import BaseResponseFailed, BaseResponse
from models.metadata import MetadataSuccess, MetadataFailed
from dto.auth import (
    AuthDTO,
    EmailOtpDTO,
    RequestChangeDTO,
    ChangePasswordOTPDTO,
    RegisterDTO,
    GoogleSSORequest,
    GenerateTwoFactorDTO,
    TwoFactorVerifyDTO,
    TwoFactorResendDTO,
)
from service.auth import Auth, AuthError, TwoFactorService
from dto.user import UserDTO

obj = Auth()
tag = os.path.splitext(os.path.basename(os.path.abspath(__file__)))[0]
router = APIRouter(**router_param_builder(tag, jwt=False))

def set_auth_cookies(response: Response, token: str, refresh_token: str):
    """HttpOnly session cookies. `Secure` follows BE_AUTH_COOKIE_SECURE (false only for plain-HTTP development)."""
    options = {"httponly": True, "secure": settings.AUTH_COOKIE_SECURE, "samesite": "lax"}
    response.set_cookie(key="token", value=token, max_age=settings.JWT_EXPIRED, **options)
    response.set_cookie(key="refresh_token", value=refresh_token, max_age=settings.JWT_REFRESH, **options)


def delete_auth_cookies(response: Response):
    options = {"httponly": True, "secure": settings.AUTH_COOKIE_SECURE, "samesite": "lax"}
    response.delete_cookie("refresh_token", **options)
    response.delete_cookie("token", **options)


REGISTRATION_CLOSED_MESSAGE = "Registration is closed."
GENERIC_ERROR_MESSAGE = "Something went wrong. Please try again later."

# Per-client budget (BE_RATE_LIMIT_AUTH_PER_MINUTE) for every endpoint that checks a password or a code or
# sends a mail: slows password guessing across accounts, code guessing and mail flooding.
AUTH_LIMIT = Depends(route_limit("auth"))

_FORBIDDEN_MESSAGES = [
    "User doesn't have login access",
    "Account has been expired",
    "Account has been deleted",
    "Account has been blocked",
]


def require_open_registration():
    """Registration endpoints answer 403 while BE_AUTH_REGISTRATION_OPEN=false."""
    if not settings.AUTH_REGISTRATION_OPEN:
        raise HTTPException(
            status_code=403,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(responseCode=403, message=REGISTRATION_CLOSED_MESSAGE)
            ).dict(),
        )


def public_message(error: Exception) -> str:
    """Refusals meant for the caller (AuthError) keep their message; anything else is logged, not shown."""
    return str(error) if isinstance(error, AuthError) else GENERIC_ERROR_MESSAGE


def failure(start_time: float, error: Exception, status_code: int = 400) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=BaseResponseFailed(
            metaData=MetadataFailed(
                executionTime=get_execution_time(start_time), message=public_message(error)
            )
        ).dict(),
    )


def google_oauth_configured() -> bool:
    """The /auth/google/* routes exist only when the Google OAuth client is configured."""
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


# Mounted onto `router` (below) only when google_oauth_configured(); otherwise /auth/google/* is a 404.
google_router = APIRouter()


@google_router.get("/google", dependencies=[AUTH_LIMIT])
async def auth_google(request: Request, redirect_uri: str):
    return await obj.oauth.google.authorize_redirect(request, redirect_uri=redirect_uri)


@google_router.post("/google/callback", dependencies=[AUTH_LIMIT])
async def google_callback(dto: GoogleSSORequest):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.login_by_google(dto),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)


@google_router.post("/google/token_exchange", dependencies=[AUTH_LIMIT])
async def google_exchange(token: str):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.google_exchange_and_get_token(token),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)


@google_router.post("/google/register", dependencies=[Depends(require_open_registration), AUTH_LIMIT])
async def google_register(dto: UserDTO):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.register_google(dto),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)


@router.post("/login", include_in_schema=is_include_schema(tag, "login"), dependencies=[AUTH_LIMIT])
def login(dto: AuthDTO, response: Response):
    start_time = time()

    try:
        data = obj.login(dto)
        auth = data.pop("auth")
        set_auth_cookies(response, auth.get("token"), auth.get("refresh_token"))

        return BaseResponse(
            data=data,
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        status_code = 403 if isinstance(error, AuthError) and str(error) in _FORBIDDEN_MESSAGES else 400
        raise failure(start_time, error, status_code)


@router.delete(
    "/logout",
    include_in_schema=is_include_schema(tag, "logout"),
    dependencies=[Depends(JWTRefresh())] if settings.JWT_ACTIVE else None,

)
def logout(request: Request, response: Response):
    start_time = time()
    try:
        # The access cookie may already have expired (only the refresh cookie is required): still log out.
        # The refresh token is revoked, so a copy of the cookie cannot start new sessions.
        refresh_token = request.cookies.get("refresh_token") or request.headers.get("Authorization")
        data = obj.logout(refresh_token)
        delete_auth_cookies(response)
        return BaseResponse(
            data=data,
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)


@router.get(
    "/validate",
    include_in_schema=is_include_schema(tag, "validate"),
    dependencies=[Depends(JWTRefresh())] if settings.JWT_ACTIVE else None,
)
def validate(request: Request, full_response: bool = Query(default=False)):
    start_time = time()
    try:
        token = request.headers.get("Authorization") or request.cookies.get("refresh_token")
        return BaseResponse(
            data=obj.validate(
                token, fullResponse=full_response
            ),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)


@router.get(
    "/refresh",
    include_in_schema=is_include_schema(tag, "refresh"),
    dependencies=[Depends(JWTRefresh())] if settings.JWT_ACTIVE else None,
)
def refresh(request: Request, response: Response):
    start_time = time()
    try:
        bearer = request.headers.get("Authorization")
        data = obj.refresh(bearer or request.cookies.get("refresh_token"))
        set_auth_cookies(response, data.get("token"), data.get("refresh_token"))
        
        return BaseResponse(
            data="Refresh Success",
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        # A refusal ends the session (the web client then goes to the login page).
        raise failure(start_time, error, 401 if isinstance(error, AuthError) else 400)


@router.post("/forgot-password/change", dependencies=[AUTH_LIMIT])
def change_password(dto: ChangePasswordOTPDTO):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.change_password_by_otp(dto),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)


@router.post("/forgot-password/request", dependencies=[AUTH_LIMIT])
def request_change_password(dto: RequestChangeDTO):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.request_change(dto=dto),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)


@router.post("/forgot-password/verify", dependencies=[AUTH_LIMIT])
def change_password_verify(dto: EmailOtpDTO):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.verity_otp(dto),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)


@router.post("/register", dependencies=[Depends(require_open_registration), AUTH_LIMIT])
def register(
    dto: RegisterDTO
):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.register(dto=dto),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)
    
@router.post("/verification", dependencies=[Depends(require_open_registration), AUTH_LIMIT])
def verification(dto: EmailOtpDTO):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.verify_register_otp(dto),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)
        
        
obj_2fa = TwoFactorService()        

@router.post(
    "/2fa/generate",
    include_in_schema=is_include_schema(tag, "generate_2fa_qr"),
    dependencies=[AUTH_LIMIT],
)
def generate_2fa_qr(dto: GenerateTwoFactorDTO): 
    start_time = time()
    try:
        result = obj_2fa.generate_2fa(dto)
        return BaseResponse(
            data=result,
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)



@router.post("/2fa/verify",
    include_in_schema=is_include_schema(tag, "verify_2fa"),
    dependencies=[AUTH_LIMIT],
    )
def verify_unified(dto: TwoFactorVerifyDTO):
    start_time = time()
    try:
        result = obj_2fa.verify_two_factor(dto)
        return BaseResponse(
            data=result,
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)

@router.post("/2fa/resend",
    include_in_schema=is_include_schema(tag, "resend_2fa"),
    dependencies=[AUTH_LIMIT],
    )
def resend_2fa(dto: TwoFactorResendDTO):
    start_time = time()
    try:
        result = obj_2fa.resend_2fa(dto)
        return BaseResponse(
            data=result,
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)

@router.post("/verify-email/request", dependencies=[AUTH_LIMIT])
def request_verify_email(
    dto: RequestChangeDTO, setting_id: str | None = Query(default=None, required=False)
):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.request_verify_email(setting_id=setting_id, dto=dto),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)
    
@router.get("/verify-email", dependencies=[AUTH_LIMIT])
def verify_email(token: str):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.verify_email(token=token),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise failure(start_time, error)
    


def mount_google_routes(target: APIRouter) -> bool:
    """Add the /google/* routes to `target` when Google OAuth is configured; True when mounted."""
    if not google_oauth_configured():
        return False
    target.include_router(google_router)
    return True


mount_google_routes(router)
