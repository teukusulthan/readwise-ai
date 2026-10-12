import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/utils/cn'

const badgeVariants = cva('inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-body-md font-medium leading-snug transition-colors', {
  variants: {
    variant: {
      default: 'border-transparent bg-primary text-font-on-accent',
      secondary: 'border-secondary-soft bg-secondary-light text-secondary-bold',
      destructive: 'border-error-soft/70 bg-error-light text-error-bold',
      outline: 'border-border-primary text-font-secondary',
      success: 'border-success-soft/70 bg-success-light text-success-bold',
      warning: 'border-warning-soft/70 bg-warning-light text-warning-bold',
      info: 'border-info-soft/70 bg-info-light text-info-bold',
      neutral: 'border-border-primary bg-neutral-soft text-font-secondary',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
})

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
