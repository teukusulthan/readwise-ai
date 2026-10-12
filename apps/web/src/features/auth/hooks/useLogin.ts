import { useMutation, useQueryClient } from '@tanstack/react-query'

import type { ILoginPayload } from '@/features/auth/types/auth.types'
import { authService } from '@/services/auth.service'
import { useAuthStore } from '@/stores/useAuthStore'

/** Sign in: the backend sets the HttpOnly cookies, the store keeps the user. Errors are shown inline by the form. */
export function useLogin() {
  const queryClient = useQueryClient()
  const setAuth = useAuthStore((state) => state.setAuth)
  return useMutation({
    mutationFn: (payload: ILoginPayload) => authService.login(payload).then((res) => res.data),
    onSuccess: ({ user }) => {
      // Conversations are per user: never show data cached for someone else.
      queryClient.clear()
      setAuth(user)
    },
  })
}
