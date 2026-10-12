import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import type { IBookListParams } from '@/features/library/types/book.types'
import { bookService } from '@/services/book.service'

/** Paginated catalog list. Returns the envelope so callers can read `metaData.pagination`. */
export function useBooks(params: IBookListParams) {
  return useQuery({
    queryKey: BOOK_KEYS.list(params),
    queryFn: () => bookService.getAll(params),
    placeholderData: keepPreviousData,
  })
}
