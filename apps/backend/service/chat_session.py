"""
Resumable chat streaming: an answer outlives the browser connection.

POST /chat/stream starts a *session*. A background task runs the chat turn
(Conversation.stream_turn) and appends every event to a Redis Stream; the HTTP
response only reads that stream. A client that disconnects (network drop, reload,
switching chats) does not stop the answer: it reconnects with
GET /chat/stream/{session_id}?after=<last event id> (or the standard `Last-Event-ID`
header) and receives every event it missed, then the live rest. Only an explicit
POST /chat/stream/{session_id}/cancel stops generation.

    browser ──POST /chat/stream──► start(): session meta + task ──► stream_turn() ──XADD──► Redis Stream
       ▲                                                                                      │
       └──────────────── SSE (id = stream entry id) ◄── events(): XREAD BLOCK from <after> ◄──┘

Redis keys (expire after CHAT_SESSION_TTL_SECONDS, refreshed while the session runs):
  chat:session:{id}:events        STREAM  entries {event, data(json)}; entry id = SSE event id
  chat:session:{id}               HASH    status running|done|error|cancelled, conversation_id, heartbeat, created_at,
                                          owner (the principal that started it; see "Ownership" below)
  chat:session:{id}:cancel        STRING  set by cancel(); the runner polls it (works across workers)
  chat:sessions:running           ZSET    session ids (score = start time) of turns that count toward
                                          CHAT_MAX_CONCURRENT_SESSIONS; entries whose session is no longer
                                          running with a fresh heartbeat are pruned when counting
  chat:conversation:{cid}:active  STRING  session id while an answer for that conversation runs (SET NX: one
                                          running turn per conversation; a second gets HTTP 409)

A runner refreshes `heartbeat` every few seconds. A reader that finds a "running" session
with a stale heartbeat (the process died) reports the answer as interrupted instead of
waiting forever.

Ownership: conversations are personal (auth/principal.py). claim() and active() check that the
caller owns the conversation (another owner's is "not found"), and every session records its
owner: resume and cancel of someone else's session behave exactly like an unknown session.
"""

import asyncio
import json
import re
import time
import uuid
from contextlib import aclosing
from dataclasses import dataclass
from typing import AsyncIterator, Optional

from loguru import logger

from auth.principal import Principal
from config.base import settings
from dto.chat import ChatAskDTO
from service import Services
from service.conversation_repository import parse_conversation_id
from util.http_errors import ConflictError, NotFoundError, TooManyRequestsError

TERMINAL_EVENTS = frozenset({"done", "error", "cancelled"})
HEARTBEAT_SECONDS = 2.0
READ_BLOCK_MS = 2000
# Plenty for one answer (a few hundred deltas); stops a runaway session from growing without bound.
STREAM_MAXLEN = 10_000

TURN_RUNNING_MESSAGE = "A question is already being answered in this conversation."
BUSY_MESSAGE = "Too many answers are being generated right now, try again shortly."
BUSY_RETRY_AFTER_SECONDS = 5

# Compare-and-delete / compare-and-swap, atomic on the Redis server.
_RELEASE_LUA = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) end return 0"
_REPLACE_LUA = "if redis.call('get', KEYS[1]) == ARGV[1] then redis.call('set', KEYS[1], ARGV[2], 'EX', ARGV[3]) return 1 end return 0"

_RUNNING_KEY = "chat:sessions:running"

_EVENT_ID_RE = re.compile(r"^(0|\d{1,20}-\d{1,20})$")


@dataclass(frozen=True)
class StoredEvent:
    id: str     # Redis stream entry id ("1760000000000-0"); "" for synthetic events
    event: str
    data: str   # JSON text


def parse_session_id(value) -> str:
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise ValueError(f"Invalid session id: {value!r}") from None


def parse_event_id(value: Optional[str]) -> str:
    """'0' (from the start) or a Redis stream entry id."""
    value = (value or "0").strip()
    if not _EVENT_ID_RE.match(value):
        raise ValueError(f"Invalid event id: {value!r}")
    return value


def _synthetic(event: str, data: dict) -> StoredEvent:
    return StoredEvent(id="", event=event, data=json.dumps(data))


