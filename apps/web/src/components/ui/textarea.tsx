import * as React from 'react'

import { cn } from '@/utils/cn'

const Textarea = React.forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      'flex min-h-24 w-full rounded-xl border border-border-primary bg-background-primary px-4 py-3 text-body-lg leading-relaxed text-font-primary shadow-xs transition-[border-color,box-shadow] duration-200 placeholder:text-font-placeholder hover:border-border-secondary',
      'focus-visible:border-primary focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary-light disabled:cursor-not-allowed disabled:opacity-50',
      'aria-[invalid=true]:border-error',
      className,
    )}
    {...props}
  />
))
Textarea.displayName = 'Textarea'

export { Textarea }
