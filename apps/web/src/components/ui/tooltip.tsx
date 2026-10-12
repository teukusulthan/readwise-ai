'use client'

import * as React from 'react'
import * as TooltipPrimitive from '@radix-ui/react-tooltip'

import { cn } from '@/utils/cn'

const TooltipProvider = TooltipPrimitive.Provider

const Tooltip = TooltipPrimitive.Root

const TooltipTrigger = TooltipPrimitive.Trigger

const TooltipContent = React.forwardRef<React.ElementRef<typeof TooltipPrimitive.Content>, React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>>(
  ({ className, sideOffset = 6, ...props }, ref) => (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        ref={ref}
        sideOffset={sideOffset}
        className={cn(
          'z-50 max-w-xs rounded-lg bg-neutral-deep px-2.5 py-1.5 text-body-sm font-medium text-font-on-accent shadow-lg',
          'origin-(--radix-tooltip-content-transform-origin) animate-in fade-in-0 zoom-in-95 duration-150 ease-fluid',
          'data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95',
          'data-[side=bottom]:slide-in-from-top-1 data-[side=left]:slide-in-from-right-1 data-[side=right]:slide-in-from-left-1 data-[side=top]:slide-in-from-bottom-1',
          className,
        )}
        {...props}
      />
    </TooltipPrimitive.Portal>
  ),
)
TooltipContent.displayName = TooltipPrimitive.Content.displayName

interface HintProps {
  label: React.ReactNode
  children: React.ReactElement
  side?: React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>['side']
  /** Keyboard shortcut shown after the label, e.g. "Enter". */
  shortcut?: string
}

/** A small tooltip for icon-only controls (wraps the child as the trigger). */
function Hint({ label, children, side = 'top', shortcut }: HintProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent side={side}>
        <span className="flex items-center gap-2">
          {label}
          {shortcut && <kbd className="rounded bg-white/15 px-1.5 py-px font-sans text-label-sm">{shortcut}</kbd>}
        </span>
      </TooltipContent>
    </Tooltip>
  )
}

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider, Hint }
