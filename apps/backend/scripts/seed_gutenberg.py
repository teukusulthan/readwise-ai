# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.27", "beautifulsoup4>=4.12"]
# ///
"""
Seed the library with real, public-domain books from Project Gutenberg.

For every book below:
  1. download Gutenberg's HTML edition (cached in storage/gutenberg/, polite delay between requests)
  2. strip the Project Gutenberg license header/footer, images and original-edition page markers
  3. print it to a text PDF with headless Chrome (real typography, so Docling sees headings)
  4. create the catalog entry (POST /book/add) and upload the PDF (POST /book/upload)
     → the backend indexes it exactly like a user upload

Safe to re-run: books that already have a document are skipped; metadata-only entries
with the same title get the PDF attached.

    cd apps/backend
    uv run scripts/seed_gutenberg.py                # all books, then exit (indexing continues in the API)
    uv run scripts/seed_gutenberg.py --wait         # ... and wait until every book is indexed
    uv run scripts/seed_gutenberg.py --only 11 84   # just these Gutenberg ids
    uv run scripts/seed_gutenberg.py --internal-token "$TOKEN"   # BE_JWT_ACTIVE=true: the service token

Needs the backend running (default http://localhost:8020, override with --api) and Google Chrome / Chromium.
Books are queued shortest first, so the first ones become searchable within minutes.
"""

import argparse
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

GUTENBERG = "https://www.gutenberg.org"
USER_AGENT = "library-rag-seed/1.0 (internal test data; ~20 books, cached)"
CACHE_DIR = Path(__file__).resolve().parent.parent / "storage" / "gutenberg"
DOWNLOAD_DELAY_S = 2.0  # Gutenberg asks automated clients to go slowly

PRINT_CSS = """
@page { size: A4; margin: 20mm 20mm 22mm; }
html { font-size: 11pt !important; }
body { font-family: Georgia, "DejaVu Serif", "Liberation Serif", serif !important; line-height: 1.45 !important;
       margin: 0 !important; padding: 0 !important; max-width: none !important; color: #111 !important; }
h1 { font-size: 22pt !important; margin: 0 0 14pt !important; }
h2 { font-size: 16pt !important; margin: 22pt 0 10pt !important; }
h3 { font-size: 13pt !important; margin: 16pt 0 8pt !important; }
h1, h2, h3 { font-weight: bold !important; text-align: left !important; break-after: avoid; }
p { margin: 0 0 0.55em !important; text-align: justify; }
img, figure, svg, .figcenter, .figleft, .figright, .illus, .pagenum, .pageno, [class*="pagenum"] { display: none !important; }
"""


@dataclass(frozen=True)
class SeedBook:
    gutenberg_id: int
    title: str
    authors: list[str]
    year: int
    subjects: list[str]
    description: str
    expect: str  # must appear in Gutenberg's <title> — guards against a wrong id
    translator: str | None = None


