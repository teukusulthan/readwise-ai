import { CATALOG_FILTERS, type TCatalogFilter } from '@/features/library/constants/catalog'
import { cn } from '@/utils/cn'

interface CatalogFilterChipsProps {
  value: TCatalogFilter
  onChange: (value: TCatalogFilter) => void
}

/** Segmented control for the indexing-status filter. */
export function CatalogFilterChips({ value, onChange }: CatalogFilterChipsProps) {
  return (
    <div className="inline-flex flex-wrap gap-1 rounded-full border border-border-primary bg-background-secondary p-1" role="group" aria-label="Filter by indexing status">
      {CATALOG_FILTERS.map((filter) => {
        const active = value === filter.value
        return (
          <button
            key={filter.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(filter.value)}
            className={cn(
              'h-9 rounded-full px-4 text-body-md font-medium transition-[background-color,color,box-shadow,scale] duration-250 ease-fluid active:scale-95 active:duration-75',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              active ? 'bg-card text-font-primary shadow-sm' : 'text-font-secondary hover:text-font-primary',
            )}
          >
            {filter.label}
          </button>
        )
      })}
    </div>
  )
}
