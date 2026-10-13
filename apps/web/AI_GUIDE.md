# AI Agent Guide — Web (React + Vite)

Quick start guide for contributors and AI agents. Start with [`AGENTS.md`](../../AGENTS.md). Entries below that point to `skills/...` refer to optional local tooling (git-ignored, may be absent); the rules in this file and in `AGENTS.md` stand on their own.

## 🚀 First Time Setup

Read these files **every time before writing any code**, in order:

1. **This file** (`AI_GUIDE.md`) — Quick start and navigation
2. **`skills/reactjs-architecture/SKILL.md`** — Folder layout, file placement, naming conventions

Then load additional skill(s) per task (see Documentation Map below).

## 📖 Documentation Map

### Skills (Load Per Task)

| File                                           | Purpose                                                                                                                               | Load When                                                                                  |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **`skills/reactjs-slicing-ui/SKILL.md`**       | Translating Figma/mockup designs into React components — DESIGN.md token chain, shadcn behavior-first primitives, component hierarchy | Building or refactoring any UI component or page                                           |
| **`skills/reactjs-anti-slop/SKILL.md`**        | Anti-AI-slop quality gate — pre-emit self-critique, honest copy, no redrawn UI chrome, 4-viewport responsive check, full interaction-state coverage, pre-handoff slop checklist | Before marking any UI slice/component complete — runs alongside `reactjs-slicing-ui`        |
| **`skills/reactjs-design-system/SKILL.md`**    | Apply active design system — shadcn token/variant wiring, CSS variables, dark mode, DESIGN.md composition patterns                    | Fixing visual drift, shadcn default styling, font/color issues, or design token compliance |
| **`skills/reactjs-api-design/SKILL.md`**       | API design reference — endpoint constants, request/response DTOs, response envelope types, `fusion-openapi.json` contract             | Writing service files, defining `API_ENDPOINTS`, or typing request/response payloads       |
| **`skills/reactjs-service/SKILL.md`**          | Service files, `createResourceService`, `apiRequests`, CRUD pattern                                                                   | Writing services, calling API                                                              |
| **`skills/reactjs-tanstack-query/SKILL.md`**   | TanStack Query — `useQuery`, `useMutation`, queryKey conventions, filter integration, infinite scroll                                 | Any API data fetch, mutation, or cache management                                          |
| **`skills/reactjs-state-management/SKILL.md`** | Decision router — Zustand, TanStack Query, XState, React Hook Form, useState                                                          | Creating/modifying any state layer                                                         |
| **`skills/reactjs-xstate/SKILL.md`**           | XState state machines — approval workflow, incident lifecycle, multi-step process                                                     | Feature with status transitions, guards, or approval flow                                  |
| **`skills/reactjs-error-handling/SKILL.md`**   | Error boundaries, try-catch, error states                                                                                             | Any async function, API call, `useEffect`                                                  |
| **`skills/reactjs-form/SKILL.md`**             | React Hook Form + Zod validation                                                                                                      | Implementing forms                                                                         |
| **`skills/reactjs-features/SKILL.md`**         | Scaffold domain feature folder (types → store → hook → component)                                                                     | Creating new feature under `src/features/`                                                 |
| **`skills/reactjs-modules/SKILL.md`**          | Scaffold reusable module (used by 2+ features)                                                                                        | Creating/extending `src/modules/`                                                          |
| **`skills/reactjs-app-layout/SKILL.md`**       | AppLayout, AppHeader, route wiring, non-overlapping shell                                                                             | Creating layout shell, adding pages/routes                                                 |
| **`skills/reactjs-sidebar/SKILL.md`**          | AppSidebar, active state, CSS vars, header offset                                                                                     | Building/fixing sidebar or navigation                                                      |
| **`skills/reactjs-menu-config/SKILL.md`**      | `APP_MENU`, `ADMINISTRATOR_MENU`, all menu IDs and paths                                                                              | Adding/modifying/rendering menu items                                                      |
| **`skills/reactjs-auth-guard/SKILL.md`**       | Enable/disable AuthGuard, route protection                                                                                            | Setting up/removing auth guards                                                            |
| **`skills/reactjs-responsive/SKILL.md`**       | Mobile-first layout, breakpoints                                                                                                      | New page/component, fixing mobile layout                                                   |
| **`skills/reactjs-icon/SKILL.md`**             | Phosphor Web CSS usage, `renderIcon()`                                                                                                | Adding/changing icons                                                                      |
| **`skills/reactjs-data-display/SKILL.md`**     | DataTable, DataList, infinite scroll, pagination                                                                                      | Rendering lists, tables, paginated data                                                    |
| **`skills/reactjs-chart/SKILL.md`**            | Charts data visualization                                                                                                             | Building any chart or graph UI                                                             |
| **`skills/reactjs-map/SKILL.md`**              | Mapbox GL JS — layers, popup, legend, markers, live feed                                                                              | Building any map-based page or feature                                                     |
| **`skills/reactjs-tactical-map/SKILL.md`**     | Tactical command map — domain override on `reactjs-map`                                                                               | Building command/tactical UI                                                               |
| **`skills/reactjs-dynamic-filter/SKILL.md`**   | Dynamic filter system — 6 filter types                                                                                                | Adding filter widgets, wiring filter to page                                               |
| **`skills/reactjs-dynamic-widget/SKILL.md`**   | Config-driven dashboard widgets — chart/stat/list/table                                                                               | Building any dashboard widget                                                              |
| **`skills/reactjs-switch-theme/SKILL.md`**     | Switch between Tactical/Fusion design systems                                                                                         | Switching design system, re-applying tokens                                                |
| **`skills/reactjs-manage-env/SKILL.md`**       | Create/add env keys — `VITE_` prefix, `env/` folder structure, `.env` + `.env.example` sync, `src/config/env.ts` typed accessor       | Adding any new env variable, creating `env/` for a new app, wiring env into typed config   |
| **`skills/reactjs-seo-html/SKILL.md`**         | SEO meta tags in `index.html` — OG, Twitter Card, Schema.org, canonical URL, favicon, placeholder replacement checklist               | Bootstrapping new app, rebranding, updating app URL/thumbnail, auditing meta tags          |

