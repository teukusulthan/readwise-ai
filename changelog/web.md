# Web Changelog

Tracks all frontend changes across sprints — screens added, components built, bugs fixed, design tokens applied.

Append-only. Newest entries at the top. Updated whenever a frontend task is created or completed.

---

<!-- ENTRY FORMAT:
### YYYY-MM-DD · [Sprint NN — slug](../sprint/active/NN-slug/sprint.md) · Task: [task title](../sprint/.../frontend/NN-task.md) · STATUS

**Event:** Task created | Task completed | Files modified
**Files:** `path/to/file.tsx`, `path/to/style.css`
> One-line summary of what changed or was delivered.
-->

### 2026-10-12 · Patch dependencies, drop unused libraries and dead boilerplate files (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `apps/web/package.json`, `apps/web/package-lock.json`, `apps/web/vite.config.ts`, `apps/web/tsconfig.json`, `apps/web/src/main.tsx`, `apps/web/AI_GUIDE.md`; removed `apps/web/public/sw.js`, `src/pwa-register.js`, `src/App.tsx`, `src/components/layouts/{BlankLayout,TopLayout,AppFooter}.tsx`, `src/services/api-factory-crud.service.ts`, `src/utils/date-formatter.ts`, `src/hooks/use-mobile.tsx`, `src/modules/{data-display,dynamic-filter}`
> `axios` 1.20.0 and `react-router-dom`/`react-router` 6.30.6 (latest of the current majors). Removed the `moment-timezone` side effect in `main.tsx` (main bundle 895 kB -> 101 kB) and the leftover service-worker registration. Dropped 28 never-imported packages (echarts, recharts, mapbox-gl, wavesurfer, styled-components, lodash, dayjs, date-fns, moment, crypto-js, immer, react-table, @tanstack/react-table, @babel/standalone, dompurify, polished, slugify, next-themes, sass, autoprefixer, terser, dotenv and others) plus their `@types`, and the matching `manualChunks` entries. `@tailwindcss/postcss` and the testing-library packages moved to `devDependencies`. Deleted the unreferenced files listed above. `npm audit --omit=dev`: 11 -> 2 moderate (remaining `react-router` 6.x advisories are only fixed in v7, a major bump).

### 2026-10-12 · Show "question already being answered" (409) in chat (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `apps/web/src/services/sse-client.test.ts`, `apps/web/src/features/library/chat/hooks/useAskStream.resume.test.ts`
> No code change needed: the SSE client already turns a pre-stream error response into `SseHttpError` with the envelope message and the hook treats 4xx as permanent, so the chat error state shows the backend's 409 text. Locked in with two tests.

### 2026-10-12 · Fresh catalog after indexing; real upload errors; no upload timeout (no sprint) · ✅ Done

**Event:** Task completed
**Files:** `apps/web/src/services/api-error.ts`, `apps/web/src/services/api-client.ts`, `apps/web/src/services/api-factory.service.ts`, `apps/web/src/features/library/books/hooks/useBook.ts`, `apps/web/src/features/library/catalog/hooks/useBooks.ts`, `apps/web/src/features/library/constants/catalog.ts`, tests (`api-error.test.ts`, `api-factory.service.test.ts`, `useBook.test.tsx`, `useBooks.test.tsx`, `useBatchUpload.test.tsx`)
> When a polled book leaves queued/processing, all book lists (catalog and the chat picker) are invalidated, and the catalog re-fetches every 5 s while a book on the page is still indexing. API failures now reject with an `ApiError` (a real `Error` carrying the backend message, `status`, `responseCode`, `response`), so batch upload rows show the server's reason (e.g. the duplicate 409) instead of "Upload failed". Multipart uploads have no client timeout; other requests keep 30 s.

### 2026-10-12 · Chat survives navigation, Stop, and bad stream frames (no sprint) · ✅ Done

**Event:** Task completed
**Files:** `apps/web/src/features/library/chat/components/ChatView.tsx`, `apps/web/src/features/library/chat/components/ChatComposer.tsx`, `apps/web/src/features/library/chat/hooks/useActiveTurn.ts`, `apps/web/src/features/library/chat/hooks/useAskStream.ts`, `apps/web/src/features/library/constants/query-keys.ts`, `apps/web/src/services/chat.service.ts`, `apps/web/src/services/sse-client.ts`, tests (`ChatView.test.tsx`, `useAskStream.stop.test.ts`, `chat.service.test.ts`, `sse-client.test.ts`)
> Leaving a conversation marks its cached thread stale and resets the per-conversation refs; the "is an answer running?" check is now a never-cached `useActiveTurn` query, so coming back re-attaches to a running turn (and a new chat no longer comes back empty). After Stop, Send stays disabled until the stream reports `cancelled` or ends (5 s fallback); asking again first refetches the thread so the stopped turn stays visible. An SSE frame with unparseable JSON is skipped with `console.warn` instead of failing the stream, and the reader is `cancel()`ed on every exit path.

