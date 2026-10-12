import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { IBook } from '@/features/library/types/book.types'
import { bookService } from '@/services/book.service'
import { EditBookDialog } from './EditBookDialog'

vi.mock('@/services/book.service', () => ({ bookService: { update: vi.fn() } }))
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

const book: IBook = {
  id: 'b1',
  title: 'Dune',
  authors: ['Frank Herbert', 'Brian Herbert'],
  description: 'Sand.',
  isbn: '9780441172719',
  coverUrl: 'https://example.com/c.jpg',
  publisher: 'Ace',
  publishedYear: 1965,
  language: 'en',
  subjects: ['Science fiction', 'Desert'],
  metadataSource: 'manual',
  hasDocument: false,
  document: null,
  ingestion: { status: 'metadata_only', error: null, chunkCount: 0, embeddingModel: null, indexedAt: null },
  searchable: false,
  createdAt: '',
  updatedAt: '',
} as unknown as IBook

function renderDialog() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  const invalidate = vi.spyOn(client, 'invalidateQueries')
  render(
    <QueryClientProvider client={client}>
      <EditBookDialog book={book} />
    </QueryClientProvider>,
  )
  fireEvent.click(screen.getByRole('button', { name: /edit details/i }))
  return invalidate
}

describe('EditBookDialog', () => {
  beforeEach(() => vi.clearAllMocks())

  it('prefills every field from the book', async () => {
    renderDialog()
    expect(await screen.findByLabelText('Title')).toHaveValue('Dune')
    expect(screen.getByLabelText('Authors')).toHaveValue('Frank Herbert, Brian Herbert')
    expect(screen.getByLabelText('ISBN')).toHaveValue('9780441172719')
    expect(screen.getByLabelText('Year')).toHaveValue('1965')
    expect(screen.getByLabelText('Publisher')).toHaveValue('Ace')
    expect(screen.getByLabelText('Language')).toHaveValue('en')
    expect(screen.getByLabelText('Subjects')).toHaveValue('Science fiction, Desert')
    expect(screen.getByLabelText('Cover URL')).toHaveValue('https://example.com/c.jpg')
    expect(screen.getByLabelText('Description')).toHaveValue('Sand.')
  })

  it('submits the update payload and invalidates book queries', async () => {
    vi.mocked(bookService.update).mockResolvedValue({ data: { ...book, title: 'Dune Messiah' } } as never)
    const invalidate = renderDialog()
    fireEvent.change(await screen.findByLabelText('Title'), { target: { value: ' Dune Messiah ' } })
    fireEvent.change(screen.getByLabelText('Language'), { target: { value: '' } })
    fireEvent.change(screen.getByLabelText('Subjects'), { target: { value: 'Sci-fi, , Sand' } })
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => expect(bookService.update).toHaveBeenCalled())
    expect(bookService.update).toHaveBeenCalledWith({
      id: 'b1',
      title: 'Dune Messiah',
      authors: ['Frank Herbert', 'Brian Herbert'],
      isbn: '9780441172719',
      publishedYear: 1965,
      description: 'Sand.',
      publisher: 'Ace',
      language: undefined,
      subjects: ['Sci-fi', 'Sand'],
      coverUrl: 'https://example.com/c.jpg',
    })
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ['book', 'b1'] }))
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['books'] })
  })

  it('shows an ISBN server error inline next to the ISBN field', async () => {
    vi.mocked(bookService.update).mockRejectedValue(new Error('A book with ISBN 9780441172719 already exists.'))
    renderDialog()
    await screen.findByLabelText('Title')
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))
    expect(await screen.findByText('A book with ISBN 9780441172719 already exists.')).toBeInTheDocument()
    expect(screen.getByLabelText('ISBN')).toHaveAttribute('aria-invalid', 'true')
  })

  it('shows other server errors in an alert and blocks invalid client input', async () => {
    vi.mocked(bookService.update).mockRejectedValue(new Error('Boom'))
    renderDialog()
    fireEvent.change(await screen.findByLabelText('Cover URL'), { target: { value: 'ftp://x' } })
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))
    expect(await screen.findByText(/must start with http/i)).toBeInTheDocument()
    expect(bookService.update).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Cover URL'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Boom')
  })
})
