import { Link } from 'react-router-dom'

import { BookCover } from '@/features/library/components/BookCover'
import { BookStatusBadge } from '@/features/library/components/BookStatusBadge'
import type { IBook } from '@/features/library/types/book.types'
import { formatAuthors } from '@/features/library/utils/format'

interface BookCardProps {
  book: IBook
}

export function BookCard({ book }: BookCardProps) {
  return (
    <Link
      to={`/books/${book.id}`}
      className="group flex h-full flex-col gap-4 rounded-2xl border border-border-primary bg-card p-4 shadow-sm transition-[translate,scale,box-shadow,border-color] duration-300 ease-fluid hover:-translate-y-1.5 hover:border-primary-soft hover:shadow-xl active:scale-[0.985] active:duration-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      {/* The cover zooms gently inside its frame on hover. */}
      <div className="overflow-hidden rounded-xl shadow-sm transition-shadow duration-300 ease-fluid group-hover:shadow-md">
        <BookCover
          src={book.coverUrl}
          title={book.title}
          className="aspect-[2/3] w-full rounded-xl transition-[scale] duration-500 ease-fluid group-hover:scale-[1.04]"
        />
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <h3 className="line-clamp-2 font-serif text-body-lg font-semibold leading-snug text-font-primary transition-colors duration-200 group-hover:text-primary-bold">{book.title}</h3>
        <p className="truncate text-body-sm text-font-secondary">
          {formatAuthors(book.authors)}
          {book.publishedYear ? ` · ${book.publishedYear}` : ''}
        </p>
        <div className="mt-auto pt-3">
          <BookStatusBadge status={book.ingestion.status} className="rounded-xl" />
        </div>
      </div>
    </Link>
  )
}
