# API Specifications

**Version:** 1.0.0

PREDEFINE REST API  — this documentation is predefined and automatically available once the boilerplate has been successfully initialized. It covers authentication (JWT-based), user management, groups, and permissions. Agents must not modify any existing code; they are only allowed to extend functionality by adding new code without altering the current structure.

> **NOTE:** Skip if `../apps/backend/` does not exist.
---

## Servers

| Environment | URL |
|---|---|
| Production | `https://api.example.com` |
| Development | `http://localhost:8020` |

---

## Authentication

All protected endpoints use **Bearer Token (JWT)**.

```
Authorization: Bearer <token>
```

| Security Scheme | Description |
|---|---|
| `JWTBearer` | Standard JWT for protected endpoints — or the service token (`X-Internal-Token`), see below |
| `JWTRefresh` | JWT refresh for token refresh & validate |
| `User` | `JWTBearer` that must be a user: the service principal gets `403` (personal data: conversations, chat sessions) |

> Tokens are also stored in HttpOnly cookies (`token`, `refresh_token`) as a fallback. `POST /auth/login` returns
> only `{ user: {id, fullname, username, email, …} }` in the body; the tokens are set as `HttpOnly`, `SameSite=Lax`
> cookies, `Secure` unless `BE_AUTH_COOKIE_SECURE=false` (development over plain HTTP only). `GET /auth/refresh` (refresh cookie) issues new ones; `DELETE /auth/logout` clears both
> (it needs only the refresh cookie).

Auth is **opt-in**: with `BE_JWT_ACTIVE=false` no endpoint checks credentials and every caller is the owner `"local"`.
With `BE_JWT_ACTIVE=true` (`auth/principal.py`, the router dependency of every `JWTBearer` route):

| Credential | Principal | Access |
|---|---|---|
| `X-Internal-Token: <BE_INTERNAL_TOKEN>` (constant-time compare; empty setting = disabled) | `service:internal` | Shared catalog, upload, search, `/chat/ask`. `403` on `User` routes. A wrong or disabled token is `403` even if a JWT is also sent |
| Access token (Bearer or `token` cookie) | the user (`user_id` claim) | Everything; conversations are filtered to the caller's own |
| none / expired | — | `401` (`403` for an invalid or refresh token) |

**Per-user conversations.** `conversations.owner_id` = the caller (user id, or `"local"` without JWT). Another
user's conversation answers `404` on every `/conversation/*` route, on `GET /chat/active`, and on
`POST /chat/stream` with its `conversationId` (a JSON 404 before any stream); another user's chat session is
reported like an unknown one (resume: `error` event code 404; cancel: `404`). Conversations created before
accounts existed (`owner_id` NULL) belong to `"local"` only. The book catalog is shared by everyone.

**Registration.** `POST /auth/register` `{ fullname?, username, email, password, phone }`. Default
(`BE_AUTH_EMAIL_VERIFICATION=true`): MX + Proofy check, an OTP is mailed over SMTP →
`{ message, verificationRequired: true }`; confirm with `POST /auth/verification?otp=`. Development
(`BE_AUTH_EMAIL_VERIFICATION=false`): the account is created at once → `{ message, verificationRequired: false, id }`.
`400` with the message when the email, username or phone is taken. `BE_AUTH_REGISTRATION_OPEN=false` closes every
registration endpoint (`/auth/register`, `/auth/verification`, `/auth/google/register`) with `403`
"Registration is closed."; existing accounts still log in.

**Login.** Only accounts with `status: "active"` log in (both registration paths create them active); any other
status answers `403` ("User doesn't have login access", or "Account has been blocked/deleted/expired") — but only
after the password matched; a wrong password is always `400` "Incorrect email or password". `emailVerified` is not
checked at login (the development registration path sets it `false`).

**Google OAuth.** `/auth/google/*` is mounted only when `BE_GOOGLE_CLIENT_ID` and `BE_GOOGLE_CLIENT_SECRET` are both
set (`404` otherwise). `/auth/google/register` uses only the profile fields of its body and always creates an active,
unverified account (see [docs/api/auth.md](./api/auth.md)).

---

## Endpoint

### Monitoring

#### `GET /monitoring/threadpool`