### Project Docs

| File                               | Purpose                    | When to Read    |
| ---------------------------------- | -------------------------- | --------------- |
| **`docs/api-spec.md`**             | Backend endpoint contracts | API integration |

## 🚨 Critical Rules Summary

### 🔴 MOST IMPORTANT: Service Layer

**NEVER call API directly from components — always go through `src/services/`!**

- ✅ Component → Hook (TanStack Query / Zustand) → `apiRequests` / Service → API
- ✅ All `fetch`/`axios` calls live in `src/services/` only
- ✅ Use `api-client.ts` (pre-configured axios) — don't create new instances
- ✅ Use `apiRequests` from `api-factory.service.ts` inside TanStack Query hooks
- ❌ **NEVER `fetch()` or `axios` inside a component**
- ❌ **NEVER manage global state with `useState`** — use Zustand stores
- ❌ **NEVER store API response data in Zustand** — use TanStack Query cache

### UI & Styling

- ✅ Use `src/components/ui/` (shadcn/ui) for behavior/accessibility primitives first
- ✅ Override shadcn tokens/variants/classes so final visuals follow active `DESIGN.md`
- ✅ Tailwind classes only — no inline styles, no CSS modules
- ✅ Always support light/dark theme via CSS variables in `styles/tailwind.css`
- ✅ Header, sidebar, and main content must occupy separate non-overlapping layout regions
- ✅ Any page navigation surface must render from `src/config/menu/*`, not hardcoded arrays
- ✅ In the current Tactical shell, primary page navigation lives in `AppSidebar` via `APP_MENU`; `AppHeader` is an operational/status bar unless the task explicitly adds header navigation
- ⚠️ Do not rewrite shadcn behavior. Controlled edits to `src/components/ui/` variants are allowed only for design-system alignment.

### Tech Stack

- ⚠️ **NEVER add new packages** without checking `package.json` first
- ✅ Path alias: always `@/` — never `../../`
- 📦 React 18 · TypeScript · Vite · Zustand · TanStack Query v5 · shadcn/ui · Tailwind
- 🧪 Checks: `npm run typecheck` · `npm run lint` · `npm test` (vitest + jsdom, tests colocated as `*.test.ts(x)`)

### State & Async

- ✅ Always handle loading + error states on every async operation
- ✅ **TanStack Query** for all server/API data — loading, caching, refetch, mutation
- ✅ **Zustand** for client UI state (filters, selections, preferences) — not API data
- ✅ **XState** for features with multi-step transitions, guards, or approval flows
- ✅ `useState` for local component state only

## 🎯 Quick Decision Guide

### What kind of feature is this?

