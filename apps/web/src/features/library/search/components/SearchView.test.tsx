import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ISearchResponse, ISearchResult } from '@/features/library/chat/types/chat.types'
import { ApiError } from '@/services/api-error'
import { bookService } from '@/services/book.service'
import { searchService } from '@/services/search.service'
import { SearchView } from './SearchView'

vi.mock('@/services/search.service', () => ({ searchService: { query: vi.fn() } }))
vi.mock('@/services/book.service', () => ({ bookService: { getAll: vi.fn() } }))

const query = vi.mocked(searchService.query)
const getAll = vi.mocked(bookService.getAll)

const result = (over: Partial<ISearchResult> = {}): ISearchResult => ({
  bookId: 'b1',
  bookTitle: 'Dracula',
  chunkIndex: 3,
  text: 'The castle stood alone.',
  headings: ['Chapter 1', 'The Journey'],
  pageStart: 12,
  pageEnd: 13,
  score: 0.8349,
  ...over,
})
const response = (over: Partial<ISearchResponse> = {}) =>
  ({ data: { query: 'castle', results: [result()], searchedBookCount: 2, skippedBooks: [], ...over } }) as never

function LocationProbe() {
  const location = useLocation()
  return <output data-testid="location">{location.pathname + location.search}</output>
}

const renderAt = (url: string) => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[url]}>
        <SearchView />
        <LocationProbe />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}
const location = () => screen.getByTestId('location').textContent

describe('SearchView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getAll.mockResolvedValue({ data: [{ id: 'b1', title: 'Dracula', authors: [] }, { id: 'b2', title: 'Emma', authors: [] }] } as never)
  })

  it('shows a hint and runs nothing without a query', () => {
    renderAt('/search')
    expect(screen.getByText(/Type a topic/)).toBeInTheDocument()
    expect(query).not.toHaveBeenCalled()
  })

  it('runs the query from the URL and renders the ranked passages', async () => {
    query.mockResolvedValue(response())
    renderAt('/search?q=castle')

    expect(await screen.findByText('Dracula')).toBeInTheDocument()
    expect(query).toHaveBeenCalledWith({ query: 'castle', bookIds: undefined })
    expect(screen.getByText('Chapter 1 › The Journey — pp. 12–13')).toBeInTheDocument()
    expect(screen.getByText('83%')).toBeInTheDocument()
    expect(screen.getByText('The castle stood alone.')).toBeInTheDocument()
    expect(screen.getByText('1 passage from 2 books, best match first')).toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Search query' })).toHaveValue('castle')
    expect(screen.getByRole('link', { name: /Open page 12/ })).toHaveAttribute('href', expect.stringMatching(/id=b1#page=12$/))
    expect(screen.getByRole('link', { name: /Ask about this/ })).toHaveAttribute('href', '/ask?bookId=b1')
  })

  it('puts a submitted query in the URL (pushing history) and searches it', async () => {
    query.mockResolvedValue(response())
    renderAt('/search')
    fireEvent.change(screen.getByRole('textbox', { name: 'Search query' }), { target: { value: '  vampire  ' } })
    fireEvent.submit(screen.getByRole('search'))

    await waitFor(() => expect(location()).toBe('/search?q=vampire'))
    await waitFor(() => expect(query).toHaveBeenCalledWith({ query: 'vampire', bookIds: undefined }))
  })

  it('does not submit a blank query', () => {
    renderAt('/search')
    expect(screen.getByRole('button', { name: 'Search' })).toBeDisabled()
    fireEvent.submit(screen.getByRole('search'))
    expect(location()).toBe('/search')
  })

  it('reads the book scope from the URL and writes a changed scope back to it', async () => {
    query.mockResolvedValue(response())
    renderAt('/search?q=castle&books=b1')
    await screen.findByText('The castle stood alone.')
    expect(query).toHaveBeenCalledWith({ query: 'castle', bookIds: ['b1'] })
    expect(screen.getByRole('button', { name: /Limited to 1 book/ })).toBeInTheDocument()

    fireEvent.click(await screen.findByRole('button', { name: 'Emma' }))
    await waitFor(() => expect(location()).toBe('/search?q=castle&books=b1%2Cb2'))
  })

  it('explains an empty result and a library with nothing indexed', async () => {
    query.mockResolvedValue(response({ results: [] }))
    renderAt('/search?q=zzz')
    expect(await screen.findByText('No passages found in 2 books.')).toBeInTheDocument()
    expect(screen.getByText(/Try other words/)).toBeInTheDocument()
  })

  it('notes books that were skipped', async () => {
    query.mockResolvedValue(
      response({ skippedBooks: [{ id: 'b9', title: 'Emma', reason: 'not_indexed:processing' }, { id: 'b8', title: null, reason: 'not_found' }] }),
    )
    renderAt('/search?q=castle')
    expect(await screen.findByText(/Not searched: Emma \(still being indexed\); Unknown book \(not found\)\./)).toBeInTheDocument()
  })

  it('shows the backend message when the search fails, e.g. rate limited, and retries', async () => {
    query.mockRejectedValueOnce(new ApiError('Too many requests, try again in 12 seconds.'))
    renderAt('/search?q=castle')
    expect(await screen.findByRole('alert')).toHaveTextContent('Too many requests, try again in 12 seconds.')

    query.mockResolvedValue(response())
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Dracula')).toBeInTheDocument()
  })

  it('shows a loading state while searching', () => {
    query.mockReturnValue(new Promise(() => undefined))
    renderAt('/search?q=castle')
    expect(screen.getByRole('status', { name: 'Searching' })).toBeInTheDocument()
  })

  it('offers Show more only when the passage is clamped', async () => {
    query.mockResolvedValue(response({ results: [result({ text: 'Short one.' }), result({ chunkIndex: 4, text: 'A very long passage.' })] }))
    const scrollHeight = vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockImplementation(function (this: HTMLElement) {
      return this.textContent === 'A very long passage.' ? 200 : 20
    })
    vi.spyOn(HTMLElement.prototype, 'clientHeight', 'get').mockReturnValue(80)
    renderAt('/search?q=castle')

    const more = await screen.findByRole('button', { name: 'Show more' })
    expect(screen.getAllByRole('button', { name: 'Show more' })).toHaveLength(1)
    fireEvent.click(more)
    expect(screen.getByRole('button', { name: 'Show less' })).toHaveAttribute('aria-expanded', 'true')
    scrollHeight.mockRestore()
  })
})
