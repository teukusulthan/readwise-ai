'use client'

import * as React from 'react'
import * as DialogPrimitive from '@radix-ui/react-dialog'

import { PerfectScrollArea } from '@/components/wrappers/PerfectScrollArea'
import { cn } from '@/utils/cn'

const Dialog = DialogPrimitive.Root

const DialogTrigger = DialogPrimitive.Trigger

const DialogPortal = DialogPrimitive.Portal

const DialogClose = DialogPrimitive.Close

const DialogOverlay = React.forwardRef<React.ElementRef<typeof DialogPrimitive.Overlay>, React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>>(
  ({ className, ...props }, ref) => <DialogPrimitive.Overlay ref={ref} className={cn('fixed inset-0 z-50 bg-neutral-deep/35 backdrop-blur-[2px] dialog-overlay', className)} {...props} />,
)
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName

const DialogContent = React.forwardRef<React.ElementRef<typeof DialogPrimitive.Content>, React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content>>(
  ({ className, children, ...props }, ref) => (
    <DialogPortal>
      <DialogOverlay />
      <DialogPrimitive.Content
        ref={ref}
        className={cn(
          'fixed left-[50%] top-[50%] z-50 flex max-h-[calc(100dvh-2rem)] w-[calc(100%-2rem)] max-w-lg translate-x-[-50%] translate-y-[-50%] flex-col overflow-hidden rounded-2xl border border-border-primary bg-card shadow-xl dialog-content',
          className,
        )}
        {...props}
      >
        {/* Never taller than the viewport: on short screens the body scrolls instead of being clipped. */}
        <PerfectScrollArea className="max-h-full" options={{ wheelPropagation: false }}>
          {/* minmax(0,1fr): long unbreakable content (titles, URLs) truncates instead of widening the dialog. */}
          <div className="grid grid-cols-[minmax(0,1fr)] gap-5 p-7">{children}</div>
        </PerfectScrollArea>
        <DialogPrimitive.Close className="group/close absolute right-4 top-4 flex size-9 items-center justify-center rounded-lg text-font-secondary transition-[background-color,color,scale] duration-200 ease-fluid hover:bg-primary-light hover:text-primary-bold active:scale-90 active:duration-75 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          <i className="ph ph-x text-[18px] transition-transform duration-300 ease-spring group-hover/close:rotate-90" aria-hidden="true" />
          <span className="sr-only">Close</span>
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPortal>
  ),
)
DialogContent.displayName = DialogPrimitive.Content.displayName

const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('flex flex-col space-y-1.5 text-center sm:text-left', className)} {...props} />
)
DialogHeader.displayName = 'DialogHeader'

const DialogFooter = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn('flex flex-col-reverse gap-2 sm:flex-row sm:justify-end', className)} {...props} />
)
DialogFooter.displayName = 'DialogFooter'

const DialogTitle = React.forwardRef<React.ElementRef<typeof DialogPrimitive.Title>, React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>>(
  ({ className, ...props }, ref) => (
    <DialogPrimitive.Title ref={ref} className={cn('font-serif text-h5 font-semibold leading-tight tracking-tight text-font-primary', className)} {...props} />
  ),
)
DialogTitle.displayName = DialogPrimitive.Title.displayName

const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => <DialogPrimitive.Description ref={ref} className={cn('text-body-md leading-relaxed text-font-secondary', className)} {...props} />)
DialogDescription.displayName = DialogPrimitive.Description.displayName

export { Dialog, DialogPortal, DialogOverlay, DialogClose, DialogTrigger, DialogContent, DialogHeader, DialogFooter, DialogTitle, DialogDescription }
