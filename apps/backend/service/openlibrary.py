"""
Book metadata from Open Library (https://openlibrary.org/developers/api) — free, no API key.

Only metadata comes from here (title, authors, cover, …). It never provides book text,
so imported books start as `ingestion_status = 'none'` (metadata only).
"""

from typing import Optional

import httpx
from loguru import logger

from config.base import settings
from dto.book import normalize_isbn
from util.http_errors import NotFoundError, ServiceUnavailableError

_SEARCH_FIELDS = "key,title,author_name,first_publish_year,publisher,language,subject,cover_i,isbn"
_HEADERS = {"User-Agent": "library-rag/0.1 (book library learning project)"}


class OpenLibraryClient:
    def __init__(self, base_url: Optional[str] = None, transport: Optional[httpx.BaseTransport] = None):
        self._http = httpx.Client(
            base_url=base_url or settings.OPENLIBRARY_BASE_URL,
            timeout=15,
            headers=_HEADERS,
            transport=transport,
            follow_redirects=True,
        )

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Candidates for the import picker. Only results that carry a valid ISBN are returned."""
        if not query or not query.strip():
            raise ValueError("Search query must not be empty.")
        body = self._get("/search.json", {"q": query.strip(), "fields": _SEARCH_FIELDS, "limit": min(limit, 20)})
        candidates = []
        for doc in body.get("docs", []):
            isbn = _pick_isbn(doc.get("isbn") or [])
            if isbn:
                candidates.append(_to_metadata(doc, isbn, description=None))
        return candidates

    def get_by_isbn(self, isbn: str) -> dict:
        """Normalized metadata for one ISBN. Raises NotFoundError if Open Library has no record."""
        body = self._get("/search.json", {"isbn": isbn, "fields": _SEARCH_FIELDS, "limit": 1})
        docs = body.get("docs") or []
        if not docs:
            raise NotFoundError(f"Open Library has no record for ISBN {isbn}.")
        doc = docs[0]
        return _to_metadata(doc, isbn, description=self._work_description(doc.get("key")))

    def _work_description(self, work_key: Optional[str]) -> Optional[str]:
        if not work_key:
            return None
        try:
            work = self._get(f"{work_key}.json", None)
        except ServiceUnavailableError:
            return None  # description is optional; don't fail the import for it
        description = work.get("description")
        if isinstance(description, dict):
            description = description.get("value")
        return description.strip() if isinstance(description, str) and description.strip() else None

    def _get(self, path: str, params: Optional[dict]) -> dict:
        try:
            response = self._http.get(path, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as error:
            logger.warning("Open Library request failed: {error!r}", error=error)
            raise ServiceUnavailableError("Open Library is unavailable right now. Try again later.") from error


def _pick_isbn(isbns: list[str]) -> Optional[str]:
    """Prefer a valid ISBN-13, fall back to a valid ISBN-10."""
    valid = []
    for raw in isbns:
        try:
            isbn = normalize_isbn(raw)
        except ValueError:
            continue
        if isbn:
            valid.append(isbn)
    return next((i for i in valid if len(i) == 13), None) or next(iter(valid), None)


def _to_metadata(doc: dict, isbn: str, description: Optional[str]) -> dict:
    cover_id = doc.get("cover_i")
    return {
        "title": (doc.get("title") or "").strip() or "Untitled",
        "authors": doc.get("author_name") or [],
        "description": description,
        "isbn": isbn,
        "cover_url": f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None,
        "publisher": (doc.get("publisher") or [None])[0],
        "published_year": doc.get("first_publish_year"),
        "language": (doc.get("language") or [None])[0],
        "subjects": (doc.get("subject") or [])[:10],
        "metadata_source": "openlibrary",
        "external_id": doc.get("key"),
    }
