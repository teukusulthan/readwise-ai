import { useMutation, useQueryClient } from '@tanstack/react-query'

import type { ILoginPayload } from '@/features/auth/types/auth.types'
import { ApiError } from '@/services/api-error'
import { authService } from '@/services/auth.service'
import { useAuthStore } from '@/stores/useAuthStore'

export const COOKIE_REJECTED_MESSAGE =
  'Signed in, but the browser rejected the session cookie. Use HTTPS, or set BE_AUTH_COOKIE_SECURE=false for local development.'

/**
 * The login response sets HttpOnly cookies the page cannot read, so ask the backend whether they came back.
 * A 401 means the browser dropped them (typically `Secure` cookies over plain HTTP from a LAN address): say so
 * instead of letting the next request bounce the user back to the login page.
 */
async function ensureSessionCookie(): Promise<void> {
  try {
    await authService.checkSession()
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) throw new Error(COOKIE_REJECTED_MESSAGE)
    // Anything else (e.g. the backend runs without JWT) does not prove the cookie is missing.
  }
}

/** Sign in: the backend sets the HttpOnly cookies, the store keeps the user. Errors are shown inline by the form. */
export function useLogin() {
  const queryClient = useQueryClient()
  const setAuth = useAuthStore((state) => state.setAuth)
  return useMutation({
    mutationFn: async (payload: ILoginPayload) => {
      const result = (await authService.login(payload)).data
      await ensureSessionCookie()
      return result
    },
    onSuccess: ({ user }) => {
      // Conversations are per user: never show data cached for someone else.
      queryClient.clear()
      setAuth(user)
    },
  })
}
