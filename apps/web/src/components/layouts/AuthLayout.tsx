import { useEffect, type ReactNode } from 'react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { PerfectScrollArea } from '@/components/wrappers/PerfectScrollArea'
import { renderIcon } from '@/utils/icon-renderer'

interface AuthLayoutProps {
  title: string
  description: string
  children: ReactNode
}

/** Shell for the sign-in / register pages: no header or sidebar, one centred card. */
function AuthLayout({ title, description, children }: AuthLayoutProps) {
  useEffect(() => {
    document.title = `${title} — Readwise AI`
  }, [title])

  return (
    <div className="h-screen w-full bg-background text-font-primary">
      <PerfectScrollArea className="h-full">
        <main className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center gap-6 px-5 py-10 animate-page-in">
          <div className="flex items-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-font-on-accent shadow-sm">
              {renderIcon({ icon: 'book-open-text', className: 'text-[22px]' })}
            </span>
            <span className="flex flex-col leading-tight">
              <span className="font-serif text-h6 font-semibold tracking-tight text-font-primary">Readwise AI</span>
              <span className="text-body-sm text-font-secondary">Answers grounded in your books</span>
            </span>
          </div>
          <Card>
            <CardHeader>
              <CardTitle>
                <h1>{title}</h1>
              </CardTitle>
              <CardDescription>{description}</CardDescription>
            </CardHeader>
            <CardContent>{children}</CardContent>
          </Card>
        </main>
      </PerfectScrollArea>
    </div>
  )
}

export default AuthLayout
