"""
Local-disk storage for uploaded PDFs (MVP — no S3 server locally).

Files are stored as `<BOOK_STORAGE_DIR>/<book_id>.pdf`. The user's filename is only
kept as metadata and never used to build a path, so it can't escape the folder.
"""

import hashlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from config.base import settings

_READ_CHUNK = 1024 * 1024  # 1 MB — never hold the whole upload in memory
PDF_MAGIC = b"%PDF-"


@dataclass
class StoredFile:
    path: Path
    sha256: str
    size_bytes: int


def storage_dir() -> Path:
    directory = Path(settings.BOOK_STORAGE_DIR)
    if not directory.is_absolute():
        directory = Path(__file__).resolve().parent.parent / directory
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def save_pdf_upload(source: BinaryIO, max_bytes: int) -> StoredFile:
    """
    Stream an upload to a temporary file while hashing it.
    Rejects non-PDF content (magic bytes) and files over `max_bytes`.
    The caller moves the temp file into place with `finalize()` or removes it with `discard()`.
    """
    temp_path = storage_dir() / f".upload-{uuid.uuid4().hex}.part"
    digest = hashlib.sha256()
    size = 0
    try:
        with open(temp_path, "wb") as out:
            first = True
            while chunk := source.read(_READ_CHUNK):
                if first:
                    if not chunk.startswith(PDF_MAGIC):
                        raise ValueError("The file is not a PDF.")
                    first = False
                size += len(chunk)
                if size > max_bytes:
                    raise ValueError(f"The file is larger than {max_bytes // (1024 * 1024)} MB.")
                digest.update(chunk)
                out.write(chunk)
        if size == 0:
            raise ValueError("The file is empty.")
    except BaseException:
        discard(temp_path)
        raise
    return StoredFile(path=temp_path, sha256=digest.hexdigest(), size_bytes=size)


def finalize(stored: StoredFile, book_id) -> Path:
    """Atomically move the temp upload to `<book_id>.pdf` and return the final path."""
    final_path = book_file_path(book_id)
    os.replace(stored.path, final_path)
    return final_path


def book_file_path(book_id) -> Path:
    return storage_dir() / f"{uuid.UUID(str(book_id))}.pdf"


def discard(path) -> None:
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        pass
