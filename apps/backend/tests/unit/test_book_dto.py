import pytest
from pydantic import ValidationError

from dto.book import BookDTO, ImportBookDTO, normalize_isbn


@pytest.mark.parametrize("raw, expected", [
    ("978-0-441-01359-3", "9780441013593"),   # ISBN-13 with hyphens
    ("0 441 17271 7", "0441172717"),           # ISBN-10 with spaces
    ("080442957X", "080442957X"),              # ISBN-10 with X check digit
    ("", None),
    (None, None),
])
def test_normalize_isbn_accepts_valid(raw, expected):
    assert normalize_isbn(raw) == expected


@pytest.mark.parametrize("raw", ["9780441013594", "123", "0441172718", "abcdefghij"])
def test_normalize_isbn_rejects_bad_checksum_or_shape(raw):
    with pytest.raises(ValueError):
        normalize_isbn(raw)


def test_book_dto_cleans_input():
    dto = BookDTO(title="  Dune ", authors=[" Frank Herbert ", ""], isbn="978-0-441-01359-3")
    assert dto.title == "Dune"
    assert dto.authors == ["Frank Herbert"]
    assert dto.isbn == "9780441013593"


@pytest.mark.parametrize("payload", [{"title": "   "}, {"title": "x", "coverUrl": "javascript:alert(1)"}, {"title": "x", "publishedYear": 99999}])
def test_book_dto_rejects_invalid(payload):
    with pytest.raises(ValidationError):
        BookDTO(**payload)


def test_import_requires_isbn():
    with pytest.raises(ValidationError):
        ImportBookDTO(isbn="")
