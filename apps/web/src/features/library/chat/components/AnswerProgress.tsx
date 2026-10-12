import { useEffect, useState } from 'react'

import type { TAskPhase } from '@/features/library/chat/hooks/useAskStream'

/** Show the elapsed-seconds counter once the wait stops feeling instant. */
export const ELAPSED_AFTER_S = 5
/** After this long, say that slow thinking is normal for the configured model. */
export const SLOW_HINT_AFTER_S = 45

interface AnswerProgressProps {
  phase: TAskPhase
  /** Passages found for this turn (arrives before generation starts). */
  sourceCount: number
}

/** Stage text, derived from state only so a live turn and a re-attached one read the same. */
export function progressLabel(phase: TAskPhase, sourceCount: number): string {
  if (phase === 'generating' || sourceCount > 0) {
    return sourceCount > 0 ? `Reading ${sourceCount} ${sourceCount === 1 ? 'passage' : 'passages'} and thinking…` : 'Thinking about your question…'
  }
  return 'Searching your books…'
}

/** Whole seconds since mount (the pending bubble is mounted exactly while the turn waits). */
function useElapsedSeconds() {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const startedAt = Date.now()
    const timer = setInterval(() => setSeconds(Math.floor((Date.now() - startedAt) / 1000)), 1000)
    return () => clearInterval(timer)
  }, [])
  return seconds
}

export function AnswerProgress({ phase, sourceCount }: AnswerProgressProps) {
  const seconds = useElapsedSeconds()
  return (
    <div className="flex min-h-9 flex-col justify-center gap-1 text-body-md text-font-secondary" data-testid="answer-progress">
      <div className="flex items-center gap-3">
        <span className="flex gap-1" aria-hidden="true">
          <span className="size-2 animate-typing rounded-full bg-primary motion-reduce:animate-none" />
          <span className="size-2 animate-typing rounded-full bg-primary [animation-delay:160ms] motion-reduce:animate-none" />
          <span className="size-2 animate-typing rounded-full bg-primary [animation-delay:320ms] motion-reduce:animate-none" />
        </span>
        <span data-testid="answer-progress-label">{progressLabel(phase, sourceCount)}</span>
        {seconds >= ELAPSED_AFTER_S && (
          // aria-hidden: a per-second counter must not be re-announced by the polite live region.
          <span className="tabular-nums text-font-placeholder" aria-hidden="true" data-testid="answer-progress-elapsed">
            {seconds}s
          </span>
        )}
      </div>
      {seconds >= SLOW_HINT_AFTER_S && (
        <p className="pl-[calc(0.5rem*3+0.25rem*2+0.75rem)] text-body-sm text-font-placeholder" data-testid="answer-progress-hint">
          Long thinking is normal for this model — the answer will start streaming as soon as it is ready.
        </p>
      )}
    </div>
  )
}
