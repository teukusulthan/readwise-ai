/** Mirrors apps/backend/service/conversation.py (conversation_to_api / message_to_api). */
import type { IAnswerSource, ISkippedBook, TAnswerMode } from './chat.types'

export interface IConversation {
  id: string
  title: string
  /** Book scope of the latest question; empty = all indexed books. */
  bookIds: string[]
  createdAt: string
  updatedAt: string
  messageCount?: number
}

/** Answer modes of saved assistant messages: the live modes plus failed / cancelled answers. */
export type TMessageMode = TAnswerMode | 'error' | 'stopped'

export interface IUserMessage {
  id: string
  role: 'user'
  content: string
  bookIds: string[]
  createdAt: string
}

export interface IAssistantMessage {
  id: string
  role: 'assistant'
  content: string
  mode: TMessageMode
  grounded: boolean
  sources: IAnswerSource[]
  skippedBooks: ISkippedBook[]
  model: string | null
  error: string | null
  createdAt: string
}

export type TChatMessage = IUserMessage | IAssistantMessage

export interface IConversationDetail extends IConversation {
  messages: TChatMessage[]
}

export interface IConversationRenamePayload {
  id: string
  title: string
}

export interface IConversationDeleteResult {
  id: string
  deleted: boolean
}
