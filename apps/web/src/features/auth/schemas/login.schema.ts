import { z } from 'zod'

/** The backend matches `email` against the email, the username or the phone number. */
export const loginSchema = z.object({
  email: z.string().trim().min(1, 'Enter your email or username'),
  password: z.string().min(1, 'Enter your password'),
})

export type TLoginFormValues = z.infer<typeof loginSchema>
