# Backend Changelog

Tracks all backend changes across sprints — API routes added, DB migrations applied, services built, auth changes.

Append-only. Newest entries at the top. Updated whenever a backend task is created or completed.

---

<!-- ENTRY FORMAT:
### YYYY-MM-DD · [Sprint NN — slug](../sprint/active/NN-slug/sprint.md) · Task: [task title](../sprint/.../backend/NN-task.md) · STATUS

**Event:** Task created | Task completed | Files modified
**Files:** `path/to/route.py`, `path/to/migration.sql`
> One-line summary of what changed or was delivered.
-->

### 2026-10-12 · Faster PDF indexing (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `apps/backend/config/base.py`, `apps/backend/util/document_parser.py`, `apps/backend/.env.example`, `apps/backend/tests/unit/test_document_parser_unit.py`, `docs/architecture.md`
> Docling now defaults to 8 threads and layout batch size 1 (new `BE_DOCLING_LAYOUT_BATCH_SIZE`). Measured 30–45% faster (~0.8 s/page vs 1.2–1.4) with byte-identical chunks and lower peak RAM; chunking, OCR and table settings are unchanged.

### 2026-10-09 · Boilerplate hardening & stack migration (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `apps/backend/pyproject.toml`, `apps/backend/uv.lock`, `apps/backend/.python-version`, `apps/backend/api.py`, `apps/backend/config/base.py`, `apps/backend/auth/auth_bearer.py`, `apps/backend/auth/auth_handler.py`, `apps/backend/router/middleware.py`, `apps/backend/middleware/body_limit.py`, `apps/backend/middleware/rate_limiter.py`, `apps/backend/router/health.py`, `apps/backend/service/health.py`, `apps/backend/service/__init__.py`, `apps/backend/service/upload.py`, `apps/backend/util/postgres.py`, `apps/backend/util/qdrant.py`, `apps/backend/util/helper.py`, `apps/backend/tests/**`, `docker-compose.yml`
> Moved to uv (Python 3.12, `requirements.txt` removed). Fixed a hard-coded JWT bypass, a predictable fixed-seed email OTP, and refresh tokens being accepted as access tokens. Added a real request-body limit, explicit CORS origins, a separate session secret, the rate limiter (fails open), and an ASGI `DecryptPayload` that works. Upload: size cap enforced, `application/octet-stream` dropped, missing `Services.boto3()` and `date_converter` added, router registered (with `role`). Added PostgreSQL and Qdrant clients, `/health` and `/health/ready`, the pytest suite, and docker compose for the infra.

### 2026-10-09 · Company embedding service integrated (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `apps/backend/util/embedding.py`, `apps/backend/config/base.py`, `apps/backend/service/__init__.py`, `apps/backend/service/health.py`, `apps/backend/.env.example`, `apps/backend/tests/unit/test_embedding.py`, `apps/backend/tests/external/test_embedding_service.py`
> Verified the company TEI service (Qwen3-Embedding-0.6B: 1024-dim normalised vectors, 32 inputs per request max, no auth). Added an `EmbeddingClient` that batches to 32, retries 429/5xx/timeouts, never retries validation errors, and rejects vectors of the wrong dimension. Exposed it as `Services.embedding()` and added an `embedding` check to `/health/ready`. Unit tests use a mocked transport; live tests run with `-m external`.

### 2026-10-09 · RAG Book Library MVP backend (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `migrations/001_create_books.sql`, `util/{migrate,storage,document_parser,http_errors}.py`, `dto/{book,search,chat}.py`, `service/{book,book_repository,ingestion,vector_store,search,rag,llm,openlibrary}.py`, `router/{book,search,chat}.py`, `api.py`, `config/base.py`, `pyproject.toml`, `tests/**`
> Added the PostgreSQL `books` table and a migration runner, catalog CRUD and search, Open Library import, PDF upload with sha256 dedupe, and background ingestion (Docling + HybridChunker → company embeddings → Qdrant, with deterministic ids and atomic status changes). Added semantic search over indexed books only, and grounded answers through Agno + LiteLLM with citations and honest fallbacks (no_context / insufficient_context / retrieval_only). Dependencies: docling 2.129.0, agno 3.0.10, litellm 1.102.0, and CPU-only torch; boto3, s3fs, numpy and pandas pins relaxed. Qwen3 query instruction enabled by default, based on measured scores. 110 tests pass (unit, integration, docling, external).

### 2026-10-09 · OpenRouter via LiteLLM + LLM error handling fix (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `apps/backend/service/llm.py`, `apps/backend/tests/unit/test_llm.py`, `apps/backend/.env.example`, `docs/architecture.md`
> Verified that OpenRouter routing works through LiteLLM: a fake key gets OpenRouter's 401. Fixed a bug where Agno's error results (`status=ERROR`, with the error text as content) would have been shown as an answer. They now become a 503 with an actionable message, and the details go to the logs. Documented OpenRouter configuration.

