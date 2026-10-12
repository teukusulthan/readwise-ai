import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'

import { BUSY_STATUSES } from '@/features/library/constants/ingestion-status'
import { CATALOG_POLL_INTERVAL_MS } from '@/features/library/constants/catalog'
import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import type { IBookListParams } from '@/features/library/types/book.types'
import { bookService } from '@/services/book.service'

/**
 * Paginated catalog list. Returns the envelope so callers can read `metaData.pagination`.
 * Polls every 5 s while a book on the page is queued or indexing; when one of them finishes, the other
 * book lists (notably the chat picker's indexed books) are invalidated too.
 */
export function useBooks(params: IBookListParams) {
  const queryClient = useQueryClient()
  const queryKey = BOOK_KEYS.list(params)
  const query = useQuery({
    queryKey,
    queryFn: () => bookService.getAll(params),
    placeholderData: keepPreviousData,
    refetchInterval: (q) =>
      q.state.data?.data?.some((book) => BUSY_STATUSES.includes(book.ingestion.status)) ? CATALOG_POLL_INTERVAL_MS : false,
  })

  const books = query.data?.data
  const busyIds = useRef<Set<string>>(new Set())
  useEffect(() => {
    if (!books) return
    const finished = books.some((book) => busyIds.current.has(book.id) && !BUSY_STATUSES.includes(book.ingestion.status))
    busyIds.current = new Set(books.filter((book) => BUSY_STATUSES.includes(book.ingestion.status)).map((book) => book.id))
    if (finished) {
      // Skip this query itself: it already holds the fresh page, so refetching it would only add a request.
      const own = JSON.stringify(queryKey)
      void queryClient.invalidateQueries({ queryKey: BOOK_KEYS.all, predicate: (q) => JSON.stringify(q.queryKey) !== own })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- queryKey is derived from params, which the data already reflects
  }, [books, queryClient])

  return query
}
