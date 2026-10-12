"""
PDF → structure-aware chunks, using Docling (verified against docling 2.129.0 / docling-core 2.96).

1. DocumentConverter turns the PDF into a DoclingDocument: headings, paragraphs,
   tables and list items, each with provenance (which page it came from).
2. HybridChunker splits that document along its structure (sections, paragraphs,
   tables) and then by token count, using the *embedding model's* tokenizer so no
   chunk exceeds CHUNK_MAX_TOKENS for that model. Small neighbouring pieces under the
   same heading are merged (merge_peers).
3. For every chunk we keep:
     text        the chunk text shown to users as a source
     embed_text  heading path + text (chunker.contextualize) — what gets embedded,
                 so "Chapter 3 > Storm" context improves retrieval
     headings    the section path, e.g. ["Chapter 3: The Great Storm of 1911"]
     page_start/page_end  from the provenance of the chunk's items
"""

import gc
import threading
from functools import lru_cache
from typing import Iterator, Optional

from loguru import logger

from config.base import settings

_converter_lock = threading.Lock()


@lru_cache(maxsize=1)
def _converter():
    # Building the converter loads the layout/table models — do it once per process.
    return _build_converter(do_ocr=settings.DOCLING_DO_OCR)


@lru_cache(maxsize=1)
def _ocr_converter():
    # OCR fallback for scanned PDFs: a separate instance, built only the first time it is needed.
    return _build_converter(do_ocr=True)


@lru_cache(maxsize=1)
def ocr_available() -> bool:
    """
    Whether Docling has a usable OCR engine, probed once per process (the answer is cached).

    Docling's automatic engine choice does not fail when no engine can be loaded: it logs
    "No OCR engine found" and converts without OCR. So the OCR converter's pipeline is built
    here (it is reused for the OCR pass) and its OCR model inspected: the auto model keeps the
    engine it picked in `_engine` (None = nothing usable); an explicitly chosen engine is the
    model itself. Any error while building it counts as "not available".
    """
    from docling.datamodel.base_models import InputFormat

    try:
        with _converter_lock:
            converter = _converter() if settings.DOCLING_DO_OCR else _ocr_converter()
            converter.initialize_pipeline(InputFormat.PDF)
            pipelines = list(converter.initialized_pipelines.values())
    except Exception:
        logger.exception("Could not build the Docling OCR pipeline")
        return False
    models = [p.ocr_model for p in pipelines if getattr(p, "ocr_model", None) is not None]
    available = bool(models) and all(getattr(m, "_engine", m) is not None for m in models)
    logger.info("Docling OCR engine available: {available}", available=available)
    return available


def _build_converter(do_ocr: bool):
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import AcceleratorOptions, PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(
        do_ocr=do_ocr,
        do_table_structure=settings.DOCLING_DO_TABLE_STRUCTURE,
        generate_page_images=False,
        generate_picture_images=False,
        layout_batch_size=settings.DOCLING_LAYOUT_BATCH_SIZE,
        accelerator_options=AcceleratorOptions(num_threads=settings.DOCLING_NUM_THREADS, device="cpu"),
    )
    logger.info("Initialising Docling converter (ocr={ocr}, tables={tables}, threads={threads}, "
                "layout_batch={batch})",
                ocr=options.do_ocr, tables=options.do_table_structure, threads=settings.DOCLING_NUM_THREADS,
                batch=options.layout_batch_size)
    return DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})


@lru_cache(maxsize=1)
def _chunker():
    from docling.chunking import HybridChunker
    from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer

    tokenizer = HuggingFaceTokenizer.from_pretrained(settings.CHUNK_TOKENIZER, max_tokens=settings.CHUNK_MAX_TOKENS)
    return HybridChunker(tokenizer=tokenizer, merge_peers=True)


def count_pages(pdf_path: str) -> int:
    """Cheap page count (pypdfium2 ships with Docling) — no layout analysis."""
    import pypdfium2

    pdf = pypdfium2.PdfDocument(pdf_path)
    try:
        return len(pdf)
    finally:
        pdf.close()


def convert(pdf_path: str, page_range: Optional[tuple[int, int]] = None, ocr: bool = False):
    """
    PDF file (or a 1-based inclusive page range of it) → DoclingDocument.
    Page numbers in the result stay absolute. Serialized: Docling models are heavy.
    `ocr=True` uses the OCR converter (scanned PDFs); otherwise the configured one.
    """
    kwargs = {"page_range": page_range} if page_range else {}
    with _converter_lock:
        converter = _ocr_converter() if ocr else _converter()  # built under the lock: models load once
        result = converter.convert(
            pdf_path,
            max_num_pages=settings.MAX_PDF_PAGES,
            max_file_size=settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024,
            **kwargs,
        )
    return result.document


def chunk_document(document) -> Iterator[dict]:
    chunker = _chunker()
    for chunk in chunker.chunk(dl_doc=document):
        text = chunk.text.strip()
        if not text:
            continue
        page_start, page_end = _page_range(chunk)
        yield {
            "text": text,
            "embed_text": chunker.contextualize(chunk=chunk),
            "headings": list(chunk.meta.headings or []),
            "page_start": page_start,
            "page_end": page_end,
        }


def parse_pdf(pdf_path: str, ocr: bool = False) -> tuple[Optional[int], Iterator[dict]]:
    """
    Entry point used by the ingestion job: (page_count, lazily generated chunks).

    The page count is known before any parsing (so the page limit is checked cheaply),
    and the PDF is converted in windows of DOCLING_PAGE_WINDOW pages: only one window's
    document is in memory at a time. `ocr=True` is the job's fallback for scanned PDFs.
    """
    page_count = count_pages(pdf_path)
    return page_count, _windowed_chunks(pdf_path, page_count, max(1, settings.DOCLING_PAGE_WINDOW), ocr=ocr)


def _windowed_chunks(pdf_path: str, page_count: int, window: int, ocr: bool = False) -> Iterator[dict]:
    last_headings: list[str] = []
    for start in range(1, page_count + 1, window):
        end = min(page_count, start + window - 1)
        logger.info("Parsing pages {start}-{end} of {total}{ocr}", start=start, end=end, total=page_count,
                    ocr=" with OCR" if ocr else "")
        document = convert(pdf_path, page_range=(start, end), ocr=ocr)
        for chunk in chunk_document(document):
            # A section that continues past a window boundary has no heading in the next
            # window's document: keep the heading it had in the previous window.
            if chunk["headings"]:
                last_headings = chunk["headings"]
            elif last_headings:
                chunk["headings"] = list(last_headings)
                chunk["embed_text"] = "\n".join(last_headings + [chunk["text"]])
            yield chunk
        del document
        gc.collect()


def _page_range(chunk) -> tuple[Optional[int], Optional[int]]:
    pages = [
        prov.page_no
        for item in (chunk.meta.doc_items or [])
        for prov in (getattr(item, "prov", None) or [])
        if getattr(prov, "page_no", None) is not None
    ]
    return (min(pages), max(pages)) if pages else (None, None)
