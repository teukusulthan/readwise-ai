import env from '@/config/env'

/**
 * Server-Sent Events over `fetch` (POST + JSON body, or GET to resume), for endpoints like /chat/stream.
 * `EventSource` can't send a POST body and axios can't stream in browsers, so this
 * small reader parses the `text/event-stream` format itself:
 *   - frames are separated by a blank line; CRLF / CR / LF line endings are accepted
 *   - `event:` sets the event name (default "message"), multiple `data:` lines are joined with "\n"
 *   - lines starting with ":" are comments (keep-alive pings) and are ignored
 */

export interface ISseMessage {
  event: string
  data: string
  /** The frame's `id:` (empty if none): send it back to resume after a disconnect. */
  id: string
}

export class SseHttpError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'SseHttpError'
    this.status = status
  }
}

/** Incremental parser: feed decoded text chunks in any size; complete frames are emitted. */
export function createSseParser(onMessage: (message: ISseMessage) => void) {
  let buffer = ''

  const dispatchBlock = (block: string) => {
    let event = 'message'
    let id = ''
    const data: string[] = []
    for (const line of block.split('\n')) {
      if (!line || line.startsWith(':')) continue
      const colon = line.indexOf(':')
      const field = colon === -1 ? line : line.slice(0, colon)
      let value = colon === -1 ? '' : line.slice(colon + 1)
      if (value.startsWith(' ')) value = value.slice(1)
      if (field === 'event') event = value || 'message'
      else if (field === 'data') data.push(value)
      else if (field === 'id' && !value.includes('\0')) id = value
      // `retry` is not used: reconnection is handled by the caller.
    }
    if (data.length) onMessage({ event, data: data.join('\n'), id })
  }

  return {
    push(chunk: string) {
      let text = buffer + chunk
      // A trailing "\r" may be the first half of a "\r\n" split across chunks — keep it for later.
      const pendingCR = text.endsWith('\r')
      if (pendingCR) text = text.slice(0, -1)
      text = text.replace(/\r\n?/g, '\n')

      const blocks = text.split('\n\n')
      buffer = blocks.pop() ?? ''
      if (pendingCR) buffer += '\r'
      blocks.forEach(dispatchBlock)
    },
    /** Call at end of stream: dispatches a final frame that had no trailing blank line. */
    flush() {
      const rest = buffer.replace(/\r\n?/g, '\n').trim()
      buffer = ''
      if (rest) dispatchBlock(rest)
    },
  }
}

interface IStreamSseOptions<TBody> {
  /** Path relative to the API base URL, e.g. API_ENDPOINTS.CHAT.STREAM */
  path: string
  /** POST with this JSON body; omit to GET (e.g. resuming a stream). */
  body?: TBody
  signal?: AbortSignal
  onMessage: (message: ISseMessage) => void
}

/** POST `body` and invoke `onMessage` for every SSE frame until the stream closes. */
export async function streamSse<TBody>({ path, body, signal, onMessage }: IStreamSseOptions<TBody>): Promise<void> {
  const response = await fetch(`${env.api.baseUrl}${path}`, {
    method: body === undefined ? 'GET' : 'POST',
    headers: body === undefined ? { Accept: 'text/event-stream' } : { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    credentials: 'include',
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  })

  if (!response.ok) throw new SseHttpError(await readErrorMessage(response), response.status)
  if (!response.body || !(response.headers.get('content-type') ?? '').includes('text/event-stream')) {
    throw new SseHttpError('The server did not return an event stream.', response.status)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  const parser = createSseParser(onMessage)
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      parser.push(decoder.decode(value, { stream: true }))
    }
    parser.push(decoder.decode())
    parser.flush()
  } finally {
    // Every exit (end, abort, a throwing handler) closes the connection, not just the lock.
    reader.cancel().catch(() => undefined)
    reader.releaseLock()
  }
}

/** Pull a human-readable message out of the backend's error envelope (or FastAPI validation errors). */
async function readErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    // Primary shape: top-level envelope. `detail` shapes are kept for back-compat / validation errors.
    if (body?.metaData?.message) return String(body.metaData.message)
    const detail = body?.detail
    if (typeof detail === 'string') return detail
    if (detail?.metaData?.message) return String(detail.metaData.message)
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg)
  } catch {
    // Not JSON — fall through to the status text.
  }
  return response.statusText || `Request failed with status ${response.status}`
}
