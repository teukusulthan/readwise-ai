from types import SimpleNamespace

import pytest

from dto.chat import ChatAskDTO
from service.rag import (INSUFFICIENT_MARKER, NO_BOOKS_ANSWER, NO_CONTEXT_ANSWER, RETRIEVAL_ONLY_ANSWER, Rag,
                         build_user_prompt, extract_citations, format_context)
from service.search import Retrieval
from service.vector_store import ChunkHit


def _hit(n=1, **kw):
    base = dict(score=0.8, book_id="b1", book_title="The Keeper of Saltmere Light", chunk_index=n,
                text=f"passage {n}", headings=["Chapter 1: The Lighthouse"], page_start=1, page_end=1)
    return ChunkHit(**{**base, **kw})


class FakeSearch:
    def __init__(self, retrieval):
        self.retrieval = retrieval
        self.calls = []

    def retrieve(self, question, book_ids=None, top_k=None, min_score=None, follow_up_of=None):
        self.calls.append((question, book_ids, top_k))
        return self.retrieval


def _rag(retrieval, answer=None):
    calls = []

    def generator(system, user):
        calls.append((system, user))
        return answer

    # These tests describe strict mode (books only); hybrid mode is covered in test_rag_hybrid.py.
    return Rag(search=FakeSearch(retrieval), generator=generator if answer is not None else None,
               allow_general_knowledge=False), calls


def test_format_context_numbers_passages_with_section_and_pages():
    text = format_context([_hit(1), _hit(2, headings=[], page_start=2, page_end=3)])
    assert text.startswith("[1] The Keeper of Saltmere Light — Chapter 1: The Lighthouse, page 1\npassage 1")
    assert "[2] The Keeper of Saltmere Light — page 2-3\npassage 2" in text


def test_user_prompt_contains_question_after_context():
    prompt = build_user_prompt("Who built it?", [_hit()])
    assert prompt.index("[1]") < prompt.index("Question: Who built it?")


def test_extract_citations_keeps_valid_in_order():
    assert extract_citations("A [2]. B [1][2]. C [7] [0]", source_count=3) == [2, 1]


def test_no_indexed_books_answers_without_llm():
    rag, calls = _rag(Retrieval(hits=[], searched_book_ids=[], skipped=[{"id": "x", "reason": "not_indexed:none"}]), "unused")
    result = rag.ask(ChatAskDTO(question="Who built it?", bookIds=["x"]))
    assert result["mode"] == "no_indexed_books" and result["answer"] == NO_BOOKS_ANSWER
    assert result["grounded"] is False and calls == []
    assert result["skippedBooks"][0]["reason"] == "not_indexed:none"


def test_no_relevant_passages_answers_without_llm():
    rag, calls = _rag(Retrieval(hits=[], searched_book_ids=["b1"]), "unused")
    result = rag.ask(ChatAskDTO(question="What is the capital of Peru?"))
    assert result["mode"] == "no_context" and result["answer"] == NO_CONTEXT_ANSWER and calls == []


def test_retrieval_only_when_no_llm_configured(settings, monkeypatch):
    monkeypatch.setattr(settings, "LLM_MODEL", None)
    rag, _ = _rag(Retrieval(hits=[_hit()], searched_book_ids=["b1"]), answer=None)
    result = rag.ask(ChatAskDTO(question="Who built it?"))
    assert result["mode"] == "retrieval_only" and result["answer"] == RETRIEVAL_ONLY_ANSWER
    assert result["grounded"] is False and len(result["sources"]) == 1


def test_llm_answer_with_citations_is_grounded():
    rag, calls = _rag(Retrieval(hits=[_hit(1), _hit(2)], searched_book_ids=["b1"]),
                      "Agnes Morrow built it in 1847 [2].")
    result = rag.ask(ChatAskDTO(question="Who built it?"))
    assert result["mode"] == "llm" and result["grounded"] is True
    assert [s["cited"] for s in result["sources"]] == [False, True]
    system, user = calls[0]
    assert INSUFFICIENT_MARKER in system and "Question: Who built it?" in user


def test_llm_insufficient_marker_becomes_honest_answer():
    rag, _ = _rag(Retrieval(hits=[_hit()], searched_book_ids=["b1"]), INSUFFICIENT_MARKER)
    result = rag.ask(ChatAskDTO(question="What colour is the keeper's cat?"))
    assert result["mode"] == "insufficient_context" and result["answer"] == NO_CONTEXT_ANSWER
    assert result["grounded"] is False


def test_llm_answer_without_citations_is_flagged_ungrounded():
    rag, _ = _rag(Retrieval(hits=[_hit()], searched_book_ids=["b1"]), "It was built long ago.")
    result = rag.ask(ChatAskDTO(question="When?"))
    assert result["mode"] == "llm" and result["grounded"] is False
