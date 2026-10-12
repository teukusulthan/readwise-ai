import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { PerfectScrollArea } from '@/components/wrappers/PerfectScrollArea'
import { useBookLookup } from '@/features/library/catalog/hooks/useBookLookup'
import { useImportBook } from '@/features/library/catalog/hooks/useImportBook'
import { SEARCH_DEBOUNCE_MS } from '@/features/library/constants/catalog'
import { BookCover } from '@/features/library/components/BookCover'
import { formatAuthors } from '@/features/library/utils/format'
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { renderIcon } from '@/utils/icon-renderer'

export function ImportBookDialog() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const debouncedQuery = useDebouncedValue(query, SEARCH_DEBOUNCE_MS)
  const lookup = useBookLookup(debouncedQuery)
  const importBook = useImportBook()

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          {renderIcon({ icon: 'magnifying-glass-plus' })}
          Import from Open Library
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Import book metadata</DialogTitle>
          <DialogDescription>
            Imports catalog information only (title, authors, cover). The book is not searchable until you upload its PDF.
          </DialogDescription>
        </DialogHeader>
        <Input autoFocus placeholder="Search by title, author or ISBN" value={query} onChange={(event) => setQuery(event.target.value)} aria-label="Search Open Library" />
        <div className="relative h-80 min-h-0">
          <PerfectScrollArea className="h-full">
            <div className="flex flex-col gap-2 pr-3">
              {debouncedQuery.trim().length < 2 && <p className="text-body-sm text-font-secondary">Type at least 2 characters.</p>}
              {lookup.isFetching && Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-24" />)}
              {lookup.error && (
                <p role="alert" className="text-body-sm text-error-bold">
                  {lookup.error.message}
                </p>
              )}
              {!lookup.isFetching && lookup.data?.length === 0 && <p className="text-body-sm text-font-secondary">No results with an ISBN.</p>}
              {!lookup.isFetching &&
                lookup.data?.map((candidate) => (
                  <div key={`${candidate.externalId}-${candidate.isbn}`} className="flex items-center gap-3 rounded-xl border border-border-primary bg-background-primary p-3 transition-colors hover:border-border-secondary">
                    <BookCover src={candidate.coverUrl} title={candidate.title} compact className="h-[4.5rem] w-12 shrink-0 rounded-md" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-body-md font-semibold text-font-primary">{candidate.title}</p>
                      <p className="truncate text-body-sm text-font-secondary">
                        {formatAuthors(candidate.authors)}
                        {candidate.publishedYear ? ` · ${candidate.publishedYear}` : ''} · ISBN {candidate.isbn}
                      </p>
                    </div>
                    <Button
                      size="xs"
                      disabled={importBook.isPending}
                      onClick={() => importBook.mutate(candidate.isbn)}
                      aria-label={`Import ${candidate.title}`}
                    >
                      Import
                    </Button>
                  </div>
                ))}
            </div>
          </PerfectScrollArea>
        </div>
      </DialogContent>
    </Dialog>
  )
}
