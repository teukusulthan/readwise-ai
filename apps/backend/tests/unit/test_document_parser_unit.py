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

    def fake_convert(path, page_range=None, ocr=False):
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


def test_ocr_converter_is_cached_separately_with_ocr_on_and_the_same_speed_settings(monkeypatch):
    from docling import document_converter

    from config.base import settings
    from util import document_parser

    built = []
    monkeypatch.setattr(document_converter, "DocumentConverter", lambda **kw: built.append(kw) or object())
    monkeypatch.setattr(settings, "DOCLING_DO_OCR", False)
    monkeypatch.setattr(settings, "DOCLING_NUM_THREADS", 6)
    monkeypatch.setattr(settings, "DOCLING_LAYOUT_BATCH_SIZE", 2)
    document_parser._converter.cache_clear()
    document_parser._ocr_converter.cache_clear()
    try:
        plain, ocr = document_parser._converter(), document_parser._ocr_converter()
        assert plain is not ocr and document_parser._ocr_converter() is ocr  # built once, kept apart
    finally:
        document_parser._converter.cache_clear()
        document_parser._ocr_converter.cache_clear()

    (plain_fmt,), (ocr_fmt,) = (kw["format_options"].values() for kw in built)
    assert plain_fmt.pipeline_options.do_ocr is False and ocr_fmt.pipeline_options.do_ocr is True
    assert ocr_fmt.pipeline_options.layout_batch_size == 2
    assert ocr_fmt.pipeline_options.accelerator_options.num_threads == 6


def test_convert_uses_the_ocr_converter_only_when_asked(monkeypatch):
    from types import SimpleNamespace

    import util.document_parser as parser

    def converter(name):
        return SimpleNamespace(convert=lambda path, **kw: SimpleNamespace(document=name))

    monkeypatch.setattr(parser, "_converter", lambda: converter("plain"))
    monkeypatch.setattr(parser, "_ocr_converter", lambda: converter("ocr"))
    assert parser.convert("book.pdf", page_range=(1, 2)) == "plain"
    assert parser.convert("book.pdf", page_range=(1, 2), ocr=True) == "ocr"


def test_parse_pdf_passes_the_ocr_flag_to_every_window(monkeypatch):
    import util.document_parser as parser

    flags = []
    monkeypatch.setattr(parser, "count_pages", lambda path: 3)
    monkeypatch.setattr(parser, "convert", lambda path, page_range=None, ocr=False: flags.append(ocr))
    monkeypatch.setattr(parser, "chunk_document", lambda document: iter(()))
    monkeypatch.setattr(parser.settings, "DOCLING_PAGE_WINDOW", 2)
    list(parser.parse_pdf("book.pdf", ocr=True)[1])
    list(parser.parse_pdf("book.pdf")[1])
    assert flags == [True, True, False, False]


def test_self_healing_defaults():
    from config.base import BaseSetting

    assert BaseSetting.__fields__["INGESTION_MAX_ATTEMPTS"].default == 3
    assert BaseSetting.__fields__["DOCLING_OCR_FALLBACK"].default is True


def test_docling_speed_defaults():
    from config.base import BaseSetting

    assert BaseSetting.__fields__["DOCLING_NUM_THREADS"].default == 8
    assert BaseSetting.__fields__["DOCLING_LAYOUT_BATCH_SIZE"].default == 1
