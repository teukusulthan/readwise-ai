import axios, { type AxiosAdapter, type InternalAxiosRequestConfig } from 'axios'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import type { ApiResponse } from '@/types/api'
import apiClient from './api-client'
import { API_ENDPOINTS } from './api-endpoints'
import { apiRequests } from './api-factory.service'

const envelope: ApiResponse<{ id: string }> = {
  metaData: { status: true, executionTime: 3, responseCode: 200, message: 'Success' },
  data: { id: 'abc' },
}

describe('apiRequests', () => {
  const originalAdapter = apiClient.defaults.adapter
  let lastConfig: InternalAxiosRequestConfig | undefined

  beforeEach(() => {
    lastConfig = undefined
    const adapter: AxiosAdapter = async (config) => {
      lastConfig = config
      return { data: envelope, status: 200, statusText: 'OK', headers: {}, config }
    }
    apiClient.defaults.adapter = adapter
  })

  afterEach(() => {
    apiClient.defaults.adapter = originalAdapter
  })

  it('resolves to the backend envelope, not just its data field', async () => {
    const result = await apiRequests.get<{ id: string }>(API_ENDPOINTS.USER.BASE + '/get-one', { id: 'abc' })

    expect(result).toEqual(envelope)
    expect(result.data.id).toBe('abc')
    expect(result.metaData.status).toBe(true)
  })

  it('builds URLs that hit the /api/v1/apps dev proxy', async () => {
    await apiRequests.post(API_ENDPOINTS.AUTH.LOGIN, { email: 'a@b.c', password: 'x' })

    expect(lastConfig).toBeDefined()
    expect(axios.getUri(lastConfig)).toBe('/api/v1/apps/auth/login')
  })

  it('keeps the 30 s timeout for ordinary requests but disables it for multipart uploads', async () => {
    await apiRequests.get('/x')
    expect(lastConfig?.timeout).toBe(30000)

    await apiRequests.upload('/apps/book/upload', new FormData())
    expect(lastConfig?.timeout).toBe(0)
  })

  it('rejects failed requests with an Error carrying the backend message and status', async () => {
    apiClient.defaults.adapter = async (config) =>
      Promise.reject(
        new axios.AxiosError('Request failed with status code 409', 'ERR_BAD_REQUEST', config, null, {
          data: { metaData: { status: false, responseCode: 409, message: 'This PDF is already in the library' } },
          status: 409,
          statusText: 'Conflict',
          headers: {},
          config,
        }),
      )

    const error = await apiRequests.upload('/apps/book/upload', new FormData()).catch((e: unknown) => e)
    expect(error).toBeInstanceOf(Error)
    expect((error as Error).message).toBe('This PDF is already in the library')
    expect((error as { status?: number }).status).toBe(409)
    expect((error as { response?: { status: number } }).response?.status).toBe(409)
  })
})