```
New page needed?
├─ Public / protected app page  → src/pages/{module}/
│                                 + add to routes/main.routes.tsx
│                                 + add menu entry unless route is explicitly hidden
├─ Admin-only page              → src/pages/administrator/{module}/
│                                 + add an admin route file (guarded by RoleGuard) and an
│                                   admin menu entry; none exists yet
└─ Auth page                    → src/pages/auth/ + add to routes/auth.routes.tsx
```

### Where does new code go?

```
What are you adding?
├─ Page route entry           → src/pages/{module}/{NamePage}.tsx  ← ONE FILE, thin composition only
├─ Domain component           → src/features/{domain}/{feature}/components/
├─ Domain hook                → src/features/{domain}/{feature}/hooks/
├─ Domain store (Zustand)     → src/features/{domain}/{feature}/store/
├─ Domain types               → src/features/{domain}/{feature}/types/
├─ Domain utils / helpers     → src/features/{domain}/{feature}/utils/
├─ Domain constants / enums   → src/features/{domain}/{feature}/constants/
├─ Domain config (col defs, chart opts) → src/features/{domain}/{feature}/config/
├─ Domain mock / fixture data → src/features/{domain}/{feature}/mocks/
├─ Process/workflow state     → src/features/{domain}/{feature}/machines/{name}.machine.ts (XState)
├─ UI primitive (shadcn)      → src/components/ui/  (install via shadcn CLI if missing)
├─ API service (complex)      → src/services/{module}.service.ts
├─ Global cross-domain hook   → src/hooks/use-{name}.ts
├─ Global cross-domain store  → src/stores/use{Module}Store.ts
├─ Global types               → src/types/{module}.d.ts
├─ Global utils               → src/utils/{name}.ts
└─ Menu item                  → src/config/menu/app.menu.ts or administrator.menu.ts
```

## 📋 Code Generation Workflow

1. ✅ Check `docs/api-spec.md` — understand endpoint contract before writing service
2. ✅ Load skill(s) matching your task (see Documentation Map above)
3. ✅ Reuse the existing tokens and classes in `src/styles/` ("Mist & Ink", light mode) for UI tasks
4. ✅ Define types in `src/types/{module}.d.ts`
5. ✅ Decide state layer — read `reactjs-state-management` decision tree first
   - API data → TanStack Query hook in `src/features/{domain}/hooks/`
   - Workflow/process → XState machine in `src/features/{domain}/machines/`
   - UI/client state → Zustand in `src/stores/`
6. ✅ Add endpoint to `src/services/api-endpoints.ts`
7. ✅ Create service in `src/services/{module}.service.ts` (if `createResourceService` applies)
8. ✅ Create page in `src/pages/{module}/`
9. ✅ Register route in `src/routes/`
10. ✅ Add menu entry in `src/config/menu/` for every user-facing page
11. ✅ Skip menu entry only if the prompt/task explicitly says the route is hidden, redirect-only, modal-only, or otherwise non-navigable

## 📁 File Locations

```
{app-root}/
├── env/
│   ├── .env                  ← dev values (gitignored)
│   ├── .env.example          ← placeholder keys (committed)
│   ├── .env.staging          ← staging build (gitignored)
│   └── .env.production       ← production build (gitignored)
src/
├── main.tsx
├── components/
│   ├── layouts/            → AppHeader, AppSidebar, AppLayout
│   ├── ui/                 → shadcn/ui primitives; preserve behavior, align variants to DESIGN.md
│   └── wrappers/           → PerfectScrollArea (exists); add other 3rd-party adapters here
├── config/
│   ├── menu/               → app.menu.ts, administrator.menu.ts
│   ├── query-client.ts     → Shared TanStack QueryClient (mounted in main.tsx)
│   └── env.ts              → Typed env accessor — consume `env.*` here, never raw `import.meta.env.*` in components
├── hooks/                  → Custom React hooks
├── features/
│   ├── auth/               → login / register forms, schemas, hooks
│   └── library/            → books, catalog, chat, search, upload (the app's domain)
├── pages/                  → Route-level page components
│   ├── auth/               → LoginPage, RegisterPage
│   └── library/            → CatalogPage, BookDetailPage, SearchPage, AskPage
├── routes/                 → React Router config
│   ├── index.tsx           → Root router
│   ├── main.routes.tsx     → App routes (library pages)
│   ├── auth.routes.tsx     → Public auth routes
│   └── guards/             → AuthGuard, RoleGuard
├── services/               → All API calls live here
│   ├── api-client.ts           → Axios instance — real backend (use this, don't create new)
│   ├── api-endpoints.ts        → Real API path constants
│   ├── api-factory.service.ts  → apiRequests helpers (get/post/put/patch/delete/upload) — resolve to the `ApiResponse<T>` envelope ({ metaData, data })
│   ├── auth.service.ts
│   ├── book / chat / conversation / search .service.ts → library API calls
│   ├── mock-client.ts          → fetch wrapper for public/data/ (POC only, created once)
│   ├── mock-endpoints.ts       → Mock file path constants (add entry per mock file)
│   └── mock.service.ts         → mockRequest() helper — used by all domain services in POC
├── stores/                 → Zustand stores
├── styles/                 → theme.css, variables.css, components.css
├── types/
│   └── *.d.ts              → TypeScript .d.ts definitions
└── utils/                  → cn, icon-renderer, auth-redirect
```

