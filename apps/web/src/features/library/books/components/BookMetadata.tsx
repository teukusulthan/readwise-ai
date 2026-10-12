import { BookCover } from '@/features/library/components/BookCover'
import { BookStatusBadge } from '@/features/library/components/BookStatusBadge'
import type { IBook } from '@/features/library/types/book.types'
import { formatAuthors } from '@/features/library/utils/format'

const SOURCE_LABEL: Record<IBook['metadataSource'], string> = {
  manual: 'Added manually',
  openlibrary: 'Imported from Open Library',
  upload: 'Created from an uploaded document',
}

interface BookMetadataProps {
  book: IBook
}

export function BookMetadata({ book }: BookMetadataProps) {
  const facts: [string, string | number | null][] = [
    ['ISBN', book.isbn],
    ['Publisher', book.publisher],
    ['Published', book.publishedYear],
    ['Language', book.language],
  ]
  const shownFacts = facts.filter(([, value]) => value !== null && value !== '')

  return (
    <section className="grid grid-cols-1 gap-8 md:grid-cols-[13.5rem_1fr] md:gap-10">
      <BookCover src={book.coverUrl} title={book.title} className="aspect-[2/3] w-44 self-start shadow-lg md:w-full" />
      <div className="flex min-w-0 flex-col gap-5">
        <div className="flex flex-col gap-2">
          <p className="text-label-md font-semibold uppercase tracking-widest text-primary">{SOURCE_LABEL[book.metadataSource]}</p>
          <h1 className="font-serif text-h2 font-semibold leading-tight tracking-tight text-font-primary">{book.title}</h1>
          <p className="text-body-lg text-font-secondary">{formatAuthors(book.authors)}</p>
        </div>
        <BookStatusBadge status={book.ingestion.status} className="self-start" />
        {book.description && <p className="max-w-[70ch] whitespace-pre-line text-body-lg leading-relaxed text-font-primary">{book.description}</p>}
        {shownFacts.length > 0 && (
          <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {shownFacts.map(([label, value]) => (
              <div key={label} className="rounded-xl border border-border-primary bg-background-primary px-4 py-3">
                <dt className="text-label-sm font-semibold uppercase tracking-wider text-font-placeholder">{label}</dt>
                <dd className="mt-1 truncate text-body-md font-medium text-font-primary" title={String(value)}>
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        )}
        {book.subjects.length > 0 && (
          <ul className="flex flex-wrap gap-2" aria-label="Subjects">
            {book.subjects.map((subject) => (
              <li key={subject} className="rounded-full border border-border-primary bg-background-primary px-3 py-1 text-body-sm text-font-secondary">
                {subject}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
