import * as React from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/utils/cn'
import { type ButtonProps } from '@/components/ui/button'

/* ── Context ── */

interface ButtonGroupContextValue {
  variant?: ButtonProps['variant']
  size?: ButtonProps['size']
  orientation?: 'horizontal' | 'vertical'
}

const ButtonGroupContext = React.createContext<ButtonGroupContextValue>({})

export function useButtonGroup() {
  return React.useContext(ButtonGroupContext)
}

/* ── ButtonGroup ── */

const buttonGroupVariants = cva('inline-flex items-stretch', {
  variants: {
    orientation: {
      horizontal: [
        'flex-row',
        '[&>*:not(:first-child)]:-ml-px',
        '[&>*:first-child]:rounded-r-none!',
        '[&>*:last-child]:rounded-l-none!',
        '[&>*:not(:first-child):not(:last-child)]:rounded-none!',
      ],
      vertical: [
        'flex-col',
        '[&>*]:w-full',
        '[&>*:not(:first-child)]:-mt-px',
        '[&>*:first-child]:rounded-b-none!',
        '[&>*:last-child]:rounded-t-none!',
        '[&>*:not(:first-child):not(:last-child)]:rounded-none!',
      ],
    },
  },
  defaultVariants: {
    orientation: 'horizontal',
  },
})

export interface ButtonGroupProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof buttonGroupVariants> {
  variant?: ButtonProps['variant']
  size?: ButtonProps['size']
}

const ButtonGroup = React.forwardRef<HTMLDivElement, ButtonGroupProps>(
  ({ className, orientation, variant, size, children, ...props }, ref) => (
    <ButtonGroupContext.Provider value={{ variant, size, orientation: orientation ?? 'horizontal' }}>
      <div
        ref={ref}
        role="group"
        className={cn(buttonGroupVariants({ orientation }), className)}
        {...props}
      >
        {children}
      </div>
    </ButtonGroupContext.Provider>
  ),
)
ButtonGroup.displayName = 'ButtonGroup'

/* ── ButtonGroupSeparator ── */

const ButtonGroupSeparator = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => {
    const { orientation } = useButtonGroup()
    return (
      <div
        ref={ref}
        aria-hidden
        className={cn(
          'relative z-10 -mx-px shrink-0 bg-border',
          orientation === 'vertical' ? 'h-px w-full -my-px' : 'w-px h-auto -mx-px',
          className,
        )}
        {...props}
      />
    )
  },
)
ButtonGroupSeparator.displayName = 'ButtonGroupSeparator'

/* ── ButtonGroupText ── */

export interface ButtonGroupTextProps extends React.HTMLAttributes<HTMLDivElement> {
  asChild?: boolean
}

const ButtonGroupText = React.forwardRef<HTMLDivElement, ButtonGroupTextProps>(
  ({ className, asChild, ...props }, ref) => {
    const Comp = asChild ? Slot : 'div'
    return (
      <Comp
        ref={ref}
        className={cn(
          'inline-flex items-center border border-input bg-muted px-3 text-sm text-muted-foreground',
          className,
        )}
        {...props}
      />
    )
  },
)
ButtonGroupText.displayName = 'ButtonGroupText'

export { ButtonGroup, ButtonGroupSeparator, ButtonGroupText, buttonGroupVariants }