Monitoring threadpool status. **Opt-in:** the `monitoring` router is not mounted by default; add `monitoring` to `BE_ENABLED_ROUTERS` (or `--routers`) to expose it (`404` otherwise).

**Response `200`**

```json
{
  "max_workers": 10,
  "current_threads": 10,
  "active_threads_estimate": 5,
  "queue_size_best_effort": 0
}
```

### Health

#### `GET /health`

Liveness probe. No dependency checks. Not wrapped in `BaseResponse`.

**Response `200`**

```json
{ "status": "ok" }
```

#### `GET /health/ready`

Readiness probe. Pings MongoDB, Redis and, when configured, PostgreSQL, Qdrant and the embedding service (TEI `GET /health`). Errors are reported by exception type only. Not wrapped in `BaseResponse`.

**Response `200` / `503`**

```json
{
  "status": "ok",
  "checks": {
    "mongo": { "status": "ok" },
    "redis": { "status": "ok" },
    "postgres": { "status": "ok" },
    "qdrant": { "status": "ok" },
    "embedding": { "status": "not_configured" }
  },
  "executionTime": 12
}
```

Per-check `status`: `ok`, `error` (with `"error": "<ExceptionType>"`), or `not_configured`. If any check is `error`, the overall `status` is `degraded` and the HTTP status is 503.

### Router module references

If you need to use these modules, you can access the documentation for the Auth, User, Group, and Permission routers directly from here:

- Auth router: [docs/api/auth.md](./api/auth.md)
- User router: [docs/api/user.md](./api/user.md)
- Group router: [docs/api/group.md](./api/group.md)
- Permission router: [docs/api/permission.md](./api/permission.md)

---

## Endpoint Registry

