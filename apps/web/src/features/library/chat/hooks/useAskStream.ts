import { useCallback, useEffect, useReducer, useRef } from 'react'

import type { IAnswerSource, IChatAnswer, IChatAskPayload, ISkippedBook, TChatStreamEvent } from '@/features/library/chat/types/chat.types'
import type { IConversation } from '@/features/library/chat/types/conversation.types'
import { chatService } from '@/services/chat.service'
import { SseHttpError } from '@/services/sse-client'

/**
 * Streams one chat turn at a time. The answer is generated in a server-side session
 * (Redis) that outlives the connection, so this hook:
 *   - remembers the session id and the id of the last event received;
 *   - on a dropped connection, re-attaches with GET /chat/stream/{session}?after=<last id>
 *     (exponential backoff) — nothing is missed and nothing is shown twice;
 *   - `detach()` only closes the connection (the answer keeps going; `attach()` picks it up
 *     again, e.g. after a reload); `cancel()` asks the server to stop generating and stays
 *     `stopping` until the stream confirms (`cancelled`) or ends — at most STOP_GRACE_MS.
 * This is local, request-scoped UI state (a live stream, not cacheable server data),
 * so it lives in a reducer here rather than in TanStack Query or Zustand.
 */

export type TAskPhase = 'idle' | 'retrieving' | 'generating' | 'done' | 'error' | 'stopped'

export interface IAskStreamState {
  phase: TAskPhase
  /** Server-side session generating this answer (from the first `session` event). */
  sessionId: string | null
  /** The connection dropped and we are re-attaching to the session. */
  reconnecting: boolean
  /** Stop was pressed and the stream has not confirmed it yet: no new question until it does. */
  stopping: boolean
  /** The saved conversation this turn belongs to (announced first by the server). */
  conversation: IConversation | null
  question: string
  /** Answer text streamed so far (replaced by `final.answer` when done). */
  text: string
  sources: IAnswerSource[]
  skippedBooks: ISkippedBook[]
  model: string | null
  final: IChatAnswer | null
  error: string | null
}

export const INITIAL_ASK_STATE: IAskStreamState = {
  phase: 'idle',
  sessionId: null,
  reconnecting: false,
  stopping: false,
  conversation: null,
  question: '',
  text: '',
  sources: [],
  skippedBooks: [],
  model: null,
  final: null,
  error: null,
}

type TAction =
  | { type: 'start'; question: string }
  | { type: 'event'; event: TChatStreamEvent }
  | { type: 'fail'; message: string }
  | { type: 'stop' }
  | { type: 'reset' }
  | { type: 'reconnecting' }
  /** The stream is over (or we stopped waiting for it to confirm Stop). */
  | { type: 'ended' }

const isLive = (phase: TAskPhase) => phase === 'retrieving' || phase === 'generating'

export function askStreamReducer(state: IAskStreamState, action: TAction): IAskStreamState {
  if (action.type === 'start') return { ...INITIAL_ASK_STATE, phase: 'retrieving', question: action.question }
  if (action.type === 'fail') return { ...state, phase: 'error', reconnecting: false, stopping: false, error: action.message }
  if (action.type === 'reset') return INITIAL_ASK_STATE
  if (action.type === 'stop') return isLive(state.phase) ? { ...state, phase: 'stopped', reconnecting: false, stopping: true } : state
  if (action.type === 'reconnecting') return { ...state, reconnecting: true }
  if (action.type === 'ended') return state.stopping ? { ...state, stopping: false } : state

  const { event } = action
  // Any event means the connection is (again) healthy.
  const next = state.reconnecting ? { ...state, reconnecting: false } : state
  // After Stop, ignore pieces that were already on the way; only the final word counts.
  if (state.phase === 'stopped' && event.type !== 'cancelled' && event.type !== 'session') return next
  switch (event.type) {
    case 'session':
      return { ...next, sessionId: event.sessionId }
    case 'conversation':
      return { ...next, conversation: event.conversation }
    case 'status':
      return { ...next, phase: event.stage }
    case 'sources':
      return { ...next, sources: event.payload.sources, skippedBooks: event.payload.skippedBooks, model: event.payload.model }
    case 'delta':
      return { ...next, phase: 'generating', text: next.text + event.text }
    case 'done':
      return {
        ...next,
        phase: 'done',
        final: event.answer,
        text: event.answer.answer,
        sources: event.answer.sources,
        skippedBooks: event.answer.skippedBooks,
        model: event.answer.model,
      }
    case 'error':
      return { ...next, phase: 'error', error: event.error.message }
    case 'cancelled':
      return { ...next, phase: 'stopped', stopping: false }
  }
}

export interface IAskCallbacks {
  /** The turn's conversation is known (created now, or the one continued). */
  onConversation?: (conversation: IConversation) => void
  /** The stream ended (done, error, cancelled or gave up) — saved history may have changed. */
  onSettled?: (conversationId: string | null) => void
}

/** Re-attach attempts after a dropped connection: 1 s, 2 s, 4 s, 8 s, 8 s, 8 s. */
export const MAX_RECONNECTS = 6
export const reconnectDelayMs = (attempt: number) => Math.min(1000 * 2 ** (attempt - 1), 8000)
/** After Stop, wait at most this long for the stream to confirm before allowing a new question. */
export const STOP_GRACE_MS = 5000

