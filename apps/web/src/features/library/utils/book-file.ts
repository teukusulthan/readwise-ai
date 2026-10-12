import env from '@/config/env'
import { API_ENDPOINTS } from '@/services/api-endpoints'

/**
 * Link to a book's stored PDF. Browser PDF viewers honour the `#page=N` fragment, so a cited page opens directly.
 * The backend reads the HttpOnly session cookie, so a plain link authenticates the same way the API calls do.
 */
export function bookFileUrl(bookId: string, page?: number | null): string {
  const url = `${env.api.baseUrl}${API_ENDPOINTS.BOOK.FILE}?id=${encodeURIComponent(bookId)}`
  return page && page > 0 ? `${url}#page=${Math.floor(page)}` : url
}
