import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AnswerProgress, progressLabel } from './AnswerProgress'

describe('AnswerProgress', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => vi.useRealTimers())

  it('maps stage and sources to a label', () => {
    expect(progressLabel('retrieving', 0)).toBe('Searching your books…')
    expect(progressLabel('retrieving', 6)).toBe('Reading 6 passages and thinking…')
    expect(progressLabel('generating', 1)).toBe('Reading 1 passage and thinking…')
    expect(progressLabel('generating', 0)).toBe('Thinking about your question…')
  })

  it('shows elapsed seconds only after 5 s and the slow hint only after 45 s', () => {
    render(<AnswerProgress phase="generating" sourceCount={4} />)
    expect(screen.getByTestId('answer-progress-label')).toHaveTextContent('Reading 4 passages and thinking…')
    expect(screen.queryByTestId('answer-progress-elapsed')).toBeNull()

    act(() => void vi.advanceTimersByTime(4000))
    expect(screen.queryByTestId('answer-progress-elapsed')).toBeNull()

    act(() => void vi.advanceTimersByTime(1000))
    expect(screen.getByTestId('answer-progress-elapsed')).toHaveTextContent('5s')
    expect(screen.queryByTestId('answer-progress-hint')).toBeNull()

    act(() => void vi.advanceTimersByTime(39000))
    expect(screen.getByTestId('answer-progress-elapsed')).toHaveTextContent('44s')
    expect(screen.queryByTestId('answer-progress-hint')).toBeNull()

    act(() => void vi.advanceTimersByTime(1000))
    expect(screen.getByTestId('answer-progress-hint')).toHaveTextContent(/long thinking is normal/i)
  })

  it('updates the label when sources arrive', () => {
    const { rerender } = render(<AnswerProgress phase="retrieving" sourceCount={0} />)
    expect(screen.getByTestId('answer-progress-label')).toHaveTextContent('Searching your books…')
    rerender(<AnswerProgress phase="retrieving" sourceCount={3} />)
    expect(screen.getByTestId('answer-progress-label')).toHaveTextContent('Reading 3 passages and thinking…')
  })
})