### 2026-10-09 · LLM configured: OpenRouter Nemotron 3 Super (free) (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `apps/backend/.env` (local, not committed), `apps/backend/.env.example`, `apps/backend/service/rag.py`, `docs/architecture.md`
> The Gemma 4 `:free` models were rate-limited upstream (Google AI Studio). Switched to `openrouter/nvidia/nemotron-3-super-120b-a12b:free`, which was verified on the sample book: cited answers, admits missing facts, ignores off-topic questions without an LLM call, and answers Indonesian questions in Indonesian. The prompt now asks for plain-text answers (no Markdown).

### 2026-10-09 · Streaming answers + narrative prompt (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `service/rag.py`, `service/llm.py`, `router/chat.py`, `config/base.py`, `.env.example`, `tests/unit/test_rag_stream.py`
> Added `POST /chat/stream`, which streams Server-Sent Events through FastAPI's `EventSourceResponse` with keep-alive pings: status → sources → delta… → done or error. The `INSUFFICIENT_CONTEXT` marker is never streamed (MarkerGate). Reasoning tokens are dropped. Agno's `RunErrorEvent` becomes an `error` event. The prompt now asks for a direct answer, then 2–4 cited paragraphs with no invented conclusions. Defaults: `RETRIEVAL_TOP_K` 8 (was 6), `LLM_MAX_TOKENS` 1600 (was 1024). 125 tests pass.

### 2026-10-09 · Bounded-memory ingestion + non-blocking workers (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `util/document_parser.py`, `service/ingestion.py`, `service/rag.py`, `config/base.py`, `.env.example`, `tests/**`
> Indexing a real 152-page book in a single Docling pass reached 3.2 GB RSS with swap full; the job was stopped. Docling now parses in windows of 20 pages (`DOCLING_PAGE_WINDOW`), the page limit is checked from a cheap page count first, headings carry over between windows, and Docling is limited to 4 CPU threads (`DOCLING_NUM_THREADS`). Result: 152 pages → 175 chunks in 210 s, with peak RSS around 2.3–2.8 GB that no longer grows per window. Ingestion workers are now daemon threads, so dev auto-reload and shutdown no longer hang until a book finishes. Answers are normalized to one paragraph per line. 129 tests pass.

### 2026-10-09 · Saved chat conversations + follow-up questions (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `migrations/002_create_conversations.sql`, `service/conversation.py`, `service/conversation_repository.py`, `router/conversation.py`, `dto/conversation.py`, `dto/chat.py`, `router/chat.py`, `service/rag.py`, `service/search.py`, `config/base.py`, `api.py`, `.env.example`, `tests/unit/test_conversation.py`, `tests/unit/test_rag_stream.py`, `tests/integration/test_conversation_api.py`
> `POST /chat/stream` now saves each turn to Postgres (`conversations`, `conversation_messages`), creating a conversation when no `conversationId` is sent. It emits a first `conversation` event, and `done`/`error` carry the saved `messageId`. Failed answers are saved as `error` and answers cut off by a client disconnect as `stopped`, with the partial text. New endpoints: `GET /conversation/get-all`, `GET /conversation/get-one`, `PUT /conversation/rename`, `DELETE /conversation/delete`. Follow-ups: the last `BE_CHAT_HISTORY_TURNS` (3) answered turns go into the prompt as context only, never as a source of facts. Retrieval also searches "previous question + question" and merges the results by best score, which was verified live: "How does it relate to motivation?" resolved to the "do something" principle. `/chat/ask` stays stateless. 142 tests pass (all markers).

### 2026-10-09 · Gutenberg seed script (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `scripts/seed_gutenberg.py`, `docs/architecture.md`
> `uv run scripts/seed_gutenberg.py --wait` adds 23 public-domain books with full text. It downloads Gutenberg HTML, strips the license boilerplate, prints a PDF with headless Chrome, and goes through the real `/book/add` + `/book/upload` pipeline. It is idempotent, and caches downloads in `storage/gutenberg/`. The script declares its own dependencies inline (PEP 723), so `pyproject.toml` is unchanged.

### 2026-10-09 · Dev reload no longer kills indexing on test/script edits (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `api.py`, `scripts/seed_gutenberg.py`, `docs/architecture.md`
> Seeding showed that editing any `.py` file under `apps/backend/` (including `scripts/` and `tests/`) reloaded the dev server. The reload killed the running indexing job and dropped the in-memory queue; at startup, 14 jobs were correctly marked failed and had to be reindexed. The dev reloader now watches only the app's source packages (`RELOAD_DIRS`). The seed script also line-buffers its output so its progress can be followed in a log.

