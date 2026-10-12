import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/services/api-error'
import { bookService } from '@/services/book.service'
import { titleFromFileName, useBatchUpload } from './useBatchUpload'

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
})
