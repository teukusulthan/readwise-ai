import { z } from 'zod'

import { addBookSchema } from '@/features/library/catalog/schemas/add-book.schema'
import type { IBook, IBookUpdatePayload } from '@/features/library/types/book.types'

/** Edit form = the add-book fields plus publisher, language, subjects and cover URL. */
export const editBookSchema = addBookSchema.extend({
  publisher: z.string().max(500, 'Publisher must be 500 characters or fewer'),
  language: z.string().max(50, 'Language must be 50 characters or fewer'),
  subjects: z.string().max(5000, 'Too many subjects'),
  coverUrl: z
    .string()
    .trim()
    .max(2000, 'Cover URL is too long')
    .regex(/^$|^https?:\/\//i, 'Cover URL must start with http:// or https://'),
})

export type TEditBookFormValues = z.infer<typeof editBookSchema>

const splitList = (value: string): string[] =>
  value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)

export function bookToFormValues(book: IBook): TEditBookFormValues {
  return {
    title: book.title,
    authors: book.authors.join(', '),
    isbn: book.isbn ?? '',
    publishedYear: book.publishedYear != null ? String(book.publishedYear) : '',
    description: book.description ?? '',
    publisher: book.publisher ?? '',
    language: book.language ?? '',
    subjects: book.subjects.join(', '),
    coverUrl: book.coverUrl ?? '',
  }
}

/** Build the PUT /book/update body. Empty optional fields are omitted so the server clears them. */
export function formValuesToPayload(id: string, values: TEditBookFormValues): IBookUpdatePayload {
  return {
    id,
    title: values.title.trim(),
    authors: splitList(values.authors),
    isbn: values.isbn.trim() || undefined,
    publishedYear: values.publishedYear ? Number(values.publishedYear) : undefined,
    description: values.description.trim() || undefined,
    publisher: values.publisher.trim() || undefined,
    language: values.language.trim() || undefined,
    subjects: splitList(values.subjects),
    coverUrl: values.coverUrl.trim() || undefined,
  }
}
