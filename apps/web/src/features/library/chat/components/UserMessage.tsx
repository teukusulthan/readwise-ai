import { cn } from '@/utils/cn'

interface UserMessageProps {
  content: string
  /** Play the entry animation (a question just sent). */
  animate?: boolean
}

export function UserMessage({ content, animate = false }: UserMessageProps) {
  return (
    <div className={cn('flex justify-end', animate && 'animate-message-in-right')} data-testid="user-message">
      <p className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-primary px-5 py-3 text-body-lg leading-relaxed text-font-on-accent shadow-sm">
        {content}
      </p>
    </div>
  )
}
