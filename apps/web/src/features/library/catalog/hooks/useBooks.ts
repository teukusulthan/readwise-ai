import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { BUSY_STATUSES } from '@/features/library/constants/ingestion-status'
import { CATALOG_POLL_INTERVAL_MS } from '@/features/library/constants/catalog'
import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import type { IBookListParams } from '@/features/library/types/book.types'
import { bookService } from '@/services/book.service'

/** Paginated catalog list. Returns the envelope so callers can read `metaData.pagination`. Polls every 5 s while a book on the page is queued or indexing. */
export function useBooks(params: IBookListParams) {
  return useQuery({
    queryKey: BOOK_KEYS.list(params),
    queryFn: () => bookService.getAll(params),
    placeholderData: keepPreviousData,
    refetchInterval: (query) =>
      query.state.data?.data?.some((book) => BUSY_STATUSES.includes(book.ingestion.status)) ? CATALOG_POLL_INTERVAL_MS : false,
  })
}
