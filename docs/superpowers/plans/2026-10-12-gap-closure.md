# Gap Closure Plan — Readwise AI

**Goal:** close the gaps found in the 2026-10-12 audit (features promised by the README /
`docs/architecture.md` / stack rules but missing, web gaps where the backend already has the
capability, quality issues, engineering basics, leftover boilerplate).

**Spec:** none exists (`sprint/` and `brief/` are empty). The audit list is the requirement
source; rulings made by the controller are provisional and recorded in the SDD ledger.

**Branch:** `feat/gap-closure` (one commit or more per task; never push; never touch `main`).

## Global Constraints (bind every task)

1. **Public repository.** Never commit secrets, internal IPs/hosts, or company names. Internal
   hosts come only from git-ignored env files (`apps/backend/.env`, `apps/web/env/.env`).
   Never edit those two env files unless the task says so. `.env.example` files hold placeholders.
2. **Python:** uv only (`uv add`, `uv run`), never pip/venv/requirements.txt. Run from `apps/backend/`.
   Backend conventions: thin routers (`router/*.py`) → services (`service/*.py`) → repositories;
   responses through the existing `BaseResponse` helpers; SQL via versioned migrations in
   `apps/backend/migrations/NNN_*.sql` (next free number) — never edit an applied migration.
   Settings: new `BE_*` keys in `config/base.py` + `.env.example` (documented).
3. **Web:** React 18 + TS + Vite + TanStack Query + shadcn/ui. Follow `.claude/rules/architecture.md`
   (component placement decision tree; domain components under `src/features/library/...`;
   routes + menu wired together via `src/config/menu/*`; scroll regions use `PerfectScrollArea`;
   shadcn/Radix primitives for dialogs/forms; the existing "Mist & Ink" tokens/classes, light mode;
   icons via the existing `renderIcon` / Phosphor setup). Read `apps/web/AI_GUIDE.md` before writing
   web code. Match neighbouring code style.
4. **Tests are required** for new behaviour: backend `uv run pytest` (unit; add `-m integration`
   tests when the change touches Postgres/Qdrant), web `npm test` (vitest) + `npm run typecheck` +
   `npx eslint` on changed files. All existing tests must stay green.
5. **Docs:** append an entry to `changelog/backend.md` and/or `changelog/web.md` (follow the entry
   format at the top of each file; "no sprint"). Update `docs/architecture.md` / `docs/api-spec.md`
   when behaviour or endpoints change.
6. **No live dev servers.** This is a shared multi-user machine: ports 8020, 8021, 3000, 3001 belong
   to other users. If a task needs a running backend/web for a smoke test, start it on a free port
   (backend 8025, web 3005), stop it before reporting, and never kill processes you didn't start.
   Databases come from `docker compose up -d`; if Docker is unavailable, say so in the report and
   rely on unit tests. Never run destructive operations against the dev databases (`library`,
   `book_chunks`) — tests use `library_test` / `book_chunks_test`. Never use sudo.
7. Commit messages: **Conventional Commits** — `<type>(<scope>): <subject>` (type ∈ feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert; lowercase scope e.g. `api`, `web`, `ingestion`, `search`, `auth`, `mcp`; imperative lowercase subject ≤72 chars, no trailing period; optional body wrapped at 72). **No attribution/Co-Authored-By lines.**
8. No subagents: implementers never dispatch subagents or reviewers.

---

### Task 1: Faster PDF indexing (same output)

**Why:** benchmarks on this machine (Ryzen 7 5800H, 8 cores/16 threads) showed Docling's layout
model is ~91% of indexing time; 8 threads + layout batch size 1 cut time 30–45% with
byte-identical chunks (sha256 over text/embed_text/headings/pages), and lower peak RAM.

**Do:**
- Add setting `DOCLING_LAYOUT_BATCH_SIZE: int = Field(default=1)` in `apps/backend/config/base.py`
  next to the other `DOCLING_*` settings; change `DOCLING_NUM_THREADS` default from `4` to `8`.
- In `apps/backend/util/document_parser.py` `_converter()`, pass
  `layout_batch_size=settings.DOCLING_LAYOUT_BATCH_SIZE` to `PdfPipelineOptions` and include it in
  the "Initialising Docling converter" log line.
- `.env.example`: `BE_DOCLING_NUM_THREADS=8` and a documented `BE_DOCLING_LAYOUT_BATCH_SIZE=1`
  (comment: measured fastest on 8-core CPU; higher values use more RAM and were slower).
