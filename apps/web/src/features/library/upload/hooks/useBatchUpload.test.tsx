import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/services/api-error'
import { bookService } from '@/services/book.service'
import { MAX_RATE_LIMIT_RETRIES, rateLimitDelaySeconds, titleFromFileName, useBatchUpload } from './useBatchUpload'

vi.mock('@/services/book.service', () => ({ bookService: { upload: vi.fn() } }))

const upload = vi.mocked(bookService.upload)
const pdf = (name: string) => new File(['x'], name, { type: 'application/pdf' })
const book = (id: string) => ({ data: { id, title: id } }) as never

function setup() {
  const client = new QueryClient()
  const wrapper = ({ children }: { children: ReactNode }) => <QueryClientProvider client={client}>{children}</QueryClientProvider>
  return renderHook(() => useBatchUpload(), { wrapper })
}

describe('useBatchUpload', () => {
  beforeEach(() => vi.clearAllMocks())

  it('derives titles from file names', () => {
    expect(titleFromFileName('Dune_Messiah.PDF')).toBe('Dune Messiah')
  })

  it('uploads sequentially in order with the edited titles', async () => {
    const order: string[] = []
    let release!: () => void
    upload.mockImplementationOnce(async ({ title }) => {
      order.push(`start ${title}`)
      await new Promise<void>((resolve) => (release = resolve))
      order.push(`end ${title}`)
      return book('a')
    })
    upload.mockImplementationOnce(async ({ title }) => {
      order.push(`start ${title}`)
      return book('b')
    })
    const { result } = setup()
    act(() => result.current.addFiles([pdf('a.pdf'), pdf('b.pdf')]))
    act(() => result.current.setTitle(result.current.rows[1].id, 'Second'))
    let done!: Promise<void>
    act(() => {
      done = result.current.start()
    })
    await waitFor(() => expect(result.current.rows[0].status).toBe('uploading'))
    expect(result.current.rows[1].status).toBe('pending')
    expect(upload).toHaveBeenCalledTimes(1)
    await act(async () => {
      release()
      await done
    })
    expect(order).toEqual(['start a', 'end a', 'start Second'])
    expect(result.current.rows.map((r) => r.status)).toEqual(['queued', 'queued'])
  })

  it('shows a 409 message on its row, continues, and does not retry finished rows', async () => {
    upload.mockRejectedValueOnce(new Error("This file was already uploaded as 'Dune' (id 1)."))
    upload.mockResolvedValueOnce(book('b'))
    const { result } = setup()
    act(() => result.current.addFiles([pdf('a.pdf'), pdf('b.pdf')]))
    await act(() => result.current.start())
    expect(result.current.rows[0]).toMatchObject({ status: 'error', error: "This file was already uploaded as 'Dune' (id 1)." })
    expect(result.current.rows[1].status).toBe('queued')
    await act(() => result.current.start())
    expect(upload).toHaveBeenCalledTimes(2)
  })

  it('marks non-pdf files as errors without uploading them', async () => {
    const { result } = setup()
    act(() => result.current.addFiles([new File(['x'], 'notes.txt')]))
    expect(result.current.rows[0]).toMatchObject({ status: 'error', error: 'Only .pdf files are supported' })
    await act(() => result.current.start())
    expect(upload).not.toHaveBeenCalled()
  })

  it('stop() lets the current file finish and leaves the rest pending', async () => {
    let release!: () => void
    upload.mockImplementationOnce(() => new Promise((resolve) => (release = () => resolve(book('a')))))
    const { result } = setup()
    act(() => result.current.addFiles([pdf('a.pdf'), pdf('b.pdf')]))
    let done!: Promise<void>
    act(() => {
      done = result.current.start()
    })
    act(() => result.current.stop())
    await act(async () => {
      release()
      await done
    })
    expect(result.current.rows.map((r) => r.status)).toEqual(['queued', 'pending'])
    expect(upload).toHaveBeenCalledTimes(1)
  })

  it('retry re-sends a failed upload with its edited title but never a queued row', async () => {
    upload.mockRejectedValueOnce(new Error('boom'))
    upload.mockResolvedValueOnce(book('b'))
    upload.mockResolvedValueOnce(book('a'))
    const { result } = setup()
    act(() => result.current.addFiles([pdf('a.pdf'), pdf('b.pdf')]))
    await act(() => result.current.start())
    const [failed, queued] = result.current.rows
    expect(failed).toMatchObject({ status: 'error', retryable: true })
    act(() => result.current.retry(queued.id))
    expect(result.current.rows[1].status).toBe('queued')
    act(() => result.current.setTitle(failed.id, 'Fixed'))
    act(() => result.current.retry(failed.id))
    await act(() => result.current.start())
    expect(upload).toHaveBeenCalledTimes(3)
    expect(upload.mock.calls[2][0]).toMatchObject({ title: 'Fixed' })
    expect(result.current.rows.map((r) => r.status)).toEqual(['queued', 'queued'])
  })

  it('does not retry local validation failures', () => {
    const { result } = setup()
    act(() => result.current.addFiles([new File(['x'], 'notes.txt')]))
    act(() => result.current.retry(result.current.rows[0].id))
    expect(result.current.rows[0].status).toBe('error')
  })

  it('never sends a blank title and falls back to the file name', async () => {
    const { result } = setup()
    act(() => result.current.addFiles([pdf('.pdf')]))
    expect(result.current.rows[0].title).toBe('.pdf')
    act(() => result.current.setTitle(result.current.rows[0].id, '   '))
    await act(() => result.current.start())
    expect(upload).not.toHaveBeenCalled()
    expect(result.current.rows[0].status).toBe('pending')
  })

  it('shows the real error message of a rejected upload verbatim', async () => {
    upload.mockRejectedValueOnce(new ApiError('A book with this file already exists', { response: { status: 409, data: {} } as never }))
    const { result } = setup()
    act(() => result.current.addFiles([pdf('a.pdf')]))
    await act(async () => {
      await result.current.start()
    })
    expect(result.current.rows[0].status).toBe('error')
    expect(result.current.rows[0].error).toBe('A book with this file already exists')
  })

  describe('rate limit (429)', () => {
    const tooMany = (retryAfter?: string) =>
      new ApiError('Too many requests, try again in a moment.', {
        response: { status: 429, data: {}, headers: retryAfter === undefined ? {} : { 'retry-after': retryAfter } } as never,
      })

    beforeEach(() => vi.useFakeTimers())
    afterEach(() => vi.useRealTimers())

    it('reads Retry-After as seconds or an HTTP date, and ignores other errors', () => {
      expect(rateLimitDelaySeconds(tooMany('12'))).toBe(12)
      expect(rateLimitDelaySeconds(tooMany('0'))).toBe(1)
      expect(rateLimitDelaySeconds(tooMany())).toBe(5)
      expect(rateLimitDelaySeconds(tooMany('9999'))).toBe(300)
      expect(rateLimitDelaySeconds(tooMany(new Date(Date.now() + 7000).toUTCString()))).toBeGreaterThanOrEqual(6)
      expect(rateLimitDelaySeconds(new ApiError('conflict', { response: { status: 409, data: {}, headers: {} } as never }))).toBeUndefined()
      expect(rateLimitDelaySeconds(new Error('boom'))).toBeUndefined()
    })

    it('waits Retry-After seconds with a countdown, then re-sends the same row and continues', async () => {
      upload.mockRejectedValueOnce(tooMany('3'))
      upload.mockResolvedValueOnce(book('a'))
      upload.mockResolvedValueOnce(book('b'))
      const { result } = setup()
      act(() => result.current.addFiles([pdf('a.pdf'), pdf('b.pdf')]))
      let done!: Promise<void>
      act(() => {
        done = result.current.start()
      })
      await act(() => vi.advanceTimersByTimeAsync(0))
      expect(result.current.rows[0]).toMatchObject({ status: 'waiting', waitSeconds: 3 })
      expect(result.current.rows[1].status).toBe('pending')
      await act(() => vi.advanceTimersByTimeAsync(1000))
      expect(result.current.rows[0]).toMatchObject({ status: 'waiting', waitSeconds: 2 })
      expect(upload).toHaveBeenCalledTimes(1)
      await act(async () => {
        await vi.advanceTimersByTimeAsync(2000)
        await done
      })
      expect(upload).toHaveBeenCalledTimes(3)
      expect(upload.mock.calls[1][0].file.name).toBe('a.pdf')
      expect(result.current.rows.map((r) => r.status)).toEqual(['queued', 'queued'])
      expect(result.current.rows[0].waitSeconds).toBeUndefined()
    })

    it(`gives up after ${MAX_RATE_LIMIT_RETRIES} automatic retries and leaves the row retryable`, async () => {
      upload.mockRejectedValue(tooMany('1'))
      const { result } = setup()
      act(() => result.current.addFiles([pdf('a.pdf')]))
      let done!: Promise<void>
      act(() => {
        done = result.current.start()
      })
      await act(async () => {
        await vi.advanceTimersByTimeAsync(10_000)
        await done
      })
      expect(upload).toHaveBeenCalledTimes(MAX_RATE_LIMIT_RETRIES + 1)
      expect(result.current.rows[0]).toMatchObject({ status: 'error', retryable: true, error: 'Too many requests, try again in a moment.' })
    })

    it('stop() cancels the wait at once and leaves the row pending', async () => {
      upload.mockRejectedValueOnce(tooMany('30'))
      const { result } = setup()
      act(() => result.current.addFiles([pdf('a.pdf'), pdf('b.pdf')]))
      let done!: Promise<void>
      act(() => {
        done = result.current.start()
      })
      await act(() => vi.advanceTimersByTimeAsync(0))
      expect(result.current.rows[0].status).toBe('waiting')
      await act(async () => {
        result.current.stop()
        await done
      })
      expect(result.current.running).toBe(false)
      expect(result.current.rows.map((r) => r.status)).toEqual(['pending', 'pending'])
      expect(upload).toHaveBeenCalledTimes(1)
      await act(() => vi.advanceTimersByTimeAsync(60_000))
      expect(upload).toHaveBeenCalledTimes(1)
    })

    it('removing a waiting row cancels its re-send', async () => {
      upload.mockRejectedValueOnce(tooMany('5'))
      upload.mockResolvedValueOnce(book('b'))
      const { result } = setup()
      act(() => result.current.addFiles([pdf('a.pdf'), pdf('b.pdf')]))
      let done!: Promise<void>
      act(() => {
        done = result.current.start()
      })
      await act(() => vi.advanceTimersByTimeAsync(0))
      act(() => result.current.removeRow(result.current.rows[0].id))
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1000)
        await done
      })
      expect(upload).toHaveBeenCalledTimes(2)
      expect(upload.mock.calls[1][0].file.name).toBe('b.pdf')
      expect(result.current.rows.map((r) => r.status)).toEqual(['queued'])
    })
  })
})
