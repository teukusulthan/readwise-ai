"""Search scoping: books named in the question, per-book retrieval for comparisons."""

from service.search import Search
from service.vector_store import ChunkHit

# Selections are validated as UUIDs, so the fake catalog uses real ones.
B_ART = "00000000-0000-0000-0000-00000000a271"
B_HAB = "00000000-0000-0000-0000-0000000000ab"
B_TM = "00000000-0000-0000-0000-0000000000e1"
B_WW = "00000000-0000-0000-0000-0000000000e2"

CATALOG = [
    {"id": B_ART, "title": "The Subtle Art of Not Giving a F*ck", "authors": ["Mark Manson"], "published_year": 2016,
     "description": "Self-help.", "ingestion_status": "indexed"},
    {"id": B_HAB, "title": "Atomic Habits", "authors": ["James Clear"], "published_year": 2018,
     "description": None, "ingestion_status": "none"},
    {"id": B_TM, "title": "The Time Machine", "authors": ["H. G. Wells"], "published_year": 1895,
     "description": None, "ingestion_status": "indexed"},
    {"id": B_WW, "title": "The War of the Worlds", "authors": ["H. G. Wells"], "published_year": 1898,
     "description": None, "ingestion_status": "indexed"},
]


class FakeRepository:
    def catalog(self):
        return CATALOG


class FakeEmbedder:
    def embed_query(self, text):
        return [0.0]


class RecordingStore:
    """Returns 5 hits per searched book; the best-scoring book is b-tm, so a plain search would favour it."""

    def __init__(self):
        self.calls = []

    def search(self, vector, book_ids, limit, min_score):
        self.calls.append(list(book_ids))
        hits = []
        for book in book_ids:
            base = 0.9 if book == B_TM else 0.6
            hits += [ChunkHit(score=base - i / 100, book_id=book, book_title=book, chunk_index=i, text="t",
                              headings=[], page_start=1, page_end=1) for i in range(5)]
        return sorted(hits, key=lambda h: h.score, reverse=True)[:limit]


def _search():
    store = RecordingStore()
    return Search(repository=FakeRepository(), vector_store=store, embedder=FakeEmbedder()), store


def test_question_naming_an_author_searches_only_that_book():
    search, store = _search()
    result = search.retrieve("what are the things mark manson tell on his book?", top_k=8)
    assert store.calls == [[B_ART]]
    assert result.searched_book_ids == [B_ART] and {h.book_id for h in result.hits} == {B_ART}
    assert result.books[0]["title"].startswith("The Subtle Art") and result.books[0]["indexed"] is True


def test_named_book_without_text_is_reported_and_described():
    search, store = _search()
    result = search.retrieve("According to Atomic Habits, why does identity matter?", top_k=8)
    assert store.calls == [[B_ART, B_TM, B_WW]]          # nothing to focus on: all indexed books
    assert result.skipped == [{"id": B_HAB, "title": "Atomic Habits", "reason": "not_indexed:none"}]
    assert result.books[0] == {"id": B_HAB, "title": "Atomic Habits", "authors": ["James Clear"], "year": 2018,
                               "description": None, "indexed": False}


def test_comparison_searches_each_book_separately():
    search, store = _search()
    result = search.retrieve("Compare The Time Machine and The War of the Worlds", top_k=8)
    assert store.calls == [[B_TM], [B_WW]]
    books = [h.book_id for h in result.hits]
    assert books.count(B_TM) == 4 and books.count(B_WW) == 4   # a plain top-8 would be all b-tm


def test_users_selection_wins_over_mentions():
    search, store = _search()
    search.retrieve("What does Mark Manson say?", book_ids=[B_TM], top_k=8)
    assert store.calls == [[B_TM]]


def test_follow_up_keeps_the_previous_questions_book():
    search, store = _search()
    search.retrieve("and what else does he say?", top_k=8, follow_up_of="What does Mark Manson say about pain?")
    assert store.calls == [[B_ART], [B_ART]]                    # plain + follow-up query, both focused


def test_a_named_book_uses_the_relaxed_threshold():
    search, store = _search()
    thresholds = []
    original = store.search
    store.search = lambda vector, book_ids, limit, min_score: thresholds.append(min_score) or original(vector, book_ids, limit, min_score)
    search.retrieve("What does Mark Manson say?", top_k=8)
    search.retrieve("What is courage?", top_k=8)
    assert thresholds[0] == 0.35 and thresholds[1] == 0.45


def test_hits_carry_the_catalog_title_not_the_stale_payload_title():
    # RecordingStore puts the book id in the payload title, as a book renamed after indexing would
    # still carry its old title in every Qdrant point.
    search, _ = _search()
    result = search.retrieve("Compare The Time Machine and The War of the Worlds", top_k=4)
    assert {h.book_title for h in result.hits} == {"The Time Machine", "The War of the Worlds"}

    from dto.search import SearchQueryDTO
    api = search.query(SearchQueryDTO(query="what happens to the traveller", bookIds=[B_TM], topK=2))
    assert {r["bookTitle"] for r in api["results"]} == {"The Time Machine"}


def test_payload_title_is_the_fallback_when_the_book_row_is_missing():
    from service.search import with_catalog_titles

    hit = ChunkHit(score=0.9, book_id="gone", book_title="Old title", chunk_index=0, text="t")
    renamed = ChunkHit(score=0.8, book_id=B_TM, book_title="Old title", chunk_index=0, text="t")
    titled = with_catalog_titles([hit, renamed], {B_TM: CATALOG[2]})
    assert [h.book_title for h in titled] == ["Old title", "The Time Machine"]
