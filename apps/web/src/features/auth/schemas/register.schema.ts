import { z } from 'zod'

import type { IRegisterPayload } from '@/features/auth/types/auth.types'

export const registerSchema = z
  .object({
    fullname: z.string().trim().max(120, 'Name must be 120 characters or fewer'),
    username: z
      .string()
      .trim()
      .min(3, 'Use at least 3 characters')
      .max(40, 'Use 40 characters or fewer')
      .regex(/^[A-Za-z0-9._-]+$/, 'Letters, digits, dots, dashes and underscores only'),
    email: z.string().trim().email('Enter a valid email address'),
    // Required by the backend (accounts are keyed by email + phone) and must be unique.
    phone: z
      .string()
      .trim()
      .regex(/^\+?[0-9][0-9\s()-]{5,19}$/, 'Enter a phone number like +62 812 3456 7890'),
    password: z.string().min(8, 'Use at least 8 characters').max(128, 'Use 128 characters or fewer'),
    confirmPassword: z.string(),
  })
  .refine((values) => values.password === values.confirmPassword, {
    path: ['confirmPassword'],
    message: 'Passwords do not match',
  })

export type TRegisterFormValues = z.infer<typeof registerSchema>

export function toRegisterPayload(values: TRegisterFormValues): IRegisterPayload {
  return {
    fullname: values.fullname.trim() || undefined,
    username: values.username.trim(),
    email: values.email.trim(),
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