## 🗂️ Mock Data

Mock data is stored in `public/data/` as **JSON** or **CSV** files and served statically by the dev server.

### Rules

- All mock files go in `public/data/` — never inside `src/`
- Use `.json` for structured records, `.csv` for tabular/export-style data
- Every `.json` mock file **must** follow this envelope structure:

```json
{
  "metaData": {
    "status": true,
    "title": "...",
    "...": "any additional metadata fields"
  },
  "data": []
}
```

> `metaData.status` is required (`boolean`). Add any other metadata fields (title, tahun, total, etc.) as needed. Domain records live in `data[]` — never at the root level.

- Initial mock data is copied from the root `data/` folder into `public/data/` when setting up the project
- In POC scope, this is the **only** data source — no backend calls
- Mock fetches live in `src/services/{module}.service.ts` — **never** inside components, hooks, or stores
- The mock service layer mirrors the real API layer exactly — one infrastructure file per concern, domain services on top
- `apiClient` is reserved for backend API calls; `mockClient` is reserved for `public/data/` static files — never mix them
- **Never** call raw `fetch('/data/...')` in domain services — always go through `mockRequest()`
- One `mockClient` + one `mock-endpoints.ts` for the whole project; each domain gets its **own service** and its **own store**

### Mock Service Layer — parallel to real API layer

| Real API                                 | Mock                                | Role                                                          |
| ---------------------------------------- | ----------------------------------- | ------------------------------------------------------------- |
| `api-client.ts`                          | `mock-client.ts`                    | HTTP/fetch transport (created once, never edited per-feature) |
| `api-endpoints.ts`                       | `mock-endpoints.ts`                 | File path constants (add an entry per mock file)              |
| `api-factory.service.ts` → `apiRequests` | `mock.service.ts` → `mockRequest()` | Typed helper used by domain services / TanStack Query hooks   |
| `{module}.service.ts`                    | `{module}.service.ts`               | Domain service (uses `mockRequest`)                           |

**`src/services/mock-client.ts`** — created once per project

```ts
const mockClient = {
  get: async <T>(path: string): Promise<T> => {
    const res = await fetch(`/data/${path}`)
    if (!res.ok) throw new Error(`Failed to load mock data: ${path}`)
    return res.json()
  },
}

export default mockClient
```

**`src/services/mock-endpoints.ts`** — add one entry per mock file (analogous to `api-endpoints.ts`)

```ts
export const MOCK_ENDPOINTS = {
  SENTIMENT: 'mock-sentiment.json',
  PENDUDUK: 'mock/data-penduduk.json',
} as const
```

> Never pass raw string literals to `mockRequest()` — always reference `MOCK_ENDPOINTS.*`.

**`src/services/mock.service.ts`** — typed helper (analogous to `api.service.ts` / `request()`)

```ts
import mockClient from './mock-client'

export function mockRequest<T>(path: string): Promise<T> {
  return mockClient.get<T>(path)
}
```

### Folder Convention

```
public/
└── data/
    ├── mock-sentiment.json     ← copied from data/mock-sentiment.json
    ├── mock/
    │   ├── data-penduduk.json  ← copied from data/mock/data-penduduk.json
    │   └── data-sentimen.json  ← copied from data/mock/data-sentimen.json
    └── ...                     ← add new mock files here
```

### Full Chain — mockRequest → Service → Store → Component

**1. Service** (`src/services/sentiment.service.ts`)

