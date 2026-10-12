import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, describe, expect, it } from 'vitest'

import { useAuthStore } from '@/stores/useAuthStore'
import AuthGuard from './AuthGuard'

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/auth/login" element={<p>Login page</p>} />
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

describe('AuthGuard', () => {
  afterEach(() => {
    useAuthStore.getState().clearAuth()
  })

  it('redirects to /auth/login when not authenticated', () => {
    renderAt('/private')

    expect(screen.getByText('Login page')).toBeInTheDocument()
    expect(screen.queryByText('Private content')).not.toBeInTheDocument()
  })

  it('renders children for an authenticated user', () => {
    useAuthStore.getState().setAuth({ id: '1', username: 'reader', email: 'reader@example.test' })
    renderAt('/private')

    expect(screen.getByText('Private content')).toBeInTheDocument()
  })
})
