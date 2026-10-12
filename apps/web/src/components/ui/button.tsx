import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import * as React from 'react'

import { cn } from '@/utils/cn'
import { useButtonGroup } from '@/components/ui/button-group'

const buttonVariants = cva(
  // Motion: a 1 px lift on hover, a quick press-in on click (75 ms), soft landing on release.
  // Disabled buttons keep pointer events so they can show "not allowed" and their title.
  'group/button inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-xl font-sans font-semibold transition-[color,background-color,border-color,box-shadow,translate,scale,opacity] duration-200 ease-fluid focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background not-disabled:active:translate-y-0 not-disabled:active:scale-[0.97] not-disabled:active:duration-75 disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0 [&_i]:transition-transform [&_i]:duration-200 [&_i]:ease-fluid',
  {
    variants: {
      variant: {
        default: 'bg-primary text-font-on-accent shadow-sm not-disabled:hover:-translate-y-px not-disabled:hover:bg-primary-bold not-disabled:hover:shadow-md',
        destructive: 'bg-error text-font-on-accent shadow-sm not-disabled:hover:-translate-y-px not-disabled:hover:bg-error-bold not-disabled:hover:shadow-md',
        outline:
          'bg-background-primary border border-border-primary text-font-primary shadow-xs not-disabled:hover:-translate-y-px not-disabled:hover:border-border-secondary not-disabled:hover:bg-primary-light not-disabled:hover:shadow-sm',
        secondary: 'bg-background-secondary border border-border-primary text-font-primary not-disabled:hover:-translate-y-px not-disabled:hover:bg-primary-light',
        ghost: 'text-font-secondary not-disabled:hover:bg-primary-light not-disabled:hover:text-primary-bold',
        link: 'text-primary underline-offset-4 not-disabled:hover:underline',
      },
      size: {
        default: 'h-11 px-5 text-body-md',
        xs: 'h-8 rounded-lg px-3 text-body-sm',
        sm: 'h-10 px-4 text-body-md',
        md: 'h-11 px-5 text-body-md',
        lg: 'h-12 px-6 text-body-lg',
        icon: 'size-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild = false, ...props }, ref) => {
  const group = useButtonGroup()
  const resolvedVariant = variant ?? group.variant
  const resolvedSize = size ?? group.size
  const Comp = asChild ? Slot : 'button'
  return <Comp className={cn(buttonVariants({ variant: resolvedVariant, size: resolvedSize, className }))} ref={ref} {...props} />
})
Button.displayName = 'Button'

export { Button, buttonVariants }
