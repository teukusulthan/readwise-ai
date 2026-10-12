import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { Input } from '@/components/ui/input'
import { smoothScrollTo } from '@/components/wrappers/inertia-scroll'
import { useBooks } from '@/features/library/catalog/hooks/useBooks'
import { CATALOG_FILTERS, CATALOG_PAGE_SIZE, SEARCH_DEBOUNCE_MS, type TCatalogFilter } from '@/features/library/constants/catalog'
import { UploadBookDialog } from '@/features/library/components/UploadBookDialog'
import { useDebouncedValue } from '@/hooks/use-debounced-value'
import { renderIcon } from '@/utils/icon-renderer'
import { AddBookDialog } from './AddBookDialog'
import { BookGrid } from './BookGrid'
import { CatalogFilterChips } from './CatalogFilterChips'
import { CatalogPagination } from './CatalogPagination'
import { ImportBookDialog } from './ImportBookDialog'

export function CatalogView() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<TCatalogFilter>('all')
  const [page, setPage] = useState(1)
  const debouncedSearch = useDebouncedValue(search.trim(), SEARCH_DEBOUNCE_MS)
  const status = CATALOG_FILTERS.find((f) => f.value === filter)?.status

  const books = useBooks({ search: debouncedSearch || undefined, status, page, size: CATALOG_PAGE_SIZE, orderBy: 'createdAt', order: 'desc' })
  const rootRef = useRef<HTMLDivElement>(null)

  // Another page starts at the top: glide the enclosing scroll area (the app's main column) up.
  const changePage = (next: number) => {
    setPage(next)
    const area = rootRef.current?.closest<HTMLElement>('.ps')
    if (area) smoothScrollTo(area, 0)
  }

  return (
    <div ref={rootRef} className="mx-auto flex w-full max-w-6xl flex-col gap-8">
      <header className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
        <div className="flex flex-col gap-2">
          <p className="text-label-md font-semibold uppercase tracking-widest text-primary">Catalog</p>
          <h1 className="font-serif text-h2 font-semibold tracking-tight text-font-primary">Your library</h1>
          <p className="max-w-[60ch] text-body-lg text-font-secondary">
            Browse every book you have added. Only books marked <span className="font-semibold text-success-bold">Indexed</span> can answer
            questions.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2 xl:flex-nowrap">
          <AddBookDialog />
          <ImportBookDialog />
          <UploadBookDialog onUploaded={(book) => navigate(`/books/${book.id}`)} />
        </div>
      </header>

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div className="relative w-full md:max-w-md">
          <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-font-secondary">{renderIcon({ icon: 'magnifying-glass', className: 'text-[18px]' })}</span>
          <Input
            className="pl-11"
            placeholder="Search title, author or ISBN"
            value={search}
            aria-label="Search the catalog"
            onChange={(event) => {
              setSearch(event.target.value)
              setPage(1)
            }}
          />
        </div>
        <CatalogFilterChips
          value={filter}
          onChange={(value) => {
            setFilter(value)
            setPage(1)
          }}
        />
      </div>

      <BookGrid books={books.data?.data} isLoading={books.isLoading} error={books.error} hasActiveFilters={!!debouncedSearch || filter !== 'all'} />
      <CatalogPagination page={page} pagination={books.data?.metaData.pagination} onPageChange={changePage} />
    </div>
  )
}
