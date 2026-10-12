import os
from time import time
from typing import Optional
from urllib.parse import quote

from fastapi.responses import FileResponse
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from middleware.route_limits import route_limit

from dto.book import BookDTO, FindBookDTO, ImportBookDTO, UpdateBookDTO
from models.base_response import BaseResponse
from models.metadata import MetadataSuccess
from models.pagination import Pagination
from service.book import Book
from util.helper import get_execution_time, is_include_schema, router_param_builder
from util.http_errors import to_http_exception

obj = Book()


def inline_disposition(name: str) -> str:
    """`inline` Content-Disposition: quoted ASCII fallback plus RFC 5987 `filename*` for other characters."""
    clean = "".join(ch for ch in name if ch.isprintable() and ch not in '"\\/;').strip() or "document.pdf"
    ascii_name = clean.encode("ascii", "replace").decode().replace("?", "_")
    header = f'inline; filename="{ascii_name}"'
    if ascii_name != clean:
        header += f"; filename*=UTF-8''{quote(clean)}"
    return header

tag = os.path.splitext(os.path.basename(os.path.abspath(__file__)))[0]
router = APIRouter(**router_param_builder(tag))


def _ok(data, start_time, pagination: Optional[Pagination] = None):
    meta = MetadataSuccess(executionTime=get_execution_time(start_time))
    if pagination:
        meta.pagination = pagination
    return BaseResponse(data=data, metaData=meta)


@router.post("/add", include_in_schema=is_include_schema(tag, "add"))
def add(dto: BookDTO):
    """Create a catalog entry (metadata only — not searchable until a PDF is indexed)."""
    start_time = time()
    try:
        return _ok(obj.add(dto), start_time)
    except Exception as error:
        raise to_http_exception(error, start_time)


@router.put("/update", include_in_schema=is_include_schema(tag, "update"))
def update(dto: UpdateBookDTO):
    start_time = time()
    try:
        return _ok(obj.update(dto), start_time)
    except Exception as error:
        raise to_http_exception(error, start_time)


@router.post("/get-all", include_in_schema=is_include_schema(tag, "get-all"))
def get_all(dto: FindBookDTO):
    """List/search the catalog. `search` matches title, author, ISBN or publisher; `status` filters ingestion."""
    start_time = time()
    try:
        data, count = obj.get_all(dto)
        return _ok(data, start_time, Pagination.count_total_pages(dto.size, count))
    except Exception as error:
        raise to_http_exception(error, start_time)


@router.get("/get-one", include_in_schema=is_include_schema(tag, "get-one"))
def get_by_id(id: str):
    start_time = time()
    try:
        return _ok(obj.get_by_id(id), start_time)
    except Exception as error:
        raise to_http_exception(error, start_time)


@router.get("/file", include_in_schema=is_include_schema(tag, "file"))
def file(id: str):
    """Stream the stored PDF inline (open with `#page=N` to jump to a page). 404 when the book or its file is missing."""
    start_time = time()
    try:
        path, name = obj.get_document(id)
        return FileResponse(path, media_type="application/pdf", headers={"Content-Disposition": inline_disposition(name)})
    except Exception as error:
        raise to_http_exception(error, start_time)


@router.delete("/delete", include_in_schema=is_include_schema(tag, "delete"))
def delete(id: str):
    """Delete the book, its stored PDF and its vectors."""
    start_time = time()
    try:
        return _ok(obj.delete(id), start_time)
    except Exception as error:
        raise to_http_exception(error, start_time)


@router.post("/upload", include_in_schema=is_include_schema(tag, "upload"), dependencies=[Depends(route_limit("upload"))])
def upload(
    file: UploadFile = File(..., description="PDF document"),
    bookId: Optional[str] = Form(default=None, description="Attach to an existing catalog entry"),
    title: Optional[str] = Form(default=None, max_length=500, description="Title for a new book"),
):
    """Upload a PDF and queue it for indexing. Poll /book/get-one for `ingestion.status`."""
    start_time = time()
    try:
        if not (file.filename or "").lower().endswith(".pdf"):
            raise ValueError("Only .pdf files are supported.")
        return _ok(obj.upload_document(file.file, file.filename, book_id=bookId, title=title), start_time)
    except Exception as error:
        raise to_http_exception(error, start_time)


@router.post("/reindex", include_in_schema=is_include_schema(tag, "reindex"))
def reindex(id: str):
    """Re-run indexing for a book that is `indexed` or `failed` (safe to repeat)."""
    start_time = time()
    try:
        return _ok(obj.reindex(id), start_time)
    except Exception as error:
        raise to_http_exception(error, start_time)


@router.get("/lookup", include_in_schema=is_include_schema(tag, "lookup"))
def lookup(q: str = Query(min_length=1, max_length=200)):
    """Search Open Library for books to import (metadata only)."""
    start_time = time()
    try:
        return _ok(obj.lookup_external(q), start_time)
    except Exception as error:
        raise to_http_exception(error, start_time)


@router.post("/import", include_in_schema=is_include_schema(tag, "import"))
def import_book(dto: ImportBookDTO):
    """Import one book's metadata from Open Library by ISBN."""
    start_time = time()
    try:
        return _ok(obj.import_by_isbn(dto.isbn), start_time)
    except Exception as error:
        raise to_http_exception(error, start_time)
