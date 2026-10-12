/**
 * Typed env accessor — the only place that reads `import.meta.env`.
 * Keys live in `env/.env*` and must use the `VITE_` prefix.
 */

// Matches the `/api/v1/apps` dev proxy in proxy.config.json (endpoints add the `/apps` segment).
const DEFAULT_API_BASE_URL = '/api/v1'

const env = {
  api: {
    baseUrl: import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL,
  },
  map: {
    mapboxToken: import.meta.env.VITE_MAPBOX_TOKEN ?? '',
  },
  app: {
    mode: import.meta.env.MODE ?? 'development',
  },
} as const

export default env
