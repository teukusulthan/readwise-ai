import { describe, expect, it } from 'vitest'

import type { IConversation, TChatMessage } from '@/features/library/chat/types/conversation.types'
import { citedBooks, groupConversations, pendingVisibility, suggestedQuestions } from './chat-thread'

const conversation = (id: string, updatedAt: string): IConversation => ({ id, title: id, bookIds: [], createdAt: updatedAt, updatedAt })
const user = (content: string): TChatMessage => ({ id: content, role: 'user', content, bookIds: [], createdAt: '' })
const assistant = (content: string): TChatMessage => ({
  id: `a-${content}`,
  role: 'assistant',
  content,
  mode: 'llm',
  grounded: true,
  sources: [],
  skippedBooks: [],
  model: null,
  error: null,
  createdAt: '',
})

describe('groupConversations', () => {
  it('buckets by last activity and keeps order', () => {
    const now = new Date(2026, 9, 9, 15, 0)
    const groups = groupConversations(
      [
        conversation('a', new Date(2026, 9, 9, 9, 0).toISOString()),
        conversation('b', new Date(2026, 9, 8, 22, 0).toISOString()),
        conversation('c', new Date(2026, 9, 4, 12, 0).toISOString()),
        conversation('d', new Date(2026, 8, 1, 12, 0).toISOString()),
      ],
      now,
    )
    expect(groups.map((g) => [g.label, g.items.map((c) => c.id)])).toEqual([
      ['Today', ['a']],
      ['Yesterday', ['b']],
      ['Previous 7 days', ['c']],
      ['Older', ['d']],
    ])
  })
})

describe('pendingVisibility', () => {
  it('shows the live turn until the saved copy arrives', () => {
    const before = [user('Q1'), assistant('A1')]
    expect(pendingVisibility(before, 2, 'Q2')).toEqual({ showQuestion: true, showAnswer: true })
    expect(pendingVisibility([...before, user('Q2')], 2, 'Q2')).toEqual({ showQuestion: false, showAnswer: true })
    expect(pendingVisibility([...before, user('Q2'), assistant('A2')], 2, 'Q2')).toEqual({ showQuestion: false, showAnswer: false })
  })

  it('ignores an identical earlier question', () => {
    expect(pendingVisibility([user('Q'), assistant('A')], 2, 'Q')).toEqual({ showQuestion: true, showAnswer: true })
  })
})

describe('suggestedQuestions', () => {
  it('uses book titles and handles an empty library', () => {
    expect(suggestedQuestions([])).toEqual([])
    expect(suggestedQuestions(['Dune', 'Hujan'])).toHaveLength(3)
    expect(suggestedQuestions(['Dune'])[0]).toContain('“Dune”')
  })
})

describe('citedBooks', () => {
  const source = (n: number, bookId: string, cited: boolean) => ({
    n, bookId, bookTitle: `Book ${bookId}`, headings: [], pageStart: 1, pageEnd: 1, score: 0.7, text: 't', cited,
  })

  it('lists only cited books, in first-citation order, with passage counts', () => {
    const books = citedBooks([source(1, 'tm', false), source(2, 'ww', true), source(3, 'tm', true), source(4, 'tm', true), source(5, 'x', false)])
    expect(books).toEqual([
      { bookId: 'ww', bookTitle: 'Book ww', citedCount: 1 },
      { bookId: 'tm', bookTitle: 'Book tm', citedCount: 2 },
    ])
  })

  it('is empty when nothing is cited', () => {
    expect(citedBooks([source(1, 'a', false)])).toEqual([])
  })
})
