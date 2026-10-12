import * as React from 'react'

import { cn } from '@/utils/cn'

interface ExpandProps {
  open: boolean
  children: React.ReactNode
  className?: string
}

/**
 * Animates its content's height open and closed (CSS grid rows 0fr ↔ 1fr, no measuring).
 * Content mounts on first open and stays mounted so closing can animate; while closed it is
 * hidden from assistive tech and can't be focused.
 */
export function Expand({ open, children, className }: ExpandProps) {
  const [mounted, setMounted] = React.useState(open)
  if (open && !mounted) setMounted(true)

  return (
    <div
      className={cn(
        'grid transition-[grid-template-rows,opacity] duration-[350ms] ease-fluid',
        open ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0',
        className,
      )}
      aria-hidden={!open}
      {...(!open ? { inert: '' } : {})}
    >
      <div className="min-h-0 overflow-hidden">{mounted && children}</div>
    </div>
  )
}
