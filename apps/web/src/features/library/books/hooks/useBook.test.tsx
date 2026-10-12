import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import { bookService } from '@/services/book.service'
import { useBook } from './useBook'

vi.mock('@/services/book.service', () => ({ bookService: { getOne: vi.fn() } }))
vi.mock('@/features/library/constants/catalog', async (orig) => ({ ...(await orig<object>()), STATUS_POLL_INTERVAL_MS: 20 }))

const getOne = vi.mocked(bookService.getOne)
const withStatus = (status: string) => ({ data: { id: 'b1', ingestion: { status } } }) as never

describe('useBook', () => {
  beforeEach(() => vi.clearAllMocks())

  it('invalidates the book lists once the polled book leaves queued/processing', async () => {
    getOne.mockResolvedValueOnce(withStatus('queued')).mockResolvedValueOnce(withStatus('processing')).mockResolvedValue(withStatus('indexed'))
    const client = new QueryClient()
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>
    const { result } = renderHook(() => useBook('b1'), { wrapper })

    await waitFor(() => expect(result.current.data?.ingestion.status).toBe('indexed'))
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: BOOK_KEYS.all }))
    expect(invalidate).toHaveBeenCalledTimes(1)
  })

  it('does not invalidate for a book that was already indexed when first loaded', async () => {
    getOne.mockResolvedValue(withStatus('indexed'))
    const client = new QueryClient()
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>
    const { result } = renderHook(() => useBook('b1'), { wrapper })

    await waitFor(() => expect(result.current.data).toBeDefined())
    expect(invalidate).not.toHaveBeenCalled()
  })
})