### 2026-10-12 · Visible progress while the model thinks (no sprint) · ✅ Done

**Event:** Task completed
**Files:** `apps/web/src/features/library/chat/components/AnswerProgress.tsx`, `apps/web/src/features/library/chat/components/AnswerProgress.test.tsx`, `apps/web/src/features/library/chat/components/AssistantMessage.tsx`, `apps/web/src/features/library/chat/components/AssistantMessage.test.tsx`
> The pending answer shows the current stage ("Searching your books…", then "Reading N passages and thinking…" once sources arrived), an elapsed-seconds counter after 5 s, and a hint after 45 s that long thinking is normal for the model. Derived from stream state, so re-attached turns read the same; the dots honour reduced motion and the counter is not announced by the live region.

### 2026-10-12 · Upload several PDFs at once (no sprint) · ✅ Done

**Event:** Task completed
**Files:** `apps/web/src/features/library/books/hooks/useBatchUpload.ts`, `apps/web/src/features/library/components/BatchUploadPanel.tsx`, `apps/web/src/features/library/components/UploadBookDialog.tsx`
> The upload dialog accepts several PDFs (picker or drag-and-drop), one editable-title row each; files upload sequentially with pending / uploading / queued for indexing / error status (409 duplicate message shown per row, finished rows never retried). Closing mid-batch asks for confirmation. Attaching a PDF to an existing book (`bookId`) is unchanged.

### 2026-10-12 · Edit book details (no sprint) · ✅ Done

**Event:** Task completed
**Files:** `apps/web/src/services/api-endpoints.ts`, `apps/web/src/services/book.service.ts`, `apps/web/src/features/library/types/book.types.ts`, `apps/web/src/features/library/books/schemas/edit-book.schema.ts`, `apps/web/src/features/library/books/hooks/useUpdateBook.ts`, `apps/web/src/features/library/books/components/EditBookDialog.tsx`, `apps/web/src/features/library/books/components/BookDetailView.tsx`
> "Edit details" button on the book detail page opens a prefilled dialog (title, authors, description, ISBN, publisher, year, language, subjects, cover URL) that calls `PUT /book/update`; server errors (bad/duplicate ISBN) show inline.

### 2026-10-12 · Error envelope top-level (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `apps/web/src/services/api-client.ts`, `apps/web/src/services/sse-client.ts`
> Comments/readers updated: top-level `metaData.message` is the primary error shape; legacy `detail` shapes kept for back-compat.

### 2026-10-12 · Rebrand to "Readwise AI" (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `apps/web/index.html`, `apps/web/public/manifest.json`, `apps/web/public/favicon.ico`, `apps/web/public/images/{16x16,24x24,32x32,64x64,180x180,512x512}.png`, `apps/web/public/images/thumbnail/share.png`, `apps/web/src/hooks/use-page-title.ts`, `apps/web/src/components/layouts/AppHeader.tsx`, `apps/web/src/styles/variable.css`, `apps/backend/api.py`
> App renamed "Book Library" → "Readwise AI" (header, tab titles, PWA manifest, Swagger title). `index.html` meta placeholders (`{{APP_NAME}}`…) replaced with real values; favicons/PWA icons/OG card (1200×630) regenerated from the boilerplate "ANA NextGen" art to a navy "R" tile in Fraunces (Mist & Ink palette). og:url/canonical omitted until a public domain exists.

### 2026-10-09 · Boilerplate fixes (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `apps/web/src/config/env.ts`, `apps/web/src/config/query-client.ts`, `apps/web/src/services/*`, `apps/web/src/main.tsx`, `apps/web/src/components/wrappers/PerfectScrollArea.tsx`, `apps/web/src/routes/guards/*`, `apps/web/vite.config.ts`, `apps/web/package.json`
> The API base URL now comes from `VITE_API_BASE_URL` via `config/env.ts` and goes through the Vite proxy. Fixed `apiRequests` unwrapping responses twice (it now returns the `BaseResponse` envelope). Mounted QueryClientProvider (TanStack Query v5) and the Toaster. Removed broken imports. Added `PerfectScrollArea`. Guards read `useAuthStore`. Added vitest, `test`/`lint`/`typecheck` scripts, and the first tests.

