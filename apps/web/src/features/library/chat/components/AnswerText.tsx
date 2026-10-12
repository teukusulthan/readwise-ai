import { useMemo } from 'react'

import { splitGeneralKnowledge } from '@/features/library/chat/utils/citations'
import { renderIcon } from '@/utils/icon-renderer'
import { AnswerMarkdown } from './AnswerMarkdown'

interface AnswerTextProps {
  text: string
  sourceNumbers: ReadonlySet<number>
  activeSource: number | null
  streaming: boolean
  onCite: (n: number) => void
}

const NO_SOURCES: ReadonlySet<number> = new Set()

/**
 * Renders the model's answer as safe Markdown with clickable [n] citation chips, then — if
 * present — the part from the model's general knowledge in its own labeled box, so it is
 * never mistaken for book content. Raw HTML in the answer is never rendered.
 */
export function AnswerText({ text, sourceNumbers, activeSource, streaming, onCite }: AnswerTextProps) {
  const [bookPart, generalPart] = useMemo(() => splitGeneralKnowledge(text), [text])

  const caret = <span className="ml-0.5 inline-block h-[1.1em] w-[2px] translate-y-[0.2em] animate-caret bg-primary" aria-hidden="true" />
  const caretInBook = streaming && generalPart === null

  return (
    <div className="flex max-w-[70ch] flex-col gap-4 text-body-lg leading-relaxed text-font-primary" data-testid="answer-text">
      <AnswerMarkdown text={bookPart} sourceNumbers={sourceNumbers} activeSource={activeSource} onCite={onCite} caret={caretInBook ? caret : undefined} />
      {generalPart !== null && (
        <section
          aria-label="From general knowledge"
          data-testid="general-knowledge"
          className="flex flex-col gap-3 rounded-xl border border-info-soft/70 bg-info-light/60 px-5 py-4 text-body-md"
        >
          <p className="flex items-center gap-2 text-label-md font-semibold uppercase tracking-wider text-info-bold">
            {renderIcon({ icon: 'globe-hemisphere-west', className: 'text-[16px]' })}
            General knowledge · not from your books
          </p>
          {/* No citation chips here: this part is not backed by your books. */}
          <AnswerMarkdown text={generalPart} sourceNumbers={NO_SOURCES} activeSource={null} onCite={onCite} caret={streaming ? caret : undefined} />
          {!generalPart.trim() && streaming && <p>{caret}</p>}
        </section>
      )}
    </div>
  )
}
