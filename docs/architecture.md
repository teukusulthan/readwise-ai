# RAG Book Library — Application Architecture

> Describes what is **built and verified** as of 2026-10-09. Items marked **🛠 Not yet** are designed but not implemented.
> Stack policy: [`.claude/rules/architecture.md`](../.claude/rules/architecture.md) · Endpoints: [`docs/api-spec.md`](./api-spec.md) · Tables: [`docs/database-schema.md`](./database-schema.md)

---

## 1. What the application does

Two separate capabilities that are never confused:

| Capability | What it means | Data source |
|---|---|---|
| **Book catalog** | Browse/search books by title, author, ISBN, publisher; details + cover | Typed in manually, imported from Open Library, or created from an upload |
| **Full-text RAG** | Questions answered *only* from the text of uploaded PDFs, with book/section/page sources | Text that Docling extracted from PDFs you uploaded |

Every book has an `ingestion_status`. **Only `indexed` books are searched or used for answers.**
`none` = metadata only (shown as "Metadata only — not searchable"). The API exposes this as `searchable: true|false`.

---

## 2. Monorepo layout

```
library-rag/
├── apps/
│   ├── backend/          FastAPI service (Python 3.12, uv)
│   └── web/              React 18 + TypeScript + Vite
├── docker-compose.yml    PostgreSQL (pgvector image), Qdrant, MongoDB, Redis — 127.0.0.1 only
├── docs/                 this file, api-spec.md, database-schema.md
└── .claude/              agent rules + skills (guidelines)
```

---

## 3. Runtime components

```
 Browser ── React SPA (Vite dev server, default :3000)
              │  axios → /api/v1/apps/*   (Vite proxy strips the prefix)
              ▼
 FastAPI backend (default :8020)
   router  →  service  →  Services.* clients
     │
     ├── PostgreSQL ........ books table (metadata + ingestion status)      psycopg 3 pool
     ├── Qdrant ............ book_chunks collection (vectors + chunk text)   qdrant-client
     ├── Embedding service . company TEI, Qwen3-Embedding-0.6B, 1024-dim     httpx
     ├── LLM ............... Agno Agent → LiteLLM → provider (key pending)    agno, litellm
     ├── Open Library ...... book metadata import                            httpx
     ├── Local disk ........ uploaded PDFs: storage/books/<book_id>.pdf
     └── MongoDB + Redis ... existing boilerplate auth/user modules only
 Background: one daemon ingestion thread inside the API process runs Docling + embedding + Qdrant writes
 (daemon = shutdown/auto-reload never waits for it; an interrupted job is marked failed at the next startup).
```

---

## 4. Core flows

### 4.1 Upload and indexing

```
POST /book/upload  (multipart: file, optional bookId | title)
  router/book.py ─► service/book.py: Book.upload_document
     1. util/storage.save_pdf_upload   stream to a temp file in 1 MB pieces, check %PDF- magic bytes,
                                      enforce MAX_UPLOAD_SIZE_MB, compute sha256
     2. sha256 already in books?  → 409 "already uploaded as …"  (no duplicate book)
     3. insert/update books row: ingestion_status = 'queued', file metadata
     4. util/storage.finalize          move temp file → storage/books/<book_id>.pdf
     5. service/ingestion.enqueue      hand the book id to the worker thread   ──► 200 + Book JSON
  worker thread: Ingestion.run
     6. claim: UPDATE … SET status='processing' WHERE status='queued'   (atomic; a job runs once)
     7. util/document_parser.parse_pdf
          page count first (pypdfium2) → reject if > MAX_PDF_PAGES
          Docling DocumentConverter (OCR off, table structure on, 4 CPU threads) in windows of 20 pages
          → one DoclingDocument per window (absolute page numbers; heading carried across window boundaries)
          HybridChunker(tokenizer = Qwen3 tokenizer, max 512 tokens, merge_peers)
          → chunks: text, embed_text (headings + text), headings, page_start, page_end
     8. for each batch of 32 chunks: Services.embedding().embed_documents(embed_text)
                                     VectorStore.upsert_chunks  (point id = uuid5(book_id, chunk_index))
     9. delete leftover points with chunk_index ≥ new count (re-index that produced fewer chunks)
    10. status='indexed', chunk_count, page_count, embedding_model, indexed_at
        on error: status='failed', ingestion_error (user-safe message) → retry with POST /book/reindex
At startup: migrations run; jobs left queued/processing by a crash are marked failed.
```

