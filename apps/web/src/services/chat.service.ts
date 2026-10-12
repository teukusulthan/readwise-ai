import type { IActiveSession, IChatAnswer, IChatAskPayload, IStreamDone, TChatStreamEvent } from '@/features/library/chat/types/chat.types'
import type { IConversation } from '@/features/library/chat/types/conversation.types'
import type { ApiResponse } from '@/types/api'
import { API_ENDPOINTS } from './api-endpoints'
import { apiRequests } from './api-factory.service'
import { streamSse, type ISseMessage } from './sse-client'

interface IStreamOptions {
  signal?: AbortSignal
  /** `id`: the frame's event id — remember the last one to resume after a disconnect. */
  onEvent: (event: TChatStreamEvent, id: string) => void
}

/**
 * Map one raw SSE frame to a typed chat event. Unknown event names are ignored; a frame whose
 * data is not a JSON object is skipped with a warning (one bad frame must not end the answer).
 */
export function toChatStreamEvent({ event, data, id }: ISseMessage): TChatStreamEvent | null {
  let payload
  try {
    payload = JSON.parse(data)
  } catch {
    payload = undefined
  }
  if (typeof payload !== 'object' || payload === null) {
    console.warn(`Skipped a "${event}" stream frame${id ? ` (id ${id})` : ''}: its data is not a JSON object.`)
    return null
  }
  switch (event) {
    case 'session':
      return typeof payload.sessionId === 'string' ? { type: 'session', sessionId: payload.sessionId } : null
    case 'cancelled':
      return { type: 'cancelled', message: payload.message ?? 'The answer was stopped.' }
    case 'conversation':
      return { type: 'conversation', conversation: payload as IConversation }
    case 'status':
      return { type: 'status', stage: payload.stage }
    case 'sources':
      return { type: 'sources', payload }
    case 'delta':
      return typeof payload.text === 'string' ? { type: 'delta', text: payload.text } : null
    case 'done':
      return { type: 'done', answer: payload as IStreamDone }
    case 'error':
      return {
        type: 'error',
        error: { message: payload.message ?? 'The answer could not be generated.', code: payload.code, messageId: payload.messageId },
      }
    default:
      return null
  }
}

/** Grounded question answering (apps/backend/router/chat.py). */
export const chatService = {
  /** Whole answer at once. */
  ask: (payload: IChatAskPayload): Promise<ApiResponse<IChatAnswer>> => apiRequests.post<IChatAnswer, IChatAskPayload>(API_ENDPOINTS.CHAT.ASK, payload),

  /**
   * One saved chat turn: session → conversation → status → sources → delta… → done | error | cancelled.
   * The answer is generated server-side and survives a disconnect — see `resume`. Resolves when the stream closes.
   */
  stream: (payload: IChatAskPayload, { signal, onEvent }: IStreamOptions): Promise<void> =>
    streamSse({ path: API_ENDPOINTS.CHAT.STREAM, body: payload, signal, onMessage: toHandler(onEvent) }),

  /** Re-attach to a running (or just finished) answer: every event after `afterId` ('0' = all), then live ones. */
  resume: (sessionId: string, afterId: string, { signal, onEvent }: IStreamOptions): Promise<void> =>
    streamSse({ path: `${API_ENDPOINTS.CHAT.SESSION(sessionId)}?after=${encodeURIComponent(afterId)}`, signal, onMessage: toHandler(onEvent) }),

  /** Stop generating (closing the connection no longer does). */
  cancel: (sessionId: string): Promise<ApiResponse<{ cancelled: boolean }>> =>
    apiRequests.post<{ cancelled: boolean }, null>(`${API_ENDPOINTS.CHAT.SESSION(sessionId)}/cancel`, null),

  /** Is an answer of this conversation still being generated (e.g. after a page reload)? */
  active: (conversationId: string): Promise<ApiResponse<IActiveSession>> => apiRequests.get<IActiveSession>(API_ENDPOINTS.CHAT.ACTIVE, { conversationId }),
}

function toHandler(onEvent: IStreamOptions['onEvent']) {
  return (message: ISseMessage) => {
    const event = toChatStreamEvent(message)
    if (event) onEvent(event, message.id)
  }
}
