import { Link } from 'react-router-dom'

import { BookCover } from '@/features/library/components/BookCover'
import type { ICitedBook } from '@/features/library/chat/utils/chat-thread'
import type { IBook } from '@/features/library/types/book.types'
import { formatAuthors } from '@/features/library/utils/format'

interface CitedBooksProps {
  books: ICitedBook[]
  /** Catalog details (cover, authors, year); a book missing here still shows its title and a placeholder cover. */
  booksById: ReadonlyMap<string, IBook>
}

/** Cover cards of the books an answer is based on, linking to each book's page. */
export function CitedBooks({ books, booksById }: CitedBooksProps) {
  if (!books.length) return null

  return (
    <section aria-label="Books this answer is based on" data-testid="cited-books" className="flex flex-col gap-2.5">
      <p className="text-label-sm font-semibold uppercase tracking-widest text-font-placeholder">Based on {books.length === 1 ? 'this book' : 'these books'}</p>
      <div className="flex flex-wrap gap-3">
        {books.map((cited) => {
          const book = booksById.get(cited.bookId)
          const title = book?.title ?? cited.bookTitle
          const byline = [book?.authors.length ? formatAuthors(book.authors) : null, book?.publishedYear].filter(Boolean).join(' · ')
          return (
            <Link
              key={cited.bookId}
              to={`/books/${cited.bookId}`}
              title={`Open “${title}”`}
              className="group flex w-full max-w-[20rem] items-center gap-3.5 rounded-xl border border-border-primary bg-card p-2.5 pr-4 shadow-xs transition-[border-color,box-shadow,translate] duration-300 ease-fluid hover:-translate-y-0.5 hover:border-primary-soft hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <BookCover
                src={book?.coverUrl ?? null}
                title={title}
                compact
                className="h-[5.25rem] w-14 shrink-0 rounded-lg shadow-sm transition-[rotate,scale,box-shadow] duration-300 ease-spring group-hover:-rotate-3 group-hover:scale-105 group-hover:shadow-md"
              />
              <span className="flex min-w-0 flex-col gap-0.5">
                <span className="line-clamp-2 font-serif text-body-md font-semibold leading-snug text-font-primary transition-colors group-hover:text-primary-bold">
                  {title}
                </span>
                {byline && <span className="truncate text-body-sm text-font-secondary">{byline}</span>}
                <span className="text-label-sm font-medium text-primary-bold">
                  {cited.citedCount} {cited.citedCount === 1 ? 'passage' : 'passages'} cited
                </span>
              </span>
            </Link>
          )
        })}
      </div>
    </section>
  )
}
