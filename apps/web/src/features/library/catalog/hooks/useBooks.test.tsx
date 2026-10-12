import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { bookService } from '@/services/book.service'
import { useBooks } from './useBooks'

vi.mock('@/services/book.service', () => ({ bookService: { getAll: vi.fn() } }))
vi.mock('@/features/library/constants/catalog', async (orig) => ({ ...(await orig<object>()), CATALOG_POLL_INTERVAL_MS: 20 }))

const getAll = vi.mocked(bookService.getAll)
const page = (...statuses: string[]) => ({ data: statuses.map((status, i) => ({ id: `b${i}`, ingestion: { status } })) }) as never
const params = { page: 1, size: 12 }

function setup() {
  const client = new QueryClient()
  const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>
  return renderHook(() => useBooks(params), { wrapper })
}

describe('useBooks', () => {
  beforeEach(() => vi.clearAllMocks())

  it('polls while a book on the page is processing and stops once none is busy', async () => {
    getAll.mockResolvedValueOnce(page('indexed', 'processing')).mockResolvedValue(page('indexed', 'indexed'))
    setup()
    await waitFor(() => expect(getAll).toHaveBeenCalledTimes(2))
    await new Promise((resolve) => setTimeout(resolve, 100))
    expect(getAll).toHaveBeenCalledTimes(2)
  })

  it('does not poll when nothing is queued or processing', async () => {
    getAll.mockResolvedValue(page('indexed', 'none', 'failed'))
    const { result } = setup()
    await waitFor(() => expect(result.current.data).toBeDefined())
    await new Promise((resolve) => setTimeout(resolve, 100))
    expect(getAll).toHaveBeenCalledTimes(1)
  })
})