# Ordered roughly shortest → longest: the first books are searchable within minutes.
BOOKS = [
    SeedBook(1952, "The Yellow Wallpaper", ["Charlotte Perkins Gilman"], 1892, ["Short story", "Gothic fiction", "Mental health"],
             "A woman confined to a rented room by her physician husband becomes obsessed with its wallpaper.", "Yellow Wallpaper"),
    SeedBook(1080, "A Modest Proposal", ["Jonathan Swift"], 1729, ["Satire", "Essay", "Ireland"],
             "Swift's satirical essay suggesting that the poor of Ireland sell their children as food to the rich.", "Modest Proposal"),
    SeedBook(5200, "Metamorphosis", ["Franz Kafka"], 1915, ["Novella", "Absurdist fiction"],
             "Gregor Samsa wakes up transformed into a monstrous insect and becomes a burden to his family.", "Metamorphosis",
             translator="David Wyllie"),
    SeedBook(844, "The Importance of Being Earnest", ["Oscar Wilde"], 1895, ["Comedy", "Drama", "Satire"],
             "A comedy of manners in which two young men invent alter egos to escape social obligations.", "Importance of Being Earnest"),
    SeedBook(43, "The Strange Case of Dr. Jekyll and Mr. Hyde", ["Robert Louis Stevenson"], 1886, ["Novella", "Gothic fiction", "Horror"],
             "A London lawyer investigates the link between his friend Dr. Jekyll and the violent Edward Hyde.", "Jekyll"),
    SeedBook(11, "Alice's Adventures in Wonderland", ["Lewis Carroll"], 1865, ["Fantasy", "Children's literature"],
             "Alice follows a white rabbit down a rabbit hole into a world of nonsense and strange creatures.", "Alice"),
    SeedBook(46, "A Christmas Carol", ["Charles Dickens"], 1843, ["Novella", "Christmas", "Ghost story"],
             "The miser Ebenezer Scrooge is visited by the ghost of his partner and three spirits on Christmas Eve.", "Christmas Carol"),
    SeedBook(1232, "The Prince", ["Niccolò Machiavelli"], 1532, ["Political philosophy", "Leadership"],
             "A practical treatise on how princes gain, keep and lose power.", "Prince", translator="W. K. Marriott"),
    SeedBook(35, "The Time Machine", ["H. G. Wells"], 1895, ["Science fiction", "Time travel"],
             "A Victorian inventor travels to the year 802,701 and finds humanity split into the Eloi and the Morlocks.", "Time Machine"),
    SeedBook(215, "The Call of the Wild", ["Jack London"], 1903, ["Adventure", "Dogs", "Klondike Gold Rush"],
             "Buck, a domestic dog stolen to work as a sled dog in the Yukon, gradually returns to the wild.", "Call of the Wild"),
    SeedBook(219, "Heart of Darkness", ["Joseph Conrad"], 1899, ["Novella", "Colonialism", "Africa"],
             "Marlow recounts his journey up the Congo River in search of the ivory trader Kurtz.", "Heart of Darkness"),
    SeedBook(2500, "Siddhartha", ["Hermann Hesse"], 1922, ["Philosophical fiction", "Spirituality", "India"],
             "A young Brahmin leaves home in search of enlightenment during the time of the Buddha.", "Siddhartha"),
    SeedBook(55, "The Wonderful Wizard of Oz", ["L. Frank Baum"], 1900, ["Fantasy", "Children's literature"],
             "Dorothy is carried by a cyclone to the Land of Oz and travels to the Emerald City to find a way home.", "Wizard of Oz"),
    SeedBook(64317, "The Great Gatsby", ["F. Scott Fitzgerald"], 1925, ["Jazz Age", "American literature", "Wealth"],
             "Nick Carraway tells the story of his mysterious neighbour Jay Gatsby and his longing for Daisy Buchanan.", "Great Gatsby"),
    SeedBook(16, "Peter Pan", ["J. M. Barrie"], 1911, ["Fantasy", "Children's literature"],
             "Wendy and her brothers fly with Peter Pan to Neverland, home of the Lost Boys, mermaids and Captain Hook.", "Peter Pan"),
    SeedBook(36, "The War of the Worlds", ["H. G. Wells"], 1898, ["Science fiction", "Alien invasion"],
             "Martians land in England and lay waste to the country with heat-rays and fighting machines.", "War of the Worlds"),
    SeedBook(120, "Treasure Island", ["Robert Louis Stevenson"], 1883, ["Adventure", "Pirates"],
             "Young Jim Hawkins sails in search of buried treasure and confronts the pirate Long John Silver.", "Treasure Island"),
    SeedBook(132, "The Art of War", ["Sun Tzu"], -500, ["Military strategy", "Philosophy", "China"],
             "The classic Chinese treatise on strategy, with Lionel Giles's translation and commentary.", "Art of War",
             translator="Lionel Giles"),
    SeedBook(84, "Frankenstein; or, The Modern Prometheus", ["Mary Wollstonecraft Shelley"], 1818, ["Gothic fiction", "Science fiction"],
             "Victor Frankenstein creates a living being and is pursued by the consequences of his creation.", "Frankenstein"),
    SeedBook(174, "The Picture of Dorian Gray", ["Oscar Wilde"], 1890, ["Gothic fiction", "Philosophical fiction"],
             "A young man's portrait ages and records his sins while he himself stays young and beautiful.", "Dorian Gray"),
    SeedBook(2680, "Meditations", ["Marcus Aurelius"], 180, ["Stoicism", "Philosophy"],
             "The Roman emperor's private notes on Stoic philosophy, duty and self-discipline.", "Meditations",
             translator="Meric Casaubon"),
    SeedBook(1661, "The Adventures of Sherlock Holmes", ["Arthur Conan Doyle"], 1892, ["Detective fiction", "Short stories"],
             "Twelve cases of the detective Sherlock Holmes, narrated by Dr. Watson.", "Sherlock Holmes"),
    SeedBook(1342, "Pride and Prejudice", ["Jane Austen"], 1813, ["Romance", "Comedy of manners", "England"],
             "Elizabeth Bennet and Mr. Darcy overcome pride, prejudice and family pressures.", "Pride and Prejudice"),
]