| Method | Route | Description | Auth |
|--------|-------|-------------|------|
| GET | `/health` | Liveness probe | No |
| GET | `/health/ready` | Readiness: pings every configured backing service (503 if any is down) | No |
| GET | `/monitoring/threadpool` | Threadpool monitoring stats (only when the `monitoring` router is enabled; unmounted by default) | No |
| POST | `/auth/login` | Login user | No |
| POST | `/auth/register` | Register new user (`403` when `BE_AUTH_REGISTRATION_OPEN=false`) | No |
| POST | `/auth/verification` | Verify registration OTP (`403` when registration is closed) | No |
| DELETE | `/auth/logout` | Logout user | JWTRefresh |
| GET | `/auth/validate` | Validate token | JWTRefresh |
| GET | `/auth/refresh` | Refresh access token | JWTRefresh |
| GET | `/auth/google` | Initiate Google OAuth (only with Google OAuth configured) | No |
| POST | `/auth/google/callback` | Google OAuth callback (only with Google OAuth configured) | No |
| POST | `/auth/google/token_exchange` | Exchange Google token (only with Google OAuth configured) | No |
| POST | `/auth/google/register` | Register via Google SSO (only with Google OAuth configured; `403` when registration is closed) | No |
| POST | `/auth/forgot-password/request` | Request forgot password OTP | No |
| POST | `/auth/forgot-password/verify` | Verify forgot password OTP | No |
| POST | `/auth/forgot-password/change` | Change password via OTP | No |
| POST | `/auth/verify-email/request` | Request email verification | No |
| GET | `/auth/verify-email` | Verify email via token | No |
| POST | `/auth/2fa/generate` | Generate 2FA QR/OTP | No |
| POST | `/auth/2fa/verify` | Verify 2FA OTP | No |
| POST | `/auth/2fa/resend` | Resend 2FA OTP | No |
| POST | `/user/add` | Add user | JWTBearer |
| PUT | `/user/update` | Update user | JWTBearer |
| DELETE | `/user/delete` | Delete user | JWTBearer |
| POST | `/user/get-all` | List users (paginated) | JWTBearer |
| GET | `/user/get-one` | User details by ID | JWTBearer |
| GET | `/user/{username}` | User details by username | JWTBearer |
| GET | `/user/check-email` | Check email uniqueness | JWTBearer |
| GET | `/user/check-username` | Check username uniqueness | JWTBearer |
| GET | `/user/check-phone` | Check phone uniqueness | JWTBearer |
| POST | `/user/reset-password` | Reset password (admin) | JWTBearer |
| PUT | `/user/settings/update-profile` | Update own profile | JWTBearer |
| POST | `/group/add` | Add group | JWTBearer |
| PUT | `/group/update` | Update group | JWTBearer |
| DELETE | `/group/delete` | Delete group | JWTBearer |
| POST | `/group/get-all` | List groups (paginated) | JWTBearer |
| GET | `/group/get-one` | Group details by ID | JWTBearer |
| POST | `/permission/add` | Add permission | JWTBearer |
| PUT | `/permission/update` | Update permission | JWTBearer |
| PUT | `/permission/update-partial` | Update partial permission | JWTBearer |
| DELETE | `/permission/delete` | Delete permission | JWTBearer |
| POST | `/permission/get-all` | List permissions (paginated) | JWTBearer |
| GET | `/permission/get-one` | Permission details by ID | JWTBearer |
| POST | `/role/add` | Add role | JWTBearer |
| PUT | `/role/update` | Update role | JWTBearer |
| DELETE | `/role/delete` | Delete role | JWTBearer |
| POST | `/role/get-all` | List roles (paginated) | JWTBearer |
| GET | `/role/get-one` | Role details by ID | JWTBearer |
| POST | `/upload/upload-file` | Upload a file to S3 storage (multipart; size cap `MAX_UPLOAD_SIZE_MB`, extension + magic-byte MIME whitelist) | JWTBearer |
| DELETE | `/upload/delete` | Delete uploaded file metadata | JWTBearer |
| POST | `/upload/get-all` | List uploads (paginated) | JWTBearer |
| GET | `/upload/get-one` | Upload metadata by ID | JWTBearer |
| POST | `/book/add` | Create a catalog entry (metadata only, not searchable) | JWTBearer |
| PUT | `/book/update` | Update catalog metadata | JWTBearer |
| POST | `/book/get-all` | List/search books (`search` on title/author/ISBN/publisher, `status` filter, paginated) | JWTBearer |
| GET | `/book/get-one` | Book details incl. `ingestion` status and `searchable` | JWTBearer |
| GET | `/book/file` | Stream the stored PDF (`?id=`, `application/pdf`, `Content-Disposition: inline` with the original file name). Open with `#page=N` to jump to a page. 404 when the book or its file is missing. Accepts the session cookie, so plain links work | JWTBearer |
| DELETE | `/book/delete` | Delete book, stored PDF and vectors (409 while indexing) | JWTBearer |
| POST | `/book/upload` | Upload a PDF (multipart `file`, optional `bookId` / `title`) and queue indexing; 409 on duplicate file or when the `bookId` book already has a document (also for the loser of two concurrent attaches) | JWTBearer |
| POST | `/book/reindex` | Re-run indexing for an `indexed`/`failed` book (`?id=`); resets `ingestion.attempts` to 0 | JWTBearer |
| GET | `/book/lookup` | Search Open Library (`?q=`) for books to import | JWTBearer |
| POST | `/book/import` | Import metadata from Open Library by ISBN | JWTBearer |
| POST | `/search/query` | Semantic search over indexed books → passages with section/page | JWTBearer |
| POST | `/chat/ask` | Grounded answer with numbered sources, or an explicit "not enough information". Stateless (nothing saved) | JWTBearer |
| POST | `/chat/stream` | One **saved** chat turn, streamed as Server-Sent Events (`conversation` → `status` → `sources` → `delta`… → `done` \| `error`); optional `conversationId` continues a conversation | User |
| GET | `/chat/stream/{sessionId}` | Re-attach to an answer session: replays events after `?after=<event id>` (or `Last-Event-ID`), then streams live ones until it ends | User |
| POST | `/chat/stream/{sessionId}/cancel` | Stop generating (a disconnect no longer does); the partial answer is saved as `stopped` | User |
| GET | `/chat/active` | `?conversationId=` → `{active, sessionId}`: an answer of this conversation is still being generated (re-attach after a reload) | User |
| GET | `/conversation/get-all` | The caller's saved conversations, most recently active first (`?page=&size=`, max 100) | User |
| GET | `/conversation/get-one` | One conversation with all messages (`?id=`) | User |
| PUT | `/conversation/rename` | Rename (`{ id, title }`, 1–120 chars) | User |
| DELETE | `/conversation/delete` | Delete a conversation and its messages (`?id=`) | User |

---

## Response Format

### Success Response

