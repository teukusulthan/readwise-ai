import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { advanceReveal, useSmoothText, type TSmoothMode } from './useSmoothText'

describe('advanceReveal', () => {
  it('reveals a large backlog fast and a small one at the floor rate', () => {
    // 600 chars behind, tau 1 s → 600 chars/s → 60 chars in 100 ms
    expect(advanceReveal(0, 600, 100, 'stream')).toBeCloseTo(60)
    // 10 chars behind → floor of 60 chars/s → 6 chars in 100 ms
    expect(advanceReveal(0, 10, 100, 'stream')).toBeCloseTo(6)
  })

  it('finishes faster than it streams', () => {
    expect(advanceReveal(0, 600, 100, 'finish')).toBeGreaterThan(advanceReveal(0, 600, 100, 'stream'))
  })

  it('never overshoots the text', () => {
    expect(advanceReveal(0, 50, 10_000, 'stream')).toBe(50)
    expect(advanceReveal(80, 50, 16, 'stream')).toBe(50)
  })
})

describe('useSmoothText', () => {
  beforeEach(() => vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'cancelAnimationFrame', 'performance'] }))
  afterEach(() => vi.useRealTimers())

  const render = (target: string, mode: TSmoothMode) =>
    renderHook(({ target, mode }) => useSmoothText(target, mode), { initialProps: { target, mode } })

  it('spreads a burst over several frames instead of showing it at once', () => {
    const burst = 'x'.repeat(600)
    const { result, rerender } = render('', 'stream')
    rerender({ target: burst, mode: 'stream' })
    expect(result.current.text).toBe('')
    expect(result.current.catchingUp).toBe(true)

    act(() => vi.advanceTimersByTime(100))
    const partial = result.current.text.length
    expect(partial).toBeGreaterThan(0)
    expect(partial).toBeLessThan(burst.length)

    act(() => vi.advanceTimersByTime(10_000))
    expect(result.current.text).toBe(burst)
    expect(result.current.catchingUp).toBe(false)
  })

  it('keeps revealing text that arrives after it caught up', () => {
    const { result, rerender } = render('', 'stream')
    rerender({ target: 'Hello', mode: 'stream' })
    act(() => vi.advanceTimersByTime(1000))
    expect(result.current.text).toBe('Hello')

    rerender({ target: 'Hello world', mode: 'stream' })
    act(() => vi.advanceTimersByTime(1000))
    expect(result.current.text).toBe('Hello world')
  })

  it('shows everything at once in instant mode and restarts for a new turn', () => {
    const { result, rerender } = render('', 'stream')
    rerender({ target: 'A stopped answer', mode: 'instant' })
    expect(result.current.text).toBe('A stopped answer')
    expect(result.current.catchingUp).toBe(false)

    rerender({ target: '', mode: 'stream' })
    rerender({ target: 'Next answer', mode: 'stream' })
    expect(result.current.text).toBe('')
  })

  it('keeps its place when the final answer is a tidied, shorter version', () => {
    const { result, rerender } = render('', 'stream')
    rerender({ target: 'One.\n\n\nTwo.  ', mode: 'stream' })
    act(() => vi.advanceTimersByTime(1000))
    rerender({ target: 'One.\n\nTwo.', mode: 'finish' })
    expect(result.current.text).toBe('One.\n\nTwo.')
    expect(result.current.catchingUp).toBe(false)
  })

  it('does not split an emoji', () => {
    const { result, rerender } = render('', 'stream')
    rerender({ target: 'a😀b', mode: 'stream' })
    act(() => vi.advanceTimersByTime(20))
    expect(result.current.text).not.toMatch(/[\uD800-\uDBFF]$/)
  })
})
