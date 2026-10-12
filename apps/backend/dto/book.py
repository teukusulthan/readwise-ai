import re
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from dto import FindDTO

_ISBN_CLEAN_RE = re.compile(r"[\s-]")


def normalize_isbn(value: Optional[str]) -> Optional[str]:
    """Strip spaces/hyphens and check the ISBN-10/13 shape and checksum. Returns None for empty."""
    if value is None:
        return None
    isbn = _ISBN_CLEAN_RE.sub("", value).upper()
    if not isbn:
        return None
    if len(isbn) == 10 and re.fullmatch(r"\d{9}[\dX]", isbn):
        total = sum((10 - i) * (10 if ch == "X" else int(ch)) for i, ch in enumerate(isbn))
        if total % 11 == 0:
            return isbn
    elif len(isbn) == 13 and isbn.isdigit():
        total = sum((1 if i % 2 == 0 else 3) * int(ch) for i, ch in enumerate(isbn))
        if total % 10 == 0:
            return isbn
    raise ValueError(f"Invalid ISBN: {value!r}")


class BookDTO(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    authors: List[str] = Field(default_factory=list, max_length=50)
    description: Optional[str] = Field(default=None, max_length=20000)
    isbn: Optional[str] = Field(default=None)
    coverUrl: Optional[str] = Field(default=None, max_length=2000)
    publisher: Optional[str] = Field(default=None, max_length=500)
    publishedYear: Optional[int] = Field(default=None, ge=0, le=3000)
    language: Optional[str] = Field(default=None, max_length=50)
    subjects: List[str] = Field(default_factory=list, max_length=100)

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Title must not be blank.")
        return value.strip()

    @field_validator("authors", "subjects")
    @classmethod
    def _clean_list(cls, values: List[str]) -> List[str]:
        return [v.strip() for v in values if v and v.strip()]

    @field_validator("isbn")
    @classmethod
    def _valid_isbn(cls, value: Optional[str]) -> Optional[str]:
        return normalize_isbn(value)

    @field_validator("coverUrl")
    @classmethod
    def _http_url(cls, value: Optional[str]) -> Optional[str]:
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("coverUrl must be an http(s) URL.")
        return value or None


class UpdateBookDTO(BookDTO):
    id: str


class FindBookDTO(FindDTO):
    # Filter by ingestion status, e.g. ["indexed"] for books that can answer questions.
    status: Optional[List[str]] = Field(default=None)
    size: int = Field(default=20, ge=1, le=100)
    page: int = Field(default=1, ge=1)


class ImportBookDTO(BaseModel):
    isbn: str

    @field_validator("isbn")
    @classmethod
    def _valid_isbn(cls, value: str) -> str:
        isbn = normalize_isbn(value)
        if not isbn:
            raise ValueError("ISBN is required.")
        return isbn
