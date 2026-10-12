import { keepPreviousData, useInfiniteQuery } from '@tanstack/react-query'
import { useMemo } from 'react'

import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import type { IBook } from '@/features/library/types/book.types'
import { bookService } from '@/services/book.service'

/** Books per page of the picker; "Load more" fetches the next page. */
export const PICKER_PAGE_SIZE = 50

/**
 * Books that can answer questions (ingestion status `indexed`), filtered server-side by `search`
 * and loaded page by page. `total` is the backend's count for this search.
 */
export function useIndexedBooks(search = '') {
  const term = search.trim()
  const query = useInfiniteQuery({
    queryKey: BOOK_KEYS.picker(term),
    initialPageParam: 1,
    placeholderData: keepPreviousData,
    queryFn: ({ pageParam }) =>
      bookService.getAll({ search: term || undefined, status: ['indexed'], page: pageParam, size: PICKER_PAGE_SIZE, orderBy: 'title', order: 'asc' }),
    getNextPageParam: (last, pages) => {
      const total = last.metaData?.pagination?.totalElements
      const loaded = pages.reduce((sum, page) => sum + page.data.length, 0)
      const hasMore = total === undefined ? last.data.length === PICKER_PAGE_SIZE : loaded < total
      return hasMore && last.data.length > 0 ? pages.length + 1 : undefined
    },
  })

  const pages = query.data?.pages
  const books = useMemo<IBook[] | undefined>(() => {
    if (!pages) return undefined
    // Pages are fetched at different times, so a book can shift across a page boundary; keep each once.
    const seen = new Set<string>()
    return pages.flatMap((page) => page.data).filter((book) => !seen.has(book.id) && !!seen.add(book.id))
  }, [pages])
  const total = pages?.at(-1)?.metaData?.pagination?.totalElements ?? books?.length

  return { ...query, books, total }
}
