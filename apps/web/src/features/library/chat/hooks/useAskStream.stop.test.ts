import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { TChatStreamEvent } from '@/features/library/chat/types/chat.types'
import { chatService } from '@/services/chat.service'
import { STOP_GRACE_MS, useAskStream } from './useAskStream'

type TOnEvent = (event: TChatStreamEvent, id: string) => void

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

/** A stream that stays open until the test emits events / finishes it. */
function openStream() {
  const stream = { emit: (() => undefined) as TOnEvent, finish: () => undefined as void }
  vi.spyOn(chatService, 'stream').mockImplementation((_payload, { onEvent }: { onEvent: TOnEvent }) => {
    stream.emit = onEvent
    return new Promise<void>((resolve) => {
      stream.finish = resolve
    })
  })
  vi.spyOn(chatService, 'cancel').mockResolvedValue({ data: { cancelled: true } } as never)
  return stream
}

function askAndStop(stream: ReturnType<typeof openStream>) {
  const hook = renderHook(() => useAskStream())
  act(() => {
    void hook.result.current.ask({ question: 'Q?' })
    stream.emit({ type: 'session', sessionId: 's1' }, '1-0')
    stream.emit({ type: 'delta', text: 'Part' }, '2-0')
  })
  act(() => hook.result.current.cancel())
  return hook
}

describe('useAskStream — Stop', () => {
  it('stays "stopping" (Send blocked) until the server confirms with cancelled', async () => {
    const stream = openStream()
    const { result } = askAndStop(stream)

    expect(result.current.state.phase).toBe('stopped')
    expect(result.current.isStreaming).toBe(false)
    expect(result.current.isStopping).toBe(true)

    act(() => stream.emit({ type: 'cancelled', message: 'The answer was stopped.' }, '3-0'))
    expect(result.current.isStopping).toBe(false)
    await act(async () => stream.finish())
    expect(result.current.state.phase).toBe('stopped')
  })

  it('stops waiting when the stream ends without cancelled (the answer finished first)', async () => {
    const stream = openStream()
    const { result } = askAndStop(stream)
    expect(result.current.isStopping).toBe(true)

    act(() =>
      stream.emit(
        { type: 'done', answer: { question: 'Q?', answer: 'Part two', grounded: false, mode: 'llm', model: 'm', sources: [], skippedBooks: [] } },
        '3-0',
      ),
    )
    await act(async () => stream.finish())
    expect(result.current.isStopping).toBe(false)
  })

  it(`gives up waiting after ${STOP_GRACE_MS} ms`, () => {
    vi.useFakeTimers()
    const stream = openStream()
    const { result } = askAndStop(stream)

    act(() => vi.advanceTimersByTime(STOP_GRACE_MS - 1))
    expect(result.current.isStopping).toBe(true)
    act(() => vi.advanceTimersByTime(1))
    expect(result.current.isStopping).toBe(false)
    expect(result.current.state.phase).toBe('stopped')
  })

  it('stops waiting when the cancel request fails', async () => {
    const stream = openStream()
    vi.mocked(chatService.cancel).mockRejectedValue(new Error('offline'))
    const { result } = askAndStop(stream)

    await act(async () => undefined)
    expect(result.current.isStopping).toBe(false)
  })

  it('a cancel request that fails late does not disconnect a newer question', async () => {
    vi.useFakeTimers()
    const stream = openStream()
    let failCancel: (error: Error) => void = () => undefined
    vi.mocked(chatService.cancel).mockReturnValue(new Promise((_resolve, reject) => (failCancel = reject)))
    const { result } = askAndStop(stream)
    act(() => vi.advanceTimersByTime(STOP_GRACE_MS))

    let signal: AbortSignal | undefined
    vi.mocked(chatService.stream).mockImplementation((_payload, options) => {
      signal = options.signal
      return new Promise<void>(() => undefined)
    })
    act(() => {
      void result.current.ask({ question: 'Next?' })
    })
    await act(async () => failCancel(new Error('offline')))

    expect(signal?.aborted).toBe(false)
    expect(result.current.isStreaming).toBe(true)
  })
})
