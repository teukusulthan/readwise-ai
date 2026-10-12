import { Navigate, useSearchParams } from 'react-router-dom'

import AuthLayout from '@/components/layouts/AuthLayout'
import { LoginForm } from '@/features/auth/components/LoginForm'
import { useAuthStore } from '@/stores/useAuthStore'
import { safeNextPath } from '@/utils/auth-redirect'

function LoginPage() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const [params] = useSearchParams()
  if (isAuthenticated) return <Navigate to={safeNextPath(params.get('next'))} replace />

  return (
    <AuthLayout title="Sign in" description="Your conversations are private to your account; the library is shared.">
      <LoginForm />
    </AuthLayout>
  )
}

export default LoginPage
