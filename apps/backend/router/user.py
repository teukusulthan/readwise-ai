import os
from loguru import logger
from time import time
from fastapi import APIRouter
from util.helper import get_execution_time, router_param_builder, is_include_schema
from models.base_response import BaseResponseFailed, BaseResponse
from fastapi import HTTPException, Depends
from auth.auth_bearer import JWTChangeUserId
from models.metadata import MetadataSuccess, MetadataFailed
from models.pagination import Pagination
from dto.user import (
    UserDTO,
    UpdateUserDTO,
    ResetPasswordDTO,
    FindUserDTO,
)
from service.user import User


obj = User()
tag = os.path.splitext(os.path.basename(os.path.abspath(__file__)))[0]
router = APIRouter(**router_param_builder(tag))

deps = router.dependencies


@router.post("/add", include_in_schema=is_include_schema(tag, "add"))
def add(dto: UserDTO):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.add(dto),
            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    execution_time=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.put("/update", include_in_schema=is_include_schema(tag, "update"))
def update(dto: UpdateUserDTO):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.update(dto),
            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)),
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    execution_time=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.delete("/delete", include_in_schema=is_include_schema(tag, "delete"))
def delete(id):
    start_time = time()
    try:
        return BaseResponse(
            data=obj.delete(id),
            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)),
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    execution_time=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.post("/get-all", include_in_schema=is_include_schema(tag, "get-all"))
def get_all(dto: FindUserDTO):
    start_time = time()
    try:
        data, count = obj.get_all(dto)
        return BaseResponse(
            data=data,
            metaData=MetadataSuccess(
                pagination=Pagination.count_total_pages(dto.size, count),
                execution_time=get_execution_time(start_time),
            ),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    execution_time=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.get("/get-one", include_in_schema=is_include_schema(tag, "get-one"))
def get_by_id(id: str):
    start_time = time()
    try:
        data = obj.get_one(id)
        return BaseResponse(
            data=data,
            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    execution_time=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.get("/check-email", include_in_schema=is_include_schema(tag, "check-email"))
def check_email(email: str):
    start_time = time()
    try:
        data = obj.check_unique(check_field="email", value=email)
        return BaseResponse(
            data=data,
            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    execution_time=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.get(
    "/check-username", include_in_schema=is_include_schema(tag, "check-username")
)
def check_username(username: str):
    start_time = time()
    try:
        data = obj.check_unique(check_field="username", value=username)
        return BaseResponse(
            data=data,
            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    execution_time=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.get("/check-phone", include_in_schema=is_include_schema(tag, "check-phone"))
def check_phone(phone: str):
    start_time = time()
    try:
        data = obj.check_unique(check_field="phone", value=phone)
        return BaseResponse(
            data=data,
            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    execution_time=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.post(
    "/reset-password", include_in_schema=is_include_schema(tag, "reset-password")
)
def reset_password(dto: ResetPasswordDTO):
    start_time = time()
    try:
        data = obj.reset_password(dto)
        return BaseResponse(
            data=data,
            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)),
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    execution_time=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )


@router.put(
    "/settings/update-profile",
    include_in_schema=is_include_schema(tag, "update-profile"),
    dependencies=[*deps, Depends(JWTChangeUserId())],
)
def update_profile(dto: UpdateUserDTO):
    start_time = time()
    try:
        data = obj.update_profile(dto)
        return BaseResponse(
            data=data,
            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)),
        )
    except Exception as error:
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    execution_time=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )

@router.get("/{username}", include_in_schema=is_include_schema(tag, "get-one"))
def get_by_id(username: str):
    start_time = time()
    try:
        data = obj.get_one_by_username(username)
        return BaseResponse(
            data=data,
            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)),
        )
    except Exception as error:
        logger.exception("Request failed")
        raise HTTPException(
            status_code=400,
            detail=BaseResponseFailed(
                metaData=MetadataFailed(
                    execution_time=get_execution_time(start_time), message=str(error)
                )
            ).dict(),
        )