```json
{
  "metaData": {
    "pagination": {
      "size": 10,
      "totalElements": 100,
      "totalPages": 10,
      "scrollId": ""
    },
    "status": true,
    "executionTime": 12,
    "responseCode": 200,
    "message": "Success"
  },
  "data": {},
  "additionalInfo": {},
  "copyright": "string"
}
```

### Error Response

```json
{
  "metaData": {
    "pagination": { "size": 0, "totalElements": 0, "totalPages": 0, "scrollId": "" },
    "status": false,
    "executionTime": 5,
    "responseCode": 400,
    "message": "Error description"
  },
  "data": null,
  "additionalInfo": {},
  "copyright": "string"
}
```

> `metaData.pagination` is only present on `get-all` (paginated) endpoints.

Failures use this same envelope as the **top-level** body (HTTP status = `metaData.responseCode`); response headers such as `WWW-Authenticate` are preserved. Plain errors without an envelope (e.g. framework 404/405) and request-validation errors (`422`) keep FastAPI's default `{"detail": ...}` shape. Clients should read `metaData.message` first and fall back to `detail`. SSE endpoints report failures as `error` events instead.

### Rate limits and capacity (HTTP 429)

`429 Too Many Requests` uses the error envelope and always carries a `Retry-After` header (seconds). Causes:

| Route | Limit | Setting |
|-------|-------|---------|
| `POST /book/upload` (new book or attach PDF) | 20 / min per client | `BE_RATE_LIMIT_UPLOAD_PER_MINUTE` |
| `POST /chat/ask`, `POST /chat/stream` | 30 / min per client | `BE_RATE_LIMIT_CHAT_PER_MINUTE` |
| `POST /search/query` | 60 / min per client | `BE_RATE_LIMIT_SEARCH_PER_MINUTE` |
| `POST /book/upload`, `POST /book/reindex` | message "Indexing queue is full, try again later." while `BE_INGESTION_MAX_QUEUED` (50) books are `queued` | `BE_INGESTION_MAX_QUEUED` |
| `POST /chat/stream` | "Too many answers are being generated right now, try again shortly." while `BE_CHAT_MAX_CONCURRENT_SESSIONS` (20) answers run | `BE_CHAT_MAX_CONCURRENT_SESSIONS` |

"Per client" = the service principal (valid `X-Internal-Token`), else the authenticated user (valid access token), else the client IP; `X-Forwarded-For` is only believed from peers listed in `BE_TRUSTED_PROXIES`. A budget of 0 disables it. These sit on top of the global per-IP limit (`BE_RATE_LIMIT`, plain `{"detail": "Too many requests"}`).

The budget is checked after FastAPI has read the request body, so an over-budget `POST /book/upload` still transfers its whole PDF (up to `MAX_UPLOAD_SIZE_MB`) before the `429` is returned; nothing is stored. Clients should honour `Retry-After` rather than re-sending at once. `POST /chat/stream` for a conversation that already has a running turn is a `409`, not a `429` (see below).

---

## Pagination & Filter Standard (FindDTO)

All `get-all` endpoints use `FindDTO` as the request body:

```json
{
  "search": "string",
  "search_by": [],
  "operator": "AND | OR",
  "orderBy": "createdAt",
  "order": "desc",
  "page": 1,
  "size": 10,
  "searchIgnoreSpecial": false,
  "filters": []
}
```

---

## General Schema

### BaseResponse

| Field | Type | Description |
|---|---|---|
| `metaData` | MetadataSuccess | Response metadata |
| `data` | object | Response data |
| `additionalInfo` | object | Additional info (optional) |
| `copyright` | string | Copyright text |

### MetadataSuccess

| Field | Type | Default |
|---|---|---|
| `status` | boolean | `true` |
| `executionTime` | integer | `0` |
| `responseCode` | integer | `200` |
| `message` | object | `"Success"` |
| `pagination` | Pagination | *(only on paginated responses)* |

### MetadataFailed

| Field | Type | Default |
|---|---|---|
| `status` | boolean | `false` |
| `executionTime` | integer | `0` |
| `responseCode` | integer | `400` |
| `message` | string | `"Failed"` |
| `pagination` | Pagination | *(always present)* |

### Pagination

