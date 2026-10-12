import type {
  IConversation,
  IConversationDeleteResult,
  IConversationDetail,
  IConversationRenamePayload,
} from '@/features/library/chat/types/conversation.types'
import type { ApiResponse } from '@/types/api'
import { API_ENDPOINTS } from './api-endpoints'
import { apiRequests } from './api-factory.service'

/** Saved chat history (apps/backend/router/conversation.py). Turns are created by chatService.stream. */
export const conversationService = {
  getAll: (page = 1, size = 100): Promise<ApiResponse<IConversation[]>> => apiRequests.get<IConversation[]>(API_ENDPOINTS.CONVERSATION.GET_ALL, { page, size }),

  getOne: (id: string): Promise<ApiResponse<IConversationDetail>> => apiRequests.get<IConversationDetail>(API_ENDPOINTS.CONVERSATION.GET_ONE, { id }),

  rename: (payload: IConversationRenamePayload): Promise<ApiResponse<IConversation>> =>
    apiRequests.put<IConversation, IConversationRenamePayload>(API_ENDPOINTS.CONVERSATION.RENAME, payload),

  remove: (id: string): Promise<ApiResponse<IConversationDeleteResult>> => apiRequests.delete<IConversationDeleteResult>(API_ENDPOINTS.CONVERSATION.DELETE, { id }),
}
