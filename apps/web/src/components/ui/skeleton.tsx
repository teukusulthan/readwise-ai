import * as React from 'react'

import { cn } from '@/utils/cn'

/** Loading placeholder with a soft light sweep (styles/components.css .skeleton-shimmer). */
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div aria-hidden="true" className={cn('skeleton-shimmer rounded-xl', className)} {...props} />
}

export { Skeleton }
