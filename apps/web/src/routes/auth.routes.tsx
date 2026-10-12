import { lazy, Suspense } from 'react'
import { RouteObject } from 'react-router-dom'

import { LOGIN_PATH, REGISTER_PATH } from '@/utils/auth-redirect'

const LoginPage = lazy(() => import('@/pages/auth/LoginPage'))
const RegisterPage = lazy(() => import('@/pages/auth/RegisterPage'))

/** Public pages without the app shell. Mounted only with VITE_AUTH_ENABLED (see routes/app.routes.tsx). */
const authRoutes: RouteObject[] = [
  { path: LOGIN_PATH, element: <Suspense><LoginPage /></Suspense> },
  { path: REGISTER_PATH, element: <Suspense><RegisterPage /></Suspense> },
]

export default authRoutes
