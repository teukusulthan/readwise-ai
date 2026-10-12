import type { AxiosError, AxiosResponse } from 'axios'

/**
 * Error every `apiClient` request rejects with (a 401 whose refresh failed rejects with the original 401).
 * `message` is the backend's own message. The axios fields callers may read (`response`, `config`, `code`) are kept.
 */
export class ApiError extends Error {
  readonly status?: number
  readonly responseCode?: string | number
  readonly response?: AxiosResponse
  readonly config?: AxiosError['config']
  readonly code?: string
  readonly isAxiosError = true

  constructor(message: string, source: Partial<Pick<AxiosError, 'response' | 'config' | 'code'>> = {}) {
    super(message)
    this.name = 'ApiError'
    this.response = source.response
    this.config = source.config
    this.code = source.code
    this.status = source.response?.status
    this.responseCode = resolveResponseCode(source.response?.data)
  }
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function resolveResponseCode(body: any): string | number | undefined {
  return body?.detail?.metaData?.responseCode ?? body?.metaData?.responseCode
}

/**
 * Backend failures arrive as a top-level `{ metaData: { message } }` envelope (primary), a plain `{ detail: string }`,
 * or the legacy `{ detail: { metaData } }` shape.
 */
export function resolveErrorMessage(error: AxiosError): string {
  const body = error.response?.data as any
  const detail = body?.detail
  return (
    detail?.metaData?.message ||
    (typeof detail === 'string' ? detail : undefined) ||
    body?.metaData?.message ||
    body?.message ||
    error.message ||
    'Something went wrong'
  )
}

export function toApiError(error: AxiosError): ApiError {
  return new ApiError(resolveErrorMessage(error), error)
}
