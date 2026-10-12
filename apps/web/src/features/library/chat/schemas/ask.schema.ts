import { z } from 'zod'

export const askSchema = z.object({
  question: z.string().trim().min(3, 'Ask a question of at least 3 characters').max(2000, 'Questions are limited to 2000 characters'),
})

export type TAskFormValues = z.infer<typeof askSchema>
