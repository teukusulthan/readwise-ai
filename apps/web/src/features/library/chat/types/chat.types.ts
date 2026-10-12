/** Mirrors the backend /chat/ask and /search/query responses (apps/backend/service/rag.py, search.py). */
import type { IConversation } from './conversation.types'

export type TAnswerMode = 'llm' | 'general_knowledge' | 'insufficient_context' | 'no_context' | 'no_indexed_books' | 'retrieval_only'

export interface ISkippedBook {
  id: string
  title: string | null
  /** `not_found` or `not_indexed:<status>` */
  reason: string
}

export interface IAnswerSource {
  n: number
  bookId: string
  bookTitle: string
  headings: string[]
  pageStart: number | null
  pageEnd: number | null
  score: number
  text: string
  cited: boolean
}

export interface IChatAnswer {
  question: string
  answer: string
  grounded: boolean
  mode: TAnswerMode
  model: string | null
  sources: IAnswerSource[]
  skippedBooks: ISkippedBook[]
  /** Part of the answer comes from the model's general knowledge (the "GENERAL KNOWLEDGE:" section). */
  usedGeneralKnowledge?: boolean
}

export interface IChatAskPayload {
  question: string
  bookIds?: string[]
  topK?: number
  /** /chat/stream: continue this saved conversation; omit to start a new one. */
  conversationId?: string
}

export interface ISearchResult {
  bookId: string
  bookTitle: string
  chunkIndex: number
  text: string
  headings: string[]
  pageStart: number | null
  pageEnd: number | null
  score: number
}

export interface ISearchResponse {
  query: string
  results: ISearchResult[]
  searchedBookCount: number
  skippedBooks: ISkippedBook[]
}

export interface ISearchPayload {
  query: string
  bookIds?: string[]
  topK?: number
}

/* ── Streaming (/chat/stream, Server-Sent Events) ─────────────────────── */

export type TStreamStage = 'retrieving' | 'generating'

export interface IStreamSources {
  question: string
  sources: IAnswerSource[]
  skippedBooks: ISkippedBook[]
  model: string | null
}

export interface IStreamError {
  message: string
  code?: number
  /** Set when the failed answer was saved to the conversation. */
  messageId?: string
}

/** `done` payload of /chat/stream: the /chat/ask answer plus where it was saved. */
export interface IStreamDone extends IChatAnswer {
  conversationId?: string
  messageId?: string
}

/** Answer still being generated for a conversation (GET /chat/active). */
export interface IActiveSession {
  active: boolean
  sessionId: string
  conversationId: string
}

/** Typed form of the SSE frames sent by POST /chat/stream and GET /chat/stream/{sessionId}. */
export type TChatStreamEvent =
  | { type: 'session'; sessionId: string }
  | { type: 'conversation'; conversation: IConversation }
  | { type: 'status'; stage: TStreamStage }
  | { type: 'sources'; payload: IStreamSources }
  | { type: 'delta'; text: string }
  | { type: 'done'; answer: IStreamDone }
  | { type: 'error'; error: IStreamError }
  | { type: 'cancelled'; message: string }
