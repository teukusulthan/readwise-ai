import { useState } from 'react'

import { cn } from '@/utils/cn'
import { renderIcon } from '@/utils/icon-renderer'

interface BookCoverProps {
  src: string | null
  title: string
  className?: string
  /** Small thumbnails: icon only, no title text in the placeholder. */
  compact?: boolean
}

/**
 * Cover image. Without a cover (or if it fails to load) a warm placeholder shows the
 * book's own title — never an invented cover.
 */
export function BookCover({ src, title, className, compact = false }: BookCoverProps) {
  const [failed, setFailed] = useState(false)
  const [loaded, setLoaded] = useState(false)

  if (!src || failed) {
    return (
      <div
        className={cn(
          'relative flex flex-col items-center justify-center gap-2 overflow-hidden rounded-xl border border-border-primary p-3 text-center',
          'bg-linear-to-br from-primary-light via-background-secondary to-primary-soft/50 text-primary-bold',
          className,
        )}
        role="img"
        aria-label={`No cover for ${title}`}
      >
        <span className="absolute inset-y-0 left-2 w-px bg-primary-soft/70" aria-hidden="true" />
        {renderIcon({ icon: 'book-open-text', className: compact ? 'text-xl' : 'text-3xl opacity-80' })}
        {!compact && <span className="line-clamp-3 font-serif text-body-sm font-semibold leading-snug text-font-primary">{title}</span>}
      </div>
    )
  }

  return (
    <img
      src={src}
      alt={`Cover of ${title}`}
      loading="lazy"
      decoding="async"
      onLoad={() => setLoaded(true)}
      onError={() => setFailed(true)}
      // Fades in once decoded (instead of painting line by line); the frame colour shows meanwhile.
      className={cn(
        'rounded-xl border border-border-primary bg-background-secondary object-cover transition-opacity duration-500 ease-fluid',
        loaded ? 'opacity-100' : 'opacity-0',
        className,
      )}
    />
  )
}
