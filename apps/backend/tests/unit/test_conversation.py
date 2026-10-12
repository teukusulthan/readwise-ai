"""Saved conversations: turn lifecycle, history for follow-ups, interrupted answers (no database)."""

import asyncio
import uuid
from datetime import datetime, timezone

from dto.chat import ChatAskDTO
from service.conversation import Conversation, history_from, make_title, message_to_api
from service.rag import ChatTurn, Rag, build_user_prompt, format_history
from service.search import Retrieval, merge_hits
from service.vector_store import ChunkHit
from util.http_errors import ServiceUnavailableError


def _hit(n, score=0.8, book="b1"):
    return ChunkHit(score=score, book_id=book, book_title="Saltmere", chunk_index=n, text=f"passage {n}",
                    headings=["Chapter 3"], page_start=3, page_end=3)


class MemoryRepository:
    """In-memory stand-in for ConversationRepository."""

    def __init__(self):
        self.conversations, self.rows = {}, []

    def create(self, title, book_ids=None):
        now = datetime.now(timezone.utc)
        row = {"id": uuid.uuid4(), "title": title, "book_ids": list(book_ids or []), "created_at": now, "updated_at": now}
        self.conversations[str(row["id"])] = row
        return row

    def get(self, conversation_id):
        return self.conversations.get(str(conversation_id))

    def add_message(self, conversation_id, fields):
        row = {"id": uuid.uuid4(), "conversation_id": str(conversation_id), "mode": None, "grounded": None,
               "sources": [], "skipped_books": [], "model": None, "error": None, "book_ids": [],
               "created_at": datetime.now(timezone.utc), **{k: v for k, v in fields.items() if v is not None}}
        self.rows.append(row)
        return row

    def messages(self, conversation_id):
        return [r for r in self.rows if r["conversation_id"] == str(conversation_id)]

    def recent_messages(self, conversation_id, limit):
        return self.messages(conversation_id)[-limit:]


class SpySearch:
    def __init__(self, hits):
        self.hits, self.calls = hits, []

    def retrieve(self, question, book_ids=None, top_k=None, min_score=None, follow_up_of=None):
        self.calls.append({"question": question, "follow_up_of": follow_up_of})
        return Retrieval(hits=self.hits, searched_book_ids=["b1"])


def _streamer(pieces, prompts=None, fail=False, pause=False):
    async def stream(system, user):
        if prompts is not None:
            prompts.append(user)
        for piece in pieces:
            yield piece
            if pause:
                await asyncio.sleep(10)  # long enough for the test to cancel mid-answer
        if fail:
            raise ServiceUnavailableError("The language model is rate-limited right now. Try again shortly.")
    return stream


def _service(pieces, **kwargs):
    search = SpySearch([_hit(1), _hit(2)])
    prompts = []
    repo = MemoryRepository()
    rag = Rag(search=search, streamer=_streamer(pieces, prompts=prompts, **kwargs), allow_general_knowledge=False)
    return Conversation(repository=repo, rag=rag), repo, search, prompts


async def _turn(service, question, conversation_id=None):
    return [e async for e in service.stream_turn(ChatAskDTO(question=question, conversationId=conversation_id))]


# ── helpers ──────────────────────────────────────────────────────────

def test_title_is_first_question_cut_at_a_word():
    assert make_title("  Who   rescued\nthe crew? ") == "Who rescued the crew?"
    long = "word " * 40
    title = make_title(long)
    assert len(title) <= 81 and title.endswith("…") and "  " not in title


def test_history_pairs_only_answered_turns():
    messages = [
        {"role": "user", "content": "Q1"}, {"role": "assistant", "content": "A1 [1]", "mode": "llm"},
        {"role": "user", "content": "Q2"}, {"role": "assistant", "content": "", "mode": "error"},
        {"role": "user", "content": "Q3"}, {"role": "assistant", "content": "A3", "mode": "llm"},
    ]
    assert history_from(messages, 3) == [ChatTurn("Q1", "A1 [1]"), ChatTurn("Q3", "A3")]
    assert history_from(messages, 1) == [ChatTurn("Q3", "A3")]
    assert history_from(messages, 0) == []


