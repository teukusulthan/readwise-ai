"""Section diversity: near-duplicate passages of one section must not crowd out the others."""

from service.search import Search, select_diverse
from service.vector_store import ChunkHit

B_CC = "00000000-0000-0000-0000-0000000000cc"
B_TM = "00000000-0000-0000-0000-0000000000e1"
B_WW = "00000000-0000-0000-0000-0000000000e2"


def _hit(index: int, score: float, headings=("STAVE I",), book: str = B_CC) -> ChunkHit:
    return ChunkHit(score=score, book_id=book, book_title=book, chunk_index=index, text=f"t{index}",
                    headings=list(headings), page_start=1, page_end=1)


def _keys(hits):
    return [(h.book_id, h.chunk_index) for h in hits]


# ── select_diverse (pure) ────────────────────────────────────────────

def test_caps_passages_per_section_and_reaches_the_next_sections():
    candidates = [_hit(i, 0.9 - i / 100) for i in range(6)]                       # six from STAVE I
    candidates += [_hit(10, 0.7, ["STAVE IV"]), _hit(11, 0.69, ["STAVE IV"]), _hit(12, 0.6, ["STAVE V"])]
    selected = select_diverse(candidates, limit=5, max_per_section=2)
    assert [h.chunk_index for h in selected] == [0, 1, 10, 11, 12]


def test_fills_from_the_best_remaining_candidates_when_the_cap_leaves_too_few():
    candidates = [_hit(i, 0.9 - i / 100) for i in range(5)] + [_hit(10, 0.5, ["STAVE IV"])]
    selected = select_diverse(candidates, limit=5, max_per_section=2)
    # 0, 1 (cap) + 10 (other section) = 3 → fill with the best capped ones: 2, 3
    assert [h.chunk_index for h in selected] == [0, 1, 2, 3, 10]


def test_result_is_ordered_by_score_and_ties_keep_candidate_order():
    candidates = [_hit(1, 0.8), _hit(2, 0.8), _hit(3, 0.8), _hit(4, 0.8, ["II"]), _hit(5, 0.7, ["II"])]
    selected = select_diverse(candidates, limit=4, max_per_section=2)
    assert [h.chunk_index for h in selected] == [1, 2, 4, 5]
    assert [h.score for h in selected] == sorted((h.score for h in selected), reverse=True)


def test_unsorted_candidates_are_ranked_by_score_first():
    candidates = [_hit(3, 0.5), _hit(1, 0.9), _hit(2, 0.8), _hit(4, 0.7, ["II"])]
    assert [h.chunk_index for h in select_diverse(candidates, limit=3, max_per_section=2)] == [1, 2, 4]


def test_section_is_book_plus_full_heading_path():
    # Same headings in two books, and a sub-section under the same chapter: three different sections.
    candidates = [_hit(1, 0.9, ["I"], B_TM), _hit(2, 0.89, ["I"], B_TM), _hit(3, 0.88, ["I"], B_TM),
                  _hit(1, 0.87, ["I"], B_WW), _hit(4, 0.86, ["I", "Part 2"], B_TM)]
    selected = select_diverse(candidates, limit=4, max_per_section=2)
    assert _keys(selected) == [(B_TM, 1), (B_TM, 2), (B_WW, 1), (B_TM, 4)]


def test_passages_without_headings_share_one_section_per_book():
    candidates = [_hit(i, 0.9 - i / 100, []) for i in range(4)] + [_hit(9, 0.5, ["I"])]
    assert [h.chunk_index for h in select_diverse(candidates, limit=3, max_per_section=2)] == [0, 1, 9]


def test_zero_disables_the_cap():
    candidates = [_hit(i, 0.9 - i / 100) for i in range(5)] + [_hit(10, 0.5, ["STAVE IV"])]
    assert [h.chunk_index for h in select_diverse(candidates, limit=4, max_per_section=0)] == [0, 1, 2, 3]


def test_never_returns_more_than_limit_or_more_than_the_candidates():
    candidates = [_hit(i, 0.9 - i / 100, [str(i)]) for i in range(3)]
    assert len(select_diverse(candidates, limit=2, max_per_section=2)) == 2
    assert len(select_diverse(candidates, limit=8, max_per_section=1)) == 3
    assert select_diverse([], limit=8, max_per_section=2) == []


# ── retrieve(): candidate pool + cap on every path ───────────────────

