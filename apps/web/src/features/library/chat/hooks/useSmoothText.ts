import { useEffect, useLayoutEffect, useRef, useState } from 'react'

/**
 * Reveals streamed text at a steady pace instead of in the bursts it arrives in.
 *
 * Some LLM providers (e.g. Kimi) send a few tokens, go quiet for ~3 s, then deliver
 * 100+ tokens within ~100 ms. The backend forwards every token as it gets it, so the
 * UI would jump by whole paragraphs. Here the not-yet-shown backlog is revealed at
 * `backlog / tau` characters per second: fast right after a burst, easing off until
 * the next one, so the text keeps moving instead of stalling and jumping.
 *
 *   stream  — the answer is still arriving
 *   finish  — the answer is complete: reveal the rest quickly
 *   instant — show everything now (stopped, failed, idle)
 */
export type TSmoothMode = 'stream' | 'finish' | 'instant'

const TAU_SECONDS: Record<Exclude<TSmoothMode, 'instant'>, number> = { stream: 1, finish: 0.4 }
/** Floor so a small backlog doesn't crawl. */
const MIN_CHARS_PER_SECOND = 60

/** Characters revealed after `elapsedMs` more milliseconds (fractional; capped at `total`). */
export function advanceReveal(shown: number, total: number, elapsedMs: number, mode: Exclude<TSmoothMode, 'instant'>): number {
  const backlog = total - shown
  if (backlog <= 0) return total
  const charsPerSecond = Math.max(MIN_CHARS_PER_SECOND, backlog / TAU_SECONDS[mode])
  return Math.min(total, shown + (charsPerSecond * elapsedMs) / 1000)
}

export function useSmoothText(target: string, mode: TSmoothMode): { text: string; catchingUp: boolean } {
  const [shown, setShown] = useState(() => (mode === 'instant' ? target.length : 0))

  // A shorter target (a new turn, or the final answer tidied up) can't keep characters it no longer has.
  const wanted = mode === 'instant' ? target.length : Math.min(shown, target.length)
  if (wanted !== shown) setShown(wanted)

  const catchingUp = mode !== 'instant' && wanted < target.length
  const latest = useRef({ target, mode, shown: wanted })
  useLayoutEffect(() => {
    latest.current = { target, mode, shown: wanted }
  })

  useEffect(() => {
    if (!catchingUp) return
    let frame = 0
    let last = performance.now()
    let position = latest.current.shown
    const tick = (now: number) => {
      const { target: text, mode: current } = latest.current
      if (current === 'instant') return
      position = advanceReveal(Math.min(position, text.length), text.length, Math.max(0, now - last), current)
      last = now
      setShown(Math.floor(position))
      // Keep ticking even when caught up: more text may arrive before the re-render ends this effect.
      frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [catchingUp])

  // Never cut a surrogate pair (emoji) in half.
  let end = wanted
  if (end > 0 && end < target.length && /[\uD800-\uDBFF]/.test(target[end - 1])) end += 1
  return { text: target.slice(0, end), catchingUp }
}
