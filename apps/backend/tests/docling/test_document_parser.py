"""
Real Docling + HybridChunker on tests/fixtures/sample_book.pdf (original text, 3 pages).
Run: `uv run pytest -m docling` — first run downloads Docling models and the tokenizer (~500 MB).
"""

from pathlib import Path

import pytest

from util.document_parser import parse_pdf

pytestmark = pytest.mark.docling

SAMPLE = Path(__file__).resolve().parent.parent / "fixtures" / "sample_book.pdf"


@pytest.fixture(scope="module")
def parsed():
    pages, chunks = parse_pdf(str(SAMPLE))
    return pages, list(chunks)


def test_page_count(parsed):
    assert parsed[0] == 3


def test_chunks_keep_headings_and_pages(parsed):
    _, chunks = parsed
    by_heading = {tuple(c["headings"]): c for c in chunks}
    storm = by_heading[("Chapter 3: The Great Storm of 1911",)]
    assert storm["page_start"] == storm["page_end"] == 3
    assert "Thomas Hale" in storm["text"]
    assert by_heading[("Chapter 1: The Lighthouse",)]["page_start"] == 1


def test_table_content_is_preserved(parsed):
    table = next(c for c in parsed[1] if "Paraffin" in c["text"])
    assert "40 litres" in table["text"] and table["page_start"] == 2


def test_embed_text_includes_heading_context(parsed):
    chunk = next(c for c in parsed[1] if "Agnes Morrow" in c["text"])
    assert chunk["embed_text"].startswith("Chapter 1: The Lighthouse")
    assert chunk["text"] in chunk["embed_text"]


def test_small_windows_give_same_pages_and_headings(settings, monkeypatch):
    monkeypatch.setattr(settings, "DOCLING_PAGE_WINDOW", 1)  # one page per Docling pass
    pages, chunks = parse_pdf(str(SAMPLE))
    chunks = list(chunks)
    assert pages == 3
    assert sorted({c["page_start"] for c in chunks}) == [1, 2, 3]
    storm = next(c for c in chunks if "Thomas Hale" in c["text"])
    assert storm["headings"] == ["Chapter 3: The Great Storm of 1911"] and storm["page_start"] == 3
