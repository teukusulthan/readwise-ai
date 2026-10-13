# Web application (React + Vite)

## Tech Stack

- **Core:** React 18+, TypeScript (strict mode, no `any`)
- **Build Tool:** Vite
- **State Management:** Zustand (UI state), TanStack Query v5 (server state — `src/config/query-client.ts`, mounted in `main.tsx`)
- **API Client:** Axios with interceptors
- **Styling:** Tailwind CSS 4
- **UI Components:** shadcn/ui (Radix-based)
- **Answers:** react-markdown (safe Markdown rendering)
- **Form Handling:** React Hook Form
- **Validation:** Zod

## Architecture

### Component Architecture

- Functional components with React hooks
- Feature-first organization (`features/{domain}/{feature}/`); a `modules/` folder is added only when logic is reused by 2+ features
- Separation of business logic (custom hooks) from UI

### State Management

- Global state: Zustand stores
- Local state: React hooks (`useState`, `useReducer`)
- Server state: TanStack Query

### Folder Structure

```
apps/web/
├── public/                       # favicon, manifest.json, robots.txt, images/
├── env/                          # .env (git-ignored) and .env.example
├── patches/                      # patch-package patches (perfect-scrollbar under CSS zoom)
├── proxy.config.json             # dev proxy: /api/v1/apps -> backend, /cdn-assets -> icon CDN
├── components.json               # shadcn/ui configuration
├── vite.config.ts                # Vite config (PORT and BACKEND_PROXY_TARGET come from env/.env)
├── Dockerfile, docker/           # production image (nginx serves the build, proxies the API)
│
└── src/
    ├── main.tsx                  # entry: providers, QueryClient, router
    ├── routes/                   # index.tsx (router), main/app/auth routes, guards/ (AuthGuard, RoleGuard)
    ├── pages/                    # thin route components: auth/ (login, register), library/ (catalog, book, search, ask)
    ├── features/                 # domain code: auth/ and library/{books,catalog,chat,search,upload,...}
    ├── components/               # ui/ (shadcn), layouts/ (shell), wrappers/ (PerfectScrollArea)
    ├── config/                   # env.ts, query-client.ts, theme.ts, menu/ (APP_MENU, ADMINISTRATOR_MENU)
    ├── services/                 # api-client (axios), api-endpoints, book/chat/conversation/search/auth services, sse-client
    ├── stores/                   # Zustand (useAuthStore)
    ├── hooks/ utils/ types/      # cross-domain helpers
    └── styles/                   # tailwind.css, variable.css (tokens), components.css
```

> Component placement follows the decision tree in [`AGENTS.md`](../../AGENTS.md) § Web rules: shadcn/Radix primitives → `components/ui/`, app shell → `components/layouts/`, 3rd-party adapters → `components/wrappers/`, generic logic reused by 2+ features → `modules/{name}/`, domain-specific → `features/{domain}/{feature}/components/`, single-page-only → `pages/{page}/parts/`. Never place domain-specific components directly under `src/components/`.

## Scrolling

Any bounded region that needs to scroll (main column, sidebar body, drawers, panels, feeds, fixed-height lists) **must** use `PerfectScrollArea` (`src/components/wrappers/PerfectScrollArea.tsx`), a wrapper around `react-perfect-scrollbar`. Do **not** use raw `overflow-auto` / `overflow-y-scroll` / `scrollbar-thin` for these regions.

```tsx
import { PerfectScrollArea } from '@/components/wrappers/PerfectScrollArea'

<PerfectScrollArea className="flex-1 min-h-0">
  {/* scrollable content */}
</PerfectScrollArea>
```

```bash
npm install react-perfect-scrollbar
```

- Preserve the flex height chain so `PerfectScrollArea` has a bounded height to scroll within (e.g. ancestors with `flex min-h-0 flex-1`).
- Thumb/rail theming is global via design tokens in `src/styles/components.css` (`.ps__thumb-*`, `.ps__rail-*`) — do not override scrollbar colors per-component.
- `overflow-auto` is only acceptable for non-boxed, page-level scroll (e.g. `<body>`/root scroll) — not for internal panels.

## Conventions

### Naming

- Variables/Functions: `camelCase`
- Components/Interfaces: `PascalCase`
- Files: `kebab-case`

### TypeScript

- Strict typing enabled
- No `any` type allowed
- Use interfaces for component props

### Imports

- Use absolute paths: `@/components/ui/` instead of `../../components/ui/`

## API & Authentication

- JWT in HTTP-only cookies (`withCredentials`); the browser attaches them, no Authorization header is injected
- `src/services/api-client.ts` interceptors: unwrap axios' `response.data`, refresh once on 401 (`GET /auth/refresh`), normalize errors (message from `detail.metaData.message`)
- `apiRequests` (`api-factory.service.ts`) resolves to the backend envelope `ApiResponse<T>` = `{ metaData, data }` — read `res.data` for the payload and `res.metaData.pagination` for paging
- Base URL comes from `env.api.baseUrl` (default `/api/v1`); endpoints in `api-endpoints.ts` carry the `/apps` proxy segment, so `/api/v1/apps/auth/login` reaches backend `/auth/login` through the dev proxy (`proxy.config.json`)

## Development

```bash
# Install dependencies
npm install

# Start dev server
npm run dev

# Build for staging / production
npm run build:staging
npm run build:prod

# Preview production build
npm run preview

# Quality checks
npm run typecheck   # tsc --noEmit
npm run lint        # eslint src
npm test            # vitest run (jsdom); npm run test:watch for watch mode
```

## Environment Variables

Environment files live in `env/` (e.g. `env/.env`; copy `env/.env.example`). Read them only through `src/config/env.ts`.

| Key | Purpose |
|-----|---------|
| `VITE_API_BASE_URL` | Base path for backend calls (default `/api/v1`, through the dev proxy) |
| `VITE_AUTH_ENABLED` | `true` = login/register pages and the sign-in guard; use together with the backend's `BE_JWT_ACTIVE=true`. Default `false` |
| `PORT` | Dev server port (default 3000; read by `vite.config.ts` only) |
| `BACKEND_PROXY_TARGET` | Backend the dev proxy forwards to (default `http://0.0.0.0:8020`) |
| `ICON_CDN_PROXY_TARGET` | Host behind `/cdn-assets/` that serves the Phosphor icon font |

## Best Practices

1. **Read documentation first** - `AI_GUIDE.md` and `docs/api-spec.md`
2. **Separate concerns** - Keep business logic in custom hooks
3. **Type safety** - Define interfaces for all props and API responses
4. **Error handling** - Use Axios interceptors for centralized error handling
5. **Responsive design** - All components must be responsive by default
