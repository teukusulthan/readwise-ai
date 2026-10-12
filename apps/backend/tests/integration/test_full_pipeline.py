"""
End-to-end with every real component: Docling parsing, the company embedding
service, PostgreSQL and Qdrant. The LLM is LiteLLM's built-in mock (no API key yet).

    uv run pytest -m "integration and external and docling" tests/integration/test_full_pipeline.py
"""

from pathlib import Path

import pytest

import router.book as book_router
import router.chat as chat_router
from config.base import settings

pytestmark = [pytest.mark.integration, pytest.mark.external, pytest.mark.docling]

SAMPLE = Path(__file__).resolve().parent.parent / "fixtures" / "sample_book.pdf"


@pytest.fixture(autouse=True)
def real_services(monkeypatch, embedding_base_url):
    monkeypatch.setattr(settings, "ENGINE_EMBEDDING_BASE_URL", embedding_base_url)
    monkeypatch.setattr(settings, "ENGINE_EMBEDDING_MODEL", "Qwen3-Embedding-0.6B")
    monkeypatch.setattr(book_router.obj.ingestion, "run_inline", True)


async def test_pdf_to_grounded_answer(client, monkeypatch):
    upload = await client.post("/book/upload", data={"title": "The Keeper of Saltmere Light"},
                               files={"file": ("saltmere.pdf", SAMPLE.read_bytes(), "application/pdf")})
    assert upload.status_code == 200, upload.text
    book = (await client.get("/book/get-one", params={"id": upload.json()["data"]["id"]})).json()["data"]
    assert book["ingestion"]["status"] == "indexed", book["ingestion"]
    assert book["document"]["pageCount"] == 3 and book["ingestion"]["chunkCount"] >= 4

    hits = (await client.post("/search/query", json={"query": "Who rescued the crew of the Marigold?"})).json()["data"]
    top = hits["results"][0]
    assert top["pageStart"] == 3 and "Chapter 3" in " ".join(top["headings"])

    # Regression: a short factual question scored below the threshold before the query instruction was enabled.
    steps = (await client.post("/search/query", json={"query": "How many steps does the tower have?"})).json()["data"]
    assert steps["results"] and steps["results"][0]["pageStart"] == 2 and "142 steps" in steps["results"][0]["text"]

    # LLM path through Agno + LiteLLM, using LiteLLM's mock response instead of a real provider.
    from service.llm import agno_generator

    monkeypatch.setattr(settings, "LLM_MODEL", "openai/mock-model")
    monkeypatch.setattr(chat_router.obj, "_generator",
                        agno_generator(request_params={"mock_response": "The Penhallow lifeboat rescued all seven crew [1]."}))
    answer = (await client.post("/chat/ask", json={"question": "Who rescued the crew of the Marigold?"})).json()["data"]
    assert answer["mode"] == "llm" and answer["grounded"] is True
    assert answer["sources"][0]["cited"] is True and answer["sources"][0]["pageStart"] == 3

    # Nothing relevant in the books: hybrid mode answers from general knowledge (labeled), strict mode refuses.
    off_topic = (await client.post("/chat/ask", json={"question": "What is the boiling point of mercury?"})).json()["data"]
    assert off_topic["mode"] == "general_knowledge" and off_topic["sources"] == []
    assert off_topic["usedGeneralKnowledge"] is True and off_topic["answer"].startswith("GENERAL KNOWLEDGE:")
    monkeypatch.setattr(settings, "RAG_ALLOW_GENERAL_KNOWLEDGE", False)
    strict = (await client.post("/chat/ask", json={"question": "What is the boiling point of mercury?"})).json()["data"]
    assert strict["mode"] == "no_context" and strict["sources"] == []
