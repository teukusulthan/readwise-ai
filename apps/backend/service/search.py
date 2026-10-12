"""
Semantic retrieval over indexed books.

question --embed_query--> vector --Qdrant similarity search--> best chunks (+ citations)

Only books whose ingestion_status is 'indexed' are searched, even if Qdrant still
holds points for a book that is being re-indexed or failed.

Three refinements on top of plain top-k search (see retrieve()):
- focus: books named in the question ("According to Atomic Habits…", "Mark Manson's book")
  narrow the search to those books when the user has not picked books themselves;
- per-book: comparison questions over a few books search each book separately, so every
  book is represented instead of the closest one taking all the slots;
- follow-ups: the previous question is searched too and the results are merged.
"""

import math
from dataclasses import asdict, dataclass, field, replace
from typing import Optional

from config.base import settings
from dto.search import SearchQueryDTO
from service import Services
from service.book_mentions import find_mentioned_books
from service.book_repository import BookRepository, parse_book_id
from service.vector_store import ChunkHit, VectorStore

# Search each book separately when the question involves this many books (2..N).
PER_BOOK_MAX_BOOKS = 6
PER_BOOK_MIN_HITS = 3
# When the question names a book, its passages are relevant by construction, so a lower similarity
# is enough. Measured: "what does Mark Manson say in his book?" scored 0.39-0.56 on that book —
# the global threshold kept only 3 passages and the answer fell back to general knowledge.
FOCUSED_MIN_SCORE = 0.35


@dataclass
class Retrieval:
    hits: list[ChunkHit]
    searched_book_ids: list[str]
    # Requested or mentioned books that can't be searched (not indexed yet / no document / unknown).
    skipped: list[dict] = field(default_factory=list)
    # Catalog details of the books the question is about (mentioned, selected, or in the hits),
    # so the answer can name them and knows which ones have no indexed text.
    books: list[dict] = field(default_factory=list)


