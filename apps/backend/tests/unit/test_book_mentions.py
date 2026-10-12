from service.book_mentions import find_mentioned_books

CATALOG = [
    {"id": "1", "title": "Atomic Habits", "authors": ["James Clear"]},
    {"id": "2", "title": "The Subtle Art of Not Giving a F*ck", "authors": ["Mark Manson"]},
    {"id": "3", "title": "The Time Machine", "authors": ["H. G. Wells"]},
    {"id": "4", "title": "The War of the Worlds", "authors": ["H. G. Wells"]},
    {"id": "5", "title": "Frankenstein; or, The Modern Prometheus", "authors": ["Mary Wollstonecraft Shelley"]},
    {"id": "6", "title": "The Prince", "authors": ["Niccolò Machiavelli"]},
    {"id": "7", "title": "Dune", "authors": ["Frank Herbert"]},
]


def ids(question):
    return [b["id"] for b in find_mentioned_books(question, CATALOG)]


def test_titles_case_insensitive_and_without_article():
    assert ids("According to atomic habits, why does identity matter?") == ["1"]
    assert ids("compare the time machine and War of the Worlds") == ["3", "4"]
    assert ids("Who is the creature in Frankenstein?") == ["5"]
    assert ids("what is the subtle art of not giving a f*ck about?") == ["2"]


def test_authors_full_name_and_capitalized_surname():
    assert ids("what are the things mark manson tell on his book?") == ["2"]
    assert ids("What does Wells think about the future?") == ["3", "4"]
    assert ids("Does Machiavelli prefer fear to love?") == ["6"]


def test_ambiguous_single_words_are_not_matched():
    assert ids("the wells in the village dried up") == []           # lower-case common word
    assert ids("is a prince better feared than loved?") == []        # "The Prince" counts as one word: needs a capital
    assert ids("the prince of the city was cruel") == []
    assert ids("What does The Prince say about cruelty?") == ["6"]
    assert ids("Who wrote Dune?") == []                              # four letters: too short to trust
    assert ids("What did the narrator see?") == []