| Field | Type | Description |
|---|---|---|
| `size` | integer | Items per page |
| `totalElements` | integer | Total items |
| `totalPages` | integer | Total pages |
| `scrollId` | string | Scroll pagination ID |

### FindDTO (base pagination & filter)

| Field | Type | Default | Description |
|---|---|---|---|
| `search` | string | `null` | Full-text search |
| `search_by` | string[] | `[]` | Fields to search in |
| `operator` | string | `null` | `AND` / `OR` |
| `orderBy` | string | `"createdAt"` | Sort field |
| `order` | string | `"desc"` | Sort direction |
| `page` | integer | `1` | Page number |
| `size` | integer | `10` | Items per page |
| `searchIgnoreSpecial` | boolean | `false` | Ignore special characters |
| `filters` | list | `[]` | Additional filters |

---
## Book Library

Full flows and response shapes: [`docs/architecture.md`](./architecture.md) §4. Swagger: `http://localhost:8020/docs`.

### Book object (`data` of `/book/*`)

```json
{
  "id": "uuid", "title": "string", "authors": ["string"], "description": "string|null", "isbn": "string|null",
  "coverUrl": "string|null", "publisher": "string|null", "publishedYear": 1965, "language": "string|null",
  "subjects": ["string"], "metadataSource": "manual|openlibrary|upload",
  "hasDocument": true,
  "document": { "fileName": "string", "sizeBytes": 35123, "pageCount": 3 },
  "ingestion": { "status": "none|queued|processing|indexed|failed", "error": "string|null",
                 "attempts": 1, "chunkCount": 5, "embeddingModel": "Qwen3-Embedding-0.6B",
                 "indexedAt": "ISO-8601|null" },
  "searchable": true,
  "createdAt": "ISO-8601", "updatedAt": "ISO-8601"
}
```

`ingestion.attempts` counts how many times the worker has claimed the book (`queued` → `processing`)
since its upload or last reindex. A job interrupted by a restart is resumed at startup while
`attempts < BE_INGESTION_MAX_ATTEMPTS` (3); at the cap it becomes `failed`.
`ingestion.error` is always safe to show; PDF parsing runs in a separate process, so a bad file fails
only its own book, e.g. "Parsing this PDF took too long and was stopped." (`BE_INGESTION_PARSE_TIMEOUT_SECONDS`),
"The PDF parser crashed on this file." or "Parsing this PDF needed more memory than the server allows."

### `POST /chat/ask`

Request `{ "question": "string (1-2000)", "bookIds": ["uuid"]?, "topK": 1-12? }` — omit `bookIds` to use every indexed book.

Response `data`:

```json
{
  "question": "Who rescued the crew of the Marigold?",
  "answer": "The Penhallow lifeboat rescued all seven crew members [1].",
  "grounded": true,
  "mode": "llm | general_knowledge | insufficient_context | no_context | no_indexed_books | retrieval_only",
  "usedGeneralKnowledge": false,
  "model": "openai/... | null",
  "sources": [{ "n": 1, "bookId": "uuid", "bookTitle": "…", "headings": ["Chapter 3: …"],
                "pageStart": 3, "pageEnd": 3, "score": 0.68, "text": "…", "cited": true }],
  "skippedBooks": [{ "id": "uuid", "title": "…", "reason": "not_indexed:none | not_found" }]
}
```

Answer policy (`BE_RAG_ALLOW_GENERAL_KNOWLEDGE`, default `true`): book facts are cited `[n]`; anything from the model's own knowledge follows a line `GENERAL KNOWLEDGE:` and is never cited (`usedGeneralKnowledge: true`). When no passage is relevant the whole answer is that section (`mode: general_knowledge`). With `false` the strict books-only modes apply (`no_context`, `insufficient_context`). An empty model reply is a `503` / `error` event, not "not enough information".

### Error statuses (book/search/chat)

`400` invalid input · `404` not found · `409` duplicate or wrong state (also: a question is already being answered in that conversation) · `429` rate limit or capacity, always with `Retry-After` (see "Rate limits and capacity") · `503` dependency unavailable · `500` unexpected (logged, generic message). Body: standard `BaseResponseFailed` with `metaData.message`.

