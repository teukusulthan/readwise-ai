import { afterEach, describe, expect, it, vi } from 'vitest'

import { queryClient } from '@/config/query-client'
import { useAuthStore } from '@/stores/useAuthStore'

const env = vi.hoisted(() => ({ auth: { enabled: true }, api: { baseUrl: '/api/v1' } }))
vi.mock('@/config/env', () => ({ default: env }))

import { handleSessionExpired } from './session-expiry'

describe('handleSessionExpired', () => {
  const assign = vi.fn()

  afterEach(() => {
    vi.unstubAllGlobals()
    assign.mockReset()
    env.auth.enabled = true
  })

  function at(path: string) {
    const url = new URL(path, 'http://app.test')
    vi.stubGlobal('location', { pathname: url.pathname, search: url.search, hash: url.hash, assign })
  }

  it('forgets the user and goes to the login page with the current page as `next`', () => {
    at('/ask/c1?x=1')
    useAuthStore.getState().setAuth({ id: 'u1', username: 'ada', email: 'ada@example.test' })
    queryClient.setQueryData(['conversations'], ['mine'])

    handleSessionExpired()

    expect(assign).toHaveBeenCalledWith('/login?next=%2Fask%2Fc1%3Fx%3D1')
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(queryClient.getQueryData(['conversations'])).toBeUndefined()
  })

  it('does nothing without accounts, and never redirects away from the login page', () => {
    env.auth.enabled = false
    at('/books')
    useAuthStore.getState().setAuth({ id: 'u1', username: 'ada', email: 'ada@example.test' })
    handleSessionExpired()
    expect(assign).not.toHaveBeenCalled()
    expect(useAuthStore.getState().isAuthenticated).toBe(true)

    env.auth.enabled = true
    at('/login?next=%2Fbooks')
    handleSessionExpired()
    expect(assign).not.toHaveBeenCalled()
    useAuthStore.getState().clearAuth()
  })
})
