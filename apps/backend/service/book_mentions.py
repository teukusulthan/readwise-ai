"""
Which catalog books does a question talk about?

"According to Atomic Habits, …", "What does Mark Manson say about …", "Compare The Time
Machine and The War of the Worlds" — semantic search alone can't tell which *book* is
meant (chunks don't contain the author's name, and every book has passages about
"habits" or "motivation"). Matching the question against catalog titles and authors lets
retrieval focus on the right books, and lets the answer say when a named book has no
indexed text.

Matching is deliberately conservative (whole words, case rules for one-word names) so a
question about "the wells in the village" or "a prince" doesn't get routed to Machiavelli by accident.
"""

import re
import unicodedata
from typing import Iterable

_ARTICLES = ("the ", "a ", "an ")
# One-word names this short or this common are too ambiguous to match on their own.
_MIN_SINGLE_WORD = 5


def _normalize(text: str) -> str:
    """lowercase, accents and punctuation removed, single spaces, padded for whole-word matching."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return f" {text.strip()} "


def _title_variants(title: str) -> set[str]:
    """Full title, the main title before a subtitle ("Frankenstein; or, …"), each without a leading article."""
    variants = {title}
    main = re.split(r"\s*(?:[;:]|,?\s+or,\s+)", title, maxsplit=1)[0]
    variants.add(main)
    for variant in list(variants):
        lowered = variant.lower()
        for article in _ARTICLES:
            if lowered.startswith(article):
                variants.add(variant[len(article):])
    # "The Prince" is effectively one word: leave it to the stricter one-word rule ("Prince").
    return {v.strip() for v in variants if v.strip() and not _is_article_plus_one_word(v)}


def _is_article_plus_one_word(text: str) -> bool:
    words = text.lower().split()
    return len(words) == 2 and f"{words[0]} " in _ARTICLES


def _contains(question_norm: str, question_raw: str, name: str) -> bool:
    name_norm = _normalize(name)
    if name_norm.strip() == "":
        return False
    if len(name_norm.split()) > 1:
        return name_norm in question_norm
    # One-word names ("Siddhartha", "Wells"): long enough and written with a capital letter.
    word = name_norm.strip()
    if len(word) < _MIN_SINGLE_WORD or name_norm not in question_norm:
        return False
    return re.search(rf"\b{re.escape(name.strip()[:1].upper() + name.strip()[1:])}\b", question_raw) is not None


def find_mentioned_books(question: str, books: Iterable[dict]) -> list[dict]:
    """Catalog rows (with `title`, `authors`) named in the question by title or author, in catalog order."""
    question_norm = _normalize(question)
    mentioned = []
    for book in books:
        names = set(_title_variants(book["title"]))
        for author in book.get("authors") or []:
            names.add(author)
            parts = author.replace(".", " ").split()
            if len(parts) > 1:
                names.add(parts[-1])  # surname
        if any(_contains(question_norm, question, name) for name in names):
            mentioned.append(book)
    return mentioned
