import { suggestedQuestions } from '@/features/library/chat/utils/chat-thread'
import { renderIcon } from '@/utils/icon-renderer'

interface ChatEmptyStateProps {
  bookTitles: string[]
  onPick: (question: string) => void
}

export function ChatEmptyState({ bookTitles, onPick }: ChatEmptyStateProps) {
  const suggestions = suggestedQuestions(bookTitles)

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-8 py-10 text-center">
      <div className="flex flex-col items-center gap-4">
        <span className="flex size-14 items-center justify-center rounded-2xl bg-primary text-font-on-accent shadow-md" aria-hidden="true">
          {renderIcon({ icon: 'book-open-text', className: 'text-[28px]' })}
        </span>
        <h1 className="font-serif text-h2 font-semibold tracking-tight text-font-primary">What would you like to know?</h1>
        <p className="max-w-[52ch] text-body-lg text-font-secondary">
          Ask about people, events or ideas in your books. Answers cite the passages they come from, anything from the
          model’s general knowledge is clearly labeled, and your conversations are saved on the left.
        </p>
      </div>

      {suggestions.length > 0 && (
        <div className="grid w-full max-w-2xl gap-3 sm:grid-cols-3">
          {suggestions.map((question, index) => (
            <button
              key={question}
              type="button"
              onClick={() => onPick(question)}
              style={{ animationDelay: `${120 + index * 70}ms` }}
              className="group flex animate-message-in flex-col items-start gap-2 rounded-xl border border-border-primary bg-card p-4 text-left text-body-md text-font-primary shadow-xs transition-[border-color,box-shadow,translate,scale] duration-300 ease-fluid hover:-translate-y-1 hover:border-primary-soft hover:shadow-lg active:scale-[0.98] active:duration-75 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {renderIcon({ icon: 'chat-circle-text', className: 'text-[18px] text-primary transition-transform duration-300 ease-spring group-hover:-rotate-6 group-hover:scale-110' })}
              {question}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
