import { Navigate } from 'react-router-dom'

import AuthLayout from '@/components/layouts/AuthLayout'
import { RegisterForm } from '@/features/auth/components/RegisterForm'
import { useAuthStore } from '@/stores/useAuthStore'
import { DEFAULT_AFTER_LOGIN } from '@/utils/auth-redirect'

function RegisterPage() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  if (isAuthenticated) return <Navigate to={DEFAULT_AFTER_LOGIN} replace />

  return (
    <AuthLayout title="Create an account" description="Join the shared library and keep your own chat history.">
      <RegisterForm />
    </AuthLayout>
  )
}

export default RegisterPage
