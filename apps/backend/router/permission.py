import os
from time import time
from fastapi import APIRouter, HTTPException
from util.helper import get_execution_time, router_param_builder, is_include_schema
from models.base_response import BaseResponseFailed, BaseResponse
from models.metadata import MetadataSuccess, MetadataFailed
from models.pagination import Pagination
from dto import FindDTO
from dto.permission import PermissionDTO, UpdatePermissionDTO
from service.permission import Permission

obj = Permission()
tag = os.path.splitext(os.path.basename(os.path.abspath(__file__)))[0]
router = APIRouter(**router_param_builder(tag))


@router.post("/add", include_in_schema=is_include_schema(tag, "add"))
def add(dto: PermissionDTO):
    start_time = time()
    try:
        return BaseResponse(data=obj.add(dto),
                            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)))
    except Exception as error:
        raise HTTPException(status_code=400, detail=BaseResponseFailed(
            metaData=MetadataFailed(execution_time=get_execution_time(start_time),
                                    message=str(error))).dict())


@router.put("/update", include_in_schema=is_include_schema(tag, "update"))
def update(dto: UpdatePermissionDTO):
    start_time = time()
    try:
        return BaseResponse(data=obj.update(dto),
                            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)))
    except Exception as error:
        raise HTTPException(status_code=400, detail=BaseResponseFailed(
            metaData=MetadataFailed(execution_time=get_execution_time(start_time),
                                    message=str(error))).dict())


@router.put("/update-partial", include_in_schema=is_include_schema(tag, "update"))
def update_partial(dto: UpdatePermissionDTO):
    start_time = time()
    try:
        return BaseResponse(data=obj.update_partial(dto),
                            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)))
    except Exception as error:
        raise HTTPException(status_code=400, detail=BaseResponseFailed(
            metaData=MetadataFailed(execution_time=get_execution_time(start_time),
                                    message=str(error))).dict())


@router.delete("/delete", include_in_schema=is_include_schema(tag, "delete"))
def delete(id):
    start_time = time()
    try:
        return BaseResponse(data=obj.delete(id),
                            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)))
    except Exception as error:
        raise HTTPException(status_code=400, detail=BaseResponseFailed(
            metaData=MetadataFailed(execution_time=get_execution_time(start_time),
                                    message=str(error))).dict())


@router.post("/get-all", include_in_schema=is_include_schema(tag, "get-all"))
def get_all(dto: FindDTO):
    start_time = time()
    try:
        data, count = obj.get_all(dto)
        return BaseResponse(data=data,
                            metaData=MetadataSuccess(pagination=Pagination.count_total_pages(dto.size, count),
                                                     execution_time=get_execution_time(start_time)))
    except Exception as error:
        raise HTTPException(status_code=400, detail=BaseResponseFailed(
            metaData=MetadataFailed(execution_time=get_execution_time(start_time),
                                    message=str(error))).dict())


@router.get("/get-one", include_in_schema=is_include_schema(tag, "get-one"))
def get_by_id(id: str):
    start_time = time()
    try:
        data = obj.get_by_id(id)
        return BaseResponse(data=data,
                            metaData=MetadataSuccess(execution_time=get_execution_time(start_time)))
    except Exception as error:
        raise HTTPException(status_code=400, detail=BaseResponseFailed(
            metaData=MetadataFailed(execution_time=get_execution_time(start_time),
                                    message=str(error))).dict())

