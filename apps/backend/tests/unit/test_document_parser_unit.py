from types import SimpleNamespace

from util.document_parser import _page_range


def _chunk(*page_lists):
    items = [SimpleNamespace(prov=[SimpleNamespace(page_no=p) for p in pages]) for pages in page_lists]
    return SimpleNamespace(meta=SimpleNamespace(doc_items=items))


def test_page_range_spans_all_items():
    assert _page_range(_chunk([3], [4, 5])) == (3, 5)


def test_page_range_unknown_without_provenance():
    assert _page_range(_chunk([])) == (None, None)
    assert _page_range(SimpleNamespace(meta=SimpleNamespace(doc_items=[]))) == (None, None)


def test_windowed_parsing_covers_all_pages_and_carries_headings(monkeypatch):
    import util.document_parser as parser

    windows = []

    def fake_convert(path, page_range=None):
        windows.append(page_range)
        return page_range

    def fake_chunks(document):
        start, end = document
        if start == 1:
            yield {"text": "intro", "embed_text": "Chapter 1\nintro", "headings": ["Chapter 1"],
                   "page_start": 1, "page_end": 1}
        else:  # continuation of Chapter 1 in the next window: Docling sees no heading here
            yield {"text": "more", "embed_text": "more", "headings": [], "page_start": start, "page_end": start}

    monkeypatch.setattr(parser, "convert", fake_convert)
    monkeypatch.setattr(parser, "chunk_document", fake_chunks)
    chunks = list(parser._windowed_chunks("book.pdf", page_count=5, window=2))

    assert windows == [(1, 2), (3, 4), (5, 5)]
    assert [c["headings"] for c in chunks] == [["Chapter 1"]] * 3
    assert chunks[1]["embed_text"] == "Chapter 1\nmore"


def test_parse_pdf_counts_pages_before_any_conversion(monkeypatch):
    import util.document_parser as parser

    monkeypatch.setattr(parser, "count_pages", lambda path: 7)
    monkeypatch.setattr(parser, "convert", lambda *a, **k: (_ for _ in ()).throw(AssertionError("too early")))
    pages, chunks = parser.parse_pdf("book.pdf")
    assert pages == 7  # chunks are lazy: nothing parsed until the job iterates


def test_converter_uses_configured_threads_and_layout_batch_size(monkeypatch):
    from docling import document_converter

    from config.base import settings
    from util import document_parser

    captured = {}
    monkeypatch.setattr(document_converter, "DocumentConverter", lambda **kw: captured.update(kw) or object())
    monkeypatch.setattr(settings, "DOCLING_NUM_THREADS", 6)
    monkeypatch.setattr(settings, "DOCLING_LAYOUT_BATCH_SIZE", 2)
    document_parser._converter.cache_clear()
    try:
        document_parser._converter()
    finally:
        document_parser._converter.cache_clear()

    (fmt,) = captured["format_options"].values()
    assert fmt.pipeline_options.layout_batch_size == 2
    assert fmt.pipeline_options.accelerator_options.num_threads == 6


def test_docling_speed_defaults():
    from config.base import BaseSetting

    assert BaseSetting.__fields__["DOCLING_NUM_THREADS"].default == 8
    assert BaseSetting.__fields__["DOCLING_LAYOUT_BATCH_SIZE"].default == 1
