import { useQuery } from '@tanstack/react-query'

import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import { bookService } from '@/services/book.service'

/** Open Library candidates for the import dialog. Runs only for queries of 2+ characters. */
export function useBookLookup(query: string) {
  const trimmed = query.trim()
  return useQuery({
    queryKey: BOOK_KEYS.lookup(trimmed),
    queryFn: () => bookService.lookup(trimmed).then((res) => res.data),
    enabled: trimmed.length >= 2,
    staleTime: 1000 * 60 * 10,
  })
}
