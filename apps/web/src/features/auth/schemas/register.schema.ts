import { z } from 'zod'

import type { IRegisterPayload } from '@/features/auth/types/auth.types'

// Mirrors apps/backend/dto/auth.py (the backend also refuses the most common passwords).
export const PASSWORD_MIN_LENGTH = 8
/** bcrypt reads only the first 72 bytes of a password; the backend refuses longer ones. */
export const PASSWORD_MAX_BYTES = 72

const byteLength = (value: string) => new TextEncoder().encode(value).length

export const registerSchema = z
  .object({
    fullname: z.string().trim().max(120, 'Name must be 120 characters or fewer'),
    username: z
      .string()
      .trim()
      .min(3, 'Use at least 3 characters')
      .max(40, 'Use 40 characters or fewer')
      .regex(/^[A-Za-z0-9._-]+$/, 'Letters, digits, dots, dashes and underscores only')
      // Usernames, emails and phone numbers all sign in, so a username must not look like a phone number.
      .regex(/[A-Za-z]/, 'Include at least one letter'),
    email: z.string().trim().max(254, 'Use 254 characters or fewer').email('Enter a valid email address'),
    // Required by the backend (accounts are keyed by email + phone) and must be unique.
    phone: z
      .string()
      .trim()
      .regex(/^\+?[0-9][0-9\s()-]{5,19}$/, 'Enter a phone number like +62 812 3456 7890'),
    password: z
      .string()
      .min(PASSWORD_MIN_LENGTH, `Use at least ${PASSWORD_MIN_LENGTH} characters`)
      .refine((value) => byteLength(value) <= PASSWORD_MAX_BYTES, 'Use a shorter password (at most 72 bytes)'),
    confirmPassword: z.string(),
  })
  .refine((values) => values.password === values.confirmPassword, {
    path: ['confirmPassword'],
    message: 'Passwords do not match',
  })
  .refine(
    (values) => {
      const password = values.password.toLowerCase()
      const email = values.email.trim().toLowerCase()
      return ![values.username.trim().toLowerCase(), email, email.split('@')[0]].includes(password)
    },
    { path: ['password'], message: 'Do not use your username or email as the password' },
  )

export type TRegisterFormValues = z.infer<typeof registerSchema>

export function toRegisterPayload(values: TRegisterFormValues): IRegisterPayload {
  return {
    fullname: values.fullname.trim() || undefined,
    username: values.username.trim(),
    email: values.email.trim().toLowerCase(),
    phone: values.phone.trim(),
    password: values.password,
  }
}

export const verifyCodeSchema = z.object({
  otp: z
    .string()
    .trim()
    .regex(/^\d{6}$/, 'Enter the 6-digit code from the email'),
})

export type TVerifyCodeFormValues = z.infer<typeof verifyCodeSchema>
