import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useAuthStore } from '@/stores/useAuthStore'
import { loginPathFor } from '@/utils/auth-redirect'

interface AuthGuardProps {
  children: React.ReactNode
}

/** Signed-out visitors go to `/login?next=<where they were going>`. Used only with VITE_AUTH_ENABLED. */
const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to={loginPathFor(`${location.pathname}${location.search}${location.hash}`)} replace />
  }

  return <>{children}</>
}

export default AuthGuard
