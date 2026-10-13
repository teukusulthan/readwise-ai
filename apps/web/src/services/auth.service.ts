import type {
  ILoginPayload,
  ILoginResult,
  IRegisterPayload,
  IRegisterResult,
  IVerifyRegistrationPayload,
} from '@/features/auth/types/auth.types'
import type { User } from '@/types/models'
import { apiRequests } from './api-factory.service'
import { API_ENDPOINTS } from './api-endpoints'

// Payload shapes mirror apps/backend/dto/auth.py
export type LoginPayload = ILoginPayload
export type RegisterPayload = IRegisterPayload

export interface ForgotPasswordPayload {
  email: string
}

/** The reset code is only valid together with the email it was sent to. */
export interface ChangePasswordPayload {
  email: string
  otp: string
  newPassword: string
}

export const authService = {
  /** Sets the HttpOnly `token` / `refresh_token` cookies; the body carries only the user. */
  login: (data: LoginPayload) => apiRequests.post<ILoginResult, LoginPayload>(API_ENDPOINTS.AUTH.LOGIN, data),

  logout: () => apiRequests.delete<null>(API_ENDPOINTS.AUTH.LOGOUT),

  register: (data: RegisterPayload) => apiRequests.post<IRegisterResult, RegisterPayload>(API_ENDPOINTS.AUTH.REGISTER, data),

  /** In the JSON body (not the query string, which ends up in access logs). */
  verifyRegistration: (data: IVerifyRegistrationPayload) =>
    apiRequests.post<{ message: string }, IVerifyRegistrationPayload>(API_ENDPOINTS.AUTH.VERIFICATION, data),

  validate: () => apiRequests.get<User>(API_ENDPOINTS.AUTH.VALIDATE, { full_response: true }),

  /** 200 when the browser sends the refresh cookie back (i.e. the session cookies were stored). */
  checkSession: () => apiRequests.get<{ status: string }>(API_ENDPOINTS.AUTH.VALIDATE),

  forgotPassword: (data: ForgotPasswordPayload) =>
    apiRequests.post<null, ForgotPasswordPayload>(API_ENDPOINTS.AUTH.FORGOT_PASSWORD_REQUEST, data),

  changePassword: (data: ChangePasswordPayload) =>
    apiRequests.post<null, ChangePasswordPayload>(API_ENDPOINTS.AUTH.FORGOT_PASSWORD_CHANGE, data),
}