class Search:
    def __init__(self, repository: Optional[BookRepository] = None, vector_store: Optional[VectorStore] = None,
                 embedder=None):
        self.repository = repository or BookRepository()
        self.vector_store = vector_store or VectorStore()
        self._embedder = embedder

    @property
    def embedder(self):
        return self._embedder or Services.embedding()

    def retrieve(self, question: str, book_ids: Optional[list[str]] = None, top_k: Optional[int] = None,
                 min_score: Optional[float] = None, follow_up_of: Optional[str] = None) -> Retrieval:
        """
        `book_ids`: the user's selection; None = every indexed book (then books named in the
        question narrow the search). `follow_up_of`: the previous question in a conversation —
        a follow-up ("what happened to him next?") often lacks the words that identify its
        topic, so we also search "previous question + question" and keep the best of both.
        """
        catalog = self.repository.catalog()
        by_id = {str(book["id"]): book for book in catalog}

        mentioned = []
        if book_ids is None:
            mentioned = find_mentioned_books(question, catalog)
            if not mentioned and follow_up_of:
                mentioned = find_mentioned_books(follow_up_of, catalog)  # "what else does it say?" keeps the focus
        mentioned_indexed = [str(b["id"]) for b in mentioned if b["ingestion_status"] == "indexed"]
        mentioned_missing = [_skip(b) for b in mentioned if b["ingestion_status"] != "indexed"]

        if mentioned_indexed:
            searchable, skipped = mentioned_indexed, []
        else:
            searchable, skipped = self._resolve_books(book_ids, by_id)
        skipped += mentioned_missing

        hits: list[ChunkHit] = []
        if searchable:
            limit = top_k or settings.RETRIEVAL_TOP_K
            threshold = settings.RETRIEVAL_MIN_SCORE if min_score is None else min_score
            if mentioned_indexed and min_score is None:
                threshold = min(threshold, FOCUSED_MIN_SCORE)
            queries = [question] + ([f"{follow_up_of}\n{question}"] if follow_up_of else [])
            vectors = [self.embedder.embed_query(q) for q in queries]

            several = len(mentioned_indexed) >= 2 or (book_ids is not None and len(searchable) >= 2)
            if several and len(searchable) <= PER_BOOK_MAX_BOOKS:
                per_book = max(PER_BOOK_MIN_HITS, math.ceil(limit / len(searchable)))
                hits = merge_hits([
                    merge_hits([self.vector_store.search(v, book_ids=[b], limit=per_book, min_score=threshold)
                                for v in vectors], per_book)
                    for b in searchable
                ], per_book * len(searchable))
            else:
                hits = merge_hits([self.vector_store.search(v, book_ids=searchable, limit=limit, min_score=threshold)
                                   for v in vectors], limit)

        hits = with_catalog_titles(hits, by_id)
        involved = list(dict.fromkeys(
            [str(b["id"]) for b in mentioned] + ([str(b) for b in book_ids] if book_ids else []) + [h.book_id for h in hits]
        ))
        books = [book_to_context(by_id[i]) for i in involved if i in by_id]
        return Retrieval(hits=hits, searched_book_ids=searchable, skipped=skipped, books=books)

    def query(self, dto: SearchQueryDTO) -> dict:
        result = self.retrieve(dto.query, dto.bookIds, dto.topK)
        return {
            "query": dto.query,
            "results": [hit_to_api(hit) for hit in result.hits],
            "searchedBookCount": len(result.searched_book_ids),
            "skippedBooks": result.skipped,
        }

    def _resolve_books(self, book_ids: Optional[list[str]], by_id: dict[str, dict]) -> tuple[list[str], list[dict]]:
        if book_ids is None:
            return [i for i, book in by_id.items() if book["ingestion_status"] == "indexed"], []

        requested = list(dict.fromkeys(str(parse_book_id(b)) for b in book_ids))  # validate + dedupe
        searchable, skipped = [], []
        for book_id in requested:
            book = by_id.get(book_id)
            if book is None:
                skipped.append({"id": book_id, "title": None, "reason": "not_found"})
            elif book["ingestion_status"] != "indexed":
                skipped.append(_skip(book))
            else:
                searchable.append(book_id)
        return searchable, skipped


def _skip(book: dict) -> dict:
    return {"id": str(book["id"]), "title": book["title"], "reason": f"not_indexed:{book['ingestion_status']}"}


def book_to_context(book: dict) -> dict:
    return {
        "id": str(book["id"]),
        "title": book["title"],
        "authors": book.get("authors") or [],
        "year": book.get("published_year"),
        "description": book.get("description"),
        "indexed": book["ingestion_status"] == "indexed",
    }


def with_catalog_titles(hits: list[ChunkHit], by_id: dict[str, dict]) -> list[ChunkHit]:
    """
    Titles come from the catalog, not the point payload: the payload keeps the title the book had
    when it was indexed, so a renamed book would be cited under its old name. The payload title is
    only a fallback for a book whose row is gone.
    """
    return [replace(hit, book_title=by_id[hit.book_id]["title"]) if hit.book_id in by_id else hit for hit in hits]


def merge_hits(results: list[list[ChunkHit]], limit: int) -> list[ChunkHit]:
    """Union of several searches: one entry per chunk (its best score), best first."""
    best: dict[tuple[str, int], ChunkHit] = {}
    for hits in results:
        for hit in hits:
            key = (hit.book_id, hit.chunk_index)
            if key not in best or hit.score > best[key].score:
                best[key] = hit
    return sorted(best.values(), key=lambda hit: hit.score, reverse=True)[:limit]


def hit_to_api(hit: ChunkHit) -> dict:
    data = asdict(hit)
    return {
        "bookId": data["book_id"],
        "bookTitle": data["book_title"],
        "chunkIndex": data["chunk_index"],
        "text": data["text"],
        "headings": data["headings"],
        "pageStart": data["page_start"],
        "pageEnd": data["page_end"],
        "score": round(data["score"], 4),
    }