type TOpen = (options: { signal: AbortSignal; onEvent: (event: TChatStreamEvent, id: string) => void }) => Promise<void>

function wait(ms: number, signal: AbortSignal) {
  return new Promise<void>((resolve) => {
    const timer = setTimeout(resolve, ms)
    signal.addEventListener('abort', () => {
      clearTimeout(timer)
      resolve()
    }, { once: true })
  })
}

export function useAskStream() {
  const [state, dispatch] = useReducer(askStreamReducer, INITIAL_ASK_STATE)
  const controllerRef = useRef<AbortController | null>(null)
  const sessionRef = useRef<{ id: string | null; cancelWhenKnown: boolean } | null>(null)
  const stopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearStopTimer = useCallback(() => {
    if (stopTimerRef.current) clearTimeout(stopTimerRef.current)
    stopTimerRef.current = null
  }, [])

  /** Close the connection only; the server keeps generating (re-attach with `attach`). */
  const detach = useCallback(() => {
    controllerRef.current?.abort()
    controllerRef.current = null
    sessionRef.current = null
    clearStopTimer()
  }, [clearStopTimer])

  /**
   * Ask the server to stop generating. The stream then ends with `cancelled` and history refreshes;
   * until then `isStopping` holds back a new question (at most STOP_GRACE_MS).
   */
  const cancel = useCallback(() => {
    const session = sessionRef.current
    if (!controllerRef.current || !session) return
    dispatch({ type: 'stop' })
    clearStopTimer()
    stopTimerRef.current = setTimeout(() => {
      stopTimerRef.current = null
      dispatch({ type: 'ended' })
    }, STOP_GRACE_MS)
    if (session.id) {
      void chatService.cancel(session.id).catch(() => {
        if (sessionRef.current !== session) return // a newer question already took over
        detach()
        dispatch({ type: 'ended' })
      })
    } else {
      session.cancelWhenKnown = true // Stop pressed before the server announced the session
    }
  }, [detach])

  const reset = useCallback(() => dispatch({ type: 'reset' }), [])

  /** Read a session's events until it ends, re-attaching after dropped connections. */
  const follow = useCallback(
    async (open: TOpen, callbacks: IAskCallbacks, knownSessionId: string | null, conversationId: string | null) => {
      controllerRef.current?.abort()
      clearStopTimer()
      const controller = new AbortController()
      controllerRef.current = controller
      const session = { id: knownSessionId, cancelWhenKnown: false }
      sessionRef.current = session
      let lastEventId = '0'
      let finished = false
      let attempt = 0

      const onEvent = (event: TChatStreamEvent, id: string) => {
        if (controller.signal.aborted) return
        if (id) lastEventId = id
        attempt = 0
        if (event.type === 'session') {
          session.id = event.sessionId
          if (session.cancelWhenKnown) void chatService.cancel(event.sessionId).catch(() => undefined)
        }
        if (event.type === 'done' || event.type === 'error' || event.type === 'cancelled') finished = true
        if (event.type === 'conversation') {
          conversationId = event.conversation.id
          callbacks.onConversation?.(event.conversation)
        }
        dispatch({ type: 'event', event })
      }

      let next: TOpen = open
      try {
        for (;;) {
          try {
            await next({ signal: controller.signal, onEvent })
            if (finished || controller.signal.aborted) return
            throw new Error('The answer stream ended unexpectedly.')
          } catch (error) {
            if (controller.signal.aborted) return
            // HTTP 4xx (bad request, auth) won't get better by retrying; network errors and 5xx might.
            const permanent = error instanceof SseHttpError && error.status < 500
            if (!session.id || permanent || attempt >= MAX_RECONNECTS) {
              dispatch({ type: 'fail', message: error instanceof Error ? error.message : 'Could not get an answer.' })
              return
            }
            attempt += 1
            dispatch({ type: 'reconnecting' })
            await wait(reconnectDelayMs(attempt), controller.signal)
            if (controller.signal.aborted) return
            const sessionId = session.id
            next = (options) => chatService.resume(sessionId, lastEventId, options)
          }
        }
      } finally {
        if (controllerRef.current === controller) {
          controllerRef.current = null
          sessionRef.current = null
          clearStopTimer()
          dispatch({ type: 'ended' })
        }
        if (!controller.signal.aborted) callbacks.onSettled?.(conversationId)
      }
    },
    [clearStopTimer],
  )

  /** Ask a new question (starts a server-side session). */
  const ask = useCallback(
    (payload: IChatAskPayload, callbacks: IAskCallbacks = {}) => {
      dispatch({ type: 'start', question: payload.question })
      return follow((options) => chatService.stream(payload, options), callbacks, null, payload.conversationId ?? null)
    },
    [follow],
  )

  /** Re-attach to an answer that is still being generated (e.g. after a reload): replays it from the start. */
  const attach = useCallback(
    (sessionId: string, question: string, conversationId: string, callbacks: IAskCallbacks = {}) => {
      dispatch({ type: 'start', question })
      return follow((options) => chatService.resume(sessionId, '0', options), callbacks, sessionId, conversationId)
    },
    [follow],
  )

  // Leaving the page only disconnects: the answer finishes and is saved server-side.
  useEffect(() => detach, [detach])

  return { state, ask, attach, cancel, detach, reset, isStreaming: isLive(state.phase), isStopping: state.stopping }
}
