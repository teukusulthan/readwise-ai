import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { PerfectScrollArea } from '@/components/wrappers/PerfectScrollArea'
import type { IBook } from '@/features/library/types/book.types'
import { cn } from '@/utils/cn'
import { renderIcon } from '@/utils/icon-renderer'

interface BookSelectorProps {
  books: IBook[] | undefined
  isLoading: boolean
  error: Error | null
  selectedIds: string[]
  onChange: (ids: string[]) => void
  /** Heading and group label; defaults to the chat's wording. */
  title?: string
}

/** Show the search box once the list is too long to scan at a glance. */
const SEARCH_THRESHOLD = 8

const chipClass = (selected: boolean) =>
  cn(
    'inline-flex h-10 max-w-full items-center gap-2 rounded-full border px-4 text-body-md font-medium transition-[background-color,border-color,color,box-shadow,scale] duration-200 ease-fluid active:scale-95 active:duration-75',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
    selected
      ? 'border-primary-soft bg-primary-light text-primary-bold shadow-xs'
      : 'border-border-primary bg-background-primary text-font-secondary hover:border-border-secondary hover:text-font-primary',
  )

/** Pick which indexed books to ask. An empty selection means “all indexed books”. */
export function BookSelector({ books, isLoading, error, selectedIds, onChange, title = 'Books to ask' }: BookSelectorProps) {
  const [query, setQuery] = useState('')
  const toggle = (id: string) => onChange(selectedIds.includes(id) ? selectedIds.filter((x) => x !== id) : [...selectedIds, id])
  const allSelected = selectedIds.length === 0

  // Selected books first, then the rest; both filtered by title or author.
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase()
    const matches = (book: IBook) => !needle || book.title.toLowerCase().includes(needle) || book.authors.some((a) => a.toLowerCase().includes(needle))
    const list = (books ?? []).filter(matches)
    return [...list.filter((b) => selectedIds.includes(b.id)), ...list.filter((b) => !selectedIds.includes(b.id))]
  }, [books, query, selectedIds])

  return (
    <section className="flex flex-col gap-3" aria-labelledby="book-selector-title">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="book-selector-title" className="text-label-md font-semibold uppercase tracking-widest text-font-secondary">
          {title}
        </h2>
        <p className="text-body-sm text-font-secondary">
          {allSelected ? `All ${books?.length ?? 0} indexed books are searched` : `${selectedIds.length} of ${books?.length ?? 0} selected`}
        </p>
      </div>

      {isLoading && (
        <div className="flex flex-wrap gap-2" aria-busy="true">
          <Skeleton className="h-10 w-36 rounded-full" />
          <Skeleton className="h-10 w-52 rounded-full" />
          <Skeleton className="h-10 w-44 rounded-full" />
        </div>
      )}
      {error && (
        <p role="alert" className="text-body-sm text-error-bold">
          Could not load indexed books: {error.message}
        </p>
      )}
      {books?.length === 0 && (
        <p className="text-body-md text-font-secondary">
          No indexed books yet.{' '}
          <Link to="/books" className="font-medium text-primary underline-offset-4 hover:underline">
            Upload a PDF in the catalog
          </Link>{' '}
          to get started.
        </p>
      )}
      {!!books?.length && (
        <>
          {books.length > SEARCH_THRESHOLD && (
            <div className="relative">
              {renderIcon({ icon: 'magnifying-glass', className: 'pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-[16px] text-font-placeholder' })}
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Find a book by title or author"
                aria-label="Find a book"
                className="h-10 pl-10"
              />
            </div>
          )}
          <div className="relative">
            <PerfectScrollArea className="max-h-52" options={{ wheelPropagation: false }}>
              <div className="flex flex-wrap gap-2 pr-3" role="group" aria-label={title}>
                {!query.trim() && (
                  <button type="button" aria-pressed={allSelected} className={chipClass(allSelected)} onClick={() => onChange([])}>
                    {renderIcon({ icon: 'books', className: 'text-[18px]' })}
                    All indexed books
                  </button>
                )}
                {visible.map((book) => {
                  const selected = selectedIds.includes(book.id)
                  return (
                    <button
                      key={book.id}
                      type="button"
                      aria-pressed={selected}
                      className={chipClass(selected)}
                      onClick={() => toggle(book.id)}
                      title={[book.title, book.authors.join(', ')].filter(Boolean).join(' — ')}
                    >
                      {/* Keyed so the check mark pops in when the book is picked. */}
                      <span key={selected ? 'on' : 'off'} className={cn('flex shrink-0', selected && 'animate-pop-in')}>
                        {renderIcon({ icon: selected ? 'check-circle' : 'book-bookmark', weight: selected ? 'fill' : 'regular', className: 'text-[18px]' })}
                      </span>
                      <span className="truncate">{book.title}</span>
                    </button>
                  )
                })}
                {visible.length === 0 && <p className="py-2 text-body-sm text-font-placeholder">No indexed book matches “{query.trim()}”.</p>}
              </div>
            </PerfectScrollArea>
          </div>
        </>
      )}
    </section>
  )
}
