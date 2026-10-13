# React.js Web Application Template

## Tech Stack

- **Core:** React 18+, TypeScript (strict mode, no `any`)
- **Build Tool:** Vite
- **State Management:** Zustand (UI state), TanStack Query v5 (server state — `src/config/query-client.ts`, mounted in `main.tsx`)
- **API Client:** Axios with interceptors
- **Styling:** Tailwind CSS 4
- **UI Components:** shadcn/ui (Radix-based)
- **Data Tables:** React Table (@tanstack/react-table)
- **Data Visualization:** Apache ECharts, Recharts
- **Maps:** Mapbox GL JS
- **Form Handling:** React Hook Form
- **Validation:** Zod

## Architecture

### Component Architecture

- Functional components with React hooks
- Feature-first organization (`features/{domain}/{feature}/`) with shared, reusable logic in `modules/`
- Separation of business logic (custom hooks) from UI

### State Management

- Global state: Zustand stores
- Local state: React hooks (`useState`, `useReducer`)
- Server state: React Query (if needed)

### Folder Structure (Scaffolding)

```
web-reactjs/
├── public/                       # STATIC ASSETS (Directly copied to dist)
│   ├── favicon.ico
│   ├── manifest.json             # PWA: Manifest for app identity
│   ├── robots.txt
│   ├── sw.js                     # Service Worker (If manual)
│   └── images/                   # Static images (Logo, Avatar, Thumbnails)
│
├── env/                           # Environment files (.env per stage)
├── .eslintrc.json                 # Code Quality: Linter
├── .gitignore                     # Git ignore rules
├── .nvmrc                         # Node Version Manager config
├── .prettierrc.json               # Code Style: Formatter
├── components.json                # shadcn/ui configuration
├── design-tokens.json             # Design System: Tokens from Figma
├── globals.css                    # Global CSS legacy / utilities
├── index.html                     # HTML Entry point (Vite entry)
├── package.json                   # Dependencies & Scripts (Vite, PWA, etc)
├── postcss.config.js              # CSS Processing: Tailwind 4 & PostCSS
├── proxy.config.json              # Dev server proxy configuration
├── README.md                      # Project documentation
├── vite.config.ts                 # Build Tool: Vite configuration
├── tsconfig.json                  # TypeScript: Config & Path Alias (@/*)
│
└── src/
    ├── main.tsx                   # Entry Point: Client Root & PWA Register
    ├── index.css                  # CSS Entry: Combines all styles
    ├── App.tsx                    # Root Component (Legacy/Reference)
    ├── vite-env.d.ts               # Vite client type references
    ├── pwa-register.js            # Logic: Service Worker registration
    ├── report-web-vitals.js       # Performance monitoring
    ├── setup-tests.js             # Test environment setup
    │
    ├── routes/                    # ROUTING ENGINE
    │   ├── index.tsx              # Master Router & RouterProvider
    │   ├── main.routes.tsx        # Config: /dashboard, /topic
    │   ├── admin.routes.tsx       # Config: /administrator
    │   ├── auth.routes.tsx        # Config: /auth
    │   └── guards/                 # ROUTE PROTECTION
    │       ├── AuthGuard.tsx      # Protected route check
    │       └── RoleGuard.tsx      # RBAC (Role Based Access Control)
    │
    ├── components/                # SHELL, PRIMITIVES & ADAPTERS ONLY
    │   ├── ui/                    # Shadcn/UI primitives (Button, Card, Dialog, ...)
    │   ├── layouts/               # App shell: AppLayout, AppHeader, AppSidebar, AppFooter, TopLayout, BlankLayout
    │   └── wrappers/               # 3rd-party adapters: PerfectScrollArea, MapboxProvider, EchartsWrapper
    │
    ├── modules/                   # GENERIC, DOMAIN-AGNOSTIC, REUSED BY 2+ FEATURES
    │   ├── data-display/          # generic list/table rendering (components/hooks/store)
    │   ├── dynamic-filter/        # generic filter builder (components/hooks/store/types/utils)
    │   └── dynamic-widget/        # generic widget rendering
    │
    ├── features/                  # DOMAIN-SPECIFIC MODULES (feature-first)
    │   └── {domain}/{feature}/    # components, hooks, etc. scoped to one business domain
    │
    ├── config/                    # APP CONFIGURATION
    │   ├── index.ts               # Config aggregator / env exports
    │   └── menu/                   # Source of truth for sidebar/header nav
    │       ├── app.menu.ts        # APP_MENU entries
    │       ├── administrator.menu.ts # ADMINISTRATOR_MENU entries
    │       └── index.ts
    │
    ├── hooks/                     # Custom React Hooks (Re-usable)
    │   ├── use-mobile.tsx
    │   └── use-toast.ts
    │
    ├── styles/                    # GLOBAL THEME & TAILWIND 4
    │   ├── tailwind.css           # @theme Tailwind 4 (Custom colors, fonts)
    │   ├── variable.css           # CSS Variables (:root design tokens)
    │   └── components.css         # Custom CSS classes / UI overrides (incl. scrollbar theming)
    │
    ├── stores/                    # State Management (Zustand)
    │   ├── useAuthStore.ts
    │   └── useThemeStore.ts
    │
    ├── services/                  # API LAYER (Axios/Fetcher)
    │   ├── api-client.ts          # Axios Instance & Interceptors
    │   ├── api-endpoints.ts       # Centralized endpoint constants
    │   ├── api-factory.service.ts        # Generic REST factory
    │   ├── api-factory-crud.service.ts   # Generic CRUD factory
    │   ├── auth.service.ts
    │   └── report.service.ts
    │
    ├── types/                     # TypeScript Definitions
    │   ├── api.d.ts               # Interface API Response/Request
    │   ├── models.d.ts            # Interface Entity (User, Project)
    │   ├── menu.d.ts              # Type for menu config entries
    │   ├── theme.d.ts             # Type for custom theme/config
    │   └── global.d.ts            # Ambient/global types
    │
    ├── utils/                     # Utility Functions (Pure Functions)
    │   ├── cn.ts                  # Tailwind Merge & Clsx helper
    │   ├── date-formatter.ts
    │   └── icon-renderer.tsx      # Dynamic icon rendering helper
    │
    └── pages/                     # ROUTE COMPONENTS (Page-based)
        ├── dashboard/
        │   └── DashboardPage.tsx
        └── auth/
            └── LoginPage.tsx
```

