import os
from loguru import logger
from time import time
from fastapi import APIRouter, HTTPException, Request, Depends, Query, Response
from auth.auth_bearer import JWTRefresh
from config.base import settings
from util.helper import get_execution_time, is_include_schema, router_param_builder
from models.base_response import BaseResponseFailed, BaseResponse
from models.metadata import MetadataSuccess, MetadataFailed
from dto.auth import (
    AuthDTO,
    RequestChangeDTO,
    ChangePasswordOTPDTO,
    RegisterDTO,
    GoogleSSORequest,
    GenerateTwoFactorDTO,
    TwoFactorVerifyDTO,
    TwoFactorResendDTO,
)
from service.auth import Auth, TwoFactorService
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


_FORBIDDEN_MESSAGES = [
    "User doesn't have login access",
    "Account has been expired",
    "Account has been deleted",
    "Account has been blocked",
]


@router.get("/google")
async def auth_google(request: Request, redirect_uri: str):
    return await obj.oauth.google.authorize_redirect(request, redirect_uri=redirect_uri)


@router.post("/google/callback")
async def google_callback(dto: GoogleSSORequest):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.login_by_google(dto),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.post("/google/token_exchange")
async def google_exchange(token: str):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.google_exchange_and_get_token(token),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.post("/google/register")
async def google_register(dto: UserDTO):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.register_google(dto),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.post("/login", include_in_schema=is_include_schema(tag, "login"))
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
        status_code = 400
        error_message = str(error)
        if error_message in _FORBIDDEN_MESSAGES:
            status_code = 403

        raise HTTPException(
            status_code=status_code,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=error_message
                )
            ).dict(),
        )


@router.delete(
    "/logout",
    include_in_schema=is_include_schema(tag, "logout"),
    dependencies=[Depends(JWTRefresh())] if settings.JWT_ACTIVE else None,

)
def logout(request: Request, response: Response):
    start_time = time()
    try:
        # The access cookie may already have expired (only the refresh cookie is required): still log out.
        token = request.headers.get("Authorization") or request.cookies.get("token") or ""
        data = obj.logout(token)
        delete_auth_cookies(response)
        return BaseResponse(
            data=data,
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


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
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.get(
    "/refresh",
    include_in_schema=is_include_schema(tag, "refresh"),
    dependencies=[Depends(JWTRefresh())] if settings.JWT_ACTIVE else None,
)
def refresh(request: Request, response: Response):
    start_time = time()
    try:
        data = obj.refresh(
                request.cookies.get("refresh_token"),
                request.query_params.get("user_id", None),
                request.query_params.get("permission_id", None),
            )
        set_auth_cookies(response, data.get("token"), data.get("refresh_token"))
        
        return BaseResponse(
            data="Refresh Success",
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        if str(error) in [
            "No active session found for user",
            "Token expired more than 24 hours ago",
        ]:
            raise HTTPException(
                status_code=401,
                detail=BaseResponseFailed(
                    metaData=MetadataFailed(
                        executionTime=get_execution_time(start_time), message=str(error)
                    )
                ).dict(),
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=BaseResponseFailed(
                    metaData=MetadataFailed(
                        executionTime=get_execution_time(start_time), message=str(error)
                    )
                ).dict(),
            )


@router.post("/forgot-password/change")
def change_password(dto: ChangePasswordOTPDTO):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.change_password_by_otp(dto),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.post("/forgot-password/request")
def request_change_password(
    dto: RequestChangeDTO, setting_id: str | None = Query(default=None, required=False)
):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.request_change(setting_id=setting_id, dto=dto),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.post("/forgot-password/verify")
def change_password_verify(otp: str):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.verity_otp(otp),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.post("/register")
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
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )
    
@router.post("/verification")
def verification(otp: str):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.verify_register_otp(otp),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )
        
        
obj_2fa = TwoFactorService()        

@router.post(
    "/2fa/generate",
    include_in_schema=is_include_schema(tag, "generate_2fa_qr"),
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
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )



@router.post("/2fa/verify",
    include_in_schema=is_include_schema(tag, "verify_2fa"),
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
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )

@router.post("/2fa/resend",
    include_in_schema=is_include_schema(tag, "resend_2fa"),
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
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )

@router.post("/verify-email/request")
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
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )
    
@router.get("/verify-email")
def verify_email(token: str):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.verify_email(token=token),
            metaData=MetadataSuccess(executionTime=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    executionTime=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )
    