# ── Gutenberg → clean HTML → PDF ─────────────────────────────────────

def download_html(client: httpx.Client, book: SeedBook) -> Path:
    path = CACHE_DIR / f"pg{book.gutenberg_id}.html"
    if path.exists() and path.stat().st_size > 10_000:
        return path
    url = f"{GUTENBERG}/cache/epub/{book.gutenberg_id}/pg{book.gutenberg_id}-images.html"
    response = client.get(url)
    response.raise_for_status()
    path.write_bytes(response.content)
    time.sleep(DOWNLOAD_DELAY_S)
    return path


def clean_html(raw_path: Path, book: SeedBook) -> Path:
    soup = BeautifulSoup(raw_path.read_bytes(), "html.parser")
    page_title = soup.title.get_text(" ", strip=True) if soup.title else ""
    if book.expect.lower() not in page_title.lower():
        raise ValueError(f"Gutenberg #{book.gutenberg_id} is {page_title!r}, expected {book.expect!r}")

    # Project Gutenberg license header/footer: not book content (and not useful to retrieve).
    for selector in ("#pg-header", "#pg-footer", "img", "figure", "svg", ".pagenum", ".pageno"):
        for element in soup.select(selector):
            element.decompose()

    style = soup.new_tag("style")
    style.string = PRINT_CSS
    (soup.head or soup).append(style)
    clean_path = CACHE_DIR / f"pg{book.gutenberg_id}.clean.html"
    clean_path.write_text(str(soup), encoding="utf-8")
    return clean_path


def find_chrome() -> str:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if path := shutil.which(name):
            return path
    sys.exit("Google Chrome or Chromium is required to print the PDFs.")