`503` messages are safe to show: `POST /search/query`, and the retrieval step of `/chat/*`, answer `503` "Search service unavailable" when the embedding service or Qdrant cannot be reached (their details are only logged); a model failure answers `503` with a short reason (bad key, rate limit, unknown model) or "The model took too long to respond. Try again." when a streamed answer sees no token within `BE_LLM_FIRST_TOKEN_TIMEOUT_SECONDS`. An unknown book or conversation is `404`, never `500`.

### `POST /chat/stream` (Server-Sent Events, saved conversation)

Request: the `/chat/ask` body plus optional `"conversationId": "uuid"`. Without it a new conversation is created (title = the question, cut to 80 chars). The question is saved before answering; the answer (with its sources) is saved when it finishes. If the client disconnects mid-answer, the partial text is saved with `mode: "stopped"`; a provider failure is saved with `mode: "error"`. The last `BE_CHAT_HISTORY_TURNS` answered turns are given to the LLM so follow-up questions make sense, and retrieval also searches "previous question + this question". Validation/auth errors return normal JSON HTTP errors **before** the stream starts. **One running turn per conversation:** if a question of that `conversationId` is still being answered (another tab, a double submit) the response is `409` with `metaData.message` = "A question is already being answered in this conversation." (a normal JSON error, no stream); the claim is released when the answer finishes, is cancelled or fails, and a claim whose session died (stale heartbeat) is taken over. `POST /chat/ask` is stateless and unaffected. Otherwise `200 text/event-stream` (not wrapped in `BaseResponse`), frames `event: <name>` + `data: <json>`; `: ping` comment lines are keep-alives.

| Event | Data | When |
|---|---|---|
| `session` | `{ "sessionId": "uuid" }` | first — the server-side session generating this answer (use it to resume or cancel) |
| `conversation` | `{ id, title, bookIds, createdAt, updatedAt }` | first — the conversation this turn belongs to (`error` 404 instead if `conversationId` is unknown) |
| `status` | `{ "stage": "retrieving" \| "generating" }` | retrieval starts; LLM starts (reasoning models may think several seconds before the first delta) |
| `sources` | `{ question, sources[] (cited=false), skippedBooks[], model }` | after retrieval |
| `delta` | `{ "text": "…" }` | answer text pieces — append in order |
| `done` | `/chat/ask` `data` + `conversationId`, `messageId` | end of a successful stream — **replace** the streamed text with `done.answer` |
| `error` | `{ "message": "…", "code": 503, "messageId"? }` | provider failure (bad key, rate limit), first-token timeout (503, "The model took too long to respond. Try again."), search outage (503, "Search service unavailable"), unknown/expired session or conversation (404), dead session (503) — stream ends without `done` |
| `cancelled` | `{ "message": "…" }` | after POST …/cancel — the partial answer was saved as `stopped` |

Every frame has an `id:` (Redis stream entry id). **Resuming:** the answer is generated by a server-side session that survives a disconnect; reconnect with `GET /chat/stream/{sessionId}?after=<last id>` to receive exactly the events you missed, then the live rest. Sessions stay replayable for `BE_CHAT_SESSION_TTL_SECONDS` (1 h).

Order: `session` → `conversation` → `status(retrieving)` → `sources` → [`status(generating)` → `delta`…] → `done` | `error`. Non-LLM outcomes (`no_context`, `no_indexed_books`, `retrieval_only`) send no deltas. The `INSUFFICIENT_CONTEXT` marker is never streamed.

### Conversation objects (`/conversation/*`)

```json
{
  "id": "uuid", "title": "string", "bookIds": ["uuid"], "createdAt": "ISO-8601", "updatedAt": "ISO-8601",
  "messageCount": 4,
  "messages": [
    { "id": "uuid", "role": "user", "content": "Who rescued the crew?", "bookIds": [], "createdAt": "ISO-8601" },
    { "id": "uuid", "role": "assistant", "content": "The Penhallow lifeboat … [1].",
      "mode": "llm | general_knowledge | insufficient_context | no_context | no_indexed_books | retrieval_only | error | stopped",
      "grounded": true, "sources": ["same shape as /chat/ask sources"], "skippedBooks": [], "model": "string|null",
      "error": "string|null", "createdAt": "ISO-8601" }
  ]
}
```

`messageCount` is only in `get-all`; `messages` only in `get-one`. Assistant messages keep a snapshot of their sources, so old answers stay readable after a book is re-indexed or deleted.
