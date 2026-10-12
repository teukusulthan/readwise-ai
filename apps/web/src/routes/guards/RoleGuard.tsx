import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useAuthStore } from '@/stores/useAuthStore'
import { loginPathFor } from '@/utils/auth-redirect'

interface RoleGuardProps {
  children: React.ReactNode
  allowedRoles: string[]
}

const RoleGuard: React.FC<RoleGuardProps> = ({ children, allowedRoles }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const userRole = useAuthStore((state) => state.user?.role ?? 'user')
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to={loginPathFor(`${location.pathname}${location.search}`)} replace />
  }

  if (!allowedRoles.includes(userRole)) {
    // Authenticated but not allowed — send back to the app root
    return <Navigate to="/" replace />
  }

  return <>{children}</>
}

export default RoleGuard
