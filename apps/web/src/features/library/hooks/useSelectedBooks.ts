import { useQueries } from '@tanstack/react-query'
import { useMemo } from 'react'

import { useIndexedBooks } from '@/features/library/hooks/useIndexedBooks'
import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import type { IBook } from '@/features/library/types/book.types'
import { bookService } from '@/services/book.service'

const NONE: IBook[] = []

/**
 * Resolves picked book ids to books, in pick order. Books on the loaded picker pages come from the cache;
 * the rest (e.g. from a shared `?bookId=` link, or past the first page) are fetched one by one.
 */
export function useSelectedBooks(selectedIds: string[], alsoLoaded: IBook[] = NONE): IBook[] {
  const { books } = useIndexedBooks()
  const loaded = useMemo(() => new Map([...(books ?? []), ...alsoLoaded].map((book) => [book.id, book])), [books, alsoLoaded])
  // Wait for the first page before fetching singles, so ids it already holds are not requested twice.
  const missing = books ? selectedIds.filter((id) => !loaded.has(id)) : []

  const fetched = useQueries({
    queries: missing.map((id) => ({
      queryKey: BOOK_KEYS.detail(id),
      queryFn: () => bookService.getOne(id).then((res) => res.data),
      staleTime: 60_000,
    })),
  })

  return useMemo(() => {
    const extra = new Map(fetched.flatMap((query) => (query.data ? [[query.data.id, query.data] as const] : [])))
    return selectedIds.flatMap((id) => {
      const book = loaded.get(id) ?? extra.get(id)
      return book ? [book] : []
    })
  }, [selectedIds, loaded, fetched])
}
