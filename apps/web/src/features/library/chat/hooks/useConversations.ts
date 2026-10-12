import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { CONVERSATION_KEYS } from '@/features/library/constants/query-keys'
import type { IConversationRenamePayload } from '@/features/library/chat/types/conversation.types'
import { conversationService } from '@/services/conversation.service'

/** Saved conversations, most recently active first. */
export function useConversations() {
  return useQuery({
    queryKey: CONVERSATION_KEYS.list,
    queryFn: () => conversationService.getAll().then((res) => res.data),
  })
}

/** One conversation with all its messages. */
export function useConversation(id: string | undefined) {
  return useQuery({
    queryKey: CONVERSATION_KEYS.detail(id ?? ''),
    queryFn: () => conversationService.getOne(id as string).then((res) => res.data),
    enabled: !!id,
    retry: false,
  })
}

export function useRenameConversation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: IConversationRenamePayload) => conversationService.rename(payload).then((res) => res.data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: CONVERSATION_KEYS.all }),
    onError: (error: Error) => toast.error('Could not rename the conversation', { description: error.message }),
  })
}

export function useDeleteConversation() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => conversationService.remove(id).then((res) => res.data),
    onSuccess: (result) => {
      queryClient.removeQueries({ queryKey: CONVERSATION_KEYS.detail(result.id) })
      queryClient.invalidateQueries({ queryKey: CONVERSATION_KEYS.list })
      toast.success('Conversation deleted')
    },
    onError: (error: Error) => toast.error('Could not delete the conversation', { description: error.message }),
  })
}
