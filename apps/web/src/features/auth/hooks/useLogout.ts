import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'

import { authService } from '@/services/auth.service'
import { useAuthStore } from '@/stores/useAuthStore'
import { LOGIN_PATH } from '@/utils/auth-redirect'

/** Sign out: the backend clears the cookies; locally the user and every cached query are dropped either way. */
export function useLogout() {
  const queryClient = useQueryClient()
  const clearAuth = useAuthStore((state) => state.clearAuth)
  const navigate = useNavigate()
  return useMutation({
    mutationFn: () => authService.logout(),
    onSettled: () => {
      clearAuth()
      queryClient.clear()
      navigate(LOGIN_PATH, { replace: true })
    },
  })
}
