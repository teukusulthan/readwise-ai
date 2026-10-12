import { Link, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useBook } from '@/features/library/books/hooks/useBook'
import { BUSY_STATUSES } from '@/features/library/constants/ingestion-status'
import { renderIcon } from '@/utils/icon-renderer'
import { BookDocumentPanel } from './BookDocumentPanel'
import { BookMetadata } from './BookMetadata'
import { DeleteBookDialog } from './DeleteBookDialog'
import { EditBookDialog } from './EditBookDialog'

interface BookDetailViewProps {
  bookId: string | undefined
}

export function BookDetailView({ bookId }: BookDetailViewProps) {
  const navigate = useNavigate()
  const { data: book, isLoading, error } = useBook(bookId)

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
      <div className="flex items-center justify-between gap-2">
        <Button asChild variant="ghost" size="sm">
          <Link to="/books">
            {renderIcon({ icon: 'arrow-left' })}
            Back to catalog
          </Link>
        </Button>
        {book && (
          <div className="flex items-center gap-2">
            <EditBookDialog book={book} />
            <DeleteBookDialog book={book} disabled={BUSY_STATUSES.includes(book.ingestion.status)} onDeleted={() => navigate('/books')} />
          </div>
        )}
      </div>

      {isLoading && (
        <div className="flex gap-8" aria-busy="true">
          <Skeleton className="aspect-[2/3] w-52" />
          <div className="flex flex-1 flex-col gap-3">
            <Skeleton className="h-8 w-2/3" />
            <Skeleton className="h-5 w-1/3" />
            <Skeleton className="h-24" />
          </div>
        </div>
      )}
      {error && (
        <p role="alert" className="rounded-2xl border border-error-soft/70 bg-error-light px-5 py-4 text-body-md text-error-bold">
          Could not load the book: {error.message}
        </p>
      )}
      {book && (
        <>
          <BookMetadata book={book} />
          <BookDocumentPanel book={book} />
        </>
      )}
    </div>
  )
}