class RedisSessionStore:
    """All Redis access for chat sessions (async client, decoded strings)."""

    def __init__(self, client=None):
        self._client = client

    @property
    def client(self):
        return self._client or Services.a_redis()

    @property
    def ttl(self) -> int:
        return settings.CHAT_SESSION_TTL_SECONDS

    @staticmethod
    def _meta_key(session_id: str) -> str:
        return f"chat:session:{session_id}"

    @staticmethod
    def _events_key(session_id: str) -> str:
        return f"chat:session:{session_id}:events"

    @staticmethod
    def _cancel_key(session_id: str) -> str:
        return f"chat:session:{session_id}:cancel"

    @staticmethod
    def _active_key(conversation_id: str) -> str:
        return f"chat:conversation:{conversation_id}:active"

    async def create(self, session_id: str, owner_id: str):
        now = time.time()
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.hset(self._meta_key(session_id),
                      mapping={"status": "running", "created_at": now, "heartbeat": now, "owner": owner_id})
            pipe.expire(self._meta_key(session_id), self.ttl)
            await pipe.execute()

    async def append(self, session_id: str, event: str, data: str) -> str:
        key = self._events_key(session_id)
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.xadd(key, {"event": event, "data": data}, maxlen=STREAM_MAXLEN, approximate=True)
            pipe.expire(key, self.ttl)
            entry_id, _ = await pipe.execute()
        return entry_id

    async def read(self, session_id: str, after: str, block_ms: Optional[int]) -> list[StoredEvent]:
        """Events with an id greater than `after`; waits up to `block_ms` for new ones (None = don't wait)."""
        response = await self.client.xread({self._events_key(session_id): after}, count=500, block=block_ms)
        return [StoredEvent(id=entry_id, event=fields["event"], data=fields["data"])
                for _key, entries in (response or []) for entry_id, fields in entries]

    async def meta(self, session_id: str) -> dict:
        return await self.client.hgetall(self._meta_key(session_id))

    async def update(self, session_id: str, **fields):
        async with self.client.pipeline(transaction=True) as pipe:
            pipe.hset(self._meta_key(session_id), mapping=fields)
            pipe.expire(self._meta_key(session_id), self.ttl)
            await pipe.execute()

    async def request_cancel(self, session_id: str):
        await self.client.set(self._cancel_key(session_id), "1", ex=self.ttl)

    async def cancel_requested(self, session_id: str) -> bool:
        return bool(await self.client.exists(self._cancel_key(session_id)))

    async def register_running(self, session_id: str):
        await self.client.zadd(_RUNNING_KEY, {session_id: time.time()})

    async def unregister_running(self, session_id: str):
        await self.client.zrem(_RUNNING_KEY, session_id)

    async def count_running(self) -> int:
        """Sessions that are running with a fresh heartbeat; dead or finished entries are pruned."""
        stale_after = settings.CHAT_SESSION_STALE_SECONDS
        live = 0
        for session_id in await self.client.zrange(_RUNNING_KEY, 0, -1):
            meta = await self.meta(session_id)
            fresh = time.time() - float(meta.get("heartbeat") or 0) <= stale_after
            if meta.get("status") == "running" and fresh:
                live += 1
            else:
                await self.client.zrem(_RUNNING_KEY, session_id)
        return live

    async def claim_active(self, conversation_id: str, session_id: str) -> bool:
        """Atomically take the conversation (SET NX EX). False if another turn holds it."""
        return bool(await self.client.set(self._active_key(conversation_id), session_id, nx=True, ex=self.ttl))

    async def replace_active(self, conversation_id: str, old_session_id: str, session_id: str) -> bool:
        """Take over a claim still held by `old_session_id` (a dead turn). Atomic."""
        return bool(await self.client.eval(_REPLACE_LUA, 1, self._active_key(conversation_id),
                                           old_session_id, session_id, self.ttl))

    async def get_active(self, conversation_id: str) -> Optional[str]:
        return await self.client.get(self._active_key(conversation_id))

    async def clear_active(self, conversation_id: str, session_id: str):
        # Only if it still points at this session (a newer turn may have started meanwhile). Atomic.
        await self.client.eval(_RELEASE_LUA, 1, self._active_key(conversation_id), session_id)


