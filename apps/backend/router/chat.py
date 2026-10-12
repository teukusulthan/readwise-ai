import os
from collections.abc import AsyncIterable
from time import time
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from fastapi.sse import EventSourceResponse, ServerSentEvent
from loguru import logger

from dto.chat import ChatAskDTO
from models.base_response import BaseResponse
from models.metadata import MetadataSuccess
from service.chat_session import ChatSessions, StoredEvent
from service.conversation import Conversation
from service.rag import Rag
from util.helper import get_execution_time, is_include_schema, router_param_builder
from util.http_errors import ConflictError, ServiceUnavailableError, to_http_exception

obj = Rag()
conversations = Conversation(rag=obj)
sessions = ChatSessions(conversations=conversations)

tag = os.path.splitext(os.path.basename(os.path.abspath(__file__)))[0]
router = APIRouter(**router_param_builder(tag))


def _sse(item: StoredEvent) -> ServerSentEvent:
    # data is already JSON text (stored in Redis), so send it as-is.
    return ServerSentEvent(id=item.id or None, event=item.event, raw_data=item.data)


@router.post("/ask", include_in_schema=is_include_schema(tag, "ask"))
def ask(dto: ChatAskDTO):
    """
    Answer a question from indexed book text, with numbered sources (whole answer at once).
    Stateless: nothing is saved (use /chat/stream for saved conversations).
    `mode`: llm | general_knowledge | insufficient_context | no_context | no_indexed_books | retrieval_only.
    """
    start_time = time()
    try:
        return BaseResponse(data=obj.ask(dto), metaData=MetadataSuccess(executionTime=get_execution_time(start_time)))
    except Exception as error:
        raise to_http_exception(error, start_time)


async def claim_turn(dto: ChatAskDTO) -> str:
    """Reserve the conversation before the stream starts, so a busy one is a plain HTTP 409."""
    start_time = time()
    try:
        return await sessions.claim(dto)
    except ConflictError as error:
        raise to_http_exception(error, start_time)
    except Exception:
        logger.exception("Could not claim the conversation")
        raise to_http_exception(ServiceUnavailableError("Chat sessions are unavailable (is Redis running?)."), start_time)


@router.post("/stream", response_class=EventSourceResponse, include_in_schema=is_include_schema(tag, "stream"))
async def stream(dto: ChatAskDTO, session_id: str = Depends(claim_turn)) -> AsyncIterable[ServerSentEvent]:
    """
    One saved chat turn as Server-Sent Events (not wrapped in BaseResponse). The answer is generated in a
    background session that survives a client disconnect; every event carries an `id`.
    `session` {sessionId} → `conversation` {id, title, …} → `status` {stage} → `sources` → `delta` {text}…
    → `done` (/chat/ask payload + conversationId, messageId) | `error` {message, code} | `cancelled`.
    Reconnect with GET /chat/stream/{sessionId}?after=<last id>. Omit `conversationId` to start a new conversation.
    HTTP 409 (before any stream) if a question is already being answered in that conversation.
    """
    try:
        await sessions.start(dto, session_id)
    except Exception:
        # The HTTP status is already 200 once streaming starts, so report failures in-band.
        logger.exception("Could not start a chat session")
        yield ServerSentEvent(event="error", data={"message": "Chat sessions are unavailable (is Redis running?).",
                                                   "code": 503})
        return
    async for item in sessions.events(session_id, "0"):
        yield _sse(item)


@router.get("/stream/{session_id}", response_class=EventSourceResponse, include_in_schema=is_include_schema(tag, "resume"))
async def resume(
    session_id: str,
    after: Optional[str] = Query(default=None, max_length=50, description="Last event id received; omit to replay everything"),
    last_event_id: Optional[str] = Header(default=None, alias="Last-Event-ID", max_length=50),
) -> AsyncIterable[ServerSentEvent]:
    """Re-attach to a chat session: every event after `after` (or `Last-Event-ID`), then live ones until it ends."""
    async for item in sessions.events(session_id, after or last_event_id or "0"):
        yield _sse(item)


@router.post("/stream/{session_id}/cancel", include_in_schema=is_include_schema(tag, "cancel"))
async def cancel(session_id: str):
    """Stop generating (a disconnect no longer does). The partial answer is saved as `stopped`."""
    start_time = time()
    try:
        data = await sessions.cancel(session_id)
        return BaseResponse(data=data, metaData=MetadataSuccess(executionTime=get_execution_time(start_time)))
    except Exception as error:
        raise to_http_exception(error, start_time)


@router.get("/active", include_in_schema=is_include_schema(tag, "active"))
async def active(conversationId: str = Query(max_length=64)):
    """Whether an answer of this conversation is still being generated: {active, sessionId} — to re-attach after a reload."""
    start_time = time()
    try:
        data = await sessions.active(conversationId)
        return BaseResponse(data=data, metaData=MetadataSuccess(executionTime=get_execution_time(start_time)))
    except Exception as error:
        raise to_http_exception(error, start_time)
