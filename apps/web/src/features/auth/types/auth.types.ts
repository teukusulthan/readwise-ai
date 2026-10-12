import type { User } from '@/types/models'

/** POST /auth/login body (apps/backend/dto/auth.py AuthDTO): `email` also accepts the username or phone. */
export interface ILoginPayload {
  email: string
  password: string
}

/** POST /auth/login data. The tokens are not in the body: the backend sets HttpOnly cookies. */
export interface ILoginResult {
  user: User
}

/** POST /auth/register body (RegisterDTO). */
export interface IRegisterPayload {
  fullname?: string
  username: string
  email: string
  password: string
  phone: string
}

/**
 * POST /auth/register data. `verificationRequired: true` = an OTP was mailed, confirm with
 * POST /auth/verification; `false` = the account exists already (BE_AUTH_EMAIL_VERIFICATION=false).
 */
export interface IRegisterResult {
  message: string
  verificationRequired: boolean
  id?: string
}
