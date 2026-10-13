import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/services/api-error'
import { authService } from '@/services/auth.service'
import { useAuthStore } from '@/stores/useAuthStore'
import { LoginForm } from './LoginForm'

vi.mock('@/services/auth.service', () => ({ authService: { login: vi.fn(), checkSession: vi.fn() } }))

const user = { id: 'u1', username: 'ada', fullname: 'Ada Reader', email: 'ada@example.test' }

function renderForm(path = '/login?next=%2Fask%2Fc1') {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  client.setQueryData(['conversations'], ['someone else’s'])
  const router = createMemoryRouter(
    [
      { path: '/login', element: <LoginForm /> },
      { path: '/ask/:id', element: <p>Chat page</p> },
      { path: '/books', element: <p>Catalog page</p> },
    ],
    { initialEntries: [path] },
  )
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { client, router }
}

function fillAndSubmit(email: string, password: string) {
  fireEvent.change(screen.getByLabelText('Email or username'), { target: { value: email } })
  fireEvent.change(screen.getByLabelText('Password'), { target: { value: password } })
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
}

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(authService.checkSession).mockResolvedValue({ data: { status: 'active' } } as never)
  })
  afterEach(() => useAuthStore.getState().clearAuth())

  it('signs in, stores the user, drops cached data and returns to the requested page', async () => {
    vi.mocked(authService.login).mockResolvedValue({ data: { user } } as never)
    const { client, router } = renderForm()

    fillAndSubmit('  ada@example.test ', 'correct horse')

    expect(await screen.findByText('Chat page')).toBeInTheDocument()
    expect(authService.login).toHaveBeenCalledWith({ email: 'ada@example.test', password: 'correct horse' })
    expect(useAuthStore.getState()).toMatchObject({ isAuthenticated: true, user })
    expect(client.getQueryData(['conversations'])).toBeUndefined()
    expect(router.state.location.pathname).toBe('/ask/c1')
  })

  it('ignores a `next` that leaves the app', async () => {
    vi.mocked(authService.login).mockResolvedValue({ data: { user } } as never)
    renderForm('/login?next=https%3A%2F%2Fevil.test')

    fillAndSubmit('ada', 'correct horse')

    expect(await screen.findByText('Catalog page')).toBeInTheDocument()
  })

  it('validates before calling the server and shows the server message on failure', async () => {
    renderForm()
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Enter your email or username')).toBeInTheDocument()
    expect(authService.login).not.toHaveBeenCalled()

    vi.mocked(authService.login).mockRejectedValue(new ApiError('Incorrect email or password'))
    fillAndSubmit('ada', 'wrong')
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password')
    await waitFor(() => expect(useAuthStore.getState().isAuthenticated).toBe(false))
    // The rejected password is cleared; the identifier stays for the next try.
    expect(screen.getByLabelText('Password')).toHaveValue('')
    expect(screen.getByLabelText('Email or username')).toHaveValue('ada')
  })

  it('explains a rejected session cookie instead of bouncing back to the login page', async () => {
    vi.mocked(authService.login).mockResolvedValue({ data: { user } } as never)
    vi.mocked(authService.checkSession).mockRejectedValue(new ApiError('Authentication required.', { response: { status: 401 } as never }))
    const { router } = renderForm()

    fillAndSubmit('ada', 'correct horse')

    expect(await screen.findByRole('alert')).toHaveTextContent('the browser rejected the session cookie')
    expect(screen.getByRole('alert')).toHaveTextContent('BE_AUTH_COOKIE_SECURE=false')
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(router.state.location.pathname).toBe('/login')
  })
})
