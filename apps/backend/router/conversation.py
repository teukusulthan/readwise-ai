import os
from time import time
from typing import Optional

from fastapi import APIRouter, Query

from dto.conversation import RenameConversationDTO
from models.base_response import BaseResponse
from models.metadata import MetadataSuccess
from models.pagination import Pagination
from service.conversation import Conversation
from util.helper import get_execution_time, is_include_schema, router_param_builder
from util.http_errors import to_http_exception

obj = Conversation()

tag = os.path.splitext(os.path.basename(os.path.abspath(__file__)))[0]
router = APIRouter(**router_param_builder(tag))


def _ok(data, start_time, pagination: Optional[Pagination] = None):
    meta = MetadataSuccess(executionTime=get_execution_time(start_time))
    if pagination:
        meta.pagination = pagination
    return BaseResponse(data=data, metaData=meta)


@router.get("/get-all", include_in_schema=is_include_schema(tag, "get-all"))
def get_all(page: int = Query(default=1, ge=1), size: int = Query(default=50, ge=1, le=100)):
    """Saved conversations, most recently active first. New ones are created by POST /chat/stream."""
    start_time = time()
    try:
        data, count = obj.get_all(page, size)
        return _ok(data, start_time, Pagination.count_total_pages(size, count))
    except Exception as error:
        raise to_http_exception(error, start_time)


@router.get("/get-one", include_in_schema=is_include_schema(tag, "get-one"))
def get_by_id(id: str):
    """One conversation with every message (assistant messages include their sources)."""
    start_time = time()
    try:
        return _ok(obj.get_by_id(id), start_time)
    except Exception as error:
        raise to_http_exception(error, start_time)


@router.put("/rename", include_in_schema=is_include_schema(tag, "rename"))
def rename(dto: RenameConversationDTO):
    start_time = time()
    try:
        return _ok(obj.rename(dto), start_time)
    except Exception as error:
        raise to_http_exception(error, start_time)


@router.delete("/delete", include_in_schema=is_include_schema(tag, "delete"))
def delete(id: str):
    """Delete the conversation and all its messages."""
    start_time = time()
    try:
        return _ok(obj.delete(id), start_time)
    except Exception as error:
        raise to_http_exception(error, start_time)
