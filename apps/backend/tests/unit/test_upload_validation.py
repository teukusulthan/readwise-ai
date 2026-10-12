import io
from types import SimpleNamespace

import pytest

from dto.upload import UploadFileDTO
from service.upload import Upload

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"


@pytest.fixture(scope="module")
def upload():
    return Upload()


def test_pdf_magic_bytes_accepted(upload):
    assert upload._validate_mime_by_magic(io.BytesIO(PDF_BYTES)) == "application/pdf"


def test_unidentified_binary_rejected(upload):
    # Random binary is detected as application/octet-stream, which is no longer whitelisted.
    with pytest.raises(ValueError):
        upload._validate_mime_by_magic(io.BytesIO(bytes(range(256)) * 8))


def test_disallowed_extension_rejected(upload):
    with pytest.raises(ValueError):
        upload._validate_extension("payload.exe")


@pytest.mark.parametrize("name", ["../../etc/passwd", "..\\..\\boot.ini", "a\x00b.pdf"])
def test_path_traversal_and_null_bytes_neutralised(upload, name):
    try:
        cleaned = upload._sanitize_filename(name)
    except ValueError:
        return
    assert "/" not in cleaned and "\\" not in cleaned and ".." not in cleaned


def test_oversized_upload_rejected_before_storage(upload, settings):
    too_big = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024 + 1
    fake_file = SimpleNamespace(size=too_big, filename="book.pdf", file=io.BytesIO(PDF_BYTES))
    with pytest.raises(ValueError, match="exceeds the maximum"):
        upload.upload_file(fake_file, fake_file.file, UploadFileDTO(createdBy="tester"))
