import { RouteObject } from 'react-router-dom'

import authRoutes from './auth.routes'
import AuthGuard from './guards/AuthGuard'
import mainRoutes from './main.routes'

/**
 * The router's route table. Accounts off (default): the app routes as they are, no login pages.
 * Accounts on (VITE_AUTH_ENABLED=true): /login and /register, and every app route behind AuthGuard.
 */
export function buildAppRoutes(authEnabled: boolean, routes: RouteObject[] = mainRoutes): RouteObject[] {
  if (!authEnabled) return routes
  return [...authRoutes, ...routes.map((route) => ({ ...route, element: <AuthGuard>{route.element}</AuthGuard> }))]
}
