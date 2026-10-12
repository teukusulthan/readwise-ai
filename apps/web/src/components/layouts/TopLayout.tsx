import { Link, Outlet } from 'react-router-dom'

import { PerfectScrollArea } from '@/components/wrappers/PerfectScrollArea'

function TopLayout() {
  return (
    <div className="flex h-screen w-full flex-col overflow-hidden">
      <header className="border-border-soft flex h-14 shrink-0 items-center justify-between border-b px-4">
        {/* Left: app icon + back link */}
        <div className="flex items-center gap-3">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-white shrink-0">
            <i className="ph ph-shield-chevron text-sm" />
          </div>
          <div className="h-5 w-px bg-border-soft" />
          <Link to="/" className="text-font-secondary hover:text-font-primary flex items-center gap-2  transition-colors">
            <i className="ph ph-arrow-left text-base" />
            Back
          </Link>
        </div>
      </header>
      <main className="relative min-h-0 flex-1">
        <PerfectScrollArea className="h-full">
          <Outlet />
        </PerfectScrollArea>
      </main>
    </div>
  )
}

export default TopLayout
