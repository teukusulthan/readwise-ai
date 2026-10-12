"""
Map service exceptions to HTTP errors in the standard BaseResponseFailed envelope.

    LookupError                         -> 404  (not found)
    DuplicateBookError / ConflictError  -> 409  (already exists / wrong state)
    ValueError                          -> 400  (bad input)
    ServiceUnavailableError             -> 503  (dependency down / not configured)
    anything else                       -> 500  (logged; generic message, no internals leaked)
"""

from fastapi import HTTPException
from loguru import logger

from models.base_response import BaseResponseFailed
from models.metadata import MetadataFailed
from util.helper import get_execution_time


class ConflictError(Exception):
    pass


class ServiceUnavailableError(Exception):
    pass


def to_http_exception(error: Exception, start_time: float) -> HTTPException:
    from service.book_repository import DuplicateBookError

    if isinstance(error, LookupError):
        status, message = 404, str(error)
    elif isinstance(error, (DuplicateBookError, ConflictError)):
        status, message = 409, str(error)
    elif isinstance(error, ValueError):
        status, message = 400, str(error)
    elif isinstance(error, ServiceUnavailableError):
        status, message = 503, str(error)
    else:
        logger.exception("Unhandled error")
        status, message = 500, "Internal server error."

    return HTTPException(
        status_code=status,
        detail=BaseResponseFailed(
            metaData=MetadataFailed(
                executionTime=get_execution_time(start_time), responseCode=status, message=message
            )
        ).dict(),
    )