> Component placement follows the decision tree in [`AGENTS.md`](../../AGENTS.md) § Web rules: shadcn/Radix primitives → `components/ui/`, app shell → `components/layouts/`, 3rd-party adapters → `components/wrappers/`, generic logic reused by 2+ features → `modules/{name}/`, domain-specific → `features/{domain}/{feature}/components/`, single-page-only → `pages/{page}/parts/`. Never place domain-specific components directly under `src/components/`.

## Component Wrappers

This template uses **High-Level Component Wrapper** architecture:

| Use Case       | Component                         | Documentation                          |
| -------------- | ---------------------------------- | --------------------------------------- |
| Authentication | `<AuthComponent>`                 | `@/docs/web-component-auth.md`         |
| Admin Layout   | `<AppLayout>`, `<AdminComponent>` | `@/docs/web-component-admin-layout.md` |
| Data Display   | `<DataList>`                      | `@/docs/web-component-data-crud.md`    |
| Data Forms     | `<DataForm>`                      | `@/docs/web-component-data-crud.md`    |

**⚠️ DO NOT** build UI components (tables, forms, pagination, modals) from scratch using raw HTML tags.

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

## Maps (Mapbox GL JS)

- Access tokens stored in environment variables
- Component: `mapbox-gl` with TypeScript definitions

```bash
npm install mapbox-gl @types/mapbox-gl
```

## Data Visualization (ECharts)

- Responsive charts themed with shadcn/ui colors
- Package: `echarts` with React wrapper

```bash
npm install echarts echarts-for-react
```

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

```env
VITE_API_BASE_URL=/api/v1
VITE_MAPBOX_TOKEN=your_mapbox_access_token
```

## Best Practices

1. **Read documentation first** - Check `@/docs/` for component contracts
2. **Separate concerns** - Keep business logic in custom hooks
3. **Type safety** - Define interfaces for all props and API responses
4. **Error handling** - Use Axios interceptors for centralized error handling
5. **Responsive design** - All components must be responsive by default
