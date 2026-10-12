import { useLayoutEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'

import { askAboutBookPath } from '@/features/library/search/utils/search-params'
import type { ISearchResult } from '@/features/library/chat/types/chat.types'
import { bookFileUrl } from '@/features/library/utils/book-file'
import { formatPageRange } from '@/features/library/utils/format'
import { cn } from '@/utils/cn'
import { renderIcon } from '@/utils/icon-renderer'

interface SearchResultCardProps {
  result: ISearchResult
  /** Unique per card; ties the toggle to the passage it expands. */
  id: string
}

const actionClass =
  'inline-flex items-center gap-1.5 rounded-md text-body-sm font-semibold text-primary-bold hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'

export function SearchResultCard({ result, id }: SearchResultCardProps) {
  const textRef = useRef<HTMLParagraphElement>(null)
  const [expanded, setExpanded] = useState(false)
  const [overflowing, setOverflowing] = useState(false)

  // Only offer "Show more" when the 4-line clamp actually hides text.
  useLayoutEffect(() => {
    const el = textRef.current
    if (el && !expanded) setOverflowing(el.scrollHeight > el.clientHeight + 1)
  }, [result.text, expanded])

  const headings = result.headings.join(' › ')
  const pages = formatPageRange(result.pageStart, result.pageEnd)

  return (
    <li className="flex flex-col gap-3 rounded-xl border border-border-primary bg-background-primary p-4 shadow-xs">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col gap-0.5">
          <Link to={`/books/${result.bookId}`} className="font-serif text-body-lg font-semibold text-font-primary hover:text-primary-bold hover:underline">
            {result.bookTitle}
          </Link>
          {(headings || pages) && (
            <p className="text-body-sm text-font-secondary">{[headings, pages].filter(Boolean).join(' — ')}</p>
          )}
        </div>
        <span className="shrink-0 text-body-sm text-font-placeholder" title="Relevance to your query">
          {Math.round(result.score * 100)}%
        </span>
      </div>

      <div className="flex flex-col items-start gap-1">
        <p ref={textRef} id={id} className={cn('whitespace-pre-wrap text-body-md leading-relaxed text-font-primary', !expanded && 'line-clamp-4')}>
          {result.text}
        </p>
        {(overflowing || expanded) && (
          <button
            type="button"
            aria-expanded={expanded}
            aria-controls={id}
            onClick={() => setExpanded((value) => !value)}
            className={actionClass}
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-border-primary pt-3">
        <Link to={askAboutBookPath(result.bookId)} className={actionClass}>
          {renderIcon({ icon: 'chat-circle-text' })}
          Ask about this
        </Link>
        {result.pageStart != null && (
          <a href={bookFileUrl(result.bookId, result.pageStart)} target="_blank" rel="noopener noreferrer" className={actionClass}>
            {renderIcon({ icon: 'arrow-square-out' })}
            Open page {result.pageStart}
          </a>
        )}
      </div>
    </li>
  )
}
