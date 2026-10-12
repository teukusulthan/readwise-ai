import { afterEach, describe, expect, it, vi } from 'vitest'

async function loadEnv() {
  vi.resetModules()
  return (await import('./env')).default
}

describe('env config', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('defaults the API base URL to the dev-proxy path', async () => {
    vi.stubEnv('VITE_API_BASE_URL', '')
    const env = await loadEnv()
    expect(env.api.baseUrl).toBe('/api/v1')
  })

  it('uses VITE_API_BASE_URL when set', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'https://api.example.test/v1')
    const env = await loadEnv()
    expect(env.api.baseUrl).toBe('https://api.example.test/v1')
  })

  it('keeps accounts off unless VITE_AUTH_ENABLED is "true"', async () => {
    vi.stubEnv('VITE_AUTH_ENABLED', '')
    expect((await loadEnv()).auth.enabled).toBe(false)
    vi.stubEnv('VITE_AUTH_ENABLED', 'true')
    expect((await loadEnv()).auth.enabled).toBe(true)
  })
})
