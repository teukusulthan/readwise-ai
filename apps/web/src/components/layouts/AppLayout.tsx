import { useLayoutEffect, useRef } from 'react'
import { Outlet, useLocation, useMatches } from 'react-router-dom'

import { PerfectScrollArea } from '@/components/wrappers/PerfectScrollArea'
import { usePageTitle } from '@/hooks/use-page-title'
import type { IRouteHandle } from '@/types/route'
import AppHeader from './AppHeader'
import AppSidebar from './AppSidebar'

/** App shell: header on top, sidebar + scrollable main below. Regions never overlap. */
function AppLayout() {
  usePageTitle()
  const { pathname } = useLocation()
  const fullHeight = useMatches().some((match) => (match.handle as IRouteHandle | undefined)?.fullHeight)
  const scrollRef = useRef<HTMLElement | null>(null)
  const scrollPositions = useRef(new Map<string, number>())

  // Each page remembers where it was scrolled: a new page opens at the top, Back returns to the same spot.
  useLayoutEffect(() => {
    const element = scrollRef.current
    if (!element) return
    element.scrollTop = scrollPositions.current.get(pathname) ?? 0
    return () => {
      scrollPositions.current.set(pathname, element.scrollTop)
    }
  }, [pathname])

  // Pages fade in on navigation. Full-height pages (the chat) are keyed by section, so moving
  // between conversations never remounts them (a live answer keeps streaming).
  const pageKey = fullHeight ? pathname.split('/')[1] : pathname

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-background text-font-primary">
      <AppHeader />
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <AppSidebar />
        <main className="relative min-h-0 min-w-0 flex-1">
          {fullHeight ? (
            <div key={pageKey} className="app-content h-full animate-page-in">
              <Outlet />
            </div>
          ) : (
            <PerfectScrollArea ref={scrollRef} className="h-full">
              <div key={pageKey} className="app-content animate-page-in px-5 py-8 md:px-10 md:py-10">
                <Outlet />
              </div>
            </PerfectScrollArea>
          )}
        </main>
      </div>
    </div>
  )
}

export default AppLayout
