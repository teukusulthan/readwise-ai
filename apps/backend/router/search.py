import os
from time import time

from fastapi import APIRouter

from dto.search import SearchQueryDTO
from models.base_response import BaseResponse
from models.metadata import MetadataSuccess
from service.search import Search
from util.helper import get_execution_time, is_include_schema, router_param_builder
from util.http_errors import to_http_exception

obj = Search()

tag = os.path.splitext(os.path.basename(os.path.abspath(__file__)))[0]
router = APIRouter(**router_param_builder(tag))


@router.post("/query", include_in_schema=is_include_schema(tag, "query"))
def query(dto: SearchQueryDTO):
    """Semantic search over indexed books. Returns matching passages with page/section references."""
    start_time = time()
    try:
        return BaseResponse(data=obj.query(dto), metaData=MetadataSuccess(executionTime=get_execution_time(start_time)))
    except Exception as error:
        raise to_http_exception(error, start_time)
