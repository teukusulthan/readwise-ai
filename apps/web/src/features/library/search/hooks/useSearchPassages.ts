import { useQuery } from '@tanstack/react-query'

import { SEARCH_KEYS } from '@/features/library/constants/query-keys'
import { searchService } from '@/services/search.service'

/** Ranked passages for `query`, optionally limited to `bookIds`. Idle while the query is empty. */
export function useSearchPassages(query: string, bookIds: string[]) {
  return useQuery({
    queryKey: SEARCH_KEYS.results(query, bookIds),
    queryFn: () => searchService.query({ query, bookIds: bookIds.length ? bookIds : undefined }).then((res) => res.data),
    enabled: query.length > 0,
    staleTime: 60_000,
    // A 429 (rate limit) or validation error will not fix itself; show it and let the user retry.
    retry: false,
  })
}
