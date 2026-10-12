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
})
