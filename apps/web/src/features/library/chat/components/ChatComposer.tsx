import { useLayoutEffect, useRef, useState } from 'react'

import { Expand } from '@/components/ui/expand'
import { Hint } from '@/components/ui/tooltip'
import { askSchema } from '@/features/library/chat/schemas/ask.schema'
import type { IBook } from '@/features/library/types/book.types'
import { cn } from '@/utils/cn'
import { renderIcon } from '@/utils/icon-renderer'
import { BookSelector } from '@/features/library/components/BookSelector'

interface ChatComposerProps {
  books: IBook[] | undefined
  booksLoading: boolean
  booksError: Error | null
  selectedIds: string[]
  onSelectedIdsChange: (ids: string[]) => void
  isStreaming: boolean
  /** Send is held back (e.g. a stopped answer is still closing); typing stays possible. */
  sendBlocked?: boolean
  disabled: boolean
  onSend: (question: string) => void
  onStop: () => void
  /** Set to put text in the box from outside (e.g. a suggested question). */
  draft?: { text: string; key: number }
}

const MAX_TEXTAREA_PX = 200

/** Message box pinned under the thread. Enter sends, Shift+Enter adds a line. */
export function ChatComposer({
  books,
  booksLoading,
  booksError,
  selectedIds,
  onSelectedIdsChange,
  isStreaming,
  sendBlocked = false,
  disabled,
  onSend,
  onStop,
  draft,
}: ChatComposerProps) {
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [scopeOpen, setScopeOpen] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useLayoutEffect(() => {
    if (!draft) return
    setText(draft.text)
    textareaRef.current?.focus()
  }, [draft])

  // Grow with the content up to MAX_TEXTAREA_PX, then scroll inside the box.
  useLayoutEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_TEXTAREA_PX)}px`
  }, [text])

  const submit = () => {
    if (isStreaming || sendBlocked || disabled) return
    const parsed = askSchema.safeParse({ question: text })
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message ?? 'Invalid question')
      return
    }
    setError(null)
    setScopeOpen(false)
    onSend(parsed.data.question)
    setText('')
  }

  const scopeLabel =
    selectedIds.length === 0
      ? 'All indexed books'
      : selectedIds.length === 1
        ? (books?.find((book) => book.id === selectedIds[0])?.title ?? '1 book')
        : `${selectedIds.length} books`

  return (
    <div className="flex flex-col gap-2">
      <form
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
        className="overflow-hidden rounded-2xl border border-border-primary bg-card shadow-md transition-[border-color,box-shadow] duration-300 ease-fluid hover:border-border-secondary focus-within:border-primary-soft focus-within:shadow-lg focus-within:hover:border-primary-soft"
      >
        <Expand open={scopeOpen}>
          <div className="border-b border-border-primary bg-background-page px-5 py-4">
            <BookSelector books={books} isLoading={booksLoading} error={booksError} selectedIds={selectedIds} onChange={onSelectedIdsChange} />
          </div>
        </Expand>

        <label htmlFor="chat-question" className="sr-only">
          Your question
        </label>
        <textarea
          id="chat-question"
          ref={textareaRef}
          rows={1}
          value={text}
          disabled={disabled}
          onChange={(event) => {
            setText(event.target.value)
            if (error) setError(null)
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault()
              submit()
            }
          }}
          placeholder={disabled ? 'Index a book in the catalog to start asking…' : 'Ask anything about your books…'}
          aria-invalid={!!error}
          aria-describedby={error ? 'chat-question-error' : undefined}
          className="block max-h-[200px] min-h-[3.5rem] w-full resize-none bg-transparent px-5 pt-4 pb-2 text-body-lg leading-relaxed text-font-primary placeholder:text-font-placeholder focus:outline-none disabled:cursor-not-allowed"
        />

        <div className="flex items-center justify-between gap-3 px-3 pb-3">
          <Hint label="Choose which books to ask">
            <button
              type="button"
              aria-expanded={scopeOpen}
              onClick={() => setScopeOpen((open) => !open)}
              className={cn(
                'inline-flex h-9 min-w-0 max-w-[60%] items-center gap-2 rounded-lg px-3 text-body-sm font-medium transition-[background-color,color,scale] duration-200 ease-fluid active:scale-[0.97] active:duration-75 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                scopeOpen || selectedIds.length ? 'bg-primary-light text-primary-bold' : 'text-font-secondary hover:bg-background-secondary hover:text-font-primary',
              )}
            >
              {renderIcon({ icon: 'books', className: 'text-[16px] shrink-0' })}
              <span className="truncate">{scopeLabel}</span>
              {renderIcon({ icon: 'caret-up', className: cn('text-[13px] shrink-0 transition-transform duration-300 ease-fluid', !scopeOpen && 'rotate-180') })}
            </button>
          </Hint>

          {isStreaming ? (
            <Hint label="Stop the answer">
              <button
                type="button"
                onClick={onStop}
                aria-label="Stop the answer"
                className="relative flex size-10 shrink-0 animate-pop-in items-center justify-center rounded-xl border border-border-primary bg-background-primary text-font-primary shadow-xs transition-[background-color,border-color,scale] duration-200 ease-fluid hover:border-border-secondary hover:bg-background-secondary active:scale-90 active:duration-75 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                {/* A soft ring pulses while the answer is being written. */}
                <span aria-hidden="true" className="absolute inset-0 animate-soft-ping rounded-xl border border-primary-soft" />
                {renderIcon({ icon: 'stop', weight: 'fill', className: 'text-[16px]' })}
              </button>
            </Hint>
          ) : (
            <Hint label="Send" shortcut="Enter">
              <button
                type="submit"
                aria-label="Send"
                disabled={disabled || sendBlocked || !text.trim()}
                className="group/send flex size-10 shrink-0 animate-pop-in items-center justify-center rounded-xl bg-primary text-font-on-accent shadow-sm transition-[background-color,opacity,scale,box-shadow] duration-200 ease-fluid not-disabled:hover:bg-primary-bold not-disabled:hover:shadow-md not-disabled:active:scale-90 not-disabled:active:duration-75 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-40"
              >
                {renderIcon({ icon: 'arrow-up', weight: 'bold', className: 'text-[18px] transition-transform duration-200 ease-fluid group-hover/send:-translate-y-0.5' })}
              </button>
            </Hint>
          )}
        </div>
      </form>

      {error ? (
        <p id="chat-question-error" role="alert" className="px-2 text-body-sm text-error-bold">
          {error}
        </p>
      ) : (
        <p className="px-2 text-center text-body-sm text-font-placeholder">
          Answers use your indexed books first, with sources; anything from general knowledge is labeled. <span className="hidden sm:inline">Enter to send · Shift + Enter for a new line.</span>
        </p>
      )}
    </div>
  )
}
