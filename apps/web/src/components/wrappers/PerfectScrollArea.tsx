import { forwardRef, useEffect, useMemo, useState } from 'react'
import PerfectScrollbar from 'react-perfect-scrollbar'

import type { PerfectScrollAreaProps } from '@/types/perfect-scroll-area'
import { cn } from '@/utils/cn'
import { attachInertiaScroll, prefersReducedMotion } from './inertia-scroll'

// perfect-scrollbar's own wheel handler jumps instantly; with inertia we take the wheel ourselves.
const HANDLERS_WITH_INERTIA = ['click-rail', 'drag-thumb', 'keyboard', 'touch']

/**
 * Canonical scroll region for bounded in-app areas (react-perfect-scrollbar), with inertia
 * (momentum) wheel scrolling — see inertia-scroll.ts. Pass `inertia={false}` for the plain
 * behaviour; it is off automatically when the OS asks for reduced motion.
 * The parent must give it a bounded height, e.g. `relative min-h-0 flex-1`.
 * The forwarded ref points at the scroll container element.
 */
export const PerfectScrollArea = forwardRef<HTMLElement, PerfectScrollAreaProps & { inertia?: boolean }>(
  ({ className, children, options, inertia = true, ...props }, ref) => {
    const [container, setContainer] = useState<HTMLElement | null>(null)
    const smooth = inertia && !prefersReducedMotion()

    const contain = options?.wheelPropagation === false
    useEffect(() => (container && smooth ? attachInertiaScroll(container, { contain }) : undefined), [container, smooth, contain])

    const mergedOptions = useMemo(() => (smooth ? { handlers: HANDLERS_WITH_INERTIA, ...options } : options), [smooth, options])

    return (
      <PerfectScrollbar
        {...props}
        options={mergedOptions}
        className={cn('perfect-scroll-area min-h-0', className)}
        containerRef={(element) => {
          setContainer(element)
          if (typeof ref === 'function') ref(element)
          else if (ref) ref.current = element
        }}
      >
        {children}
      </PerfectScrollbar>
    )
  },
)

PerfectScrollArea.displayName = 'PerfectScrollArea'
