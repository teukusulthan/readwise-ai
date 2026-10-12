import { render, screen } from '@testing-library/react'
import { createMemoryRouter, Outlet, RouterProvider, type RouteObject } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it } from 'vitest'

import { useAuthStore } from '@/stores/useAuthStore'
import { buildAppRoutes } from './app.routes'

// Stand-in for main.routes (the real pages fetch data): a shell route with one page.
const appRoutes: RouteObject[] = [
  { path: '/', element: <Outlet />, children: [{ path: '/books', element: <p>Catalog page</p> }] },
]

function renderAt(path: string, authEnabled: boolean) {
  const router = createMemoryRouter(buildAppRoutes(authEnabled, appRoutes), { initialEntries: [path] })
  render(
    <QueryClientProvider client={new QueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return router
}

describe('app routes', () => {
  afterEach(() => {
    useAuthStore.getState().clearAuth()
  })

  it('sends a signed-out visitor to the login page when accounts are enabled', async () => {
    const router = renderAt('/books?status=indexed', true)

    expect(await screen.findByRole('heading', { name: 'Sign in' })).toBeInTheDocument()
    expect(screen.queryByText('Catalog page')).not.toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/login')
    expect(router.state.location.search).toBe('?next=%2Fbooks%3Fstatus%3Dindexed')
  })

  it('lets a signed-in user through when accounts are enabled', () => {
    useAuthStore.getState().setAuth({ id: 'u1', username: 'ada', email: 'ada@example.test' })
    renderAt('/books', true)

    expect(screen.getByText('Catalog page')).toBeInTheDocument()
  })

  it('has no guard and no login page when accounts are disabled', () => {
    const routes = buildAppRoutes(false, appRoutes)
    renderAt('/books', false)

    expect(screen.getByText('Catalog page')).toBeInTheDocument()
    expect(routes).toBe(appRoutes)
    expect(routes.some((route) => route.path === '/login' || route.path === '/register')).toBe(false)
  })
})
