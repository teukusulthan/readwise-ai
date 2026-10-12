import type { TIngestionStatus } from '@/features/library/types/book.types'

export type TStatusBadgeVariant = 'success' | 'neutral' | 'info' | 'warning' | 'destructive'

export interface IIngestionStatusMeta {
  label: string
  variant: TStatusBadgeVariant
  icon: string
  /** Plain-language explanation shown in tooltips and on the detail page. */
  description: string
}

/**
 * The single source of truth for how ingestion status is shown.
 * Only `indexed` books are searchable — every other label says so explicitly.
 */
export const INGESTION_STATUS_META: Record<TIngestionStatus, IIngestionStatusMeta> = {
  indexed: {
    label: 'Indexed (searchable)',
    variant: 'success',
    icon: 'check-circle',
    description: 'The full text is indexed. You can ask questions about this book.',
  },
  none: {
    label: 'Metadata only — not searchable',
    variant: 'neutral',
    icon: 'book-open',
    description: 'Only catalog information is stored. Upload a PDF to make the text searchable.',
  },
  queued: {
    label: 'Queued — not searchable yet',
    variant: 'info',
    icon: 'hourglass',
    description: 'The document is waiting to be indexed.',
  },
  processing: {
    label: 'Indexing — not searchable yet',
    variant: 'warning',
    icon: 'spinner-gap',
    description: 'The document is being parsed, chunked and embedded.',
  },
  failed: {
    label: 'Indexing failed — not searchable',
    variant: 'destructive',
    icon: 'warning-circle',
    description: 'Indexing did not finish. Check the error and retry with Reindex.',
  },
}

export const BUSY_STATUSES: TIngestionStatus[] = ['queued', 'processing']