def test_history_in_prompt_drops_old_citations():
    text = format_history([ChatTurn("Who was the keeper?", "Elias Penhallow [1] kept the light [2].")])
    assert text == "User: Who was the keeper?\nAssistant: Elias Penhallow kept the light."
    prompt = build_user_prompt("What did he do?", [_hit(1)], [ChatTurn("Q", "A")])
    assert prompt.startswith("Earlier conversation") and prompt.index("Context passages") < prompt.index("Question: What did he do?")
    assert not build_user_prompt("Q", [_hit(1)]).startswith("Earlier")


def test_merge_hits_keeps_best_score_per_chunk():
    merged = merge_hits([[_hit(1, 0.5), _hit(2, 0.7)], [_hit(1, 0.9), _hit(3, 0.6)]], limit=3)
    assert [(h.chunk_index, h.score) for h in merged] == [(1, 0.9), (2, 0.7), (3, 0.6)]


# ── stream_turn ──────────────────────────────────────────────────────

async def test_new_conversation_saves_question_and_answer():
    service, repo, search, _ = _service(["The lifeboat ", "saved them [2]."])
    events = await _turn(service, "Who rescued the crew?")

    assert [n for n, _ in events][:2] == ["conversation", "status"] and events[-1][0] == "done"
    conversation = events[0][1]
    assert conversation["title"] == "Who rescued the crew?"
    done = events[-1][1]
    assert done["conversationId"] == conversation["id"] and done["messageId"]

    user, assistant = repo.messages(conversation["id"])
    assert user["role"] == "user" and user["content"] == "Who rescued the crew?"
    assert assistant["mode"] == "llm" and assistant["content"] == "The lifeboat saved them [2]."
    assert [s["cited"] for s in assistant["sources"]] == [False, True]
    assert search.calls == [{"question": "Who rescued the crew?", "follow_up_of": None}]


async def test_follow_up_gets_history_and_previous_question():
    service, repo, search, prompts = _service(["Answer [1]."])
    first = await _turn(service, "Who kept the Saltmere light?")
    conversation_id = first[0][1]["id"]
    await _turn(service, "What did he do in 1911?", conversation_id)

    assert search.calls[1] == {"question": "What did he do in 1911?", "follow_up_of": "Who kept the Saltmere light?"}
    assert "User: Who kept the Saltmere light?" in prompts[1]
    assert len(repo.messages(conversation_id)) == 4


async def test_follow_up_after_failed_answer_still_uses_previous_question():
    service, repo, search, prompts = _service(["INSUFFICIENT_CONTEXT"])
    first = await _turn(service, "Who kept the Saltmere light?")
    await _turn(service, "And his daughter?", first[0][1]["id"])

    assert repo.rows[1]["mode"] == "insufficient_context"
    assert search.calls[1]["follow_up_of"] == "Who kept the Saltmere light?"
    assert "Earlier conversation" not in prompts[1]  # a failed answer is not shown to the LLM


async def test_provider_error_is_saved_with_partial_text():
    service, repo, _, _ = _service(["Partial answer"], fail=True)
    events = await _turn(service, "Who rescued the crew?")
    name, data = events[-1]
    assert name == "error" and data["messageId"]
    assistant = repo.rows[-1]
    assert assistant["mode"] == "error" and assistant["content"] == "Partial answer"
    assert "rate-limited" in assistant["error"]


async def test_disconnect_mid_answer_saves_stopped_partial():
    service, repo, _, _ = _service(["The lifeboat ", "never sent"], pause=True)
    stream = service.stream_turn(ChatAskDTO(question="Who rescued the crew?"))
    async for name, _ in stream:
        if name == "delta":
            break  # like the browser pressing Stop after the first words
    await stream.aclose()
    assistant = repo.rows[-1]
    assert assistant["role"] == "assistant" and assistant["mode"] == "stopped"
    assert assistant["content"] == "The lifeboat"


async def test_unknown_conversation_is_an_error_event():
    service, repo, _, _ = _service(["x"])
    events = await _turn(service, "Q?", str(uuid.uuid4()))
    assert events == [("error", {"message": "Conversation not found.", "code": 404})]
    assert repo.rows == []


def test_message_shapes():
    user = message_to_api({"id": uuid.uuid4(), "role": "user", "content": "Q", "book_ids": [uuid.UUID(int=1)],
                           "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)})
    assert user["bookIds"] == ["00000000-0000-0000-0000-000000000001"] and "sources" not in user
