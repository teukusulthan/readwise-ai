import type { ILoginPayload, ILoginResult, IRegisterPayload, IRegisterResult } from '@/features/auth/types/auth.types'
import type { User } from '@/types/models'
import { apiRequests } from './api-factory.service'
import { API_ENDPOINTS } from './api-endpoints'
import apiClient from './api-client'
import type { ApiResponse } from '@/types/api'

// Payload shapes mirror apps/backend/dto/auth.py
export type LoginPayload = ILoginPayload
export type RegisterPayload = IRegisterPayload

export interface ForgotPasswordPayload {
  email: string
}

export interface ChangePasswordPayload {
  otp: string
  newPassword: string
}

export const authService = {
  /** Sets the HttpOnly `token` / `refresh_token` cookies; the body carries only the user. */
  login: (data: LoginPayload) => apiRequests.post<ILoginResult, LoginPayload>(API_ENDPOINTS.AUTH.LOGIN, data),

  logout: () => apiRequests.delete<null>(API_ENDPOINTS.AUTH.LOGOUT),

  register: (data: RegisterPayload) => apiRequests.post<IRegisterResult, RegisterPayload>(API_ENDPOINTS.AUTH.REGISTER, data),

  /** The backend reads the code from the query string, not the body. */
  verifyRegistration: (otp: string) =>
    apiClient.post<ApiResponse<unknown>, ApiResponse<unknown>>(API_ENDPOINTS.AUTH.VERIFICATION, null, { params: { otp } }),

  validate: () => apiRequests.get<User>(API_ENDPOINTS.AUTH.VALIDATE, { full_response: true }),

  forgotPassword: (data: ForgotPasswordPayload) =>
    apiRequests.post<null, ForgotPasswordPayload>(API_ENDPOINTS.AUTH.FORGOT_PASSWORD_REQUEST, data),

  changePassword: (data: ChangePasswordPayload) =>
    apiRequests.post<null, ChangePasswordPayload>(API_ENDPOINTS.AUTH.FORGOT_PASSWORD_CHANGE, data),
}
