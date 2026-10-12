import { useQuery } from '@tanstack/react-query'

import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import type { IBookListParams } from '@/features/library/types/book.types'
import { bookService } from '@/services/book.service'

const INDEXED_PARAMS: IBookListParams = { status: ['indexed'], page: 1, size: 100, orderBy: 'title', order: 'asc' }

/** Books that can answer questions (ingestion status `indexed`). */
export function useIndexedBooks() {
  return useQuery({
    queryKey: BOOK_KEYS.list(INDEXED_PARAMS),
    queryFn: () => bookService.getAll(INDEXED_PARAMS).then((res) => res.data),
  })
}
