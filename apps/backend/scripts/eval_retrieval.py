# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27"]
# ///
"""
Retrieval evaluation: does search find the section that answers the question?

Each case is a question whose answer clearly lives in one identifiable section of one seeded
Project Gutenberg book (see seed_gutenberg.py). The script asks the running backend
(POST /search/query, read-only) and counts a hit when one of the top-k passages comes from the
expected book and has a heading matching the expected pattern. It prints, per case, hit/miss and
the rank of the first matching passage, then hit@k over all cases.

    cd apps/backend
    uv run scripts/eval_retrieval.py                          # http://127.0.0.1:8025, top 8
    uv run scripts/eval_retrieval.py --api http://localhost:8021 --top-k 5 -v

To compare two versions of the retrieval code, run it against each and compare the output.
Cases whose book is not in the library (or not indexed yet) are reported as "skip".
Requests are paced to stay under the /search/query rate limit (60/min per client).
"""

import argparse
import re
import sys
import time
from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class Case:
    question: str
    book: str              # catalog title prefix (case-insensitive)
    heading: str           # regex searched (case-insensitive) in each heading of a passage
    note: str = ""


CASES = [
    Case("What does Scrooge learn from the Ghost of Christmas Yet to Come?",
         "A Christmas Carol", r"last of the spirits", "Stave IV"),
    Case("Why does the creature turn against Victor and decide to take revenge?",
         "Frankenstein", r"^chapter 1[0-6]$", "chapters 10-16: the meeting on the glacier and the creature's story"),
    Case("How does Gregor's family react when they first see him after his transformation?",
         "Metamorphosis", r"^I$", "part I"),
    Case("How did Dr. Jekyll first turn himself into Mr. Hyde?",
         "The Strange Case of Dr. Jekyll", r"full statement", "Henry Jekyll's full statement"),
    Case("What did Dr. Lanyon see when the visitor drank the potion in his house?",
         "The Strange Case of Dr. Jekyll", r"lanyon's narrative", "Dr. Lanyon's narrative"),
    Case("What does the Time Traveller see at the end of the world, with the giant crabs and the dying sun?",
         "The Time Machine", r"further vision", "XIV. The Further Vision"),
    Case("How does Kurtz die and what are his last words?",
         "Heart of Darkness", r"^III$", "part III"),
]

# 60 requests/min per client on /search/query: stay comfortably below.
REQUEST_INTERVAL_SECONDS = 1.2


def first_match_rank(results: list[dict], case: Case) -> int | None:
    pattern = re.compile(case.heading, re.IGNORECASE)
    for rank, result in enumerate(results, start=1):
        if not (result.get("bookTitle") or "").lower().startswith(case.book.lower()):
            continue
        if any(pattern.search(heading) for heading in result.get("headings") or []):
            return rank
    return None


def indexed_titles(client: httpx.Client) -> list[str]:
    response = client.post("/book/get-all", json={"page": 1, "size": 100})
    response.raise_for_status()
    return [book["title"] for book in response.json()["data"]
            if (book.get("ingestion") or {}).get("status") == "indexed"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://127.0.0.1:8025", help="backend base URL")
    parser.add_argument("--top-k", type=int, default=8, help="passages per question (1-20)")
    parser.add_argument("-v", "--verbose", action="store_true", help="print every retrieved passage")
    args = parser.parse_args()

    hits = evaluated = 0
    with httpx.Client(base_url=args.api.rstrip("/"), timeout=60) as client:
        titles = indexed_titles(client)
        for number, case in enumerate(CASES, start=1):
            label = f"[{number}] {case.question}"
            if not any(title.lower().startswith(case.book.lower()) for title in titles):
                print(f"{'skip':<11} {label}\n      ({case.book} is not indexed)")
                continue
            if evaluated:
                time.sleep(REQUEST_INTERVAL_SECONDS)
            response = client.post("/search/query", json={"query": case.question, "topK": args.top_k})
            response.raise_for_status()
            results = response.json()["data"]["results"]
            rank = first_match_rank(results, case)
            evaluated += 1
            hits += rank is not None
            outcome = f"hit rank {rank}" if rank else "MISS"
            print(f"{outcome:<11} {label}\n      expected: {case.book} / {case.note}")
            sections = [f"{r['bookTitle'][:24]} | {' > '.join(r['headings']) or '-'}" for r in results]
            if args.verbose or rank is None:
                for position, (result, section) in enumerate(zip(results, sections), start=1):
                    print(f"        {position:>2}. {result['score']:.3f}  {section}")

    if not evaluated:
        print("No case could be evaluated.")
        return 1
    print(f"\nhit@{args.top_k}: {hits}/{evaluated} = {hits / evaluated:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
