import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import type { TChatStreamEvent } from '@/features/library/chat/types/chat.types'
import { chatService } from '@/services/chat.service'
import { SseHttpError } from '@/services/sse-client'
import { useAskStream } from './useAskStream'

type TOnEvent = (event: TChatStreamEvent, id: string) => void

const done: TChatStreamEvent = {
  type: 'done',
  answer: { question: 'Q?', answer: 'Hello world', grounded: false, mode: 'llm', model: 'm', sources: [], skippedBooks: [] },
}

afterEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

describe('useAskStream — surviving a dropped connection', () => {
  it('re-attaches from the last event id and finishes the answer', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.spyOn(chatService, 'stream').mockImplementation(async (_payload, { onEvent }: { onEvent: TOnEvent }) => {
      onEvent({ type: 'session', sessionId: 's1' }, '1-0')
      onEvent({ type: 'delta', text: 'Hello' }, '2-0')
      throw new TypeError('network error') // the connection drops mid-answer
    })
    const resume = vi.spyOn(chatService, 'resume').mockImplementation(async (_id, _after, { onEvent }: { onEvent: TOnEvent }) => {
      onEvent({ type: 'delta', text: ' world' }, '3-0')
      onEvent(done, '4-0')
    })
    const onSettled = vi.fn()

    const { result } = renderHook(() => useAskStream())
    act(() => {
      void result.current.ask({ question: 'Q?' }, { onSettled })
    })
    await waitFor(() => expect(result.current.state.reconnecting).toBe(true))
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000)
    })

    await waitFor(() => expect(result.current.state.phase).toBe('done'))
    expect(resume).toHaveBeenCalledWith('s1', '2-0', expect.anything()) // only what was missed
    expect(result.current.state.text).toBe('Hello world')
    expect(result.current.state.reconnecting).toBe(false)
    expect(onSettled).toHaveBeenCalledTimes(1)
  })

  it('does not retry a request the server rejected', async () => {
    vi.spyOn(chatService, 'stream').mockRejectedValue(new SseHttpError('Unauthorized', 401))
    const resume = vi.spyOn(chatService, 'resume')
    const { result } = renderHook(() => useAskStream())
    await act(async () => {
      await result.current.ask({ question: 'Q?' })
    })
    expect(result.current.state.phase).toBe('error')
    expect(resume).not.toHaveBeenCalled()
  })

  it('Stop asks the server to cancel instead of just disconnecting', async () => {
    let emit: TOnEvent = () => undefined
    let finish: () => void = () => undefined
    vi.spyOn(chatService, 'stream').mockImplementation((_payload, { onEvent }: { onEvent: TOnEvent }) => {
      emit = onEvent
      return new Promise<void>((resolve) => {
        finish = resolve
      })
    })
    const cancel = vi.spyOn(chatService, 'cancel').mockResolvedValue({ data: { cancelled: true } } as never)

    const { result } = renderHook(() => useAskStream())
    act(() => {
      void result.current.ask({ question: 'Q?' })
      emit({ type: 'session', sessionId: 's9' }, '1-0')
      emit({ type: 'delta', text: 'Part' }, '2-0')
    })
    act(() => result.current.cancel())
    expect(cancel).toHaveBeenCalledWith('s9')
    expect(result.current.state.phase).toBe('stopped')

    await act(async () => {
      emit({ type: 'cancelled', message: 'The answer was stopped.' }, '3-0')
      finish()
    })
    expect(result.current.state.phase).toBe('stopped')
  })

  it('attach replays a running session from the start', async () => {
    const resume = vi.spyOn(chatService, 'resume').mockImplementation(async (_id, _after, { onEvent }: { onEvent: TOnEvent }) => {
      onEvent({ type: 'delta', text: 'Hello world' }, '5-0')
      onEvent(done, '6-0')
    })
    const { result } = renderHook(() => useAskStream())
    await act(async () => {
      await result.current.attach('s2', 'Q?', 'c1')
    })
    expect(resume).toHaveBeenCalledWith('s2', '0', expect.anything())
    expect(result.current.state.question).toBe('Q?')
    expect(result.current.state.phase).toBe('done')
  })
})
