import { afterEach, describe, expect, it, vi } from 'vitest'

import { createSseParser, streamSse, type ISseMessage } from './sse-client'

function parseWithIds(chunks: string[]): ISseMessage[] {
  const messages: ISseMessage[] = []
  const parser = createSseParser((message) => messages.push(message))
  chunks.forEach((chunk) => parser.push(chunk))
  parser.flush()
  return messages
}

/** Event + data only (most tests don't care about ids). */
const parseChunks = (chunks: string[]) => parseWithIds(chunks).map(({ event, data }) => ({ event, data }))

describe('createSseParser', () => {
  it('parses named events with JSON data', () => {
    expect(parseChunks(['event: delta\ndata: {"text":"Hi"}\n\n'])).toEqual([{ event: 'delta', data: '{"text":"Hi"}' }])
  })

  it('reassembles frames split at arbitrary points across chunks', () => {
    const stream = 'event: status\ndata: {"stage":"retrieving"}\n\nevent: delta\ndata: {"text":"Hello"}\n\n'
    const chunks = stream.match(/.{1,3}/gs) ?? []
    expect(parseChunks(chunks).map((m) => m.event)).toEqual(['status', 'delta'])
  })

  it('accepts CRLF line endings, even when "\\r\\n" is split between chunks', () => {
    expect(parseChunks(['event: done\r\ndata: {}\r', '\n\r\n'])).toEqual([{ event: 'done', data: '{}' }])
  })

  it('ignores comment lines such as keep-alive pings', () => {
    expect(parseChunks([': ping\n\n', 'event: delta\n: note\ndata: {"text":"a"}\n\n'])).toEqual([{ event: 'delta', data: '{"text":"a"}' }])
  })

  it('joins multi-line data with newlines and defaults the event name', () => {
    expect(parseChunks(['data: first\ndata: second\n\n'])).toEqual([{ event: 'message', data: 'first\nsecond' }])
  })

  it('dispatches a final frame without a trailing blank line on flush', () => {
    expect(parseChunks(['event: done\ndata: {"ok":true}'])).toEqual([{ event: 'done', data: '{"ok":true}' }])
  })

  it('keeps the id of each frame so a client can resume after it', () => {
    expect(parseWithIds(['id: 1760-0\nevent: delta\ndata: {"text":"a"}\n\nevent: done\ndata: {}\n\n'])).toEqual([
      { event: 'delta', data: '{"text":"a"}', id: '1760-0' },
      { event: 'done', data: '{}', id: '' },
    ])
  })
})

/** A fetch Response whose body hands out `chunks`, then waits (like a live stream) until aborted. */
function streamingResponse(chunks: string[], signal?: AbortSignal) {
  const encoder = new TextEncoder()
  const queue = chunks.map((chunk) => encoder.encode(chunk))
  const reader = {
    read: vi.fn(() => {
      const value = queue.shift()
      if (value) return Promise.resolve({ done: false as const, value })
      return new Promise<never>((_resolve, reject) => {
        signal?.addEventListener('abort', () => reject(new DOMException('The operation was aborted.', 'AbortError')), { once: true })
      })
    }),
    cancel: vi.fn(() => Promise.resolve()),
    releaseLock: vi.fn(),
  }
  const response = {
    ok: true,
    status: 200,
    statusText: 'OK',
    headers: new Headers({ 'content-type': 'text/event-stream' }),
    body: { getReader: () => reader },
  }
  return { response, reader }
}

describe('streamSse', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('cancels the reader when the stream is aborted, not just releases the lock', async () => {
    const controller = new AbortController()
    const { response, reader } = streamingResponse(['event: delta\ndata: {"text":"a"}\n\n'], controller.signal)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))
    const onMessage = vi.fn()

    const streaming = streamSse({ path: '/chat/stream', body: {}, signal: controller.signal, onMessage })
    await vi.waitFor(() => expect(onMessage).toHaveBeenCalledTimes(1))
    controller.abort()

    await expect(streaming).rejects.toThrow(/aborted/)
    expect(reader.cancel).toHaveBeenCalledTimes(1)
  })

  it('cancels the reader when a frame handler throws', async () => {
    const { response, reader } = streamingResponse(['event: delta\ndata: {"text":"a"}\n\n'])
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))

    const streaming = streamSse({
      path: '/chat/stream',
      onMessage: () => {
        throw new Error('handler failed')
      },
    })

    await expect(streaming).rejects.toThrow('handler failed')
    expect(reader.cancel).toHaveBeenCalledTimes(1)
  })

  it('cancels the reader after a stream that ended normally', async () => {
    const { response, reader } = streamingResponse([])
    reader.read.mockResolvedValueOnce({ done: true, value: undefined } as never)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response))

    await streamSse({ path: '/chat/stream', onMessage: vi.fn() })
    expect(reader.cancel).toHaveBeenCalledTimes(1)
  })
})
