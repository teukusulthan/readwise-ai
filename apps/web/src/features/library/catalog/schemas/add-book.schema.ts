import { z } from 'zod'

const currentYear = new Date().getFullYear()

export const addBookSchema = z.object({
  title: z.string().trim().min(1, 'Title is required').max(500, 'Title must be 500 characters or fewer'),
  authors: z.string().max(1000, 'Too many authors'),
  isbn: z
    .string()
    .trim()
    .regex(/^$|^[0-9Xx\-\s]{10,17}$/, 'ISBN must be 10 or 13 digits (hyphens allowed)'),
  publishedYear: z
    .string()
    .trim()
    .regex(/^$|^\d{1,4}$/, 'Enter a year like 1965')
    .refine((value) => !value || Number(value) <= currentYear + 1, 'Year is in the future'),
  description: z.string().max(20000, 'Description is too long'),
})

export type TAddBookFormValues = z.infer<typeof addBookSchema>
