import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { IBook } from '@/features/library/types/book.types'
import { bookService } from '@/services/book.service'
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

const TOTAL = 120
const LIBRARY = Array.from({ length: TOTAL }, (_, i) => book(`id-${i + 1}`, `Book ${String(i + 1).padStart(3, '0')}`, i % 2 ? 'Jane Austen' : 'Mark Twain'))
LIBRARY[99] = book('id-100', 'Moby Dick', 'Herman Melville')

/** Fake list endpoint: filters by `search` and pages like the backend, reporting the filtered total. */
const listBooks = (params: { search?: string; page: number; size: number }) => {
  const needle = params.search?.toLowerCase()
  const matches = LIBRARY.filter((b) => !needle || b.title.toLowerCase().includes(needle) || b.authors.some((a) => a.toLowerCase().includes(needle)))
  const data = matches.slice((params.page - 1) * params.size, params.page * params.size)
  return Promise.resolve({ data, metaData: { pagination: { size: params.size, totalElements: matches.length, totalPages: Math.ceil(matches.length / params.size) } } } as never)
}

const getAll = vi.spyOn(bookService, 'getAll')
const getOne = vi.spyOn(bookService, 'getOne')

const renderSelector = (selectedIds: string[] = [], onChange = vi.fn()) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <BookSelector selectedIds={selectedIds} onChange={onChange} />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const chipNames = () => within(screen.getByRole('group', { name: 'Books to ask' })).getAllByRole('button').map((b) => b.textContent)
const filterBox = () => screen.getByRole('textbox', { name: 'Find a book' })

describe('BookSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getAll.mockImplementation(listBooks as never)
    getOne.mockImplementation((id) => Promise.resolve({ data: LIBRARY.find((b) => b.id === id) }) as never)
  })

  it('labels the scope with the backend total and pages with Load more', async () => {
    renderSelector()
    expect(await screen.findByText('All 120 indexed books are searched')).toBeInTheDocument()
    expect(getAll).toHaveBeenCalledWith(expect.objectContaining({ status: ['indexed'], page: 1, size: 50 }))
    expect(chipNames()).toHaveLength(1 + 50) // "All" chip + one page

    fireEvent.click(screen.getByRole('button', { name: 'Load more books' }))
    await waitFor(() => expect(chipNames()).toHaveLength(1 + 100))
    fireEvent.click(screen.getByRole('button', { name: 'Load more books' }))
    await waitFor(() => expect(chipNames()).toHaveLength(1 + 120))
    expect(screen.queryByRole('button', { name: 'Load more books' })).not.toBeInTheDocument()
  })

  it('searches on the server after a pause in typing', async () => {
    renderSelector()
    await screen.findByText('All 120 indexed books are searched')
    getAll.mockClear()

    for (const value of ['m', 'mo', 'moby']) fireEvent.change(filterBox(), { target: { value } })
    expect(getAll).not.toHaveBeenCalled()
    await waitFor(() => expect(chipNames()).toEqual(['Moby Dick']))
    expect(getAll).toHaveBeenCalledTimes(1)
    expect(getAll).toHaveBeenCalledWith(expect.objectContaining({ search: 'moby', status: ['indexed'], page: 1 }))
    expect(screen.getByText('All 120 indexed books are searched')).toBeInTheDocument()
  })

  it('says when nothing matches', async () => {
    renderSelector()
    await screen.findByText('All 120 indexed books are searched')
    fireEvent.change(filterBox(), { target: { value: 'zzz' } })
    expect(await screen.findByText('No indexed book matches “zzz”.')).toBeInTheDocument()
  })

  it('keeps picked books visible even when they are not on a loaded page', async () => {
    const onChange = vi.fn()
    renderSelector(['id-100', 'id-2'], onChange)
    await screen.findByText('2 of 120 selected')
    await waitFor(() => expect(chipNames().slice(0, 3)).toEqual(['All indexed books', 'Moby Dick', 'Book 002']))
    expect(screen.getByRole('button', { name: 'Moby Dick' })).toHaveAttribute('aria-pressed', 'true')
    expect(getOne).toHaveBeenCalledWith('id-100')
    expect(getOne).not.toHaveBeenCalledWith('id-2')

    fireEvent.click(screen.getByRole('button', { name: 'Moby Dick' }))
    expect(onChange).toHaveBeenCalledWith(['id-2'])
  })

  it('toggles a book on', async () => {
    const onChange = vi.fn()
    renderSelector(['id-6'], onChange)
    fireEvent.click(await screen.findByRole('button', { name: 'Book 004' }))
    expect(onChange).toHaveBeenCalledWith(['id-6', 'id-4'])
  })

  it('does not submit a surrounding form when Enter is pressed in the filter', async () => {
    const onSubmit = vi.fn((event: { preventDefault: () => void }) => event.preventDefault())
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <form role="search" onSubmit={onSubmit}>
            <BookSelector selectedIds={[]} onChange={vi.fn()} />
          </form>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await screen.findByText('All 120 indexed books are searched')
    // Pressing Enter fires keydown first; a prevented keydown stops the browser's implicit form submit.
    expect(fireEvent.keyDown(filterBox(), { key: 'Enter' })).toBe(false)
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