### 2026-10-09 · Smarter answers: general knowledge (labeled), book focus, per-book retrieval (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `service/rag.py`, `service/search.py`, `service/book_mentions.py` (new), `service/book_repository.py`, `service/conversation.py`, `config/base.py`, `.env.example`, `tests/unit/{test_rag_hybrid,test_search_focus,test_book_mentions}.py` (new), `tests/unit/{test_rag,test_rag_stream,test_conversation}.py`, `tests/integration/test_full_pipeline.py`
> The history showed four separate causes of "Not enough information in the books":
> - **Model flakiness and the token budget:** retrieval was perfect, but the reasoning model's hidden thinking used 300–1,300 of its 1,600 tokens (measured), so the answer could come back empty, and an empty answer was treated as "insufficient".
> - **Named books:** a question about "Mark Manson's book" searched every book.
> - **Comparisons:** one book took every passage slot.
> - **Metadata-only books:** *Atomic Habits* has no text to answer from.
>
> Changes:
> - **Hybrid policy (`BE_RAG_ALLOW_GENERAL_KNOWLEDGE=true`, the new default):** books first and cited, with the model's own knowledge in a separate `GENERAL KNOWLEDGE:` section that is never cited. When no passage is relevant the answer comes from general knowledge (`mode: general_knowledge`), and `usedGeneralKnowledge` is returned. Strict mode is still available.
> - **Book focus:** books named by title or author narrow the search when the user hasn't picked books, and use a relaxed 0.35 threshold. A named book without text is reported in `skippedBooks` and described to the LLM as "text not available".
> - **Comparisons:** 2–6 books are searched one book at a time.
> - **Prompt:** includes book details (title, authors, year, description). Lists are allowed; the conflicting "plain text only" rule was removed.
> - **Robustness:** `LLM_MAX_TOKENS` raised to 4000. An empty reply is now an error ("try again"), and a real answer that also contains the marker is kept.
>
> Verified live: "do something" → book answer (4 cited); "Mark Manson's book" → his book (5 cited); "According to Atomic Habits…" → labeled general knowledge, with the book listed as not searched; *Time Machine* vs *War of the Worlds* → passages from both (5 cited); "boiling point of mercury" → labeled general knowledge. 161 tests pass (all markers).

### 2026-10-09 · LLM switched to Kimi; temperature/top_p optional (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `service/llm.py`, `config/base.py`, `.env.example`, `tests/unit/test_llm.py`, `docs/architecture.md` (local `.env`: model + base URL)
> The OpenRouter account had used its shared daily cap for free models (`free-models-per-day`, 50; 0 credits), so every free model was blocked until 07:00 WIB. Switched to the user's Kimi Code key: `openai/kimi-for-coding` at `https://api.kimi.com/coding/v1`. The model rejects any temperature except 1 and any `top_p` except 0.95, and Agno sends its own defaults (0.7 / 1.0) unless a value is `None`. `BE_LLM_TEMPERATURE` and the new `BE_LLM_TOP_P` are now optional: empty means "not sent", so the provider default applies. This also suits many reasoning models. Verified live on all five reference questions and in the browser (book citations + a labeled general-knowledge section).

### 2026-10-09 · Resumable chat answers with Redis sessions (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `service/chat_session.py` (new), `router/chat.py`, `api.py`, `config/base.py`, `.env.example`, `tests/unit/test_chat_session.py` (new), `tests/integration/test_chat_session_redis.py` (new), `tests/integration/conftest.py`, `tests/unit/test_rag_stream.py`, `tests/integration/test_conversation_api.py`
> **What changed:** an answer now runs in a background *session* instead of inside the HTTP request. Each event is appended to a Redis Stream, and its entry id is the SSE event id. A disconnect no longer stops generation. New endpoints:
> - `GET /chat/stream/{sessionId}?after=` (or `Last-Event-ID`): replays the missed events, then streams live.
> - `POST …/cancel`: Stop; the partial answer is saved as `stopped`.
> - `GET /chat/active`: re-attach after a reload.
>
> A heartbeat lets readers tell a dead session from a slow model, and shutdown cancels running answers cleanly.
>
> **Verified live (Kimi):**
> - curl cut off after 4 events: the server generated 169 more with no client; resuming from the last id delivered exactly the remaining 457.
> - Browser: a simulated network drop showed "reconnecting" and finished the same answer; a full page reload mid-answer re-attached; Stop saved a 499-character `stopped` answer.
>
> 174 tests pass (all markers).
