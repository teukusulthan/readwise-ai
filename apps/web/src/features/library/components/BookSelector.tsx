import { useState, type KeyboardEvent } from 'react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { PerfectScrollArea } from '@/components/wrappers/PerfectScrollArea'
import { useIndexedBooks } from '@/features/library/hooks/useIndexedBooks'
import { useSelectedBooks } from '@/features/library/hooks/useSelectedBooks'
import type { IBook } from '@/features/library/types/book.types'
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { cn } from '@/utils/cn'
import { renderIcon } from '@/utils/icon-renderer'

interface BookSelectorProps {
  selectedIds: string[]
  onChange: (ids: string[]) => void
  /** Heading and group label; defaults to the chat's wording. */
  title?: string
}

/** Show the search box once the library is too long to scan at a glance. */
const SEARCH_THRESHOLD = 8
const SEARCH_DEBOUNCE_MS = 300

const chipClass = (selected: boolean) =>
  cn(
    'inline-flex h-10 max-w-full items-center gap-2 rounded-full border px-4 text-body-md font-medium transition-[background-color,border-color,color,box-shadow,scale] duration-200 ease-fluid active:scale-95 active:duration-75',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
    selected
      ? 'border-primary-soft bg-primary-light text-primary-bold shadow-xs'
      : 'border-border-primary bg-background-primary text-font-secondary hover:border-border-secondary hover:text-font-primary',
  )

/**
 * Pick which indexed books to ask. An empty selection means “all indexed books”.
 * The list is paged and searched on the server, so it works for libraries of any size.
 */
export function BookSelector({ selectedIds, onChange, title = 'Books to ask' }: BookSelectorProps) {
  const [query, setQuery] = useState('')
  const term = query.trim()
  const debouncedTerm = useDebouncedValue(term, SEARCH_DEBOUNCE_MS)

  // `library` (no search) gives the label's total; `results` is what the box currently matches.
  const library = useIndexedBooks()
  const results = useIndexedBooks(debouncedTerm)
  const picked = useSelectedBooks(selectedIds, results.books)

  const toggle = (id: string) => onChange(selectedIds.includes(id) ? selectedIds.filter((x) => x !== id) : [...selectedIds, id])
  const allSelected = selectedIds.length === 0
  const total = library.total ?? 0
  const searching = !!term
  // Picked books stay on top even when they are not on a loaded page; while searching, only matches show.
  const visible: IBook[] = searching
    ? [...(results.books ?? []).filter((b) => selectedIds.includes(b.id)), ...(results.books ?? []).filter((b) => !selectedIds.includes(b.id))]
    : [...picked, ...(library.books ?? []).filter((b) => !selectedIds.includes(b.id))]
  const active = searching ? results : library
  const settling = searching && (term !== debouncedTerm || results.isFetching)

  // Enter in the filter must not submit a surrounding form (e.g. the search page's).
  const onFilterKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') event.preventDefault()
  }

  return (
    <section className="flex flex-col gap-3" aria-labelledby="book-selector-title">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 id="book-selector-title" className="text-label-md font-semibold uppercase tracking-widest text-font-secondary">
          {title}
        </h2>
        <p className="text-body-sm text-font-secondary">
          {allSelected ? `All ${total} indexed books are searched` : `${selectedIds.length} of ${total} selected`}
        </p>
      </div>

      {library.isLoading && (
        <div className="flex flex-wrap gap-2" aria-busy="true">
          <Skeleton className="h-10 w-36 rounded-full" />
          <Skeleton className="h-10 w-52 rounded-full" />
          <Skeleton className="h-10 w-44 rounded-full" />
        </div>
      )}
      {library.error && (
        <p role="alert" className="text-body-sm text-error-bold">
          Could not load indexed books: {library.error.message}
        </p>
      )}
      {library.books?.length === 0 && (
        <p className="text-body-md text-font-secondary">
          No indexed books yet.{' '}
          <Link to="/books" className="font-medium text-primary underline-offset-4 hover:underline">
            Upload a PDF in the catalog
          </Link>{' '}
          to get started.
        </p>
      )}
      {!!library.books?.length && (
        <>
          {(total > SEARCH_THRESHOLD || searching) && (
            <div className="relative">
              {renderIcon({
                icon: 'magnifying-glass',
                className: 'pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-[16px] text-font-placeholder',
              })}
              <Input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                onKeyDown={onFilterKeyDown}
                placeholder="Find a book by title or author"
                aria-label="Find a book"
                className="h-10 pl-10"
              />
            </div>
          )}
          <div className="relative">
            <PerfectScrollArea className="max-h-52" options={{ wheelPropagation: false }}>
              <div className="flex flex-wrap gap-2 pr-3" role="group" aria-label={title} aria-busy={settling}>
                {!searching && (
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
                {searching && !settling && visible.length === 0 && <p className="py-2 text-body-sm text-font-placeholder">No indexed book matches “{term}”.</p>}
              </div>
              {active.hasNextPage && (
                <div className="pt-2">
                  <Button type="button" variant="outline" size="sm" disabled={active.isFetchingNextPage} onClick={() => void active.fetchNextPage()}>
                    {active.isFetchingNextPage ? 'Loading…' : 'Load more books'}
                  </Button>
                </div>
              )}
            </PerfectScrollArea>
          </div>
        </>
      )}
    </section>
  )
}