### 2026-10-09 · RAG Book Library MVP UI (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `src/pages/library/*`, `src/features/library/**`, `src/services/{book,search,chat}.service.ts`, `src/routes/main.routes.tsx`, `src/config/menu/app.menu.ts`, `src/components/layouts/*`, `src/components/ui/{input,textarea,label,checkbox,skeleton,form}.tsx`, `vite.config.ts`
> Added the Catalog page (search, Indexed/Metadata-only filters, Open Library import, add, upload), Book detail (document status polling, reindex, delete), and Ask (book selector, answer with sources and non-grounded banners). The dev proxy target can be overridden with `BACKEND_PROXY_TARGET`. 26 tests pass; typecheck, lint and build pass.

### 2026-10-09 · Streaming answers + cream light redesign (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `src/services/sse-client.ts`, `src/features/library/chat/**` (useAskStream, AnswerText, citations utils), `src/styles/variable.css`, `src/config/theme.ts`, `index.html`, `src/index.css`, `src/components/ui/*`, `src/components/layouts/*`, `src/features/library/**`
> The Ask page streams answers over SSE (fetch POST) with a status for each stage, a Stop button, inline [n] citation chips linked to the source cards, and a clear error banner that keeps the sources visible. The redesign uses a warm cream light theme (caramel accent, sage, warm shadows), Fraunces headings with Inter for UI text, a 16px base with larger controls, an editorial book detail page with an ingestion progress track, and covers on the catalog cards. Light mode is pinned. Paragraphs now split on any line break. 46 tests pass; typecheck, lint and build pass.

### 2026-10-09 · Dialog centering fix, navy theme, chatbot Ask page (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `src/styles/components.css`, `src/components/ui/dialog.tsx`, `src/styles/variable.css`, `index.html`, `src/components/layouts/{AppLayout,AppSidebar}.tsx`, `src/types/route.d.ts`, `src/routes/main.routes.tsx`, `src/features/library/chat/**` (ChatView, ChatComposer, ConversationSidebar, AssistantMessage, UserMessage, ChatEmptyState, useConversations, chat-thread utils; AskView/AnswerPanel/AskForm removed), `src/services/{conversation,chat}.service.ts`, `src/services/api-endpoints.ts`, `src/features/library/constants/query-keys.ts`
> **Dialog bug:** every dialog opened half its own width and height up and to the left of centre (its top was clipped). The cause was Tailwind v4's `translate-x/y-[-50%]`, which sets the CSS `translate` property, while the open animation also set `transform: translate(-50%,-50%)`. The browser applies both, so the dialog moved twice. The keyframes now animate only `scale` and `opacity`. Dialogs are also capped at the viewport height and scroll inside (PerfectScrollArea), and long content can no longer widen them.
> **Theme:** the accent changed from caramel to ink navy (`#2F4F86`, 7.9:1 on white), and the warm cream neutrals changed to cool "mist" greys that suit it. The main column renders at 0.88× and the sidebar at 1.1×, set by the `--content-scale` / `--sidebar-scale` CSS zoom tokens.
> **Ask page:** now a chatbot. Saved conversations sit on the left (grouped by date, inline rename, delete with confirmation; a drawer on mobile). The thread scrolls and follows new text, with the input pinned at the bottom (Enter sends, Shift+Enter adds a line, book scope picker, Stop). Every answer keeps its citation chips and collapsible sources. New chats switch the URL to `/ask/:id` without interrupting the stream. 51 tests pass; typecheck, lint and build pass.

### 2026-10-09 · Book picker search for large libraries (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `src/features/library/chat/components/BookSelector.tsx`, `src/features/library/chat/components/BookSelector.test.tsx`
> With 20+ indexed books, the scope picker had turned into a tall wall of chips, and a book was easy to miss. It now has a "Find a book" search box (by title or author, shown when there are more than 8 books). Selected books are listed first, and the list scrolls inside a bounded area. 54 web tests pass.