- Unit test: `_converter()` builds options with the configured threads and layout batch size
  (patch/inspect without loading models if possible; otherwise mark `docling`).
- Update the measured-behaviour table in `docs/architecture.md` §6 (≈0.8 s/page vs 1.2–1.4 before).
- Changelog entry (backend).

**Do not** change chunking, OCR, table settings, or anything that alters output.

---

### Task 2: One error envelope + CORS for the dev port

**Why:** success responses are `{metaData, data, …}` at top level; errors come back as
`{"detail": {metaData, …}}` because routers raise `HTTPException(detail=<envelope>)`.
`BE_CORS_ORIGINS` allows `:3000` while the web dev server runs on `:3001`.

**Do:**
- Register an exception handler in `apps/backend/api.py` for `fastapi.HTTPException` (and
  `starlette.exceptions.HTTPException`): when `detail` is a dict that looks like the envelope
  (has `metaData`), return it as the top-level JSON body with the same status code and headers;
  otherwise keep FastAPI's default `{"detail": ...}`. Validation errors (422) unchanged.
- SSE endpoints are not affected (they emit `error` events) — verify, don't change.
- Backend tests: an endpoint that raises the envelope (e.g. `GET /book/get-one?id=<unknown uuid>`
  → 404) returns top-level `metaData.responseCode == 404`; a plain-string HTTPException still
  returns `{"detail": "..."}`. Update existing tests that asserted `["detail"]["metaData"]`.
- Web: `services/api-client.ts` and `services/sse-client.ts` already read both shapes — keep
  both (back-compat), adjust the comment to say the top-level shape is primary.
- CORS: change the default of `CORS_ORIGINS` in `config/base.py` and `.env.example` to
  `http://localhost:3000,http://localhost:3001` (check how the value is parsed — comma list).
- Update `docs/api-spec.md` error section. Changelog entries.

---

### Task 3: Self-healing indexing (resume after restart + OCR fallback)

**Why:** a backend restart/reload marks in-flight jobs `failed` (user must press Reindex);
scanned PDFs fail with "No text could be extracted" because OCR is off for speed.

**Do:**
- Migration `NNN_ingestion_attempts.sql`: add `ingestion_attempts INT NOT NULL DEFAULT 0` to `books`.
- `service/ingestion.py`: each claim (`queued`→`processing`) increments `ingestion_attempts`.
  At startup, `recover_interrupted` re-queues (status `queued`, re-enqueued to the worker) jobs left
  `queued`/`processing` whose attempts `< BE_INGESTION_MAX_ATTEMPTS` (new setting, default 3);
  only jobs at the cap become `failed` with the existing user-safe message. Re-index (`POST
  /book/reindex`) resets attempts to 0. Keep the daemon-thread design and the atomic claim.
- OCR fallback: when a parse with OCR off yields zero chunks, retry that book once with OCR on
  (a second converter instance cached separately, `do_ocr=True`), behind setting
  `BE_DOCLING_OCR_FALLBACK` (default true). If OCR also yields nothing → `failed` with the
  existing "No text could be extracted" message. Log which path ran.
- Tests: unit tests for the requeue decision (below cap → queued + enqueued; at cap → failed),
  attempts increment, reindex resets attempts, OCR fallback invoked only on zero chunks (fake
  parser). Integration test for the migration + recovery against `library_test`.
- Expose `attempts` in the book API `ingestion` object (`to_api()`), docs + changelog.

---

### Task 4: Retrieval that doesn't miss the right chapter

**Why:** "What does Scrooge learn from the Ghost of Christmas Yet to Come?" retrieved 8 passages
all from Staves 1–3 (near-duplicate passages from the same sections crowd out Stave 4).

**Do:**
- In `service/search.py` / `service/vector_store.py`: fetch a larger candidate pool
  (`BE_RETRIEVAL_CANDIDATE_MULTIPLIER`, default 4 → `topK*4` candidates, same score threshold),
  then select the final `topK` greedily by score while capping passages per section
  (`(book_id, tuple(headings))`) at `BE_RETRIEVAL_MAX_PER_SECTION` (default 2). If the cap leaves
  fewer than `topK`, fill with the best remaining candidates. Apply to every retrieval path
  (single book, per-book searches for 2–6 books, follow-up merge) without breaking the
  "every named book represented" behaviour.