### 4.2 Semantic search

```
POST /search/query {query, bookIds?, topK?}
  service/search.py: Search.retrieve
    1. resolve books: only ingestion_status='indexed'; others reported in skippedBooks
    2. Services.embedding().embed_query(query)   (Qwen3 query instruction prepended)
    3. VectorStore.search: Qdrant cosine search, filter book_id ∈ indexed books,
       score ≥ RETRIEVAL_MIN_SCORE (0.45), limit topK (6)
  → results [{bookTitle, headings, pageStart, pageEnd, text, score}]
```

### 4.3 Answer (books first, general knowledge labeled)

```
POST /chat/ask {question, bookIds?, topK?}        (whole answer, stateless)
POST /chat/stream {same, conversationId?}         (SSE: conversation → status → sources → delta… → done | error;
                                                   saved — see 4.5)
  service/search.py: Search.retrieve
    catalog (all books)  → books named in the question by title/author (service/book_mentions.py)
      no books picked + an indexed book is named → search only the named book(s)
      a named book has no text (metadata only)   → skippedBooks + "text not available" note for the LLM
    2–6 books involved (named, or picked)        → search each book separately (every book represented)
    follow-up                                    → also search "previous question + question", merge
    → hits (top 8, score ≥ 0.45) + books (title, authors, year, description, indexed?)
  service/rag.py: Rag.ask / ask_stream
    no LLM configured → mode retrieval_only (passages, no generated text)
    prompt = earlier conversation + "Books involved" + numbered passages [1]..[k] (or "none") + question
    Agno Agent(LiteLLM model), reasoning text never forwarded:
    ── hybrid (BE_RAG_ALLOW_GENERAL_KNOWLEDGE=true, default) ─────────────────────────────────────────
       book facts cite [n]; anything else goes after a line "GENERAL KNOWLEDGE:" (never cited)
       book part with [n]          → mode llm, grounded=true      (usedGeneralKnowledge if a section exists)
       only the general section    → mode general_knowledge       (also when no passage was found at all)
    ── strict (false) ───────────────────────────────────────────────────────────────────────────────
       no indexed book / no passage → no_indexed_books / no_context (no LLM call)
       reply is exactly INSUFFICIENT_CONTEXT → insufficient_context (a real answer that mentions it is kept)
    empty reply (a reasoning model used its whole token budget) → error "empty answer, try again"
  → {answer, grounded, mode, usedGeneralKnowledge, sources [{n, bookTitle, headings, pageStart, pageEnd, score, text, cited}], skippedBooks}
```

The web shows the general-knowledge part in its own box ("General knowledge · not from your books") without
citation chips, so it can never be mistaken for book content. Lists ("- item", "1. step") render as real lists.

### 4.5 Chat history (saved conversations)

```
POST /chat/stream (service/conversation.py: Conversation.stream_turn)
  conversationId?  no → create conversation (title = question)   yes → load it (404 error event if unknown)
  save user message            → event conversation {id, title, …}
  history = last BE_CHAT_HISTORY_TURNS answered turns (mode llm)   → shown to the LLM as "earlier conversation"
  previous question            → retrieval also searches "previous question + this question" and merges by best score,
                                  so "what did he do next?" finds the right passages; the question alone is always searched too
  Rag.ask_stream … → done  → save assistant message (answer + sources snapshot) → done {+conversationId, messageId}
                   → error → save assistant message mode=error (+ partial text)
  client disconnect (Stop / closed tab) → save partial answer mode=stopped
GET /conversation/get-all · GET /conversation/get-one · PUT /conversation/rename · DELETE /conversation/delete
```

Postgres tables `conversations` + `conversation_messages` (`docs/database-schema.md`). No users yet, so every
visitor shares one history (like the catalog). The web keeps the live turn locally and swaps in the saved copy
when the refetched conversation contains it (`utils/chat-thread.ts: pendingVisibility`), so nothing flickers.

