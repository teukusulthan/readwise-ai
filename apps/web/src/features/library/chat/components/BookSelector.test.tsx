import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'

import type { IBook } from '@/features/library/types/book.types'
import { BookSelector } from './BookSelector'

const book = (id: string, title: string, author: string): IBook => ({
  id,
  title,
  authors: [author],
  description: null,
  isbn: null,
  coverUrl: null,
  publisher: null,
  publishedYear: null,
  language: 'en',
  subjects: [],
  metadataSource: 'manual',
  hasDocument: true,
  document: null,
  ingestion: { status: 'indexed', error: null, chunkCount: 10, embeddingModel: 'm', indexedAt: null },
  searchable: true,
  createdAt: '',
  updatedAt: '',
})

const LIBRARY = [
  book('1', 'A Christmas Carol', 'Charles Dickens'),
  book('2', 'Heart of Darkness', 'Joseph Conrad'),
  book('3', 'Metamorphosis', 'Franz Kafka'),
  book('4', 'Peter Pan', 'J. M. Barrie'),
  book('5', 'The Prince', 'Niccolò Machiavelli'),
  book('6', 'The Subtle Art of Not Giving a F*ck', 'Mark Manson'),
  book('7', 'The Time Machine', 'H. G. Wells'),
  book('8', 'The War of the Worlds', 'H. G. Wells'),
  book('9', 'Treasure Island', 'Robert Louis Stevenson'),
]

const renderSelector = (selectedIds: string[] = [], onChange = vi.fn()) =>
  render(
    <MemoryRouter>
      <BookSelector books={LIBRARY} isLoading={false} error={null} selectedIds={selectedIds} onChange={onChange} />
    </MemoryRouter>,
  )

const chipNames = () => within(screen.getByRole('group', { name: 'Books to ask' })).getAllByRole('button').map((b) => b.textContent)

describe('BookSelector', () => {
  it('filters a long list by title or author', () => {
    renderSelector()
    fireEvent.change(screen.getByRole('textbox', { name: 'Find a book' }), { target: { value: 'manson' } })
    expect(chipNames()).toEqual(['The Subtle Art of Not Giving a F*ck'])

    fireEvent.change(screen.getByRole('textbox', { name: 'Find a book' }), { target: { value: 'wells' } })
    expect(chipNames()).toEqual(['The Time Machine', 'The War of the Worlds'])
  })

  it('lists selected books first and toggles a book', () => {
    const onChange = vi.fn()
    renderSelector(['6'], onChange)
    expect(chipNames().slice(0, 2)).toEqual(['All indexed books', 'The Subtle Art of Not Giving a F*ck'])
    expect(screen.getByText('1 of 9 selected')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Peter Pan' }))
    expect(onChange).toHaveBeenCalledWith(['6', '4'])
  })

  it('says when nothing matches', () => {
    renderSelector()
    fireEvent.change(screen.getByRole('textbox', { name: 'Find a book' }), { target: { value: 'zzz' } })
    expect(screen.getByText('No indexed book matches “zzz”.')).toBeInTheDocument()
  })
})
