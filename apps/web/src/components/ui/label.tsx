import * as React from 'react'
import { Label as LabelPrimitive } from 'radix-ui'

import { cn } from '@/utils/cn'

const Label = React.forwardRef<React.ElementRef<typeof LabelPrimitive.Root>, React.ComponentPropsWithoutRef<typeof LabelPrimitive.Root>>(
  ({ className, ...props }, ref) => (
    <LabelPrimitive.Root
      ref={ref}
      className={cn('text-body-md font-medium text-font-primary peer-disabled:cursor-not-allowed peer-disabled:opacity-70', className)}
      {...props}
    />
  ),
)
Label.displayName = LabelPrimitive.Root.displayName

export { Label }
