"""
Saved chat conversations.

/chat/stream runs one *turn*: it stores the user's question, streams the answer from
Rag (with the last few turns as context, so follow-ups work), and stores the answer
with its sources. History therefore survives reloads and is the same in every browser.

    conversation → user message → assistant message (llm | insufficient_context | no_context
                                   | no_indexed_books | retrieval_only | error | stopped)

If the client goes away mid-answer (Stop button, closed tab), the partial answer is
saved as mode "stopped" so the history never shows a question without a reply.
"""

import asyncio
from typing import AsyncIterator, Iterable, Optional

from loguru import logger

from config.base import settings
from dto.chat import ChatAskDTO
from dto.conversation import RenameConversationDTO
from service.conversation_repository import ConversationRepository
from service.rag import ChatTurn, Rag, _tidy
from util.http_errors import NotFoundError

TITLE_MAX_CHARS = 80


class ConversationNotFoundError(NotFoundError):
    pass


def make_title(question: str) -> str:
    """First question, on one line, cut at a word boundary."""
    title = " ".join(question.split())
    if len(title) <= TITLE_MAX_CHARS:
        return title
    return title[:TITLE_MAX_CHARS].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def history_from(messages: Iterable[dict], max_turns: int) -> list[ChatTurn]:
    """Completed question → generated-answer pairs, oldest first (failed/empty answers are skipped)."""
    answered = ("llm", "general_knowledge")
    turns, question = [], None
    for message in messages:
        if message["role"] == "user":
            question = message["content"]
        elif question is not None and message["mode"] in answered and message["content"]:
            turns.append(ChatTurn(question=question, answer=message["content"]))
            question = None
    return turns[-max_turns:] if max_turns > 0 else []


class Conversation:
    def __init__(self, repository: Optional[ConversationRepository] = None, rag: Optional[Rag] = None):
        self.repository = repository or ConversationRepository()
        self.rag = rag or Rag()

    # ── CRUD ─────────────────────────────────────────────────────────

    def get_all(self, page: int, size: int) -> tuple[list[dict], int]:
        rows, total = self.repository.list_recent(page=page, size=size)
        return [conversation_to_api(row) for row in rows], total

    def get_by_id(self, conversation_id) -> dict:
        row = self._get(conversation_id)
        messages = self.repository.messages(row["id"])
        return {**conversation_to_api(row), "messages": [message_to_api(m) for m in messages]}

    def rename(self, dto: RenameConversationDTO) -> dict:
        row = self.repository.rename(dto.id, dto.title)
        if not row:
            raise ConversationNotFoundError("Conversation not found.")
        return conversation_to_api(row)

    def delete(self, conversation_id) -> dict:
        row = self.repository.delete(conversation_id)
        if not row:
            raise ConversationNotFoundError("Conversation not found.")
        return {"id": str(row["id"]), "deleted": True}

    def _get(self, conversation_id) -> dict:
        row = self.repository.get(conversation_id)
        if not row:
            raise ConversationNotFoundError("Conversation not found.")
        return row

    # ── one streamed turn ────────────────────────────────────────────

    async def stream_turn(self, dto: ChatAskDTO) -> AsyncIterator[tuple[str, dict]]:
        """
        Yields (event, data): `conversation` {conversation} first, then the Rag events
        (status → sources → delta… → done | error). `done` / `error` also carry the
        saved assistant `messageId`.
        """
        try:
            if dto.conversationId:
                row = await asyncio.to_thread(self._get, dto.conversationId)
                # 2 messages per turn, plus slack for failed turns that history_from skips.
                recent = await asyncio.to_thread(self.repository.recent_messages, row["id"],
                                                 settings.CHAT_HISTORY_TURNS * 2 + 4)
            else:
                row = await asyncio.to_thread(self.repository.create, make_title(dto.question), dto.bookIds)
                recent = []
        except (NotFoundError, ValueError) as error:
            yield "error", {"message": str(error), "code": 404 if isinstance(error, NotFoundError) else 400}
            return

        conversation_id = str(row["id"])
        await asyncio.to_thread(self.repository.add_message, conversation_id,
                                {"role": "user", "content": dto.question, "book_ids": dto.bookIds})
        yield "conversation", conversation_to_api(row)

        history = history_from(recent, settings.CHAT_HISTORY_TURNS)
        # Retrieval uses the last question even when its answer failed: it still names the topic.
        previous_question = next((m["content"] for m in reversed(recent) if m["role"] == "user"), None)
        partial: list[str] = []
        saved = False
        try:
            async for event, data in self.rag.ask_stream(dto, history=history, previous_question=previous_question):
                if event == "delta":
                    partial.append(data["text"])
                elif event == "done":
                    message = await asyncio.to_thread(self._save_answer, conversation_id, data)
                    saved = True
                    data = {**data, "conversationId": conversation_id, "messageId": str(message["id"])}
                elif event == "error":
                    message = await asyncio.to_thread(self._save_failure, conversation_id, "error",
                                                      "".join(partial), data.get("message"))
                    saved = True
                    data = {**data, "conversationId": conversation_id, "messageId": str(message["id"])}
                yield event, data
        except (asyncio.CancelledError, GeneratorExit):
            # Client disconnected. Saved synchronously: the task is being cancelled.
            if not saved:
                self._save_failure_quietly(conversation_id, "stopped", "".join(partial), None)
            raise
        except Exception:
            if not saved:
                self._save_failure_quietly(conversation_id, "error", "".join(partial), "Internal server error.")
            raise

    def _save_answer(self, conversation_id: str, final: dict) -> dict:
        return self.repository.add_message(conversation_id, {
            "role": "assistant",
            "content": final["answer"],
            "mode": final["mode"],
            "grounded": final["grounded"],
            "sources": final["sources"],
            "skipped_books": final.get("skippedBooks") or [],
            "model": final.get("model"),
        })

    def _save_failure(self, conversation_id: str, mode: str, partial: str, error: Optional[str]) -> dict:
        return self.repository.add_message(conversation_id, {
            "role": "assistant", "content": _tidy(partial), "mode": mode, "grounded": False, "error": error,
        })

    def _save_failure_quietly(self, conversation_id, mode, partial, error):
        try:
            self._save_failure(conversation_id, mode, partial, error)
        except Exception:
            logger.exception("Could not save the interrupted answer of conversation {id}", id=conversation_id)


def _iso(value) -> Optional[str]:
    return value.isoformat() if value else None


def conversation_to_api(row: dict) -> dict:
    data = {
        "id": str(row["id"]),
        "title": row["title"],
        "bookIds": [str(b) for b in row["book_ids"] or []],
        "createdAt": _iso(row["created_at"]),
        "updatedAt": _iso(row["updated_at"]),
    }
    if "message_count" in row:
        data["messageCount"] = row["message_count"]
    return data


def message_to_api(row: dict) -> dict:
    data = {
        "id": str(row["id"]),
        "role": row["role"],
        "content": row["content"],
        "createdAt": _iso(row["created_at"]),
    }
    if row["role"] == "user":
        data["bookIds"] = [str(b) for b in row["book_ids"] or []]
    else:
        data.update(
            mode=row["mode"],
            grounded=bool(row["grounded"]),
            sources=row["sources"] or [],
            skippedBooks=row["skipped_books"] or [],
            model=row["model"],
            error=row["error"],
        )
    return data
