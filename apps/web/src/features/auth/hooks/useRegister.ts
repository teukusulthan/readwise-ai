import { useMutation } from '@tanstack/react-query'

import type { IRegisterPayload } from '@/features/auth/types/auth.types'
import { authService } from '@/services/auth.service'

export function useRegister() {
  return useMutation({
    mutationFn: (payload: IRegisterPayload) => authService.register(payload).then((res) => res.data),
  })
}

/** Confirms a registration with the emailed code (only when the backend verifies emails). */
export function useVerifyRegistration() {
  return useMutation({
    mutationFn: (otp: string) => authService.verifyRegistration(otp).then((res) => res.data),
  })
}
