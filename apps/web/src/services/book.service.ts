import type {
  IBook,
  IBookCreatePayload,
  IBookDeleteResult,
  IBookListParams,
  IBookUploadPayload,
  IExternalBook,
} from '@/features/library/types/book.types'
import type { ApiResponse } from '@/types/api'
import { API_ENDPOINTS } from './api-endpoints'
import { apiRequests } from './api-factory.service'

/** Book catalog + document endpoints (apps/backend/router/book.py). Resolves to the ApiResponse envelope. */
export const bookService = {
  getAll: (params: IBookListParams): Promise<ApiResponse<IBook[]>> => apiRequests.post<IBook[], IBookListParams>(API_ENDPOINTS.BOOK.GET_ALL, params),

  getOne: (id: string): Promise<ApiResponse<IBook>> => apiRequests.get<IBook>(API_ENDPOINTS.BOOK.GET_ONE, { id }),

  add: (payload: IBookCreatePayload): Promise<ApiResponse<IBook>> => apiRequests.post<IBook, IBookCreatePayload>(API_ENDPOINTS.BOOK.ADD, payload),

  remove: (id: string): Promise<ApiResponse<IBookDeleteResult>> => apiRequests.delete<IBookDeleteResult>(API_ENDPOINTS.BOOK.DELETE, { id }),

  upload: ({ file, bookId, title }: IBookUploadPayload, onProgress?: (percent: number) => void): Promise<ApiResponse<IBook>> => {
    const formData = new FormData()
    formData.append('file', file)
    if (bookId) formData.append('bookId', bookId)
    if (title?.trim()) formData.append('title', title.trim())
    return apiRequests.upload<IBook>(API_ENDPOINTS.BOOK.UPLOAD, formData, onProgress)
  },

  // The backend reads `id` from the query string on these POST endpoints.
  reindex: (id: string): Promise<ApiResponse<IBook>> => apiRequests.post<IBook, null>(`${API_ENDPOINTS.BOOK.REINDEX}?id=${encodeURIComponent(id)}`, null),

  lookup: (q: string): Promise<ApiResponse<IExternalBook[]>> => apiRequests.get<IExternalBook[]>(API_ENDPOINTS.BOOK.LOOKUP, { q }),

  importByIsbn: (isbn: string): Promise<ApiResponse<IBook>> => apiRequests.post<IBook, { isbn: string }>(API_ENDPOINTS.BOOK.IMPORT, { isbn }),
}
