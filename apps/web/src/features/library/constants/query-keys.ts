import type { IBookListParams } from '@/features/library/types/book.types'

/** TanStack Query keys for the library domain. Invalidate `BOOK_KEYS.all` after any book mutation. */
export const BOOK_KEYS = {
  all: ['books'] as const,
  list: (params: IBookListParams) => ['books', params] as const,
  /** Paged, indexed-only picker list (under `all`, so book mutations invalidate it). */
  picker: (search: string) => ['books', 'picker', search] as const,
  detail: (id: string) => ['book', id] as const,
  lookup: (query: string) => ['book-lookup', query] as const,
}

/** Saved chat conversations. Invalidate `CONVERSATION_KEYS.all` after a turn, rename or delete. */
export const CONVERSATION_KEYS = {
  all: ['conversations'] as const,
  list: ['conversations', 'list'] as const,
  detail: (id: string) => ['conversations', 'detail', id] as const,
  /** Is an answer of this conversation still being generated (GET /chat/active)? */
  active: (id: string) => ['conversations', 'active', id] as const,
}

/** Semantic passage searches (POST /search/query), keyed by the URL's query and book scope. */
export const SEARCH_KEYS = {
  results: (query: string, bookIds: string[]) => ['search', query, bookIds] as const,
}