### 2026-10-09 · General-knowledge section, lists, clearer skip reasons (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `src/features/library/chat/components/{AnswerText,AssistantMessage,ChatComposer,ChatEmptyState}.tsx`, `src/features/library/chat/utils/citations.ts`, `src/features/library/chat/constants/answer-modes.ts`, `src/features/library/chat/types/chat.types.ts`, `src/features/library/utils/format.ts`, tests
> The part of an answer after `GENERAL KNOWLEDGE:` is shown in its own box ("General knowledge · not from your books"), with no citation chips; this also works while the answer streams. A general-knowledge-only answer gets an info banner instead of the warning. "- item" and "1. step" lines render as real lists. "Not searched" reasons now read "metadata only, no text" or "still being indexed". 61 tests pass.

### 2026-10-09 · Cover cards of the cited books under each answer (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `src/features/library/chat/components/CitedBooks.tsx` (new), `src/features/library/chat/components/{AssistantMessage,ChatView}.tsx`, `src/features/library/chat/utils/chat-thread.ts`, tests
> An answer that cites books now shows "Based on these books": one card per cited book (cover, title, authors, year, number of passages cited), in the order the answer first cites them, each linking to the book's page. The cards are built from the catalog the chat page already loads, so saved answers get them too, with no backend change. Books that are only retrieved but not cited, and general-knowledge-only answers, show no card; a cited book missing from the catalog falls back to a placeholder cover. 66 web tests pass.

### 2026-10-09 · Answers survive disconnects, reloads and chat switching (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `src/services/sse-client.ts`, `src/services/chat.service.ts`, `src/services/api-endpoints.ts`, `src/features/library/chat/hooks/useAskStream.ts`, `src/features/library/chat/components/ChatView.tsx`, `src/features/library/chat/types/chat.types.ts`, tests (incl. `useAskStream.resume.test.ts`)
> The SSE client keeps each frame's `id`. `useAskStream` remembers the session and last event id. After a dropped connection it re-attaches (`GET …?after=`, retrying 1–8 s, up to 6 times) and shows "Connection lost — reconnecting".
> - `detach()` (switching chats, leaving the page) only disconnects, and `attach()` re-joins a running answer after a reload (via `/chat/active`).
> - Stop now calls the server's cancel.
> - The existing smooth-reveal (`useSmoothText`) flow is unchanged.
>
> 81 tests pass.

### 2026-10-09 · Fluid UX: inertia scrolling, cursors, hover and motion polish (no sprint) · ✅ Done

**Event:** Files modified
**Files:** `src/components/wrappers/{inertia-scroll.ts (new), inertia-scroll.test.ts (new), PerfectScrollArea.tsx}`, `src/components/ui/{expand.tsx (new), button.tsx, tooltip.tsx, skeleton.tsx, dialog.tsx}`, `src/components/layouts/{AppLayout,AppSidebar}.tsx`, `src/main.tsx`, `src/index.css`, `src/styles/{tailwind.css,components.css}`, catalog/book/chat components
> **Inertia scrolling.** Every scroll area (`PerfectScrollArea`) now has momentum wheel scrolling. Wheel input moves a target and the content eases towards it frame by frame, so a notch glides instead of jumping (measured: 30 positions over about 600 ms). Nested areas hand the scroll to their parent at the edges, and pinch-zoom, scrollbar dragging, keyboard and touch keep their native behaviour. It is off when the OS asks for reduced motion.
>
> **Cursors.** Pointer on everything clickable (Tailwind v4 resets buttons to the arrow); not-allowed on disabled controls, which no longer swallow pointer events, so their explanations show; help on status badges; grab and grabbing on scrollbar thumbs; progress while an answer is being written.
>
> **Motion.** Shared easing tokens (`ease-fluid`, `ease-spring`).
> - Buttons lift 1 px on hover and press in on click.
> - Book cards lift, zoom the cover and tint the title; covers fade in once loaded.
> - Pages fade in, and each page remembers its scroll position.
> - Navigation has a springy active marker.
> - Source passages, the sources panel and the book picker expand smoothly (`Expand`, grid-rows transition).
> - New messages slide in, and the chat follows streaming text with a glide that stops as soon as you scroll up.
> - The typing indicator bounces, Stop pulses, and the Send arrow nudges up on hover.
> - Tooltips are proper ones (with shortcuts) on icon buttons and truncated conversation titles; loading skeletons shimmer.
>
> **Fixes.** Several hover lifts didn't animate because their transitions listed `transform`, while Tailwind v4 uses the separate `translate`/`scale` properties. A tooltip `asChild` on `NavLink` had broken its className function.
>
> 86 tests pass (5 new inertia tests); typecheck, lint and build pass.
