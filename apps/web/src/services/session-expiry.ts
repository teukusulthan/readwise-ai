import env from '@/config/env'
import { queryClient } from '@/config/query-client'
import { useAuthStore } from '@/stores/useAuthStore'
import { isAuthPage, loginPathFor } from '@/utils/auth-redirect'

/**
 * The session is gone (a 401 that a refresh could not fix): forget the user and their cached data, then go to
 * `/login?next=<current page>`. Only with VITE_AUTH_ENABLED — without accounts there is no login page to go to.
 */
export function handleSessionExpired(): void {
  if (!env.auth.enabled) return
  useAuthStore.getState().clearAuth()
  queryClient.clear()
  const { pathname, search, hash } = window.location
  if (isAuthPage(pathname)) return
  window.location.assign(loginPathFor(`${pathname}${search}${hash}`))
}
