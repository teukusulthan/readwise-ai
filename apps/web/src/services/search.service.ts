import type { ISearchPayload, ISearchResponse } from '@/features/library/chat/types/chat.types'
import type { ApiResponse } from '@/types/api'
import { API_ENDPOINTS } from './api-endpoints'
import { apiRequests } from './api-factory.service'

/** Semantic passage search (apps/backend/router/search.py). */
export const searchService = {
  query: (payload: ISearchPayload): Promise<ApiResponse<ISearchResponse>> =>
    apiRequests.post<ISearchResponse, ISearchPayload>(API_ENDPOINTS.SEARCH.QUERY, payload),
}