```ts
import { mockRequest } from './mock.service'
import { MOCK_ENDPOINTS } from './mock-endpoints'
import type { TSentiment } from '@/types/models'

export const sentimentService = {
  getAll: () => mockRequest<TSentiment[]>(MOCK_ENDPOINTS.SENTIMENT),
}
```

**2. Zustand store** (`src/stores/useSentimentStore.ts`)

```ts
import { create } from 'zustand'
import { sentimentService } from '@/services/sentiment.service'
import type { TSentiment } from '@/types/models'

interface SentimentState {
  data: TSentiment[]
  loading: boolean
  error: string | null
  fetch: () => Promise<void>
}

export const useSentimentStore = create<SentimentState>((set) => ({
  data: [],
  loading: false,
  error: null,
  fetch: async () => {
    set({ loading: true, error: null })
    try {
      const data = await sentimentService.getAll()
      set({ data })
    } catch (e) {
      set({ error: (e as Error).message })
    } finally {
      set({ loading: false })
    }
  },
}))
```

**3. Component** (`src/pages/sentiment/SentimentPage.tsx`)

```tsx
import { useEffect } from 'react'
import { useSentimentStore } from '@/stores/useSentimentStore'

export function SentimentPage() {
  const { data, loading, error, fetch } = useSentimentStore()

  useEffect(() => {
    fetch()
  }, [fetch])

  if (loading) return <p>Loading…</p>
  if (error) return <p className="text-destructive">{error}</p>

  return (
    <ul>
      {data.map((item) => (
        <li key={item.id}>{item.label}</li>
      ))}
    </ul>
  )
}
```

> **Flow:** Component → store → domain service → `mockRequest()` → `mockClient` → `public/data/`. Never skip a layer. One client, one endpoints file, many services, many stores.

---

## ⚠️ Common Mistakes to Avoid

1. ❌ **API call inside component** — always use `src/services/`
2. ❌ **`useState` for shared state** — use Zustand store
3. ❌ **Relative imports** — always use `@/`
4. ❌ **Rewrite shadcn behavior** — keep behavior/accessibility and adjust tokens/variants/classes only
5. ❌ **Inline styles** — always use Tailwind classes
6. ❌ **Skip loading/error states** — every async operation needs both
7. ❌ **New axios instance** — use `src/services/api-client.ts`
8. ❌ **Store API response data in Zustand** — use TanStack Query cache; Zustand is for UI/client state only
9. ❌ **Manage `isLoading`/`isError` with `useState` for API calls** — let `useQuery` handle them
10. ❌ **Use Zustand `status` string + scattered `if` checks for workflows** — use XState for features with transition rules
11. ❌ **Raw `fetch('/data/...')` in domain services** — use `mockRequest()` from `src/services/mock.service.ts`
12. ❌ **Raw string path in `mockRequest()`** — always reference `MOCK_ENDPOINTS.*` from `mock-endpoints.ts`
13. ❌ **Flat JSON array at root of mock file** — wrap in `{ metaData: { status: boolean, ... }, data: [] }` envelope
14. ❌ **New package without checking `package.json`** first
15. ❌ **Hardcode colors** — use CSS variables from `styles/tailwind.css`
16. ❌ **Accept raw shadcn defaults as final UI** — align with active `DESIGN.md`
17. ❌ **Let shadcn Sidebar cover the header** — offset fixed sidebar below a full-width topbar
18. ❌ **Finish a user-facing page without wiring navigation** — add route + menu entry together unless the route is explicitly hidden
19. ❌ **Hardcode sidebar/header menu arrays** — add items to `src/config/menu/*`
20. ❌ **Use `REACT_` prefix for env keys** — this stack uses Vite, prefix must be `VITE_`
21. ❌ **Put `.env` at app root** — env files live in `env/` subfolder (`env/.env`, `env/.env.example`, etc.)
22. ❌ **Call `import.meta.env.*` directly in components** — always go through `src/config/env.ts`
23. ❌ **Add key to `.env` without updating `.env.example`** — always sync both files
24. ❌ **Hardcode brand values in `index.html`** — use `{{PLACEHOLDER}}` tokens; replace all when bootstrapping a new app (see `reactjs-seo-html` skill)
25. ❌ **Use `react-helmet` for static app-level meta tags** — static SEO belongs in `index.html` only; `usePageTitle` handles per-page `document.title` at runtime
26. ❌ **Define helper/util functions inside a `.tsx` component file** — extract to `src/utils/` (global) or `features/{domain}/{name}/utils/` (domain)
27. ❌ **Define types or interfaces inside a `.tsx` component file** — extract to `src/types/` (global) or `features/{domain}/{name}/types/` (domain)
28. ❌ **Define constants, enums, or label maps inside a `.tsx` component file** — extract to `src/config/constants.ts` (global) or `features/{domain}/{name}/constants/`
29. ❌ **Define column defs, chart options, or filter config inside a `.tsx` component file** — extract to `features/{domain}/{name}/config/` or `pages/{page}/{name}.config.ts`
30. ❌ **Put mock/fixture data arrays inside a component file** — use `public/data/*.json` (POC) or `features/{domain}/{name}/mocks/` (local fixtures)
31. ❌ **Put domain-specific utils/constants in `src/utils/` or `src/config/`** — only truly cross-domain, generic helpers belong at the global level
32. ❌ **Hand-write a shadcn primitive from scratch** when `src/components/ui/` doesn't have it — install via `npx shadcn@latest add <name>` first, then wire tokens to `DESIGN.md`
33. ❌ **Run shadcn CLI at repo root** — always run it inside the target app folder (`apps/{app}/`)
34. ❌ **Create `parts/` or `hooks/` subfolders inside `pages/{page}/`** — a page folder contains exactly one file (`{NamePage}.tsx`); all supporting code goes into `src/features/{domain}/{feature}/`
35. ❌ **Skip creating a feature folder because the code is "only used by one page"** — always scaffold under `features/{domain}/`; there is no `pages/` subfolder fallback

