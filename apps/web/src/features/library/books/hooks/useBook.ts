import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'

import { BUSY_STATUSES } from '@/features/library/constants/ingestion-status'
import { STATUS_POLL_INTERVAL_MS } from '@/features/library/constants/catalog'
import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import type { TIngestionStatus } from '@/features/library/types/book.types'
import { bookService } from '@/services/book.service'

/**
 * One book. Polls every 2 s while its document is queued or being indexed; when it leaves that state the
 * book lists (catalog and the chat picker's indexed-books list, both under `BOOK_KEYS.all`) are refreshed.
 */
export function useBook(id: string | undefined) {
  const queryClient = useQueryClient()
  const query = useQuery({
    queryKey: BOOK_KEYS.detail(id ?? ''),
    queryFn: () => bookService.getOne(id as string).then((res) => res.data),
    enabled: !!id,
    staleTime: 0,
    refetchInterval: (q) => (q.state.data && BUSY_STATUSES.includes(q.state.data.ingestion.status) ? STATUS_POLL_INTERVAL_MS : false),
  })

  const status = query.data?.ingestion.status
  const previous = useRef<{ id: string | undefined; status: TIngestionStatus | undefined }>({ id, status })
  useEffect(() => {
    const before = previous.current
    previous.current = { id, status }
    if (before.id === id && before.status && BUSY_STATUSES.includes(before.status) && status && !BUSY_STATUSES.includes(status)) {
      void queryClient.invalidateQueries({ queryKey: BOOK_KEYS.all })
    }
  }, [id, status, queryClient])

  return query
}
