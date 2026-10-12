"""Hybrid answers: books first (cited), general knowledge allowed but always labeled."""

import pytest

from dto.chat import ChatAskDTO
from service.rag import (EMPTY_ANSWER_ERROR, GENERAL_HEADING, SYSTEM_PROMPT_HYBRID, Rag, build_user_prompt, split_general)
from service.search import Retrieval
from service.vector_store import ChunkHit
from util.http_errors import ServiceUnavailableError


def _hit(n=1):
    return ChunkHit(score=0.8, book_id="b1", book_title="The Subtle Art", chunk_index=n, text=f"passage {n}",
                    headings=["Chapter 5"], page_start=111, page_end=112)


class FakeSearch:
    def __init__(self, retrieval):
        self.retrieval = retrieval

    def retrieve(self, question, book_ids=None, top_k=None, min_score=None, follow_up_of=None):
        return self.retrieval


def _ask(retrieval, answer):
    prompts = []

    def generator(system, user):
        prompts.append((system, user))
        return answer

    rag = Rag(search=FakeSearch(retrieval), generator=generator, allow_general_knowledge=True)
    return rag.ask(ChatAskDTO(question="What is the do something principle?")), prompts


def _stream_rag(retrieval, pieces):
    async def stream(system, user):
        for piece in pieces:
            yield piece
    return Rag(search=FakeSearch(retrieval), streamer=stream, allow_general_knowledge=True)


BOOKS = [{"id": "b1", "title": "The Subtle Art", "authors": ["Mark Manson"], "year": 2016, "description": None, "indexed": True},
         {"id": "b2", "title": "Atomic Habits", "authors": ["James Clear"], "year": 2018, "description": None, "indexed": False}]


def test_split_general_tolerates_markdown_and_inline_text():
    assert split_general("Fact [1].\n\nGENERAL KNOWLEDGE:\nMore.") == ("Fact [1].\n\n", "\nMore.")
    assert split_general("Fact [1].\n**General knowledge:** More.")[1] == "More."
    assert split_general("Only books [1].") == ("Only books [1].", None)


def test_split_general_requires_the_colon():
    assert split_general("Fact [1].\n\nGeneral knowledge of the era says more.") == ("Fact [1].\n\nGeneral knowledge of the era says more.", None)
    assert split_general("Fact [1].\nGeneral knowledge\nno colon.")[1] is None
    assert split_general("Fact [1].\n\nGENERAL KNOWLEDGE:\nMore.")[1] == "\nMore."
    assert split_general("Fact [1].\n**General knowledge:** More.")[1] == "More."


def test_book_answer_with_general_section_keeps_both_parts_apart():
    result, prompts = _ask(Retrieval(hits=[_hit(1), _hit(2)], searched_book_ids=["b1"]),
                           "Action comes before motivation [2].\n\ngeneral knowledge:\nThe idea is also known as behavioral activation.")
    assert prompts[0][0] == SYSTEM_PROMPT_HYBRID
    assert result["mode"] == "llm" and result["grounded"] is True and result["usedGeneralKnowledge"] is True
    assert result["answer"] == ("Action comes before motivation [2].\n\n" + GENERAL_HEADING +
                                "\n\nThe idea is also known as behavioral activation.")
    assert [s["cited"] for s in result["sources"]] == [False, True]


def test_citations_inside_the_general_section_do_not_count():
    result, _ = _ask(Retrieval(hits=[_hit(1)], searched_book_ids=["b1"]), "GENERAL KNOWLEDGE:\nSomething [1].")
    assert result["mode"] == "general_knowledge" and result["grounded"] is False
    assert result["sources"][0]["cited"] is False


def test_no_passages_still_calls_the_llm_and_everything_is_general_knowledge():
    # The model forgot the heading: with zero passages nothing can come from the books anyway.
    result, prompts = _ask(Retrieval(hits=[], searched_book_ids=["b1"]), "Your books do not cover this. Mercury boils at 357 C.")
    assert "Context passages: none" in prompts[0][1]
    assert result["mode"] == "general_knowledge" and result["usedGeneralKnowledge"] is True
    assert result["answer"] == f"{GENERAL_HEADING}\n\nYour books do not cover this. Mercury boils at 357 C."


def test_no_indexed_books_also_falls_back_to_general_knowledge():
    result, prompts = _ask(Retrieval(hits=[], searched_book_ids=[], skipped=[{"id": "b2", "title": "Atomic Habits",
                                                                             "reason": "not_indexed:none"}]),
                           "GENERAL KNOWLEDGE:\nAtomic Habits is not indexed; in general it argues ...")
    assert prompts and result["mode"] == "general_knowledge"
    assert result["skippedBooks"][0]["title"] == "Atomic Habits"


def test_empty_answer_is_an_error_not_insufficient_context():
    with pytest.raises(ServiceUnavailableError, match="empty answer"):
        _ask(Retrieval(hits=[_hit()], searched_book_ids=["b1"]), "   ")


def test_prompt_lists_books_and_marks_unindexed_ones():
    prompt = build_user_prompt("According to Atomic Habits?", [_hit()], books=BOOKS)
    assert "Books involved:\n- The Subtle Art by Mark Manson (2016)" in prompt
    assert "- Atomic Habits by James Clear (2018) — text not available (catalog entry only)" in prompt
    assert prompt.index("Books involved") < prompt.index("Context passages") < prompt.index("Question:")


async def test_stream_passes_text_through_and_labels_the_final_answer():
    rag = _stream_rag(Retrieval(hits=[_hit()], searched_book_ids=["b1"]),
                      ["Act first [1].", "\n\nGENERAL KNOWLEDGE:\n", "Psychologists agree."])
    events = [e async for e in rag.ask_stream(ChatAskDTO(question="q"))]
    deltas = "".join(d["text"] for n, d in events if n == "delta")
    assert deltas == "Act first [1].\n\nGENERAL KNOWLEDGE:\nPsychologists agree."
    done = events[-1][1]
    assert events[-1][0] == "done" and done["usedGeneralKnowledge"] is True and done["grounded"] is True


async def test_stream_empty_answer_is_an_error_event():
    rag = _stream_rag(Retrieval(hits=[_hit()], searched_book_ids=["b1"]), ["", "  "])
    events = [e async for e in rag.ask_stream(ChatAskDTO(question="q"))]
    assert events[-1] == ("error", {"message": EMPTY_ANSWER_ERROR, "code": 503})


def test_strict_mode_keeps_a_real_answer_that_mentions_the_marker():
    rag = Rag(search=FakeSearch(Retrieval(hits=[_hit()], searched_book_ids=["b1"])),
              generator=lambda s, u: "Action comes first [1]. The books do not say who coined it. INSUFFICIENT_CONTEXT",
              allow_general_knowledge=False)
    result = rag.ask(ChatAskDTO(question="q"))
    assert result["mode"] == "llm" and "INSUFFICIENT_CONTEXT" not in result["answer"]