## 💡 Pro Tips

1. **`api-factory.service.ts`** — use `apiRequests.get/post/put/patch/delete/upload` directly in TanStack Query hooks; don't call `apiClient` manually
2. **TanStack Query is the default for API data** — `useQuery` in hooks, never store responses in Zustand
3. **XState for workflow/process state** — any feature with explicit transitions or approval steps; read `reactjs-xstate` skill first
4. **`RoleGuard` + `AuthGuard`** are already built — use them for protected routes
5. **Mock layer mirrors real API layer** — `mock-client` / `mock-endpoints` / `mock.service` swap out cleanly for `api-client` / `api-endpoints` / `api-factory.service` when graduating from POC to MVP
6. **shadcn primitive missing from `src/components/ui/`?** Install it first: `npx shadcn@latest add <name>` (run from inside `apps/{app}/`), then align `cva` variants to active `DESIGN.md` before using it

## 📞 Quick Commands

```bash
# Check existing API contracts
cat docs/api-spec.md

# Check installed packages
cat package.json

# Check existing stores
ls src/stores/

# Check existing services
ls src/services/

# Check existing types
ls src/types/

# Check route config
cat src/routes/index.tsx
```

## ✅ Success Checklist

Your generated code is good if:

- [ ] No API calls inside components — all in `src/services/`
- [ ] TypeScript types defined in `src/types/`
- [ ] API data fetched via TanStack Query hooks (`useQuery` / `useMutation`) using `apiRequests` from `api-factory.service.ts`
- [ ] Mock data fetched via `mockRequest()` + `MOCK_ENDPOINTS.*` (POC)
- [ ] Global UI state uses Zustand store — no API response data stored in Zustand
- [ ] Features with status transitions use XState machine, not ad-hoc `status` strings in Zustand
- [ ] Path aliases used (`@/`) — no relative imports
- [ ] Tailwind classes only — no inline styles
- [ ] Light/dark theme supported via CSS variables
- [ ] shadcn primitives keep behavior/accessibility but visual classes match active `DESIGN.md`
- [ ] Header/sidebar/main shell regions do not overlap
- [ ] Any rendered page navigation comes from `src/config/menu/*`
- [ ] Loading and error states handled
- [ ] Route registered in `src/routes/`
- [ ] Menu entry added in `src/config/menu/` for every user-facing page, or the route is explicitly documented as hidden
- [ ] Env keys use `VITE_` prefix, ALL_CAPS, stored in `env/.env` and `env/.env.example`
- [ ] Env values consumed via `src/config/env.ts` — no raw `import.meta.env.*` in components/services
- [ ] Component files (`.tsx`) contain no inline helper functions, types, constants, mock data, or config objects — all extracted to proper subfolders
- [ ] `index.html` has no leftover `{{PLACEHOLDER}}` tokens — all replaced with real project values
- [ ] No new packages added without permission
- [ ] `src/components/ui/` behavior not rewritten; any variant edits are design-system alignment only
