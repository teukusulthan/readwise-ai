import { useMutation } from '@tanstack/react-query'

import type { IRegisterPayload, IVerifyRegistrationPayload } from '@/features/auth/types/auth.types'
import { authService } from '@/services/auth.service'

export function useRegister() {
  return useMutation({
    mutationFn: (payload: IRegisterPayload) => authService.register(payload).then((res) => res.data),
  })
}

/** Confirms a registration with the emailed code (only when the backend verifies emails). */
export function useVerifyRegistration() {
  return useMutation({
    mutationFn: (payload: IVerifyRegistrationPayload) => authService.verifyRegistration(payload).then((res) => res.data),
  })
}
