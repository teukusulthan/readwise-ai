import { useQuery } from '@tanstack/react-query'

import { BUSY_STATUSES } from '@/features/library/constants/ingestion-status'
import { STATUS_POLL_INTERVAL_MS } from '@/features/library/constants/catalog'
import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import { bookService } from '@/services/book.service'

/** One book. Polls every 2 s while its document is queued or being indexed. */
export function useBook(id: string | undefined) {
  return useQuery({
    queryKey: BOOK_KEYS.detail(id ?? ''),
    queryFn: () => bookService.getOne(id as string).then((res) => res.data),
    enabled: !!id,
    staleTime: 0,
    refetchInterval: (query) => (query.state.data && BUSY_STATUSES.includes(query.state.data.ingestion.status) ? STATUS_POLL_INTERVAL_MS : false),
  })
}
