import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { BookSelector } from '@/features/library/components/BookSelector'
import { useIndexedBooks } from '@/features/library/hooks/useIndexedBooks'
import { useSearchPassages } from '@/features/library/search/hooks/useSearchPassages'
import { buildSearchParams, readSearchParams } from '@/features/library/search/utils/search-params'
import { describeSkipReason } from '@/features/library/utils/format'
import { renderIcon } from '@/utils/icon-renderer'
import { SearchResultCard } from './SearchResultCard'

const MAX_QUERY_LENGTH = 2000

/** Semantic passage search. The URL (`?q=`, `?books=`) is the source of truth, so back/forward and shared links work. */
export function SearchView() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { query, bookIds } = readSearchParams(searchParams)
  const [draft, setDraft] = useState(query)
  const [scopeOpen, setScopeOpen] = useState(bookIds.length > 0)

  // Back/forward (or a pasted link) changes the URL: show its query in the box.
  useEffect(() => setDraft(query), [query])

  const indexedBooks = useIndexedBooks()
  const search = useSearchPassages(query, bookIds)

  const submit = (event: FormEvent) => {
    event.preventDefault()
    const next = draft.trim()
    if (!next) return
    setSearchParams(buildSearchParams({ query: next, bookIds }))
  }
  // Re-scoping an existing search replaces the history entry instead of piling one up per click.
  const changeScope = (ids: string[]) => setSearchParams(buildSearchParams({ query, bookIds: ids }), { replace: true })

  const data = search.data
  const titleOf = (id: string, title: string | null) => title ?? indexedBooks.data?.find((book) => book.id === id)?.title ?? 'Unknown book'

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
      <header className="flex flex-col gap-2">
        <p className="text-label-md font-semibold uppercase tracking-widest text-primary">Search</p>
        <h1 className="font-serif text-h2 font-semibold tracking-tight text-font-primary">Search passages</h1>
        <p className="max-w-[60ch] text-body-lg text-font-secondary">
          Find the passages that match what you mean, not just the words you type. Results link back to the page they come from.
        </p>
      </header>

      <form onSubmit={submit} role="search" className="flex flex-col gap-3">
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <span className="pointer-events-none absolute top-1/2 left-4 -translate-y-1/2 text-font-secondary">
              {renderIcon({ icon: 'magnifying-glass', className: 'text-[18px]' })}
            </span>
            <Input
              className="pl-11"
              value={draft}
              maxLength={MAX_QUERY_LENGTH}
              placeholder="Describe what you are looking for"
              aria-label="Search query"
              onChange={(event) => setDraft(event.target.value)}
            />
          </div>
          <Button type="submit" disabled={!draft.trim()}>
            Search
          </Button>
        </div>
        <div className="flex flex-col gap-3">
          <button
            type="button"
            aria-expanded={scopeOpen}
            onClick={() => setScopeOpen((open) => !open)}
            className="inline-flex w-fit items-center gap-1.5 rounded-md text-body-sm font-semibold text-primary-bold hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {renderIcon({ icon: scopeOpen ? 'caret-up' : 'caret-down' })}
            {bookIds.length ? `Limited to ${bookIds.length} ${bookIds.length === 1 ? 'book' : 'books'}` : 'All indexed books'}
          </button>
          {scopeOpen && (
            <BookSelector
              title="Books to search"
              books={indexedBooks.data}
              isLoading={indexedBooks.isLoading}
              error={indexedBooks.error}
              selectedIds={bookIds}
              onChange={changeScope}
            />
          )}
        </div>
      </form>

      <section aria-label="Search results" aria-live="polite" className="flex flex-col gap-4">
        {!query && (
          <p className="rounded-xl border border-dashed border-border-secondary px-4 py-8 text-center text-body-md text-font-secondary">
            Type a topic, a name or a question to see the passages that match it best.
          </p>
        )}

        {query && search.isPending && (
          <div className="flex flex-col gap-3" aria-busy="true" role="status" aria-label="Searching">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-36 w-full rounded-xl" />
            ))}
          </div>
        )}

        {search.isError && (
          <div role="alert" className="flex flex-col items-start gap-3 rounded-xl border border-error-soft bg-error-light px-4 py-3">
            <p className="text-body-md text-error-bold">{search.error.message || 'The search failed.'}</p>
            <Button variant="outline" size="xs" onClick={() => search.refetch()} disabled={search.isFetching}>
              Try again
            </Button>
          </div>
        )}

        {data && (
          <>
            <p className="text-body-sm text-font-secondary">
              {data.results.length === 0
                ? `No passages found in ${data.searchedBookCount} ${data.searchedBookCount === 1 ? 'book' : 'books'}.`
                : `${data.results.length} ${data.results.length === 1 ? 'passage' : 'passages'} from ${data.searchedBookCount} ${data.searchedBookCount === 1 ? 'book' : 'books'}, best match first`}
            </p>

            {data.skippedBooks.length > 0 && (
              <p className="text-body-sm text-font-secondary">
                Not searched:{' '}
                {data.skippedBooks.map((book) => `${titleOf(book.id, book.title)} (${describeSkipReason(book.reason)})`).join('; ')}.
              </p>
            )}

            {data.results.length === 0 && data.searchedBookCount === 0 && (
              <p className="text-body-md text-font-secondary">There are no indexed books to search yet. Index a book in the catalog first.</p>
            )}
            {data.results.length === 0 && data.searchedBookCount > 0 && (
              <p className="text-body-md text-font-secondary">Try other words, or search more books.</p>
            )}

            {data.results.length > 0 && (
              <ol className="flex flex-col gap-3">
                {data.results.map((result, index) => (
                  <SearchResultCard key={`${result.bookId}-${result.chunkIndex}`} result={result} id={`search-result-${index}`} />
                ))}
              </ol>
            )}
          </>
        )}
      </section>
    </div>
  )
}