### 4.6 Resumable answers (Redis chat sessions)

```
POST /chat/stream ──► ChatSessions.start(): session id + background task ──► Conversation.stream_turn()
                                                                                  │ every event: XADD
browser ◄── SSE (id = Redis stream entry id) ◄── ChatSessions.events(): XREAD BLOCK ◄── chat:session:{id}:events
   │ connection drops (Wi-Fi, reload, switching chats): the task keeps generating and saving
   └──► GET /chat/stream/{id}?after=<last id>  → exactly the missed events, then live (auto-retry 1-8 s, 6×)
        GET /chat/active?conversationId=       → after a reload: re-attach to the running answer (replay from 0)
        POST /chat/stream/{id}/cancel          → Stop: the runner is cancelled, partial answer saved as "stopped",
                                                 stream ends with "cancelled" (flag in Redis works across workers)
```

`service/chat_session.py`. Redis keys (TTL `BE_CHAT_SESSION_TTL_SECONDS`, default 1 h): `chat:session:{id}:events` (stream),
`chat:session:{id}` (hash: status, conversation_id, heartbeat), `chat:session:{id}:cancel`, `chat:conversation:{cid}:active`.
The runner refreshes `heartbeat` every 2 s; a reader that sees a "running" session without heartbeat for
`BE_CHAT_SESSION_STALE_SECONDS` (30) reports it as interrupted instead of waiting forever. On shutdown, running
answers are cancelled so their partial text is saved. Web: `useAskStream` (`ask`, `attach`, `cancel`, `detach`).

### 4.4 Catalog

```
POST /book/add · PUT /book/update · POST /book/get-all · GET /book/get-one · DELETE /book/delete
GET  /book/lookup?q=   → Open Library search (candidates with ISBN)
POST /book/import      → Open Library by ISBN → books row, status 'none' (metadata only)
Duplicates prevented by unique indexes on isbn, file_sha256, (metadata_source, external_id).
Delete order: Qdrant points → PDF file → row (search never returns chunks of a half-deleted book).
```

---

## 5. Where the code lives

### Backend (`apps/backend/`)

| File | Role |
|---|---|
| `api.py` | App entry: middleware, `ROUTER_MODULES` (`book`, `search`, `chat`, `conversation` added), startup (migrations + interrupted-job recovery) |
| `config/base.py` | All settings (`BE_*` in `.env`): storage, chunking, Docling, retrieval, LLM, Open Library |
| `migrations/001_create_books.sql` | `books` table + unique/status indexes |
| `migrations/002_create_conversations.sql` | `conversations` + `conversation_messages` (chat history) |
| `util/migrate.py` | Migration runner (`uv run python -m util.migrate`), advisory-locked, idempotent |
| `service/book_repository.py` | All SQL for `books` (parameterized; whitelisted columns) |
| `dto/book.py`, `dto/search.py`, `dto/chat.py` | Request validation (ISBN checksum, lengths, URLs) |
| `service/book.py` | Catalog, upload, reindex, delete, Open Library import; `to_api()` response shape |
| `router/book.py`, `router/search.py`, `router/chat.py` | HTTP endpoints (thin) |
| `util/storage.py` | Streaming PDF storage + sha256 |
| `util/document_parser.py` | Docling conversion + HybridChunker → chunk dicts |
| `service/ingestion.py` | Background indexing job + status state machine |
| `service/vector_store.py` | Qdrant collection, upsert, delete, search |
| `util/embedding.py` | Company embedding client (batches of 32, retries, dim check, query instruction) |
| `service/search.py` | Retrieval restricted to indexed books; follow-up search merged with the plain search |
| `service/rag.py` | Prompt, context blocks, conversation history in the prompt, citation parsing, honest fallbacks |
| `service/chat_session.py` | Resumable answers: background session per turn, events in a Redis Stream, resume/cancel/active |
| `service/conversation.py`, `service/conversation_repository.py`, `router/conversation.py`, `dto/conversation.py` | Saved conversations: one streamed turn = question + answer saved; list/get/rename/delete |
| `service/llm.py` | Agno Agent + LiteLLM model |
| `service/openlibrary.py` | Open Library client |
| `util/http_errors.py` | Exception → HTTP status (400/404/409/503/500) in the standard envelope |
| `tests/unit/*` | Fast tests (no services) |
| `tests/integration/*` | Real Postgres + Qdrant (`-m integration`); full pipeline (`-m "integration and external and docling"`) |
| `tests/docling/*` | Real Docling parsing of `tests/fixtures/sample_book.pdf` (`-m docling`) |
| `tests/fixtures/sample_book.(html\|pdf)` | Original 3-page test book (free to use) |

