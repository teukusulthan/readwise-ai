/**
 * API Endpoint Constants
 * Centralized paths for all backend services.
 *
 * Paths are relative to `env.api.baseUrl` (default `/api/v1`). The `/apps` segment is
 * the dev-proxy prefix that proxy.config.json strips before forwarding to the backend,
 * e.g. `/api/v1/apps/auth/login` -> backend `/auth/login`.
 */
const SUFFIX_BASE = '/apps'

export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: `${SUFFIX_BASE}/auth/login`,
    LOGOUT: `${SUFFIX_BASE}/auth/logout`,
    REGISTER: `${SUFFIX_BASE}/auth/register`,
    REFRESH: `${SUFFIX_BASE}/auth/refresh`,
    VALIDATE: `${SUFFIX_BASE}/auth/validate`,
    FORGOT_PASSWORD_REQUEST: `${SUFFIX_BASE}/auth/forgot-password/request`,
    FORGOT_PASSWORD_VERIFY: `${SUFFIX_BASE}/auth/forgot-password/verify`,
    FORGOT_PASSWORD_CHANGE: `${SUFFIX_BASE}/auth/forgot-password/change`,
  },
  USER: {
    BASE: `${SUFFIX_BASE}/user`,
  },
  BOOK: {
    GET_ALL: `${SUFFIX_BASE}/book/get-all`,
    GET_ONE: `${SUFFIX_BASE}/book/get-one`,
    ADD: `${SUFFIX_BASE}/book/add`,
    UPDATE: `${SUFFIX_BASE}/book/update`,
    DELETE: `${SUFFIX_BASE}/book/delete`,
    UPLOAD: `${SUFFIX_BASE}/book/upload`,
    REINDEX: `${SUFFIX_BASE}/book/reindex`,
    LOOKUP: `${SUFFIX_BASE}/book/lookup`,
    IMPORT: `${SUFFIX_BASE}/book/import`,
  },
  SEARCH: {
    QUERY: `${SUFFIX_BASE}/search/query`,
  },
  CHAT: {
    ASK: `${SUFFIX_BASE}/chat/ask`,
    STREAM: `${SUFFIX_BASE}/chat/stream`,
    /** + `/{sessionId}?after=<eventId>` to resume, + `/{sessionId}/cancel` to stop */
    SESSION: (sessionId: string) => `${SUFFIX_BASE}/chat/stream/${encodeURIComponent(sessionId)}`,
    ACTIVE: `${SUFFIX_BASE}/chat/active`,
  },
  CONVERSATION: {
    GET_ALL: `${SUFFIX_BASE}/conversation/get-all`,
    GET_ONE: `${SUFFIX_BASE}/conversation/get-one`,
    RENAME: `${SUFFIX_BASE}/conversation/rename`,
    DELETE: `${SUFFIX_BASE}/conversation/delete`,
  },
} as const

export type ApiEndpoints = typeof API_ENDPOINTS
