import { useMemo, useState } from 'react'

import { Expand } from '@/components/ui/expand'

import { UNCITED_ANSWER_META, UNGROUNDED_MODE_META, type IAnswerModeMeta } from '@/features/library/chat/constants/answer-modes'
import type { TAskPhase } from '@/features/library/chat/hooks/useAskStream'
import type { IAnswerSource, ISkippedBook } from '@/features/library/chat/types/chat.types'
import type { TMessageMode } from '@/features/library/chat/types/conversation.types'
import { citedBooks } from '@/features/library/chat/utils/chat-thread'
import type { IBook } from '@/features/library/types/book.types'
import { splitGeneralKnowledge } from '@/features/library/chat/utils/citations'
import { describeSkipReason } from '@/features/library/utils/format'
import { cn } from '@/utils/cn'
import { renderIcon } from '@/utils/icon-renderer'
import { AnswerProgress } from './AnswerProgress'
import { AnswerText } from './AnswerText'
import { CitedBooks } from './CitedBooks'
import { SourceList } from './SourceList'

/** What an answer bubble needs — built from a saved message or from the live stream. */
export interface IAssistantView {
  id: string
  content: string
  /** null while the answer is still streaming */
  mode: TMessageMode | null
  grounded: boolean
  sources: IAnswerSource[]
  skippedBooks: ISkippedBook[]
  model: string | null
  error: string | null
}

interface AssistantMessageProps {
  message: IAssistantView
  phase?: TAskPhase
  /** Play the entry animation (new answers only — not every saved message on load). */
  animate?: boolean
  /** Catalog by book id: enables the cover cards of the books the answer cites. */
  booksById?: ReadonlyMap<string, IBook>
}

function resolveBanner(mode: TMessageMode | null, grounded: boolean, content: string): IAnswerModeMeta | null {
  if (mode === null || mode === 'error' || mode === 'stopped') return null
  if (mode !== 'llm') return UNGROUNDED_MODE_META[mode]
  // Only the book part is expected to carry citations; a labeled general-knowledge section never does.
  const bookPart = splitGeneralKnowledge(content)[0].trim()
  return grounded || !bookPart ? null : UNCITED_ANSWER_META
}

export function AssistantMessage({ message, phase = 'done', animate = false, booksById }: AssistantMessageProps) {
  const [activeSource, setActiveSource] = useState<number | null>(null)
  const passagesAreTheAnswer = message.mode === 'retrieval_only'
  const [sourcesOpen, setSourcesOpen] = useState(passagesAreTheAnswer)
  const sourceNumbers = useMemo(() => new Set(message.sources.map((source) => source.n)), [message.sources])
  const citedCount = message.sources.filter((source) => source.cited).length
  const books = useMemo(() => citedBooks(message.sources), [message.sources])

  const streaming = phase === 'retrieving' || phase === 'generating'
  const banner = resolveBanner(message.mode, message.grounded, message.content)
  const failed = message.mode === 'error' || !!message.error

  const cite = (n: number) => {
    setSourcesOpen(true)
    setActiveSource(n)
  }

  return (
    <article className={cn('flex gap-4', animate && 'animate-message-in')} aria-busy={streaming} data-testid="assistant-message">
      <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary text-font-on-accent shadow-sm" aria-hidden="true">
        {renderIcon({ icon: 'book-open-text', className: 'text-[18px]' })}
      </span>

      <div className="flex min-w-0 flex-1 flex-col gap-4">
        {banner && (
          <div
            role="status"
            data-testid="ungrounded-banner"
            data-tone={banner.tone}
            className={cn(
              'flex items-start gap-3 rounded-xl border px-4 py-3',
              banner.tone === 'info' ? 'border-info-soft/70 bg-info-light' : 'border-warning-soft/70 bg-warning-light',
            )}
          >
            {renderIcon({ icon: banner.icon, className: cn('mt-0.5 text-[20px]', banner.tone === 'info' ? 'text-info-bold' : 'text-warning-bold') })}
            <div className="text-body-md">
              <p className="font-semibold text-font-primary">{banner.title}</p>
              <p className="text-font-secondary">{banner.description}</p>
            </div>
          </div>
        )}

        {message.skippedBooks.length > 0 && (
          <div role="note" className="flex items-start gap-2 rounded-xl bg-background-secondary px-4 py-3 text-body-sm text-font-secondary">
            {renderIcon({ icon: 'info', className: 'mt-0.5 text-[16px]' })}
            <span>
              Not searched: {message.skippedBooks.map((book) => `${book.title ?? book.id} (${describeSkipReason(book.reason)})`).join(', ')}
            </span>
          </div>
        )}

        {streaming && !message.content ? (
          <AnswerProgress phase={phase} sourceCount={message.sources.length} />
        ) : (
          message.content && (
            <AnswerText text={message.content} sourceNumbers={sourceNumbers} activeSource={activeSource} streaming={streaming} onCite={cite} />
          )
        )}

        {failed && (
          <div role="alert" className="flex items-start gap-3 rounded-xl border border-error-soft/70 bg-error-light px-4 py-3 text-body-md text-error-bold">
            {renderIcon({ icon: 'warning-circle', className: 'mt-0.5 text-[20px]' })}
            <div>
              <p className="font-semibold">The answer could not be completed</p>
              <p>{message.error ?? 'Something went wrong. Please ask again.'}</p>
            </div>
          </div>
        )}

        {message.mode === 'stopped' && (
          <p className="flex items-center gap-1.5 text-body-sm text-font-placeholder">
            {renderIcon({ icon: 'stop-circle', className: 'text-[15px]' })}
            {message.content ? 'You stopped this answer.' : 'You stopped this answer before it started.'}
          </p>
        )}

        {!streaming && booksById && <CitedBooks books={books} booksById={booksById} />}

        {!streaming && (message.sources.length > 0 || message.model) && (
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            {message.sources.length > 0 && (
              <button
                type="button"
                aria-expanded={sourcesOpen}
                aria-label={`${message.sources.length} ${message.sources.length === 1 ? 'source' : 'sources'}${citedCount ? `, ${citedCount} cited` : ''}`}
                onClick={() => setSourcesOpen((open) => !open)}
                className="inline-flex h-9 items-center gap-2 rounded-lg border border-border-primary bg-background-primary px-3 text-body-sm font-medium text-font-secondary shadow-xs transition-colors hover:border-border-secondary hover:text-font-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {renderIcon({ icon: 'books', className: 'text-[16px]' })}
                {message.sources.length} {message.sources.length === 1 ? 'source' : 'sources'}
                {citedCount > 0 && <span className="text-primary-bold">· {citedCount} cited</span>}
                {renderIcon({ icon: 'caret-down', className: cn('text-[14px] transition-transform duration-200', sourcesOpen && 'rotate-180') })}
              </button>
            )}
            {message.model && (
              <span className="flex items-center gap-1.5 text-body-sm text-font-placeholder">
                {renderIcon({ icon: 'sparkle', className: 'text-[14px]' })}
                {message.model}
              </span>
            )}
          </div>
        )}

        <Expand open={sourcesOpen && !streaming}>
          <SourceList sources={message.sources} activeSource={activeSource} expandAll={passagesAreTheAnswer} idPrefix={`msg-${message.id}`} />
        </Expand>
      </div>
    </article>
  )
}
