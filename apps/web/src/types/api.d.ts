/** Mirrors the backend `BaseResponse` envelope (apps/backend/models/*). */
export interface ApiPagination {
  size: number
  totalElements: number
  totalPages: number
  scrollId?: string
}

export interface ApiMetaData {
  pagination?: ApiPagination
  status: boolean
  executionTime: number
  responseCode: number
  message: string | null
  [key: string]: unknown
}

export interface ApiResponse<T = unknown> {
  metaData: ApiMetaData
  data: T
  additionalInfo?: unknown
  copyright?: string
}

export interface ApiError {
  message: string
  status?: number
  errors?: Record<string, string[]>
}
