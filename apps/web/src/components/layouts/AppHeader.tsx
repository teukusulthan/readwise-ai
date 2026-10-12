import { Link } from 'react-router-dom'

import env from '@/config/env'
import { AccountMenu } from '@/features/auth/components/AccountMenu'
import { renderIcon } from '@/utils/icon-renderer'

function AppHeader() {
  return (
    <header className="flex h-16 shrink-0 items-center gap-3 border-b border-border-primary bg-background-primary px-5 md:px-6">
      <Link
        to="/books"
        className="group flex items-center gap-3 rounded-xl pr-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <span className="flex size-10 items-center justify-center rounded-xl bg-primary text-font-on-accent shadow-sm transition-transform duration-200 group-hover:-rotate-3">
          {renderIcon({ icon: 'book-open-text', className: 'text-[22px]' })}
        </span>
        <span className="flex flex-col leading-tight">
          <span className="font-serif text-h6 font-semibold tracking-tight text-font-primary">Readwise AI</span>
          <span className="hidden text-body-sm text-font-secondary sm:block">Answers grounded in your books</span>
        </span>
      </Link>
      {env.auth.enabled && <AccountMenu />}
    </header>
  )
}

export default AppHeader
