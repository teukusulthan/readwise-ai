import { useEffect, useState } from 'react'

import type { IAnswerSource } from '@/features/library/chat/types/chat.types'
import { formatPageRange } from '@/features/library/utils/format'
import { Expand } from '@/components/ui/expand'
import { cn } from '@/utils/cn'
import { renderIcon } from '@/utils/icon-renderer'

interface SourceListProps {
  sources: IAnswerSource[]
  /** Source highlighted from a citation chip; it is expanded and scrolled into view. */
  activeSource?: number | null
  /** Show every passage expanded (e.g. retrieval-only mode, where the passages are the answer). */
  expandAll?: boolean
  /** Unique per answer: a chat thread shows many source lists at once. */
  idPrefix?: string
}

export const sourceElementId = (n: number, idPrefix = 'answer') => `${idPrefix}-source-${n}`

export function SourceList({ sources, activeSource = null, expandAll = false, idPrefix = 'answer' }: SourceListProps) {
  const [open, setOpen] = useState<Set<number>>(new Set())

  useEffect(() => {
    if (activeSource === null) return
    setOpen((current) => new Set(current).add(activeSource))
    document.getElementById(sourceElementId(activeSource, idPrefix))?.scrollIntoView?.({ behavior: 'smooth', block: 'nearest' })
  }, [activeSource, idPrefix])

  if (!sources.length) return null

  const toggle = (n: number) =>
    setOpen((current) => {
      const next = new Set(current)
      if (next.has(n)) next.delete(n)
      else next.add(n)
      return next
    })

  return (
    <section aria-labelledby={`${idPrefix}-sources-title`} className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between gap-3">
        <h3 id={`${idPrefix}-sources-title`} className="font-serif text-h6 font-semibold text-font-primary">
          Sources
        </h3>
        <p className="text-body-sm text-font-secondary">Passages retrieved from the books, best match first</p>
      </div>
      <ol className="flex flex-col gap-2.5">
        {sources.map((source) => {
          const location = [source.headings.join(' › '), formatPageRange(source.pageStart, source.pageEnd)].filter(Boolean).join(' — ')
          const isOpen = expandAll || open.has(source.n)
          const isActive = activeSource === source.n
          return (
            <li
              key={source.n}
              id={sourceElementId(source.n, idPrefix)}
              data-cited={source.cited}
              className={cn(
                'overflow-hidden rounded-xl border bg-background-primary transition-[border-color,box-shadow] duration-200',
                source.cited ? 'border-primary-soft' : 'border-border-primary',
                isActive && 'shadow-md ring-2 ring-primary-soft',
              )}
            >
              <button
                type="button"
                aria-expanded={isOpen}
                onClick={() => toggle(source.n)}
                className="group/source flex w-full items-start gap-3 px-4 py-3 text-left transition-colors duration-200 ease-fluid hover:bg-background-secondary/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
              >
                <span
                  className={cn(
                    'mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-lg text-label-md font-semibold transition-[scale] duration-200 ease-spring group-hover/source:scale-110',
                    source.cited ? 'bg-primary text-font-on-accent' : 'bg-background-secondary text-font-secondary',
                  )}
                >
                  {source.n}
                </span>
                <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                  <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="font-serif text-body-lg font-semibold text-font-primary">{source.bookTitle}</span>
                    {source.cited && (
                      <span className="rounded-full bg-primary-light px-2 py-0.5 text-label-sm font-semibold text-primary-bold">Cited</span>
                    )}
                  </span>
                  {location && <span className="text-body-sm text-font-secondary">{location}</span>}
                  <span className="text-body-sm text-font-placeholder">Relevance score {source.score.toFixed(2)}</span>
                </span>
                {renderIcon({
                  icon: 'caret-down',
                  className: cn('mt-1 text-font-secondary transition-transform duration-300 ease-fluid group-hover/source:text-font-primary', isOpen && 'rotate-180'),
                })}
              </button>
              <Expand open={isOpen}>
                <p className="whitespace-pre-wrap border-t border-border-primary bg-background-page px-4 py-3 text-body-md leading-relaxed text-font-primary">
                  {source.text}
                </p>
              </Expand>
            </li>
          )
        })}
      </ol>
    </section>
  )
}