class ChatSessions:
    def __init__(self, conversations=None, store: Optional[RedisSessionStore] = None):
        self._conversations = conversations
        self.store = store or RedisSessionStore()
        # Strong references: asyncio keeps only weak ones to running tasks.
        self._tasks: dict[str, asyncio.Task] = {}

    @property
    def conversations(self):
        if self._conversations is None:
            from service.conversation import Conversation

            self._conversations = Conversation()
        return self._conversations

    # ── writing side ────────────────────────────────────────────────

    @staticmethod
    def _requested_conversation(dto: ChatAskDTO) -> Optional[str]:
        try:
            return str(parse_conversation_id(dto.conversationId)) if dto.conversationId else None
        except ValueError:
            return None  # the turn itself reports the bad id

    async def claim(self, dto: ChatAskDTO, owner: Principal) -> str:
        """
        Reserve the conversation this turn continues, before any stream starts, so a second turn gets
        a normal HTTP 409 instead of interleaving messages. Returns the new session id to pass to
        start(). A new conversation needs no claim (it is claimed once it exists). A claim whose
        session died (finished, or heartbeat stale) is taken over. Someone else's conversation is
        NotFoundError (so nobody can hold another user's conversation busy).
        """
        conversation_id = self._requested_conversation(dto)
        if conversation_id:
            await asyncio.to_thread(self.conversations.ensure_owned, conversation_id, owner)
        cap = settings.CHAT_MAX_CONCURRENT_SESSIONS
        # Soft cap: the check and the registration below are not atomic, so a burst of simultaneous
        # claims can overshoot it by a few; it exists to bound load, not to be exact.
        if cap > 0 and await self.store.count_running() >= cap:
            raise TooManyRequestsError(BUSY_MESSAGE, retry_after=BUSY_RETRY_AFTER_SECONDS)
        session_id = str(uuid.uuid4())
        # Meta (status + heartbeat) first: a claim leaked before start() runs (client gone, process
        # died) then has no live heartbeat and is taken over / stops counting after
        # CHAT_SESSION_STALE_SECONDS.
        await self.store.create(session_id, owner.owner_id)
        await self.store.register_running(session_id)
        if conversation_id and not await self._claim(conversation_id, session_id):
            await self._unregister(session_id)
            raise ConflictError(TURN_RUNNING_MESSAGE)
        return session_id

    async def _claim(self, conversation_id: str, session_id: str) -> bool:
        for _ in range(2):  # the second pass covers a holder that released between our SET and GET
            if await self.store.claim_active(conversation_id, session_id):
                return True
            holder = await self.store.get_active(conversation_id)
            if holder is None:
                continue
            meta = await self.store.meta(holder)
            fresh = time.time() - float(meta.get("heartbeat") or 0) <= settings.CHAT_SESSION_STALE_SECONDS
            if meta.get("status") == "running" and fresh:
                return False
            return await self.store.replace_active(conversation_id, holder, session_id)
        return False

    async def start(self, dto: ChatAskDTO, owner: Principal, session_id: Optional[str] = None) -> str:
        """
        Create the session and start answering in the background. Returns the session id.
        Pass the id from claim() when the conversation was already claimed; otherwise it is claimed here.
        """
        if session_id is None:
            session_id = await self.claim(dto, owner)
        try:
            if not await self.store.meta(session_id):  # claim() already created it for a continued conversation
                await self.store.create(session_id, owner.owner_id)
            await self.store.append(session_id, "session", json.dumps({"sessionId": session_id}))
        except BaseException:
            await self._release(self._requested_conversation(dto), session_id)
            await self._unregister(session_id)
            raise
        task = asyncio.create_task(self._run(session_id, dto, owner), name=f"chat-session-{session_id}")
        self._tasks[session_id] = task
        task.add_done_callback(lambda _task: self._tasks.pop(session_id, None))
        return session_id

    async def _run(self, session_id: str, dto: ChatAskDTO, owner: Principal):
        watcher = asyncio.create_task(self._watch(session_id, asyncio.current_task()))
        requested = self._requested_conversation(dto)
        conversation_id, status = None, "error"
        try:
            # aclosing: if we are cancelled mid-append, the turn generator is closed too,
            # so it saves the partial answer as "stopped".
            async with aclosing(self.conversations.stream_turn(dto, owner)) as turn:
                async for event, data in turn:
                    if event == "conversation":
                        conversation_id = data["id"]
                        await self.store.update(session_id, conversation_id=conversation_id)
                        if conversation_id != requested:  # a new conversation: nobody else can hold it yet
                            await self.store.claim_active(conversation_id, session_id)
                    await self.store.append(session_id, event, json.dumps(data, default=str))
                    if event in ("done", "error"):
                        status = event
        except asyncio.CancelledError:
            status = "cancelled"
            await self._append_quietly(session_id, "cancelled", {"message": "The answer was stopped."})
        except Exception:
            logger.exception("Chat session {id} failed", id=session_id)
            await self._append_quietly(session_id, "error", {"message": "Internal server error.", "code": 500})
        finally:
            watcher.cancel()
            try:
                await self.store.update(session_id, status=status, finished_at=time.time())
            except Exception:
                logger.exception("Could not finalize chat session {id}", id=session_id)
            # Always release the claim (finished, cancelled or failed), even if the status write failed.
            await self._release(requested, session_id)
            await self._release(conversation_id, session_id)
            await self._unregister(session_id)

    async def _unregister(self, session_id: str):
        try:
            await self.store.unregister_running(session_id)
        except Exception:
            logger.exception("Could not unregister chat session {id}", id=session_id)

    async def _release(self, conversation_id: Optional[str], session_id: str):
        if not conversation_id:
            return
        try:
            await self.store.clear_active(conversation_id, session_id)
        except Exception:
            logger.exception("Could not release conversation {cid}", cid=conversation_id)

    async def _watch(self, session_id: str, runner: asyncio.Task):
        """Heartbeat for readers, and cancel requests made through Redis (possibly by another worker)."""
        while True:
            await asyncio.sleep(HEARTBEAT_SECONDS)
            try:
                await self.store.update(session_id, heartbeat=time.time())
                if await self.store.cancel_requested(session_id):
                    runner.cancel()
                    return
            except Exception:
                logger.warning("Chat session {id}: heartbeat failed", id=session_id)

    async def _append_quietly(self, session_id: str, event: str, data: dict):
        try:
            await self.store.append(session_id, event, json.dumps(data))
        except Exception:
            logger.exception("Chat session {id}: could not record {event}", id=session_id, event=event)

    async def cancel(self, session_id, owner: Principal) -> dict:
        session_id = parse_session_id(session_id)
        meta = await self.store.meta(session_id)
        if not meta or not owner.can_see(meta.get("owner")):
            raise NotFoundError("Chat session not found or expired.")
        if meta.get("status") != "running":
            return {"sessionId": session_id, "cancelled": False, "status": meta.get("status")}
        await self.store.request_cancel(session_id)
        task = self._tasks.get(session_id)
        if task:  # running in this process: stop now instead of at the next heartbeat
            task.cancel()
        return {"sessionId": session_id, "cancelled": True, "status": "running"}

    async def shutdown(self, timeout: float = 5.0):
        """Server stopping: stop running answers so their partial text is saved as "stopped"."""
        tasks = list(self._tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.wait(tasks, timeout=timeout)

    # ── reading side ────────────────────────────────────────────────

    async def events(self, session_id, after: Optional[str] = None, *,
                     owner: Principal) -> AsyncIterator[StoredEvent]:
        """Every event after `after` ('0' = all), then live ones, until the session ends."""
        try:
            session_id, after = parse_session_id(session_id), parse_event_id(after)
        except ValueError as error:
            yield _synthetic("error", {"message": str(error), "code": 400})
            return
        meta = await self.store.meta(session_id)
        if not meta or not owner.can_see(meta.get("owner")):
            yield _synthetic("error", {"message": "This answer session has expired or does not exist.", "code": 404})
            return

        while True:
            batch = await self.store.read(session_id, after, block_ms=READ_BLOCK_MS)
            for item in batch:
                after = item.id
                yield item
                if item.event in TERMINAL_EVENTS:
                    return
            if batch:
                continue

            meta = await self.store.meta(session_id)
            if not meta:
                yield _synthetic("error", {"message": "This answer session has expired.", "code": 404})
                return
            if meta.get("status") != "running":
                # Finished between our read and this check: deliver anything left, then stop.
                for item in await self.store.read(session_id, after, block_ms=None):
                    yield item
                return
            if time.time() - float(meta.get("heartbeat") or 0) > settings.CHAT_SESSION_STALE_SECONDS:
                yield _synthetic("error", {"message": "The answer was interrupted (the server restarted). "
                                                      "Please ask again.", "code": 503})
                return

    async def active(self, conversation_id, owner: Principal) -> dict:
        """Whether an answer of this conversation is still being generated (to re-attach after a reload)."""
        conversation_id = str(parse_conversation_id(conversation_id))
        await asyncio.to_thread(self.conversations.ensure_owned, conversation_id, owner)
        session_id = await self.store.get_active(conversation_id)
        meta = await self.store.meta(session_id) if session_id else {}
        if meta.get("status") == "running" and owner.can_see(meta.get("owner")):
            return {"active": True, "sessionId": session_id, "conversationId": conversation_id}
        return {"active": False, "sessionId": "", "conversationId": conversation_id}
