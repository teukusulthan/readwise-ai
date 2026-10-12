import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { useReindexBook } from '@/features/library/books/hooks/useReindexBook'
import { BookStatusBadge } from '@/features/library/components/BookStatusBadge'
import { UploadBookDialog } from '@/features/library/components/UploadBookDialog'
import { BUSY_STATUSES, INGESTION_STATUS_META } from '@/features/library/constants/ingestion-status'
import type { IBook, TIngestionStatus } from '@/features/library/types/book.types'
import { formatBytes, formatDateTime } from '@/features/library/utils/format'
import { cn } from '@/utils/cn'
import { renderIcon } from '@/utils/icon-renderer'

interface BookDocumentPanelProps {
  book: IBook
}

const STEPS = [
  { key: 'uploaded', label: 'Uploaded' },
  { key: 'queued', label: 'Queued' },
  { key: 'processing', label: 'Parsing & embedding' },
  { key: 'indexed', label: 'Searchable' },
] as const

/** How far along the pipeline a status is (index into STEPS). */
const STEP_INDEX: Record<TIngestionStatus, number> = { none: -1, queued: 1, processing: 2, indexed: 3, failed: 2 }

function IngestionSteps({ status }: { status: TIngestionStatus }) {
  const current = STEP_INDEX[status]
  return (
    <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4" aria-label="Indexing progress">
      {STEPS.map((step, index) => {
        const done = index < current || (index === current && status === 'indexed')
        const active = index === current && status !== 'indexed'
        const failed = active && status === 'failed'
        return (
          <li
            key={step.key}
            aria-current={active ? 'step' : undefined}
            className={cn(
              'flex items-center gap-2 rounded-xl border px-3.5 py-3 text-body-md font-medium transition-colors duration-300',
              done && 'border-success-soft/70 bg-success-light text-success-bold',
              active && !failed && 'border-warning-soft/70 bg-warning-light text-warning-bold',
              failed && 'border-error-soft/70 bg-error-light text-error-bold',
              !done && !active && 'border-border-primary bg-background-primary text-font-placeholder',
            )}
          >
            {renderIcon({
              icon: failed ? 'x-circle' : done ? 'check-circle' : active ? 'spinner-gap' : 'circle',
              className: cn('text-[16px] shrink-0', active && !failed && 'animate-spin'),
            })}
            {step.label}
          </li>
        )
      })}
    </ol>
  )
}

export function BookDocumentPanel({ book }: BookDocumentPanelProps) {
  const reindex = useReindexBook()
  const { ingestion, document } = book
  const busy = BUSY_STATUSES.includes(ingestion.status)

  const facts: [string, string | number][] = document
    ? [
        ['File', document.fileName],
        ['Size', formatBytes(document.sizeBytes)],
        ['Pages', document.pageCount ?? '—'],
        ['Passages indexed', ingestion.chunkCount],
        ['Indexed at', formatDateTime(ingestion.indexedAt)],
        ...(ingestion.embeddingModel ? ([['Embedding model', ingestion.embeddingModel]] as [string, string][]) : []),
      ]
    : []

  return (
    <section className="flex flex-col gap-6 rounded-2xl border border-border-primary bg-card p-6 shadow-sm md:p-8" aria-labelledby="full-text-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <h2 id="full-text-title" className="font-serif text-h4 font-semibold tracking-tight text-font-primary">
            Full text
          </h2>
          <p className="max-w-[60ch] text-body-md text-font-secondary">{INGESTION_STATUS_META[ingestion.status].description}</p>
        </div>
        <BookStatusBadge status={ingestion.status} />
      </div>

      {!document ? (
        <div className="flex flex-col items-start gap-4 rounded-xl border border-dashed border-border-secondary bg-background-page px-5 py-5">
          <p className="text-body-md text-font-primary">No document has been uploaded for this book yet.</p>
          <UploadBookDialog bookId={book.id} triggerLabel="Upload the PDF" />
        </div>
      ) : (
        <>
          <IngestionSteps status={ingestion.status} />
          <dl className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {facts.map(([label, value]) => (
              <div key={label} className="rounded-xl bg-background-page px-4 py-3">
                <dt className="text-label-sm font-semibold uppercase tracking-wider text-font-placeholder">{label}</dt>
                <dd className="mt-1 truncate text-body-md font-medium text-font-primary" title={String(value)}>
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </>
      )}

      {ingestion.status === 'failed' && ingestion.error && (
        <p role="alert" className="flex items-start gap-3 rounded-xl border border-error-soft/70 bg-error-light px-4 py-3 text-body-md text-error-bold">
          {renderIcon({ icon: 'warning-circle', className: 'mt-0.5 text-[18px]' })}
          {ingestion.error}
        </p>
      )}
      {busy && (
        <p className="flex items-center gap-2 text-body-md text-font-secondary" aria-live="polite">
          {renderIcon({ icon: 'spinner-gap', className: 'animate-spin text-primary' })}
          Indexing large books can take a few minutes. This page refreshes automatically.
        </p>
      )}

      <div className="flex flex-wrap gap-3 border-t border-border-primary pt-5">
        {book.searchable ? (
          <Button asChild>
            <Link to={`/ask?bookId=${book.id}`}>
              {renderIcon({ icon: 'chat-circle-text' })}
              Ask this book
            </Link>
          </Button>
        ) : (
          <Button disabled title="Only indexed books can answer questions">
            {renderIcon({ icon: 'chat-circle-text' })}
            Ask this book
          </Button>
        )}
        {document && (ingestion.status === 'indexed' || ingestion.status === 'failed') && (
          <Button variant="outline" disabled={reindex.isPending} onClick={() => reindex.mutate(book.id)}>
            {renderIcon({ icon: 'arrows-clockwise' })}
            {reindex.isPending ? 'Starting…' : 'Reindex'}
          </Button>
        )}
      </div>
    </section>
  )
}
