import * as React from 'react'

import { cn } from '@/utils/cn'

const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(({ className, type, ...props }, ref) => (
  <input
    type={type}
    ref={ref}
    className={cn(
      'flex h-11 w-full rounded-xl border border-border-primary bg-background-primary px-4 py-2 text-body-md text-font-primary shadow-xs transition-[border-color,box-shadow] duration-200 placeholder:text-font-placeholder hover:border-border-secondary',
      'focus-visible:border-primary focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-primary-light disabled:cursor-not-allowed disabled:opacity-50',
      'file:mr-3 file:border-0 file:bg-transparent file:text-body-md file:font-medium file:text-font-primary',
      'aria-[invalid=true]:border-error',
      className,
    )}
    {...props}
  />
))
Input.displayName = 'Input'

export { Input }
