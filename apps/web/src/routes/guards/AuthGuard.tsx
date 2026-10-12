import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useAuthStore } from '@/stores/useAuthStore'

interface AuthGuardProps {
  children: React.ReactNode
}

const AuthGuard: React.FC<AuthGuardProps> = ({ children }) => {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const location = useLocation()

  if (!isAuthenticated) {
    // Redirect to login but remember where the user was going
    return <Navigate to="/auth/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}

export default AuthGuard
