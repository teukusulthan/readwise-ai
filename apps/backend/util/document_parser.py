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
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import AcceleratorOptions, PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions(
        do_ocr=settings.DOCLING_DO_OCR,
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


def convert(pdf_path: str, page_range: Optional[tuple[int, int]] = None):
    """
    PDF file (or a 1-based inclusive page range of it) → DoclingDocument.
    Page numbers in the result stay absolute. Serialized: Docling models are heavy.
    """
    kwargs = {"page_range": page_range} if page_range else {}
    with _converter_lock:
        result = _converter().convert(
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


def parse_pdf(pdf_path: str) -> tuple[Optional[int], Iterator[dict]]:
    """
    Entry point used by the ingestion job: (page_count, lazily generated chunks).

    The page count is known before any parsing (so the page limit is checked cheaply),
    and the PDF is converted in windows of DOCLING_PAGE_WINDOW pages: only one window's
    document is in memory at a time.
    """
    page_count = count_pages(pdf_path)
    return page_count, _windowed_chunks(pdf_path, page_count, max(1, settings.DOCLING_PAGE_WINDOW))


def _windowed_chunks(pdf_path: str, page_count: int, window: int) -> Iterator[dict]:
    last_headings: list[str] = []
    for start in range(1, page_count + 1, window):
        end = min(page_count, start + window - 1)
        logger.info("Parsing pages {start}-{end} of {total}", start=start, end=end, total=page_count)
        document = convert(pdf_path, page_range=(start, end))
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
