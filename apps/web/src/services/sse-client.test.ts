import { describe, expect, it } from 'vitest'

import { createSseParser, type ISseMessage } from './sse-client'

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
