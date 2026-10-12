import { Button } from '@/components/ui/button'
import type { ApiPagination } from '@/types/api'
import { renderIcon } from '@/utils/icon-renderer'

interface CatalogPaginationProps {
  page: number
  pagination: ApiPagination | undefined
  onPageChange: (page: number) => void
}

export function CatalogPagination({ page, pagination, onPageChange }: CatalogPaginationProps) {
  const totalPages = pagination?.totalPages ?? 0
  if (totalPages <= 1) return null

  return (
    <nav className="flex items-center justify-between gap-4 border-t border-border-primary pt-5" aria-label="Catalog pages">
      <p className="text-body-md text-font-secondary">
        Page <span className="font-semibold text-font-primary">{page}</span> of {totalPages} · {pagination?.totalElements ?? 0} books
      </p>
      <div className="flex gap-2">
        <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          {renderIcon({ icon: 'caret-left' })}
          Previous
        </Button>
        <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
          Next
          {renderIcon({ icon: 'caret-right' })}
        </Button>
      </div>
    </nav>
  )
}
