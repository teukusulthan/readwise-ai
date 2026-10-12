'use client'

import { Toaster as Sonner } from 'sonner'

import { APP_THEME } from '@/config/theme'

type ToasterProps = React.ComponentProps<typeof Sonner>

const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      theme={APP_THEME}
      className="toaster group"
      position="bottom-right"
      icons={{
        success: <i className="ph ph-check-circle text-[18px] text-success-bold" aria-hidden="true" />,
        info: <i className="ph ph-info text-[18px] text-info-bold" aria-hidden="true" />,
        warning: <i className="ph ph-warning text-[18px] text-warning-bold" aria-hidden="true" />,
        error: <i className="ph ph-x-octagon text-[18px] text-error-bold" aria-hidden="true" />,
        loading: <i className="ph ph-spinner text-[18px] animate-spin" aria-hidden="true" />,
      }}
      toastOptions={{
        classNames: {
          toast:
            'group toast group-[.toaster]:rounded-xl group-[.toaster]:bg-card group-[.toaster]:text-foreground group-[.toaster]:border-border-primary group-[.toaster]:shadow-lg group-[.toaster]:text-body-md',
          description: 'group-[.toast]:text-font-secondary',
          actionButton: 'group-[.toast]:bg-primary group-[.toast]:text-primary-foreground',
          cancelButton: 'group-[.toast]:bg-muted group-[.toast]:text-font-secondary',
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
