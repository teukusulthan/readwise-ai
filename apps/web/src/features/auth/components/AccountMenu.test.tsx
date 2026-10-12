import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { authService } from '@/services/auth.service'
import { useAuthStore } from '@/stores/useAuthStore'
import { AccountMenu } from './AccountMenu'

vi.mock('@/services/auth.service', () => ({ authService: { logout: vi.fn() } }))

describe('AccountMenu', () => {
  afterEach(() => useAuthStore.getState().clearAuth())

  it('shows the signed-in user and signs out (even if the server call fails)', async () => {
    vi.mocked(authService.logout).mockRejectedValue(new Error('offline'))
    useAuthStore.getState().setAuth({ id: 'u1', username: 'ada', fullname: 'Ada Reader', email: 'ada@example.test' })
    const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    client.setQueryData(['conversations'], ['mine'])
    const router = createMemoryRouter(
      [
        { path: '/books', element: <AccountMenu /> },
        { path: '/login', element: <p>Login page</p> },
      ],
      { initialEntries: ['/books'] },
    )
    render(
      <QueryClientProvider client={client}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    )

    expect(screen.getByText('Ada Reader')).toBeInTheDocument()
    expect(screen.getByText('ada@example.test')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))

    expect(await screen.findByText('Login page')).toBeInTheDocument()
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(client.getQueryData(['conversations'])).toBeUndefined()
  })
})
