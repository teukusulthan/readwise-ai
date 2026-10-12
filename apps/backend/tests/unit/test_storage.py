import hashlib
import io
import uuid

import pytest

from util import storage

PDF = b"%PDF-1.4\n" + b"x" * 5000


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path, settings, monkeypatch):
    monkeypatch.setattr(settings, "BOOK_STORAGE_DIR", str(tmp_path))
    return tmp_path


def test_streams_pdf_to_temp_and_hashes(isolated_storage):
    stored = storage.save_pdf_upload(io.BytesIO(PDF), max_bytes=10_000)
    assert stored.sha256 == hashlib.sha256(PDF).hexdigest()
    assert stored.size_bytes == len(PDF)
    assert stored.path.parent == isolated_storage and stored.path.read_bytes() == PDF


def test_finalize_names_file_by_book_id(isolated_storage):
    stored = storage.save_pdf_upload(io.BytesIO(PDF), max_bytes=10_000)
    book_id = uuid.uuid4()
    final = storage.finalize(stored, book_id)
    assert final == isolated_storage / f"{book_id}.pdf" and final.exists() and not stored.path.exists()


@pytest.mark.parametrize("content, message", [
    (b"<html>not a pdf</html>", "not a PDF"),
    (b"", "empty"),
    (PDF, "larger than"),
])
def test_rejects_bad_uploads_and_leaves_no_temp_file(isolated_storage, content, message):
    with pytest.raises(ValueError, match=message):
        storage.save_pdf_upload(io.BytesIO(content), max_bytes=1000)
    assert list(isolated_storage.iterdir()) == []


def test_book_file_path_rejects_non_uuid():
    with pytest.raises(ValueError):
        storage.book_file_path("../../etc/passwd")
