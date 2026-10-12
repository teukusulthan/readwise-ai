import type { User } from '@/types/models'
import { apiRequests } from './api-factory.service'
import { API_ENDPOINTS } from './api-endpoints'

// Payload shapes mirror apps/backend/dto/auth.py
export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  fullname?: string
  username: string
  email: string
  password: string
  phone: string
}

export interface ForgotPasswordPayload {
  email: string
}

export interface ChangePasswordPayload {
  otp: string
  newPassword: string
}

export const authService = {
  login: (data: LoginPayload) => apiRequests.post<User, LoginPayload>(API_ENDPOINTS.AUTH.LOGIN, data),

  logout: () => apiRequests.delete<null>(API_ENDPOINTS.AUTH.LOGOUT),

  register: (data: RegisterPayload) => apiRequests.post<User, RegisterPayload>(API_ENDPOINTS.AUTH.REGISTER, data),

  validate: () => apiRequests.get<User>(API_ENDPOINTS.AUTH.VALIDATE, { full_response: true }),

  forgotPassword: (data: ForgotPasswordPayload) =>
    apiRequests.post<null, ForgotPasswordPayload>(API_ENDPOINTS.AUTH.FORGOT_PASSWORD_REQUEST, data),

  changePassword: (data: ChangePasswordPayload) =>
    apiRequests.post<null, ChangePasswordPayload>(API_ENDPOINTS.AUTH.FORGOT_PASSWORD_CHANGE, data),
}
