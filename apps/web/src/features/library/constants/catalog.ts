import type { TIngestionStatus } from '@/features/library/types/book.types'

export type TCatalogFilter = 'all' | 'indexed' | 'metadata'

export const CATALOG_FILTERS: { value: TCatalogFilter; label: string; status?: TIngestionStatus[] }[] = [
  { value: 'all', label: 'All' },
  { value: 'indexed', label: 'Indexed', status: ['indexed'] },
  { value: 'metadata', label: 'Metadata only', status: ['none'] },
]

export const CATALOG_PAGE_SIZE = 12
export const SEARCH_DEBOUNCE_MS = 350
export const STATUS_POLL_INTERVAL_MS = 2000
/** Catalog refresh cadence while any listed book is still being indexed. */
export const CATALOG_POLL_INTERVAL_MS = 5000
export const MAX_UPLOAD_MB = 100
