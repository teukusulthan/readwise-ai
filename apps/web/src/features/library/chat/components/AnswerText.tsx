import { Fragment, useMemo } from 'react'

import { segmentCitations, splitGeneralKnowledge, splitParagraphs, toBlocks, type TAnswerBlock } from '@/features/library/chat/utils/citations'
import { cn } from '@/utils/cn'
import { renderIcon } from '@/utils/icon-renderer'

interface AnswerTextProps {
  text: string
  sourceNumbers: ReadonlySet<number>
  activeSource: number | null
  streaming: boolean
  onCite: (n: number) => void
}

const NO_SOURCES: ReadonlySet<number> = new Set()

/**
 * Renders the model's answer: paragraphs and lists with clickable [n] citation chips, then —
 * if present — the part from the model's general knowledge in its own labeled box, so it is
 * never mistaken for book content. Everything is React text/elements: output is never HTML.
 */
export function AnswerText({ text, sourceNumbers, activeSource, streaming, onCite }: AnswerTextProps) {
  const [bookBlocks, generalBlocks] = useMemo(() => {
    const [bookPart, generalPart] = splitGeneralKnowledge(text)
    return [toBlocks(splitParagraphs(bookPart)), generalPart === null ? null : toBlocks(splitParagraphs(generalPart))]
  }, [text])

  const caret = <span className="ml-0.5 inline-block h-[1.1em] w-[2px] translate-y-[0.2em] animate-caret bg-primary" aria-hidden="true" />
  const caretInBook = streaming && generalBlocks === null

  const renderInline = (content: string, sources: ReadonlySet<number>) =>
    segmentCitations(content, sources).map((segment, i) =>
      segment.type === 'text' ? (
        <Fragment key={i}>{segment.text}</Fragment>
      ) : (
        <button
          key={i}
          type="button"
          onClick={() => onCite(segment.n)}
          aria-label={`Show source ${segment.n}`}
          data-citation={segment.n}
          className={cn(
            'mx-0.5 inline-flex h-6 min-w-6 -translate-y-px items-center justify-center rounded-md px-1.5 align-middle text-label-md font-semibold leading-none transition-[background-color,color,scale,box-shadow] duration-200 ease-spring hover:scale-110 hover:shadow-sm active:scale-95 active:duration-75',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            activeSource === segment.n ? 'bg-primary text-font-on-accent' : 'bg-primary-light text-primary-bold hover:bg-primary-soft',
          )}
        >
          {segment.n}
        </button>
      ),
    )

  const renderBlocks = (blocks: TAnswerBlock[], sources: ReadonlySet<number>, withCaret: boolean) =>
    blocks.map((block, index) => {
      const tail = withCaret && index === blocks.length - 1 ? caret : null
      if (block.type === 'p') {
        return (
          <p key={index} className="whitespace-pre-line">
            {renderInline(block.text, sources)}
            {tail}
          </p>
        )
      }
      const List = block.type
      return (
        <List key={index} className={cn('flex flex-col gap-1.5 pl-6', block.type === 'ul' ? 'list-disc' : 'list-decimal')}>
          {block.items.map((item, i) => (
            <li key={i} className="pl-1 marker:text-font-placeholder">
              {renderInline(item, sources)}
              {tail && i === block.items.length - 1 ? tail : null}
            </li>
          ))}
        </List>
      )
    })

  return (
    <div className="flex max-w-[70ch] flex-col gap-4 text-body-lg leading-relaxed text-font-primary" data-testid="answer-text">
      {renderBlocks(bookBlocks, sourceNumbers, caretInBook)}
      {generalBlocks !== null && (
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
          {renderBlocks(generalBlocks, NO_SOURCES, streaming)}
          {generalBlocks.length === 0 && streaming && <p>{caret}</p>}
        </section>
      )}
    </div>
  )
}
