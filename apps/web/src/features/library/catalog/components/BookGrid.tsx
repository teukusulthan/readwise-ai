import { Skeleton } from '@/components/ui/skeleton'
import type { IBook } from '@/features/library/types/book.types'
import { renderIcon } from '@/utils/icon-renderer'
import { BookCard } from './BookCard'

interface BookGridProps {
  books: IBook[] | undefined
  isLoading: boolean
  error: Error | null
  hasActiveFilters: boolean
}

const GRID = 'grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4'

export function BookGrid({ books, isLoading, error, hasActiveFilters }: BookGridProps) {
  if (isLoading) {
    return (
      <div className={GRID} aria-busy="true">
        {Array.from({ length: 8 }, (_, i) => (
          <div key={i} className="flex flex-col gap-3 rounded-2xl border border-border-primary bg-card p-4">
            <Skeleton className="aspect-[2/3] w-full" />
            <Skeleton className="h-5 w-4/5" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ))}
      </div>
    )
  }

  if (error) {
    return (
      <div role="alert" className="flex items-center gap-3 rounded-2xl border border-error-soft/70 bg-error-light px-5 py-4 text-body-md text-error-bold">
        {renderIcon({ icon: 'warning-circle', className: 'text-[20px]' })}
        Could not load the catalog: {error.message}
      </div>
    )
  }

  if (!books?.length) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border-secondary bg-background-primary/60 px-6 py-14 text-center">
        <span className="flex size-14 items-center justify-center rounded-2xl bg-primary-light text-primary-bold">
          {renderIcon({ icon: hasActiveFilters ? 'magnifying-glass' : 'books', className: 'text-[28px]' })}
        </span>
        <p className="font-serif text-h6 font-semibold text-font-primary">{hasActiveFilters ? 'No books match' : 'Your shelves are empty'}</p>
        <p className="max-w-md text-body-md text-font-secondary">
          {hasActiveFilters ? 'Try another search term or filter.' : 'Upload a PDF or import a book from Open Library to get started.'}
        </p>
      </div>
    )
  }

  return (
    <div className={GRID}>
      {books.map((book) => (
        <BookCard key={book.id} book={book} />
      ))}
    </div>
  )
}
