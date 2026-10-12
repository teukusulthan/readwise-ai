import type { IAnswerSource } from '@/features/library/chat/types/chat.types'
import type { IConversation, TChatMessage } from '@/features/library/chat/types/conversation.types'

export interface IConversationGroup {
  label: string
  items: IConversation[]
}

const DAY_MS = 24 * 60 * 60 * 1000

/** Sidebar groups by last activity: Today, Yesterday, Previous 7 days, Older (input is newest first). */
export function groupConversations(conversations: IConversation[], now: Date = new Date()): IConversationGroup[] {
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const bucket = (iso: string) => {
    const time = new Date(iso).getTime()
    if (time >= startOfToday) return 'Today'
    if (time >= startOfToday - DAY_MS) return 'Yesterday'
    if (time >= startOfToday - 7 * DAY_MS) return 'Previous 7 days'
    return 'Older'
  }
  const groups: IConversationGroup[] = []
  for (const conversation of conversations) {
    const label = bucket(conversation.updatedAt)
    const group = groups.find((g) => g.label === label)
    if (group) group.items.push(conversation)
    else groups.push({ label, items: [conversation] })
  }
  return groups
}

/**
 * The live turn (question + streaming answer) is drawn locally until the saved copy
 * shows up in the refetched conversation, then the saved messages take over.
 * `fromIndex`: how many saved messages existed when the question was sent.
 */
export function pendingVisibility(saved: TChatMessage[], fromIndex: number, question: string) {
  const userIndex = saved.findIndex((message, i) => i >= fromIndex && message.role === 'user' && message.content === question)
  if (userIndex === -1) return { showQuestion: true, showAnswer: true }
  return { showQuestion: false, showAnswer: saved[userIndex + 1]?.role !== 'assistant' }
}

/** Starter questions for an empty chat, built from the indexed book titles. */
export function suggestedQuestions(titles: string[]): string[] {
  const [first, second] = titles
  if (!first) return []
  const questions = [`What are the main ideas of “${first}”?`, `Summarize the first chapter of “${first}”.`]
  if (second) questions.push(`What do “${first}” and “${second}” have in common?`)
  else questions.push(`What advice does “${first}” give?`)
  return questions
}

export interface ICitedBook {
  bookId: string
  bookTitle: string
  /** How many of this book's passages the answer cites. */
  citedCount: number
}

/** Books an answer actually cites, in the order the answer first cites them (lowest source number first). */
export function citedBooks(sources: IAnswerSource[]): ICitedBook[] {
  const books = new Map<string, ICitedBook & { firstN: number }>()
  for (const source of sources) {
    if (!source.cited) continue
    const book = books.get(source.bookId)
    if (book) {
      book.citedCount += 1
      book.firstN = Math.min(book.firstN, source.n)
    } else {
      books.set(source.bookId, { bookId: source.bookId, bookTitle: source.bookTitle, citedCount: 1, firstN: source.n })
    }
  }
  return [...books.values()]
    .sort((a, b) => a.firstN - b.firstN)
    .map((book) => ({ bookId: book.bookId, bookTitle: book.bookTitle, citedCount: book.citedCount }))
}