CATALOG = [
    {"id": B_CC, "title": "A Christmas Carol", "authors": ["Charles Dickens"], "published_year": 1843,
     "description": None, "ingestion_status": "indexed"},
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


class SectionedStore:
    """Per book: 10 near-duplicates of section A (0.90..0.81), 5 of B (0.70..0.66), 5 of C (0.60..0.56)."""

    def __init__(self):
        self.limits = []

    def search(self, vector, book_ids, limit, min_score):
        self.limits.append(limit)
        hits = []
        for book in book_ids:
            hits += [_hit(i, 0.9 - i / 100, ["A"], book) for i in range(10)]
            hits += [_hit(10 + i, 0.7 - i / 100, ["B"], book) for i in range(5)]
            hits += [_hit(20 + i, 0.6 - i / 100, ["C"], book) for i in range(5)]
        return sorted(hits, key=lambda h: h.score, reverse=True)[:limit]


def _search():
    store = SectionedStore()
    return Search(repository=FakeRepository(), vector_store=store, embedder=FakeEmbedder()), store


def _sections(hits):
    return [(h.book_id, h.headings[0]) for h in hits]


def test_single_search_fetches_a_larger_pool_and_caps_each_section(monkeypatch):
    monkeypatch.setattr("service.search.settings.RETRIEVAL_CANDIDATE_MULTIPLIER", 4)
    monkeypatch.setattr("service.search.settings.RETRIEVAL_MAX_PER_SECTION", 2)
    search, store = _search()
    result = search.retrieve("what does scrooge learn?", book_ids=[B_CC], top_k=6)
    assert store.limits == [24]
    # A plain top 6 would be six near-duplicates of A.
    assert _sections(result.hits) == [(B_CC, "A")] * 2 + [(B_CC, "B")] * 2 + [(B_CC, "C")] * 2
    assert [h.chunk_index for h in result.hits] == [0, 1, 10, 11, 20, 21]


def test_cap_disabled_gives_plain_top_k(monkeypatch):
    monkeypatch.setattr("service.search.settings.RETRIEVAL_CANDIDATE_MULTIPLIER", 4)
    monkeypatch.setattr("service.search.settings.RETRIEVAL_MAX_PER_SECTION", 0)
    search, _ = _search()
    result = search.retrieve("what does scrooge learn?", book_ids=[B_CC], top_k=6)
    assert [h.chunk_index for h in result.hits] == [0, 1, 2, 3, 4, 5]


def test_per_book_search_caps_within_each_book_and_keeps_every_book(monkeypatch):
    monkeypatch.setattr("service.search.settings.RETRIEVAL_CANDIDATE_MULTIPLIER", 4)
    monkeypatch.setattr("service.search.settings.RETRIEVAL_MAX_PER_SECTION", 2)
    search, store = _search()
    result = search.retrieve("Compare The Time Machine and The War of the Worlds", top_k=8)
    assert store.limits == [16, 16]                          # per_book 4 × multiplier 4, per book
    for book in (B_TM, B_WW):
        assert _sections([h for h in result.hits if h.book_id == book]) == [(book, "A")] * 2 + [(book, "B")] * 2
    assert len(result.hits) == 8
    assert [h.score for h in result.hits] == sorted((h.score for h in result.hits), reverse=True)


def test_follow_up_merges_both_searches_before_capping(monkeypatch):
    monkeypatch.setattr("service.search.settings.RETRIEVAL_CANDIDATE_MULTIPLIER", 4)
    monkeypatch.setattr("service.search.settings.RETRIEVAL_MAX_PER_SECTION", 2)
    search, store = _search()
    result = search.retrieve("and then?", book_ids=[B_CC], top_k=4, follow_up_of="what does scrooge learn?")
    assert store.limits == [16, 16]                          # question + "previous\nquestion"
    # Both searches return the same chunks: merged by chunk, then capped → no duplicates.
    assert [h.chunk_index for h in result.hits] == [0, 1, 10, 11]


def test_multiplier_below_one_still_fetches_top_k(monkeypatch):
    monkeypatch.setattr("service.search.settings.RETRIEVAL_CANDIDATE_MULTIPLIER", 0)
    monkeypatch.setattr("service.search.settings.RETRIEVAL_MAX_PER_SECTION", 2)
    search, store = _search()
    result = search.retrieve("what does scrooge learn?", book_ids=[B_CC], top_k=6)
    assert store.limits == [6] and len(result.hits) == 6