### Frontend (`apps/web/src/`)

| Path | Role |
|---|---|
| `pages/library/CatalogPage.tsx`, `BookDetailPage.tsx`, `AskPage.tsx` | Thin route pages |
| `routes/main.routes.tsx` | `/books`, `/books/:id`, `/ask/:conversationId?` (full-height route via `handle.fullHeight`; `/` → `/books`) |
| `config/menu/app.menu.ts` | Sidebar entries (Catalog, Ask) |
| `services/book.service.ts`, `search.service.ts`, `chat.service.ts`, `conversation.service.ts`, `api-endpoints.ts` | API calls via `apiRequests` |
| `features/library/catalog/*` | Catalog grid, search, filters, pagination, import/add dialogs |
| `features/library/books/*` | Detail view, document panel (upload/status polling/reindex), delete |
| `features/library/chat/*` | Chatbot page (`ChatView`): conversation sidebar (grouped by date, rename/delete), message thread (`UserMessage`, `AssistantMessage` with citation chips + collapsible sources), composer pinned at the bottom (Enter to send, book scope picker, Stop) |
| `services/sse-client.ts` + `features/library/chat/hooks/useAskStream.ts` | SSE over `fetch` POST (EventSource can't POST); status → sources → deltas → done/error, abortable (Stop) |
| `styles/variable.css`, `config/theme.ts`, `index.html` | "Mist & Ink" light theme tokens (cool mist neutrals, ink-navy accent, radii), light mode pinned, Fraunces (headings) + Inter (UI); `--content-scale` (0.88) / `--sidebar-scale` (1.1) size the main column and sidebar via CSS zoom |
| `features/library/components/BookStatusBadge.tsx` | The one place status → label ("Indexed (searchable)" vs "Metadata only — not searchable") |
| `components/layouts/AppLayout.tsx`, `AppHeader.tsx`, `AppSidebar.tsx` | App shell (menu-driven sidebar, PerfectScrollArea main; full-height routes manage their own scrolling) |

---

## 6. Measured behaviour (sample book, this machine: 16 CPU, no GPU)

| What | Result |
|---|---|
| Docling first run | ~7 min (downloads ~520 MB of models to `~/.cache/huggingface`, once) |
| Docling warm, 3-page PDF | ~14 s incl. model load; peak RAM ~1.5 GB |
| 152-page book, whole PDF in one Docling pass | RSS reached 3.2 GB with swap full → stopped; led to windowed parsing |
| Upload → indexed (API, background thread) | ~15 s for the sample book |
| Docling layout model share of indexing time | ~91% |
| Docling throughput, 8 threads + layout batch size 1 (defaults) | ~0.8 s/page, vs 1.2–1.4 s/page with 4 threads + batch 4; byte-identical chunks, lower peak RAM |
| Retrieval scores (with query instruction) | relevant top hit 0.53–0.77; off-topic best 0.39 → threshold 0.45 |
| Without query instruction | relevant 0.42–0.72 vs off-topic 0.34 → would miss answers at 0.45 (why the instruction is on) |

---

## 7. Key decisions

| Decision | Why | Trade-off |
|---|---|---|
| Postgres for books/status, Qdrant for chunks | SQL for catalog + atomic status changes; filtered vector search in Qdrant | Two stores; delete removes from both |
| Chunk text in the Qdrant payload | Search returns text without a second query | Moving to pgvector means re-indexing |
| Docling + HybridChunker | Keeps headings, tables and page numbers; chunks sized with the embedding model's tokenizer | Heavy (PyTorch CPU, ~1.7 GB venv), slow on CPU |
| Embed `heading path + text`, display plain text | Section context improves matching | Changing it requires re-indexing |
| Deterministic point ids + sha256 dedupe + atomic status claim | Retries never duplicate books, chunks or jobs | Changing chunk settings needs a reindex |
| Retrieve first; skip the LLM when nothing is relevant | Cheap and cannot hallucinate in that case | Threshold depends on the embedding model — re-measure if it changes |
| `retrieval_only` mode without an LLM | The app is usable before the LLM key exists | Users see passages, not a written answer |
| Windowed Docling parsing (20 pages) | Bounded memory on big books on a CPU-only machine | Tables/sections spanning a window edge are split (heading is carried over) |
| In-process daemon worker thread | No queue infrastructure for the MVP; never blocks shutdown or reload | Jobs die with the process (marked failed at startup); one job at a time |
| Local disk for PDFs | No S3 server locally | Single machine only |

---

## 8. Known limitations

- **LLM:** Kimi Code `openai/kimi-for-coding` (OpenAI-compatible endpoint `https://api.kimi.com/coding/v1`) via LiteLLM, set in `apps/backend/.env`; temperature/top_p left empty because the model only accepts its own values. Verified: cited book answers, separate general-knowledge sections, per-book comparisons. Previously OpenRouter `nvidia/nemotron-3-super-120b-a12b:free`, until the account hit OpenRouter's shared 50 free requests/day cap. Kimi positions the Code plan for coding tools; a Kimi Open Platform key is the intended route for applications. Without `BE_LLM_MODEL` the app falls back to `retrieval_only`.
- Agno returns provider errors as a normal result with `status=ERROR`; `service/llm.py` converts that into a 503 with a short message (bad key / rate limit / unknown model) and logs the details.
- **Cross-language questions are weak**: an Indonesian question about an English book ranked the wrong chapter first.
- **Scanned PDFs** fail with "No text could be extracted" (OCR is off for speed/RAM; `BE_DOCLING_DO_OCR=true` enables it).
- **No login page**: local `.env` runs with `BE_JWT_ACTIVE=false`. The book endpoints use the standard JWT dependency, so enabling it protects them once a login UI exists.
- **One shared library** — no per-user ownership.
- 🛠 Not yet: MCP server, Docker images for the apps, S3 storage.

---

## 9. Run it

```bash
docker compose up -d                                  # repo root: postgres, qdrant, mongo, redis
cd apps/backend && cp .env.example .env               # fill BE_JWT_SECRET / BE_SESSION_SECRET (openssl rand -hex 32)
uv sync && uv run python api.py --port 8020           # migrations run automatically at startup
cd apps/web && npm install && npm run dev             # http://localhost:3000
```

Dev auto-reload watches only the source packages (`RELOAD_DIRS` in `api.py`): a reload kills indexing jobs running in the API process (they are marked failed and need **Reindex**), so editing `tests/`, `scripts/` or writing to `storage/` does not restart the server. After editing `api.py` itself, restart by hand.

Ports taken by another project? Run the backend on another port and point the web proxy at it in `apps/web/env/.env`:
`PORT=3001` and `BACKEND_PROXY_TARGET=http://localhost:8021`.

Tests: `uv run pytest` (unit) · `-m integration` · `-m docling` · `-m external` · `-m ""` (everything) · web: `npm test`.

### Test data: real books from Project Gutenberg

```bash
cd apps/backend
uv run scripts/seed_gutenberg.py --wait        # 23 public-domain books (backend must be running)
uv run scripts/seed_gutenberg.py --only 11 84  # just some Gutenberg ids
```

`scripts/seed_gutenberg.py` downloads each book's HTML edition, strips the Project Gutenberg license header/footer,
images and old page markers, prints a text PDF with headless Chrome, then uses the normal API (`/book/add` with
title, authors, year, subjects, cover → `/book/upload`). So seeding exercises exactly the same path as a user upload.
Downloads and PDFs are cached in `storage/gutenberg/` (git-ignored); re-running skips books that already have a document.
Use `--api` for another backend URL and `--token` when JWT is on.
