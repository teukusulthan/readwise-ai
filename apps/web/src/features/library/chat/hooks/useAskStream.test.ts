import { describe, expect, it } from 'vitest'

import type { IChatAnswer } from '@/features/library/chat/types/chat.types'
import { askStreamReducer, INITIAL_ASK_STATE, type IAskStreamState } from './useAskStream'

const final: IChatAnswer = {
  question: 'Q?',
  answer: 'Final text [1].',
  grounded: true,
  mode: 'llm',
  model: 'm',
  sources: [{ n: 1, bookId: 'b', bookTitle: 'Book', headings: [], pageStart: 1, pageEnd: 1, score: 0.7, text: 'p', cited: true }],
  skippedBooks: [],
}

function run(...events: Parameters<typeof askStreamReducer>[1][]): IAskStreamState {
  return events.reduce(askStreamReducer, INITIAL_ASK_STATE)
}

describe('askStreamReducer', () => {
  it('accumulates deltas and switches to generating', () => {
    const state = run(
      { type: 'start', question: 'Q?' },
      { type: 'event', event: { type: 'status', stage: 'retrieving' } },
      { type: 'event', event: { type: 'delta', text: 'Hel' } },
      { type: 'event', event: { type: 'delta', text: 'lo' } },
    )
    expect(state.phase).toBe('generating')
    expect(state.text).toBe('Hello')
  })

  it('replaces streamed text with the final answer on done', () => {
    const state = run(
      { type: 'start', question: 'Q?' },
      { type: 'event', event: { type: 'delta', text: 'draft' } },
      { type: 'event', event: { type: 'done', answer: final } },
    )
    expect(state.phase).toBe('done')
    expect(state.text).toBe('Final text [1].')
    expect(state.final?.sources[0].cited).toBe(true)
  })

  it('keeps sources when the stream reports an error', () => {
    const state = run(
      { type: 'start', question: 'Q?' },
      { type: 'event', event: { type: 'sources', payload: { question: 'Q?', sources: final.sources, skippedBooks: [], model: null } } },
      { type: 'event', event: { type: 'error', error: { message: 'Rate limited', code: 503 } } },
    )
    expect(state.phase).toBe('error')
    expect(state.error).toBe('Rate limited')
    expect(state.sources).toHaveLength(1)
  })

  it('resets everything when a new question starts', () => {
    const state = run({ type: 'start', question: 'Old' }, { type: 'event', event: { type: 'delta', text: 'x' } }, { type: 'start', question: 'New' })
    expect(state).toEqual({ ...INITIAL_ASK_STATE, phase: 'retrieving', question: 'New' })
  })
})

describe('askStreamReducer — resumable sessions', () => {
  it('remembers the session and ends as stopped on cancelled', () => {
    const state = run(
      { type: 'start', question: 'Q?' },
      { type: 'event', event: { type: 'session', sessionId: 's1' } },
      { type: 'event', event: { type: 'delta', text: 'Part' } },
      { type: 'stop' },
      { type: 'event', event: { type: 'delta', text: ' late' } }, // already in flight when Stop was pressed
      { type: 'event', event: { type: 'cancelled', message: 'stopped' } },
    )
    expect(state.sessionId).toBe('s1')
    expect(state.phase).toBe('stopped')
    expect(state.text).toBe('Part')
  })

  it('shows reconnecting until the next event arrives', () => {
    const lost = run({ type: 'start', question: 'Q?' }, { type: 'reconnecting' })
    expect(lost.reconnecting).toBe(true)
    expect(askStreamReducer(lost, { type: 'event', event: { type: 'delta', text: 'x' } }).reconnecting).toBe(false)
  })
})
