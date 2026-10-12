import type { AxiosError, AxiosResponse } from 'axios'
import { describe, expect, it } from 'vitest'

import { ApiError, toApiError } from './api-error'

const failure = (data: unknown, status = 409, message = 'Request failed with status code 409') =>
  ({ message, code: 'ERR_BAD_REQUEST', response: { status, data } as AxiosResponse, config: {} }) as AxiosError

describe('toApiError', () => {
  it('is a real Error carrying the top-level envelope message, status and response code', () => {
    const error = toApiError(failure({ metaData: { message: 'A book with this ISBN already exists', responseCode: 409 } }))
    expect(error).toBeInstanceOf(Error)
    expect(error).toBeInstanceOf(ApiError)
    expect(error.message).toBe('A book with this ISBN already exists')
    expect(error.status).toBe(409)
    expect(error.responseCode).toBe(409)
    expect(error.response?.status).toBe(409)
  })

  it('reads the legacy detail envelope and plain detail strings', () => {
    expect(toApiError(failure({ detail: { metaData: { message: 'legacy', responseCode: 400 } } }, 400)).message).toBe('legacy')
    expect(toApiError(failure({ detail: 'plain' }, 422)).message).toBe('plain')
  })

  it('falls back to the transport message, then a generic one', () => {
    const network = { message: 'Network Error', config: {} } as AxiosError
    expect(toApiError(network).message).toBe('Network Error')
    expect(toApiError(network).status).toBeUndefined()
    expect(toApiError({ config: {} } as AxiosError).message).toBe('Something went wrong')
  })
})