def print_pdf(chrome: str, html_path: Path, book: SeedBook) -> Path:
    pdf_path = CACHE_DIR / f"{book.gutenberg_id}-{_slug(book.title)}.pdf"
    if pdf_path.exists() and pdf_path.stat().st_size > 10_000:
        return pdf_path
    subprocess.run(
        [chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
         f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        check=True, capture_output=True, timeout=300,
    )
    if not pdf_path.exists() or pdf_path.stat().st_size < 10_000:
        raise RuntimeError(f"Chrome did not produce a PDF for {book.title}")
    return pdf_path


def _slug(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in text).strip("-")[:60]


# ── backend API ──────────────────────────────────────────────────────

def error_message(response: httpx.Response) -> str:
    """The API's failure message: top-level `metaData.message` (the envelope), else `detail` (plain or legacy)."""
    try:
        body = response.json()
    except ValueError:
        return response.text.strip() or response.reason_phrase
    if not isinstance(body, dict):
        return str(body)
    meta = body.get("metaData")
    if isinstance(meta, dict) and meta.get("message"):
        return str(meta["message"])
    detail = body.get("detail")
    if isinstance(detail, dict):
        legacy = detail.get("metaData")
        if isinstance(legacy, dict) and legacy.get("message"):
            return str(legacy["message"])
    if detail:
        return detail if isinstance(detail, str) else str(detail)
    return response.reason_phrase


class Library:
    def __init__(self, base_url: str, token: str | None, internal_token: str | None = None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        if internal_token:
            headers["X-Internal-Token"] = internal_token
        self.http = httpx.Client(base_url=base_url, headers=headers, timeout=120)

    def _data(self, response: httpx.Response):
        if response.status_code >= 400:
            message = error_message(response)
            raise RuntimeError(f"{response.request.method} {response.request.url.path} → {response.status_code}: {message}")
        return response.json()["data"]

    def find_by_title(self, title: str) -> dict | None:
        books = self._data(self.http.post("/book/get-all", json={"search": title, "size": 50, "page": 1}))
        return next((b for b in books if b["title"].casefold() == title.casefold()), None)

    def add(self, book: SeedBook) -> dict:
        description = book.description + (f" Translated by {book.translator}." if book.translator else "")
        return self._data(self.http.post("/book/add", json={
            "title": book.title,
            "authors": book.authors,
            "publishedYear": book.year if book.year > 0 else None,
            "language": "en",
            "publisher": "Project Gutenberg",
            "subjects": book.subjects,
            "description": f"{description} Public domain text from Project Gutenberg (#{book.gutenberg_id}).",
            "coverUrl": f"{GUTENBERG}/cache/epub/{book.gutenberg_id}/pg{book.gutenberg_id}.cover.medium.jpg",
        }))

    def upload(self, book_id: str, pdf_path: Path) -> dict:
        with pdf_path.open("rb") as file:
            return self._data(self.http.post("/book/upload", data={"bookId": book_id},
                                             files={"file": (pdf_path.name, file, "application/pdf")}))

    def get(self, book_id: str) -> dict:
        return self._data(self.http.get("/book/get-one", params={"id": book_id}))


# ── main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://localhost:8020", help="backend base URL")
    parser.add_argument("--token", default=None, help="JWT bearer token (only if BE_JWT_ACTIVE=true)")
    parser.add_argument("--internal-token", default=None,
                        help="service token sent as X-Internal-Token (the backend's BE_INTERNAL_TOKEN; "
                             "an alternative to --token while BE_JWT_ACTIVE=true)")
    parser.add_argument("--only", type=int, nargs="*", help="Gutenberg ids to seed (default: all)")
    parser.add_argument("--wait", action="store_true", help="wait until every seeded book is indexed")
    args = parser.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # progress shows up live even when logged to a file

    books =[b for b in BOOKS if not args.only or b.gutenberg_id in args.only]
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome()
    library = Library(args.api, args.token, args.internal_token)
    gutenberg = httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60, follow_redirects=True)

    queued: dict[str, str] = {}
    failures = 0
    for i, book in enumerate(books, start=1):
        label = f"[{i:2}/{len(books)}] {book.title}"
        try:
            existing = library.find_by_title(book.title)
            if existing and existing["hasDocument"]:
                print(f"{label}: already has a document ({existing['ingestion']['status']}) — skipped")
                continue
            pdf = print_pdf(chrome, clean_html(download_html(gutenberg, book), book), book)
            entry = existing or library.add(book)
            uploaded = library.upload(entry["id"], pdf)
            queued[uploaded["id"]] = book.title
            print(f"{label}: {pdf.stat().st_size // 1024} KB PDF uploaded → {uploaded['ingestion']['status']}")
        except Exception as error:  # keep going: one bad book must not stop the rest
            failures += 1
            print(f"{label}: FAILED — {error}")

    print(f"\n{len(queued)} uploaded, {failures} failed. Indexing runs in the backend (one book at a time).")
    if args.wait and queued:
        wait_for_indexing(library, queued)
    return 1 if failures else 0


def wait_for_indexing(library: Library, queued: dict[str, str]):
    pending = dict(queued)
    started = time.monotonic()
    while pending:
        time.sleep(15)
        for book_id, title in list(pending.items()):
            book = library.get(book_id)
            status = book["ingestion"]["status"]
            if status in ("indexed", "failed"):
                detail = f"{book['ingestion']['chunkCount']} chunks, {book['document']['pageCount']} pages" \
                    if status == "indexed" else book["ingestion"]["error"]
                print(f"  {time.monotonic() - started:6.0f}s  {status:8} {title} ({detail})")
                del pending[book_id]
    print("All seeded books finished indexing.")


if __name__ == "__main__":
    sys.exit(main())
