import type { ApiResponse } from '@/types/api'
import apiClient from './api-client'

/**
 * Thin typed helpers over `apiClient`.
 * The response interceptor already unwraps axios' `response.data`, so every
 * helper resolves to the backend `ApiResponse<T>` envelope (metaData + data).
 */
export const apiRequests = {
  get: <T>(url: string, params?: object): Promise<ApiResponse<T>> =>
    apiClient.get<ApiResponse<T>, ApiResponse<T>>(url, { params }),

  post: <T, P = unknown>(url: string, data: P): Promise<ApiResponse<T>> =>
    apiClient.post<ApiResponse<T>, ApiResponse<T>, P>(url, data),

  put: <T, P = unknown>(url: string, data: P): Promise<ApiResponse<T>> =>
    apiClient.put<ApiResponse<T>, ApiResponse<T>, P>(url, data),

  patch: <T, P = unknown>(url: string, data: Partial<P>): Promise<ApiResponse<T>> =>
    apiClient.patch<ApiResponse<T>, ApiResponse<T>, Partial<P>>(url, data),

  delete: <T>(url: string, params?: object): Promise<ApiResponse<T>> =>
    apiClient.delete<ApiResponse<T>, ApiResponse<T>>(url, { params }),

  upload: <T>(url: string, formData: FormData, onProgress?: (percent: number) => void): Promise<ApiResponse<T>> =>
    apiClient.post<ApiResponse<T>, ApiResponse<T>, FormData>(url, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded * 100) / e.total))
        }
      },
    }),
}
