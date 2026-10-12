import { afterEach, describe, expect, it, vi } from 'vitest'

import type { TChatStreamEvent } from '@/features/library/chat/types/chat.types'
import { chatService, toChatStreamEvent } from './chat.service'

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('toChatStreamEvent', () => {
  it('skips a frame whose data is not valid JSON, with a warning', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    expect(toChatStreamEvent({ event: 'delta', data: '{"text": "cut off', id: '3-0' })).toBeNull()
    expect(warn).toHaveBeenCalledTimes(1)
  })

  it('skips a frame whose JSON is not an object', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    expect(toChatStreamEvent({ event: 'session', data: 'null', id: '' })).toBeNull()
    expect(warn).toHaveBeenCalledTimes(1)
  })
})

describe('chatService.stream', () => {
  it('delivers the frames after a malformed one instead of failing the stream', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined)
    const body = [
      'id: 1-0\nevent: delta\ndata: {"text":"Hel"}\n\n',
      'id: 2-0\nevent: delta\ndata: {not json\n\n',
      'id: 3-0\nevent: delta\ndata: {"text":"lo"}\n\n',
      'id: 4-0\nevent: cancelled\ndata: {"message":"stopped"}\n\n',
    ].join('')
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response(body, { status: 200, headers: { 'content-type': 'text/event-stream' } })),
    )
    const events: [TChatStreamEvent, string][] = []

    await chatService.stream({ question: 'Q?' }, { onEvent: (event, id) => events.push([event, id]) })

    expect(events).toEqual([
      [{ type: 'delta', text: 'Hel' }, '1-0'],
      [{ type: 'delta', text: 'lo' }, '3-0'],
      [{ type: 'cancelled', message: 'stopped' }, '4-0'],
    ])
    expect(warn).toHaveBeenCalledTimes(1)
  })
})
