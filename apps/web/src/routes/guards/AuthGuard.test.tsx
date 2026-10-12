import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { useAuthStore } from '@/stores/useAuthStore'
import AuthGuard from './AuthGuard'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<LoginProbe />} />
        <Route
          path="/private"
          element={
            <AuthGuard>
              <p>Private content</p>
            </AuthGuard>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

function LoginProbe() {
  const location = useLocation()
  return <p>Login page {location.search}</p>
}

describe('AuthGuard', () => {
  afterEach(() => {
    useAuthStore.getState().clearAuth()
  })

  it('redirects to /login?next=<path> when not authenticated', () => {
    renderAt('/private?tab=2')

    expect(screen.getByText('Login page ?next=%2Fprivate%3Ftab%3D2')).toBeInTheDocument()
    expect(screen.queryByText('Private content')).not.toBeInTheDocument()
  })

  it('renders children for an authenticated user', () => {
    useAuthStore.getState().setAuth({ id: '1', username: 'reader', email: 'reader@example.test' })
    renderAt('/private')

    expect(screen.getByText('Private content')).toBeInTheDocument()
  })
})
