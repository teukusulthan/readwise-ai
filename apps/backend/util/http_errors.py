"""
Map service exceptions to HTTP errors in the standard BaseResponseFailed envelope.

    NotFoundError                       -> 404  (not found; plain LookupError/KeyError/IndexError are bugs -> 500)
    DuplicateBookError / ConflictError  -> 409  (already exists / wrong state)
    ValueError                          -> 400  (bad input)
    ServiceUnavailableError             -> 503  (dependency down / not configured)
    EmbeddingError / Qdrant outage      -> 503  "Search service unavailable"
    anything else                       -> 500  (logged; generic message, no internals leaked)
"""

from fastapi import HTTPException
from loguru import logger

from models.base_response import BaseResponseFailed
from models.metadata import MetadataFailed
from util.helper import get_execution_time


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class ServiceUnavailableError(Exception):
    pass


SEARCH_UNAVAILABLE_MESSAGE = "Search service unavailable"


def is_search_outage(error: BaseException) -> bool:
    """True when retrieval failed because the embedding service or Qdrant could not be reached."""
    from qdrant_client.http.exceptions import ResponseHandlingException

    from util.embedding import EmbeddingError

    return isinstance(error, (EmbeddingError, ResponseHandlingException))


def to_http_exception(error: Exception, start_time: float) -> HTTPException:
    from service.book_repository import DuplicateBookError

    if isinstance(error, NotFoundError):
        status, message = 404, str(error)
    elif isinstance(error, (DuplicateBookError, ConflictError)):
        status, message = 409, str(error)
    elif isinstance(error, ValueError):
        status, message = 400, str(error)
    elif isinstance(error, ServiceUnavailableError):
        status, message = 503, str(error)
    elif is_search_outage(error):
        logger.warning("Search service unavailable: {error}", error=error)
        status, message = 503, SEARCH_UNAVAILABLE_MESSAGE
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