- Unit tests for the selection function (cap, fill, ordering, per-book interplay).
- Evaluation script `apps/backend/scripts/eval_retrieval.py` (uv script, uses the running dev
  backend's real data via `POST /search/query`, read-only): a small list of question → expected
  (book title, heading substring) pairs including the Scrooge case, Frankenstein "why does the
  creature turn against Victor" (Chapter 10/16-ish), Metamorphosis "how does Gregor's family react"
  and 3–5 more over indexed Gutenberg books; prints hit@k before/after is not possible in one run —
  print hit@k for the current code. Run it against the dev backend on :8021 and paste the result
  into the report. Acceptance: the Scrooge question has a passage whose heading mentions the last
  spirit / Stave 4 in its top 8, and no other eval case regresses vs. the baseline you record by
  running the script BEFORE your change (stash or run first).
- Settings in `config/base.py` + `.env.example`; docs §4.2 + changelog.

---

### Task 5: Open the PDF at the cited page

**Why:** citations show passage text, but you can't see the source page.

**Do:**
- Backend: `GET /book/file?id=<uuid>` streams the stored PDF (`FileResponse`,
  `application/pdf`, `Content-Disposition: inline; filename="<original file name>"`), 404 when the
  book or file is missing. Same auth as the other book endpoints. Path must come from the book row /
  storage helper — never from user input (no traversal). Tests (unit/integration).
- Web: helper building `${API_BASE}/book/file?id=<id>#page=<n>` (browser PDF viewers honour
  `#page=`). Add an "Open page N" link (new tab, `rel="noopener noreferrer"`) on each source in the
  chat sources list / citation popover, and an "Open PDF" action on the book detail document
  panel when `hasDocument`. Vitest for the URL helper and that the link renders for a source.
- `docs/api-spec.md`, changelog (backend + web).

---

### Task 6: Edit book details in the web app

**Why:** `PUT /book/update` exists but the web never calls it — typos can't be fixed.

**Do:**
- `services/book.service.ts`: `update(payload)` using the existing endpoint constants pattern.
- An "Edit details" button on the book detail page opening a shadcn Dialog form (React Hook Form +
  zod, reuse the add-book schema/fields where possible): title, authors, description, ISBN,
  publisher, published year, language, subjects, cover URL. Prefill from the book; on success
  invalidate the book detail + catalog queries and toast; show backend validation errors inline
  (e.g. invalid ISBN checksum, duplicate ISBN → 409 message).
- Read `dto/book.py` `UpdateBookDTO` for the exact payload shape/field names.
- Vitest: form prefill, submit payload shape, error display. Changelog (web).

---

### Task 7: Upload several PDFs at once

**Why:** one PDF per upload; bulk adds need a script.

**Do:**
- Extend `features/library/components/UploadBookDialog.tsx` (or split into a feature component
  if it grows) to accept multiple files (input `multiple` + drag-and-drop if the dialog already
  supports drop). Each file becomes its own `POST /book/upload` (title derived from the file name,
  editable per row before starting), uploaded **sequentially** with a per-file row showing
  pending / uploading / queued for indexing / error (409 duplicate message shown). Already-uploaded
  rows are not retried; the dialog can be closed while later rows wait only after confirming.
- Single-file flow (including the existing "attach PDF to an existing book" via `bookId`) must keep
  working unchanged.
- Vitest: sequential order, per-row status, 409 handling. Changelog (web).

---

### Task 8: Semantic search page

**Why:** `POST /search/query` works but there is no page for it.

**Do:**
- New route `/search` (thin page in `src/pages/library/`) + menu entry in
  `src/config/menu/app.menu.ts` (between Catalog and Ask; Phosphor magnifying-glass icon;
  `seo.title` "Search passages").
- Feature UI under `src/features/library/search/`: query input (submit on Enter), optional book
  scope picker (reuse the chat's picker component if it is reusable; otherwise move it to
  `features/library/components/` and use it from both), results list: book title, headings path,
  pages, score as a subtle percentage, passage text (clamped, expandable), an "Ask about this"
  action that opens `/ask` with the book preselected (reuse how the chat reads `bookId` search
  params), and "Open page" (Task 5 helper). Empty / no-results / error / loading states;
  `skippedBooks` shown as a note. Keep the query in the URL (`?q=`) so results are shareable.
- Vitest for the results rendering and URL sync. Changelog (web).

---

### Task 9: Visible progress while the model thinks

**Why:** reasoning models stay silent 30 s+ before the first token; the UI shows a static line.

**Do:**
- In the chat's pending assistant message, show the current stage from SSE `status` events
  ("Searching your books…" for `retrieving`, "Reading N passages and thinking…" once `sources`
  arrived, then streaming) plus an elapsed-seconds counter after 5 s, and a hint after 45 s that
  long thinking is normal for the configured model. Respect reduced motion. No backend change.
- Vitest with fake timers. Changelog (web).

---

### Task 10: Accounts — login UI, per-user chats, service token

**Why:** no login page; everyone shares one chat history; MCP needs a service credential.

**Decisions (controller rulings):** the **book catalog stays a shared team library** (README:
"personal/team book library"); **conversations become per-user**. Auth uses the existing
boilerplate `/auth/register` + `/auth/login` (Mongo users) and its JWT. A service token
(`X-Internal-Token`) authorises system-to-system calls.

**Do (backend):**
- Setting `BE_INTERNAL_TOKEN` (empty = disabled). Extend the router auth dependency used by
  `router_param_builder` so that when `JWT_ACTIVE` is true a request is authorised by EITHER a valid
  JWT bearer OR an `X-Internal-Token` header equal (constant-time compare) to `INTERNAL_TOKEN`.
  Internal-token requests act as a service principal (`subject = "service:internal"`).
- Migration: `owner_id TEXT` on `conversations` (nullable; existing rows stay `NULL` = legacy
  shared). Conversation create/list/get/rename/delete/stream are scoped to the caller's user id
  (from the JWT `sub`/user id claim — check `auth/` for the claim name). When `JWT_ACTIVE` is false
  every caller is the fixed owner `"local"` and legacy `NULL` rows are visible to `"local"` so
  today's local setup keeps its history. Chat sessions (`/chat/active`, resume, cancel) must not
  leak across users (check ownership via the conversation).
- If `/auth/register` requires email verification/SMTP that is not configured, add a documented
  setting to allow registration without verification in development (default: keep existing
  behaviour) — do not weaken production defaults.
- Tests: internal token accepted / wrong token rejected (constant-time compare used), JWT path still
  works, conversations isolated between two users, `JWT_ACTIVE=false` → `"local"` sees legacy rows.

**Do (web):**
- Real `LoginPage` (email + password, link to register) and a register page, using the existing
  `useAuthStore` / api-client (inspect how it expects tokens — cookies vs bearer — and use what the
  backend's `/auth/login` actually returns). Mount `auth.routes` (no app shell) and protect the main
  routes with the existing `AuthGuard` **only when auth is enabled** — add `VITE_AUTH_ENABLED`
  (default `false`, documented in `env/.env.example`) so the current local no-login setup keeps
  working. Header: signed-in user + "Sign out" when enabled. 401 → redirect to login.
- Vitest: login form submit, guard redirect when enabled, no guard when disabled.

**Also:** `.env.example` entries; `apps/backend/scripts/seed_gutenberg.py` keeps working with
`--token` and gains `--internal-token`; docs (architecture §8 "No login page" removed, api-spec
auth section); changelog (backend + web). Do not change the local `.env` files.

---

### Task 11: MCP server exposing the library

**Why:** headline feature from the README, entirely missing.

**Do:**
- New uv project `apps/mcp/library/` (FastMCP, Python 3.12; `uv init --app`, `uv add fastmcp httpx`)
  with `server.py`, `README.md`, `.env.example`, tests. Read `.claude/skills/mcp-builder/SKILL.md`
  for conventions (it is on disk though not in git) — MCPHub registration is optional/skip.
- Calls ONLY the backend REST API (`LIBRARY_API_URL`, default `http://localhost:8020`) with header
  `X-Internal-Token: $LIBRARY_INTERNAL_TOKEN` (Task 10). Never touches databases.
- Read-only tools: `list_books(query?, indexed_only?, page?, size?)`, `get_book(book_id)`,
  `search_passages(query, book_ids?, top_k?)`, `ask_library(question, book_ids?)` (uses non-streaming
  `POST /chat/ask`; returns answer, mode, cited sources with book/pages). Typed inputs, concise
  structured outputs, clear errors (backend down, 401, 404) as tool errors.
- Inbound auth: HTTP transport requires `Authorization: Bearer $MCP_BEARER_TOKEN` (reject missing/
  wrong, constant-time compare); stdio transport for local clients needs no token. Refuse to start
  the HTTP transport without `MCP_BEARER_TOKEN`.
- Tests with a mocked backend (httpx MockTransport / respx): each tool's request mapping and
  output shape, error mapping, bearer check. A manual smoke run against the dev backend on :8021
  (stdio, list_books + search_passages) recorded in the report.
- Root README + `docs/architecture.md` (MCP section, remove "Not yet: MCP server"), changelog.

---

### Task 12: Docker images for the apps

**Why:** compose only runs the databases; "one Dockerfile per app" is the stated deployment.

**Do:**
- `apps/backend/Dockerfile`: python:3.12-slim + uv (copy uv binary from the official uv image),
  `uv sync --frozen --no-dev`, CPU-only torch as locked, `libmagic1` + runtime libs Docling needs,
  non-root user, `CMD uv run python api.py --port 8020 --worker 1` (reload off when not dev — check
  api.py flags), volumes for `storage/` and the Hugging Face cache, `.dockerignore`.
- `apps/web/Dockerfile`: multi-stage node build (`npm ci`, `vite build`) → nginx serving `build/`
  with SPA fallback and a reverse proxy `/api/v1/apps/` → backend and `/cdn-assets/` →
  `${ICON_CDN_PROXY_TARGET}` (nginx envsubst template; no internal host in git), `.dockerignore`.
- `apps/mcp/library/Dockerfile` (HTTP transport).
- Root `docker-compose.yml`: add `backend`, `web`, `mcp` services under a compose **profile `app`**
  (so `docker compose up -d` still starts only the databases), wired to the existing services by
  service name, env from `apps/backend/.env` etc. (env_file, git-ignored), healthchecks.
- Verify: `docker compose --profile app build` succeeds for all three and `docker compose --profile
  app config` is valid. Do not leave app containers running; do not touch the running database
  containers or volumes. Docs (README "Running with Docker"), changelog.

---

### Task 13: Continuous integration

**Do:** `.github/workflows/ci.yml` on push/PR: job `backend` (uv setup, `uv sync --frozen`,
`uv run pytest` unit only — default addopts already exclude integration/external/docling; cache uv),
job `web` (Node 20, `npm ci`, `npm run typecheck`, `npm run lint`, `npm test`), job `mcp`
(`uv run pytest` in `apps/mcp/library`). No secrets required. Validate YAML locally (e.g.
`uvx check-jsonschema --builtin-schema vendor.github-workflows`). If `npm run lint` currently fails
on untouched files, scope the CI lint to what passes and note it in the report rather than mass-
reformatting. README badge optional. Changelog.

---

### Task 14: Remove leftover boilerplate + refresh docs

**Do:**
- Delete `docs/mock-data.md` and `data/mock/mock-sentiment-layanan-publik.json` (unrelated
  "penduduk/sentimen" mocks) unless something references them (grep first; `data/mock/.gitkeep` stays).
- Remove unmounted web stubs replaced by Task 10 (e.g. empty `DashboardPage`, `admin.routes.tsx` if
  still unused) — only if nothing imports them.
- README: correct ports (web 3001 via `env/.env`, backend 8021 example), object storage = local disk,
  add MCP + Docker + search + accounts to the feature list, link `docs/architecture.md`.
- `docs/architecture.md`: reconcile §4–§9 with Tasks 1–13 (no stale "Not yet" items for done work;
  list what remains: S3, pgvector evaluation, Langfuse, cross-language retrieval).
- Changelog.

---

## Addendum — 2026-10-12 code review findings (Tasks 15–26)

Source: a second read-only review of backend and web (bugs, security, reliability, cleanup).
File:line references are from commit `1e4c5b8`; re-locate them if code moved. Same Global
Constraints apply.

### Task 15: Chat survives navigation, Stop, and bad stream frames

**Why:** (a) switching conversations mid-answer and coming back shows a stale thread that does
not re-attach to the running turn: `ChatView.tsx` keeps `attachCheckedFor` / `restoredScopeFor`
refs across conversation changes and the conversation query is cached (`staleTime` 5 min in
`src/config/query-client.ts`); a brand-new chat seeded with `messages: []` shows empty when
revisited. (b) Stop sets phase `stopped` (`useAskStream.ts` ~:68) so Send re-enables before the
old stream's `cancelled` event; asking again cancels the old stream whose cleanup skips the
history refresh, and `setPendingFrom(saved.length)` is computed from a list without the stopped
turn — the stopped Q/A vanishes. (c) `chat.service.ts` `JSON.parse` of an SSE frame can throw
inside the reader loop; `sse-client.ts` then only `releaseLock()`s (no `reader.cancel()`), leaving
the connection open, and reconnects replay the same bad frame until retries run out.

**Do:**
- When the active conversation changes, invalidate the previous conversation's query and reset
  the per-conversation refs; move the `chatService.active` lookup into a TanStack `useQuery` keyed
  by conversation id (AI_GUIDE: components don't call services directly) so re-entering a
  conversation with a running turn re-attaches.
- Keep Send disabled after Stop until the stream reports `cancelled` (or ends), with a 5 s
  fallback; when a new question is sent after a stopped turn, base `pendingFrom` on refreshed
  history so the stopped turn stays visible.
- SSE: a frame whose JSON cannot be parsed is skipped with a `console.warn` (not fatal); the
  reader is `cancel()`ed in `finally` on every exit path.
- Vitest: switch away mid-stream and back → re-attaches / shows latest; Stop then ask → stopped
  turn still rendered and Send disabled until `cancelled`; malformed frame skipped and later
  frames delivered; reader cancelled on abort. Changelog (web).

---

### Task 16: Fresh catalog after indexing; uploads that report real errors and don't time out

**Why:** (a) `useBook.ts` polls a book until indexing finishes but never invalidates the book
lists; `useBooks` (catalog) never polls — newly indexed books stay "Indexing" in the catalog and
missing from the chat picker for up to 5 min. (b) `api-client.ts` rejects with a plain object
(`{...error, message}`), so `useBatchUpload.ts` (`error instanceof Error`) always shows "Upload
failed". (c) axios `timeout: 30000` applies to uploads; a 100 MB PDF fails on normal links.

**Do:**
- When a polled book leaves `queued`/`processing`, invalidate the catalog/list queries (and the
  indexed-books query the chat picker uses). `useBooks`: `refetchInterval` (e.g. 5 s) only while
  any book in the current page is `queued`/`processing`.
- `api-client.ts`: reject with an `Error` subclass (e.g. `ApiError extends Error` carrying
  `status`, `responseCode`, original response) whose `message` is the resolved backend message;
  keep existing fields callers read. Audit callers that read `.message`/`.response` and keep them
  working.
- Uploads: no client timeout for multipart uploads (`timeout: 0`) — other requests keep 30 s.
- Vitest for each. Changelog (web).

---

### Task 17: One running turn per conversation (backend)

**Why:** `service/chat_session.py` (`set_active`, ~:144) is a plain SET; nothing stops two turns
on the same conversation (two tabs / double submit) → messages saved Q1,Q2,A1,A2 and
`history_from` pairs A1 with Q2.

**Do:**
- Claim the conversation atomically (Redis `SET NX` with the existing TTL/heartbeat semantics, or
  the equivalent in whatever store `chat_session` uses); release on finish/cancel/error. A second
  turn while one is running → HTTP 409 with the envelope message "A question is already being
  answered in this conversation." (streaming endpoint: before the stream starts, so the client
  gets a normal error response). Stale claims expire with the heartbeat TTL.
- Web: show that 409 message in the chat error state (check existing error display handles it).
- Unit tests: concurrent claim → second gets 409; release on completion, cancel, and exception;
  expired claim can be re-taken. Docs api-spec + changelog.

---

### Task 18: Book edits, deletes and attachments stay consistent with the index

**Why:** (a) `service/book.py` `update()` changes Postgres only; `book_title` is copied into
every Qdrant point payload (`vector_store.py` upsert) and prompts/citations/search read it —
renamed books show the old title until reindex. (b) `delete` (~:66-75) checks status then deletes
non-atomically; a reindex claimed in between upserts vectors for a deleted book (orphans).
(c) attaching a PDF to an existing book writes `file_path` after `finalize()` outside the `try`;
two concurrent attaches both pass the `file_sha256` check.

**Do:**
- Read titles from the Postgres catalog at retrieval time (`retrieve()` already loads a
  `by_id` catalog in `service/search.py`) for prompts, sources and `/search/query` results; keep
  the payload field for back-compat but stop trusting it. (Do not rewrite payloads on update.)
- Delete: atomic `DELETE … WHERE id=%s AND ingestion_status NOT IN ('queued','processing')
  RETURNING …` (409 when busy, 404 when missing), then delete Qdrant points and the file; the
  ingestion worker, after upserting, verifies the row still exists and deletes its own points if
  not.
- Attach: single guarded statement (`… WHERE id=%s AND file_sha256 IS NULL RETURNING`) that sets
  hash + path + queued status together; on conflict remove the just-written file and return 409.
- Unit tests with fakes for each race; integration tests (`-m integration`) for the SQL guards
  when Docker is available. Changelog + api-spec if responses change.

---

### Task 19: Safe startup defaults

**Why:** (a) legacy boilerplate routers (user, role, group, permission, S3 upload,
`/monitoring/threadpool`) are mounted with no auth while `BE_JWT_ACTIVE=false`. (b) `api.py`
enables uvicorn `reload=True` whenever `--worker` is 1, so plain `python api.py` deploys run the
reloader and any file change kills running ingestions. (c) `JWT_SECRET` / `ENC_SECRET` accept
empty strings (PyJWT signs with an empty key). (d) Service singletons (`util/postgres.py`,
Qdrant, embedding, Redis) use unlocked check-then-create; concurrent first requests on the
64-thread pool can build duplicate pools.

**Do:**
- Router enablement: when `ENABLED_ROUTERS` is empty, mount the library routers + health + auth
  only; legacy admin routers (user, role, group, permission, upload, monitoring) mount only when
  listed explicitly. Document in `.env.example` and AI_GUIDE.
- Add `--reload` flag (default off); `nx` `serve` target / README dev command pass `--reload`.
- Validator: when `JWT_ACTIVE` (resp. `ENC_ACTIVE`) is true, the secret must be ≥32 chars or
  startup fails with a clear message. `.env.example` explains how to generate one.
- Double-checked locking for each singleton; document the Postgres pool size vs thread count.
- Tests for router selection, secret validation, reload flag parsing, singleton under threads.
  Changelog + architecture doc.

---

### Task 20: LLM timeouts and honest error codes

**Why:** `service/llm.py` LiteLLM calls have no timeout/retries (default 600 s) — a stalled
provider pins a chat session and a worker thread. `util/http_errors.py` maps any `LookupError`
(incl. `KeyError`/`IndexError` from bugs) to 404; embedding/Qdrant outages surface as 500
"Internal server error" in `rag.ask_stream`.

**Do:**
- Settings `BE_LLM_TIMEOUT_SECONDS` (default 120), `BE_LLM_NUM_RETRIES` (default 2),
  `BE_LLM_FIRST_TOKEN_TIMEOUT_SECONDS` (default 90) passed via the Agno/LiteLLM request params;
  first-token timeout ends the turn with a user-safe error event.
- Introduce a project `NotFoundError` and map that (not `LookupError`) to 404; migrate raisers.
  Map `EmbeddingError` and Qdrant connection errors to 503 "Search service unavailable" in REST
  and SSE paths.
- Unit tests for the mapping and timeout propagation. Changelog + architecture doc.

---

### Task 21: Patch vulnerable dependencies and drop unused ones

**Do (backend):** `uv lock --upgrade-package` for urllib3, python-multipart, pymongo, uvicorn (to
current releases; check uvicorn's `reload`/`workers` API still matches `api.py`); remove direct
deps not imported anywhere in app/tests/scripts (verify each with grep before removing; reviewer
candidates: pydash, pytz, tzlocal, python-dateutil, regex, requests). Keep deps used by the
legacy modules. `uv run pytest` green.
**Do (web):** upgrade `axios` and `react-router`/`react-router-dom` within their current major
(fix any breakage); remove the `moment-timezone` side-effect in `src/main.tsx` and the leftover
service-worker registration + `public/sw.js`; remove dependencies that are never imported
(verify each with grep over `src/`, configs, and tests — reviewer candidates: echarts, recharts,
mapbox-gl, wavesurfer.js, styled-components, lodash, dayjs, date-fns, crypto-js, immer,
@babel/standalone, react-table, @tanstack/react-table, moment/moment-timezone) and the matching
`manualChunks` in `vite.config.ts`; move test/build-only packages to `devDependencies`. Do NOT
delete source files in this task (Task 14 owns dead-file removal). `npm ci && npm run typecheck
&& npm run lint && npm test && npx vite build` green; report bundle size before/after and
`npm audit --omit=dev` before/after. Changelog (backend + web).

---

### Task 22: Render answers as safe Markdown, announce completion, tighten "general knowledge"

**Why:** models emit Markdown but `AnswerText.tsx` shows it raw; there's no live-region
announcement when an answer finishes; `citations.ts` (~:286) splits off a "general knowledge"
box on any paragraph starting "General knowledge of" (optional colon, `/m`).

**Do:**
- Render answer text with `react-markdown` (+ `remark-gfm`), raw HTML disabled, links
  `target=_blank rel="noopener noreferrer"`; keep the existing citation chips (`[n]` markers)
  working inside paragraphs, lists and tables; style with existing tokens (no new theme).
- Polite live region that announces "Answer ready" / "Answer stopped" / errors once per turn.
- Require the exact heading format the backend prompt instructs (read `service/llm.py`/prompt
  text) for the general-knowledge split.
- Vitest: markdown elements render, `<script>`/raw HTML is not rendered, citations inside lists,
  live-region text, general-knowledge false positive. Changelog (web).

---

### Task 23: Chat book picker scales past 100 books; upload components in a feature folder

**Why:** `useIndexedBooks.ts` fetches `size: 100`; beyond that books can't be picked and the
label "All 100 indexed books are searched" is wrong. `features/library/components/UploadBookDialog.tsx`
and `BatchUploadPanel.tsx` sit outside a feature folder (architecture placement rule).

**Do:**
- Picker searches server-side (debounced `query` against the list endpoint, indexed only) with
  paging/infinite scroll; the "all books" label uses the backend total; selected books not in the
  current page stay shown. Must work for both the chat and (if Task 8 shares it) the search page.
- Move upload components + their tests to `features/library/upload/components/` (hooks alongside
  if upload-only), update imports. Vitest. Changelog (web).

---

### Task 24: Per-route rate limits and a bounded ingestion queue

**Why:** one global per-IP limiter (`middleware/rate_limiter.py`); upload/chat/search have no
tighter budgets, the ingestion queue is unbounded, and behind a proxy all clients share one IP.

**Do:**
- Settings for per-route budgets (defaults: upload 20/min, chat ask/stream 30/min, search
  60/min per client) using the existing Redis limiter; 429 with the envelope + `Retry-After`.
- `BE_TRUSTED_PROXIES` (CIDR list, default empty): only then honour `X-Forwarded-For`.
- `BE_INGESTION_MAX_QUEUED` (default 50): upload/reindex beyond it → 429 "Indexing queue is
  full, try again later."; `BE_CHAT_MAX_CONCURRENT_SESSIONS` (default 20) → 429.
- Unit tests with a fake Redis/clock. Changelog + api-spec.

---

### Task 25: Parse PDFs in a child process

**Why:** Docling runs inside the API process; a PDF that crashes the native parser or exhausts
memory kills the API and every live chat session.

**Do:**
- Run `parse` in a separate process (`ProcessPoolExecutor(max_workers=1, max_tasks_per_child=…)`
  with `spawn` context, or a dedicated subprocess) that loads the cached converter(s) once per
  child; parent keeps the queue/claim/status logic. Per-book wall-clock timeout
  `BE_INGESTION_PARSE_TIMEOUT_SECONDS` (default 1800) and optional memory cap
  `BE_INGESTION_PARSE_MAX_MEMORY_MB` (RLIMIT_AS in the child, default 0 = off). Crash/timeout →
  book `failed` with a user-safe message, worker recreated, API unaffected. Must keep Task 1
  options and Task 3 OCR fallback behaviour.
- Unit tests with a fake parse function that raises / sleeps / segfaults (`os._exit`) in the
  child. Measure and report per-page timing vs Task 1 numbers on one small PDF. Changelog +
  architecture doc.

---

### Task 26: Repo hygiene for collaborators

**Why:** `AGENTS.md` / `CLAUDE.md` are tracked but reference `.claude/` rules and skills that are
git-ignored, so clones get dangling references; `nx/package-lock.json` is untracked.

**Do:**
- Decide per file: track the project-specific rule files the docs depend on
  (`.claude/rules/**`, `apps/*/AI_GUIDE.md` already tracked?) — check for secrets/internal
  hosts first (Global Constraint 1; e.g. the embedding host in `.claude/rules/architecture.md`
  must be replaced by a placeholder) — or rewrite `AGENTS.md`/`CLAUDE.md` so they don't point at
  untracked paths. Prefer tracking `.claude/rules/` (sanitised) and leaving skills/settings
  ignored; update `.gitignore` accordingly.
- Commit `nx/package-lock.json`. README "Running locally": note the `docker` group requirement.
