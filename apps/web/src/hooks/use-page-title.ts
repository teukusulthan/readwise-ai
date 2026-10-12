import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

import { ALL_MENUS } from '@/config/menu'

const APP_NAME = 'Readwise AI'

/** Sets document.title from the active menu entry's `seo.title`. */
export function usePageTitle() {
  const { pathname } = useLocation()

  useEffect(() => {
    const menu = ALL_MENUS().find((m) => pathname === m.path || pathname.startsWith(`${m.path}/`))
    document.title = menu?.seo.title ? `${menu.seo.title} — ${APP_NAME}` : APP_NAME
  }, [pathname])
}
