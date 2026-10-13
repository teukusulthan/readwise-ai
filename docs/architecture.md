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
│   ├── web/              React 18 + TypeScript + Vite
│   └── mcp/library/      FastMCP server over the backend REST API (stdio / HTTP)
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
 Background: one daemon ingestion thread inside the API process runs the job (claim, status, OCR
 fallback decision, embedding, Qdrant writes); Docling itself parses in one child process
 (util/parse_process.py), so a crashing or runaway PDF cannot take the API and its chat sessions down
 (daemon = shutdown/auto-reload never waits for it; an interrupted job is re-queued at the next startup,
 up to BE_INGESTION_MAX_ATTEMPTS claims, then marked failed).
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
     3. new book: insert row (ingestion_status = 'queued', file metadata)
        existing book (bookId): one guarded UPDATE … WHERE id AND file_sha256 IS NULL sets hash + path +
        'queued' together; a concurrent attach that lost gets 409 and its temp file is removed
     4. util/storage.finalize          move temp file → storage/books/<book_id>.pdf
     5. service/ingestion.enqueue      hand the book id to the worker thread   ──► 200 + Book JSON
  worker thread: Ingestion.run
     6. claim: UPDATE … SET status='processing', ingestion_attempts + 1 WHERE status='queued'
        (atomic; a job runs once; every claim counts an attempt)
     7. util/parse_process.parse_pdf → in the parse child: util/document_parser.parse_pdf
          child: ProcessPoolExecutor(max_workers=1, spawn), replaced after BE_INGESTION_PARSE_TASKS_PER_CHILD
          (20) parses; converters/models are cached per child; chunks come back as one list of dicts.
          Wall-clock limit per parse BE_INGESTION_PARSE_TIMEOUT_SECONDS (1800) → child killed (not awaited),
          failed "Parsing this PDF took too long and was stopped."; child died (segfault, os._exit, OOM kill)
          → failed "The PDF parser crashed on this file."; MemoryError under the optional RLIMIT_AS cap
          BE_INGESTION_PARSE_MAX_MEMORY_MB (0 = off) → failed "Parsing this PDF needed more memory than the
          server allows.". A fresh child takes the next job; the API process is unaffected.
          page count first (pypdfium2) → reject if > MAX_PDF_PAGES
          Docling DocumentConverter (OCR off, table structure on, 4 CPU threads) in windows of 20 pages
          → one DoclingDocument per window (absolute page numbers; heading carried across window boundaries)
          HybridChunker(tokenizer = Qwen3 tokenizer, max 512 tokens, merge_peers)
          → chunks: text, embed_text (headings + text), headings, page_start, page_end
          zero chunks (scanned PDF) and BE_DOCLING_OCR_FALLBACK=true → if Docling has a usable OCR engine
          (util/document_parser.ocr_available: probed in the parse child by building the OCR pipeline;
          the answer is cached once per API process; a probe that crashed/timed out counts as "no", uncached),
          parse once more with a second, separately cached converter with OCR on (same threads / layout
          batch); still nothing → failed "No text could be extracted, even with OCR. …". No engine → no
          OCR pass, one warning per process ("OCR fallback enabled but no OCR engine is available;
          skipping") and the original "No text could be extracted. … (OCR is disabled) …" message.
          Logs say which path ran.
     8. for each batch of 32 chunks: Services.embedding().embed_documents(embed_text)
                                     VectorStore.upsert_chunks  (point id = uuid5(book_id, chunk_index))
     9. delete leftover points with chunk_index ≥ new count (re-index that produced fewer chunks)
    10. book row deleted meanwhile? → delete this book's points, stop (no orphan vectors)
        status='indexed', chunk_count, page_count, embedding_model, indexed_at
        on error: status='failed', ingestion_error (user-safe message) → retry with POST /book/reindex
        (reindex resets ingestion_attempts to 0). The final indexed/failed write is guarded
        (WHERE status='processing'); if no row matched, a warning is logged.
At startup (Ingestion.recover_interrupted): migrations run, then one UPDATE moves every book left
queued/processing by the previous process: ingestion_attempts < BE_INGESTION_MAX_ATTEMPTS (3) → 'queued'
and handed to the worker again (interrupted 'processing' job first, then queue order; the
BE_INGESTION_MAX_QUEUED cap does not apply — it is not a new submission); at the cap → 'failed'
"Ingestion was interrupted (server restart). Retry with reindex." Counts of both are logged.
At shutdown (lifespan → service/ingestion.shutdown): waiting jobs are no longer started (they stay
'queued', no attempt spent), the parse child is killed without waiting, and the job it was parsing stays
'processing' — both resume at the next startup.
Assumption: exactly one API process owns the ingestion queue. With several processes, a starting one
would re-queue jobs another is still running (a multi-process owner/heartbeat design is out of scope).
```

### 4.2 Semantic search

```
POST /search/query {query, bookIds?, topK?}
  service/search.py: Search.retrieve
    1. resolve books: only ingestion_status='indexed'; others reported in skippedBooks
    2. Services.embedding().embed_query(query)   (Qwen3 query instruction prepended)
    3. VectorStore.search: Qdrant cosine search, filter book_id ∈ indexed books,
       score ≥ RETRIEVAL_MIN_SCORE (0.45), limit topK (8) × RETRIEVAL_CANDIDATE_MULTIPLIER (4)
    4. select_diverse: keep the best topK candidates with at most RETRIEVAL_MAX_PER_SECTION (2)
       per section = (book_id, heading path); if the cap leaves fewer than topK, the best skipped
       candidates fill the rest; best first. Applied per search scope: the whole selection, each
       book of a 2–6-book comparison (so every book stays represented), and after merging the
       follow-up query's candidates. RETRIEVAL_MAX_PER_SECTION=0 = plain top-k.
  → results [{bookTitle, headings, pageStart, pageEnd, text, score}]
     bookTitle (here, in prompts and in chat sources) comes from the books table, not the point
     payload (which keeps the title at indexing time), so a rename shows at once without re-indexing
```

Why the section cap: a chapter is chunked into many similar passages, so a plain top-k often
returns eight near-duplicates of the one or two closest chapters. "What does Scrooge learn from the
Ghost of Christmas Yet to Come?" got passages from Staves 1–3 only; with the cap, Stave IV
("The Last of the Spirits") is rank 6. Measure changes with `apps/backend/scripts/eval_retrieval.py`
(question → expected book + heading over the seeded Gutenberg books, prints hit@k for the running
backend): baseline 5/7, with the cap 6/7 at k = 8.

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
citation chips, so it can never be mistaken for book content. The split only happens on a line starting with the
heading and a required colon (`GENERAL KNOWLEDGE:`, same rule in the backend; case and Markdown decoration tolerated), never on a sentence that starts with those
words. Answers render as safe Markdown (`react-markdown` + `remark-gfm`, no raw HTML, links open in a new tab,
images shown as alt text) with `[n]` citation chips inside paragraphs, lists and tables. A visually hidden live
region announces "Answer ready" / "Answer stopped" once per turn (errors are spoken by the answer's alert); the streaming text is not a live region.

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

Postgres tables `conversations` + `conversation_messages` (`docs/database-schema.md`). Conversations are
**per user** (`conversations.owner_id`, see §4.7); the book catalog stays one shared team library. The web keeps the live turn locally and swaps in the saved copy
when the refetched conversation contains it (`utils/chat-thread.ts: pendingVisibility`), so nothing flickers.

### 4.6 Resumable answers (Redis chat sessions)

```
POST /chat/stream ──► ChatSessions.start(): session id + background task ──► Conversation.stream_turn()
                                                                                  │ every event: XADD
browser ◄── SSE (id = Redis stream entry id) ◄── ChatSessions.events(): XREAD BLOCK ◄── chat:session:{id}:events
   │ connection drops (Wi-Fi, reload, switching chats): the task keeps generating and saving
   └──► GET /chat/stream/{id}?after=<last id>  → exactly the missed events, then live (auto-retry 1-8 s, 6×)
        GET /chat/active?conversationId=       → after a reload or on coming back to the chat: re-attach to the
                                                 running answer (replay from 0)
        POST /chat/stream/{id}/cancel          → Stop: the runner is cancelled, partial answer saved as "stopped",
                                                 stream ends with "cancelled" (flag in Redis works across workers)
```

`service/chat_session.py`. Redis keys (TTL `BE_CHAT_SESSION_TTL_SECONDS`, default 1 h): `chat:session:{id}:events` (stream),
`chat:session:{id}` (hash: status, conversation_id, heartbeat), `chat:session:{id}:cancel`, `chat:conversation:{cid}:active` (the claim: set with `SET NX EX` before the stream starts, so only one turn runs per conversation — a second `POST /chat/stream` gets HTTP 409 "A question is already being answered in this conversation."; released by atomic compare-and-delete on finish/cancel/error; a claim whose session heartbeat is stale is taken over).
The runner refreshes `heartbeat` every 2 s; a reader that sees a "running" session without heartbeat for
`BE_CHAT_SESSION_STALE_SECONDS` (30) reports it as interrupted instead of waiting forever. On shutdown, running
answers are cancelled so their partial text is saved. Web: `useAskStream` (`ask`, `attach`, `cancel`, `detach`).
Web specifics: leaving a conversation marks its cached thread stale and every visit asks `GET /chat/active` afresh
(`useActiveTurn`, never cached), so coming back re-attaches. After Stop, Send stays disabled until the stream ends
with `cancelled` (or ends at all; 5 s fallback). Asking again while the previous turn is only drawn locally refetches
the thread first so that turn stays visible. A frame whose data is not a JSON object is skipped with a console
warning, and `streamSse` cancels the body reader on every exit (end, abort, error), which closes the connection.

### 4.7 Accounts and the service token

```
BE_JWT_ACTIVE=false  → no login: every caller is the owner "local" (sees its rows + legacy owner-NULL rows)
BE_JWT_ACTIVE=true   → router dependency auth/principal.py: current_principal
    X-Internal-Token == BE_INTERNAL_TOKEN (hmac.compare_digest) → "service:internal"  (wrong value → 403)
    else access token (Bearer header or HttpOnly `token` cookie, JWTBearer) → user = JWT `user_id` claim
web: /login, /register (no app shell) → POST /auth/login sets HttpOnly `token` + `refresh_token` cookies,
     body = {user}; 401 → GET /auth/refresh once → else /login?next=<path>   (only with VITE_AUTH_ENABLED=true)
```

- **Shared:** catalog, upload, search, `/chat/ask` — any principal, including the service token (the seed script's
  `--internal-token` uses it to add and upload books).
- **Personal:** `/conversation/*`, `/chat/stream`, resume, cancel, `/chat/active`. Rows are filtered by
  `owner_id`; another user's conversation answers 404 (existence not revealed), and continuing it is refused with
  404 before any claim, so nobody can keep someone else's conversation busy. Each Redis chat session stores its
  `owner`: resume/cancel of a foreign session look like an unknown session. The service principal gets 403.
- **Legacy rows** (created before migration 004, `owner_id NULL`) are visible only to "local": the no-login setup keeps
  its history, real users never see them once JWT is on. Rows created without login are owned by "local" and
  likewise stay invisible to real users.
- Registration: `/auth/register` needs SMTP + Proofy by default (OTP mail, then `POST /auth/verification`).
  `BE_AUTH_EMAIL_VERIFICATION=false` (development only) creates the account at once.
- Rate limits key the service principal as `service:internal` (valid token only), users as `user:<id>`, else IP.

### 4.4 Catalog

```
POST /book/add · PUT /book/update · POST /book/get-all · GET /book/get-one · DELETE /book/delete
GET  /book/lookup?q=   → Open Library search (candidates with ISBN)
POST /book/import      → Open Library by ISBN → books row, status 'none' (metadata only)
Duplicates prevented by unique indexes on isbn, file_sha256, (metadata_source, external_id).
Delete: one guarded DELETE … WHERE id AND ingestion_status NOT IN ('queued','processing') (409 while
indexing, 404 if missing) → Qdrant points → PDF file. Search only uses books in the catalog, so a
deleted book's points are never returned; the worker drops points of a book deleted under it.
```

---

### 4.8 MCP server (`apps/mcp/library/`)

```
MCP client ──stdio──────────────► server.py (FastMCP) ──HTTP + X-Internal-Token──► backend REST API
           ──http /mcp + Bearer──►   list_books  → POST /book/get-all
                                     get_book    → GET  /book/get-one
                                     search_passages → POST /search/query
                                     ask_library → POST /chat/ask   (non-streaming, stateless)
```

Read-only tools; the server never connects to Postgres, Qdrant or storage, so the backend's access rules (service principal §4.7, rate limits, indexed-only search) apply unchanged. Outbound auth: `LIBRARY_INTERNAL_TOKEN` is sent as `X-Internal-Token` (= `BE_INTERNAL_TOKEN`); with `BE_JWT_ACTIVE=false` it can stay empty. Inbound auth: stdio needs none (the client spawns the process); the HTTP transport refuses to start without `MCP_BEARER_TOKEN` (>= 32 chars) and a FastMCP `TokenVerifier` accepts exactly that token (`hmac.compare_digest`), others get 401. Backend failures become tool errors (unreachable, 401/403 credentials, 404, 429 with `Retry-After`, 503). Outputs are trimmed typed models, not backend envelopes (passages cut at 1500 chars, source snippets at 600). Setup and config: `apps/mcp/library/README.md`.

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
| `util/document_parser.py` | Docling conversion + HybridChunker → chunk dicts (runs in the parse child) |
| `util/parse_process.py` | The parse child: timeout, memory cap, crash → user-safe errors, kill on shutdown |
| `service/ingestion.py` | Background indexing job + status state machine |
| `service/vector_store.py` | Qdrant collection, upsert, delete, search |
| `util/embedding.py` | Company embedding client (batches of 32, retries, dim check, query instruction) |
| `service/search.py` | Retrieval restricted to indexed books; follow-up search merged with the plain search |
| `service/rag.py` | Prompt, context blocks, conversation history in the prompt, citation parsing, honest fallbacks |
| `service/chat_session.py` | Resumable answers: background session per turn, events in a Redis Stream, resume/cancel/active |
| `service/conversation.py`, `service/conversation_repository.py`, `router/conversation.py`, `dto/conversation.py` | Saved conversations: one streamed turn = question + answer saved; list/get/rename/delete |
| `service/llm.py` | Agno Agent + LiteLLM model |
| `service/openlibrary.py` | Open Library client |
| `util/http_errors.py` | Exception → HTTP status in the standard envelope: `NotFoundError` 404, `ConflictError`/duplicate 409, `ValueError` 400, `ServiceUnavailableError` and search outages (`EmbeddingError`, Qdrant connection errors; message "Search service unavailable") 503, anything else 500 (logged). Plain `LookupError`/`KeyError` is a bug, not a 404 |
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
| Parse child vs in-process (shared 32-CPU box under load ~10–14, so slower than the row above) | warm: 3.4–3.7 vs 3.6 s/page (3-page sample), 2.8–3.4 vs 2.4–3.0 s/page (14-page book) — within run-to-run noise; first parse incl. model load 34–37 s vs 31–36 s (+~1–3 s: spawning the child and re-importing `api.py`); identical chunks |
| `BE_INGESTION_PARSE_MAX_MEMORY_MB` on the 3-page sample | 3072: child spins, stopped by the timeout; 6144: native (Rust tokenizer) panic → generic failure; 12288: parses. RLIMIT_AS counts virtual memory (PyTorch reserves far more than it uses) |
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
| In-process daemon worker thread | No queue infrastructure for the MVP; never blocks shutdown or reload | Jobs die with the process (re-queued at startup); one job at a time |
| Docling in one child process (spawn, recycled every 20 parses) | A native crash, memory blow-up or endless parse fails one book instead of killing the API and every chat session | Chunks of a book cross the process boundary as one list; ~1–3 s to start a child plus a model load per new child |
| Local disk for PDFs | No S3 server locally | Single machine only |

---

## 8. Known limitations

- **LLM:** Kimi Code `openai/kimi-for-coding` (OpenAI-compatible endpoint `https://api.kimi.com/coding/v1`) via LiteLLM, set in `apps/backend/.env`; temperature/top_p left empty because the model only accepts its own values. Verified: cited book answers, separate general-knowledge sections, per-book comparisons. Previously OpenRouter `nvidia/nemotron-3-super-120b-a12b:free`, until the account hit OpenRouter's shared 50 free requests/day cap. Kimi positions the Code plan for coding tools; a Kimi Open Platform key is the intended route for applications. Without `BE_LLM_MODEL` the app falls back to `retrieval_only`.
- LLM timeouts: `BE_LLM_TIMEOUT_SECONDS` (120) and `BE_LLM_NUM_RETRIES` (2) go to LiteLLM through Agno's `request_params` (sync and streaming). `BE_LLM_FIRST_TOKEN_TIMEOUT_SECONDS` (90) applies to streaming only: if no content or reasoning token arrives in time, the generation is cancelled and the turn ends with the SSE `error` event "The model took too long to respond. Try again."; the conversation claim is released through the normal finish path.
- Rate limits and caps (see `docs/api-spec.md` § Rate limits): per-route fixed-window budgets live in `middleware/route_limits.py` (Redis, per user else per IP via `util/client_ip.py`; `X-Forwarded-For` only from `BE_TRUSTED_PROXIES`). The ingestion queue cap counts `queued` books in Postgres (`BookRepository.count_queued`), so it holds across processes; the chat cap counts running sessions with a fresh heartbeat in the Redis ZSET `chat:sessions:running`, checked in `ChatSessions.claim` and released with the conversation claim. Both caps are soft (check-then-insert) and can overshoot by a few under a simultaneous burst.
- Agno returns provider errors as a normal result with `status=ERROR`; `service/llm.py` converts that into a 503 with a short message (bad key / rate limit / unknown model) and logs the details.
- **Cross-language questions are weak**: an Indonesian question about an English book ranked the wrong chapter first.
- **Scanned PDFs** are parsed twice: first with OCR off (fast), then — only when that yields no text — once more with OCR on (`BE_DOCLING_OCR_FALLBACK`, default true). OCR is much slower; if it also finds nothing the book fails with "No text could be extracted, even with OCR. …". `BE_DOCLING_DO_OCR=true` turns OCR on for every book (no fallback). **The OCR pass needs a working Docling OCR engine:** with the current lock (docling 2.129.0 + rapidocr 3.10.0, which no longer exposes `PP_OCRV6_LANGS`) Docling finds no engine, so the startup-cached probe reports "no OCR engine", the OCR pass is skipped and scanned PDFs still fail with the original message. rapidocr 3.9.x works with docling, but resolving it upgrades numpy/pandas/opencv, so that pin is a separate dependency decision. A failed probe (e.g. an OCR model download error) is cached too: restart to probe again.
- **Accounts are opt-in**: local `.env` runs with `BE_JWT_ACTIVE=false` and the web with `VITE_AUTH_ENABLED=false` (no login, owner "local"). Turn both on together (§4.7). The auth cookies are `Secure` (`BE_AUTH_COOKIE_SECURE=true`): browsers accept them on `http://localhost`, but over plain HTTP from another host (e.g. `http://<LAN IP>:3000`) they are dropped — use HTTPS, or `BE_AUTH_COOKIE_SECURE=false` in development only. After login the web calls `GET /auth/validate` and says so if the cookie did not stick.
- **One shared library** — books have no owner; only conversations are per user. No roles: every signed-in user can add, edit and delete books.
- Registration with the default email verification needs working SMTP and a Proofy key; without them use `BE_AUTH_EMAIL_VERIFICATION=false` in development only.
- Docker images exist for all three apps (§9, profile `app`); their builds have not been verified on a host with a working Docker daemon yet. 🛠 Not yet: S3 storage.

---

## 9. Run it

```bash
docker compose up -d                                  # repo root: postgres, qdrant, mongo, redis
cd apps/backend && cp .env.example .env               # fill BE_JWT_SECRET / BE_SESSION_SECRET (openssl rand -hex 32)
uv sync && uv run python api.py --port 8020           # migrations run automatically at startup
cd apps/web && npm install && npm run dev             # http://localhost:3000
```

Dev auto-reload is opt-in (`--reload`; the nx `serve` target passes it) and watches only the source packages (`RELOAD_DIRS` in `api.py`): a reload kills indexing jobs running in the API process (and the parse child) (the next startup re-queues them, up to `BE_INGESTION_MAX_ATTEMPTS` claims; after that they are marked failed and need **Reindex**), so editing `tests/`, `scripts/` or writing to `storage/` does not restart the server. After editing `api.py` itself, restart by hand.

**Containers.** `docker compose --profile app up -d --build` also runs `backend` (Python 3.12 slim + uv, one worker, volumes `book-storage` and `hf-cache`), `web` (Vite build behind unprivileged nginx on host port 3000: SPA fallback, `/api/v1/apps/` proxied to the backend with the prefix stripped, SSE unbuffered on `/chat/stream`, `/cdn-assets/` proxied to `ICON_CDN_PROXY_TARGET`) and `mcp` (HTTP transport, port 8030). Compose points the backend at `postgres`/`qdrant`/`mongo`/`redis` by service name; the env files stay git-ignored. Details: README "Running with Docker".

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
Use `--api` for another backend URL and, when JWT is on, `--token <access token>` or `--internal-token <BE_INTERNAL_TOKEN>`.

### Startup defaults

- **Routers:** with `BE_ENABLED_ROUTERS` empty, only the library routers mount (`health`, `auth`, `book`, `search`, `chat`, `conversation`; list in `config/routers.py`). The legacy boilerplate admin surface (`user`, `role`, `group`, `permission`, `upload`, and `/monitoring/threadpool` as `monitoring`) mounts only when named in `BE_ENABLED_ROUTERS` / `--routers`. Explicit lists behave as before.
- **Reload:** `uvicorn` reload is off unless `--reload` is passed (ignored with `--worker > 1`).
- **Secrets:** with `BE_JWT_ACTIVE=true`, `BE_JWT_SECRET` must be at least 32 characters; with `BE_ENC_ACTIVE=true`, `BE_ENC_SECRET` must be exactly 32 (AES-256 key). Startup fails with the key name and a generator command otherwise.
- **Singletons:** the Postgres pool, Qdrant, embedding, Mongo and Redis clients are created under a per-class lock (double-checked). The Postgres pool (`BE_POSTGRES_POOL_MAX_SIZE`, default 10) is intentionally smaller than the 64-thread worker pool: threads hold a connection only while querying and otherwise wait on the pool. The async Redis client is a process-wide singleton bound to the server's single event loop.
