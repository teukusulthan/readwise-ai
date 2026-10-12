import { useQuery } from '@tanstack/react-query'

import { CONVERSATION_KEYS } from '@/features/library/constants/query-keys'
import { chatService } from '@/services/chat.service'

/**
 * Is an answer of this conversation still being generated (e.g. after a reload, or when the
 * user comes back to it)? Never served from cache: every visit asks the server again, so a
 * turn that kept running while the user was elsewhere is found and re-attached.
 * An error (nothing running, or Redis unavailable) just means: show the saved history.
 */
export function useActiveTurn(conversationId: string | undefined) {
  return useQuery({
    queryKey: CONVERSATION_KEYS.active(conversationId ?? ''),
    queryFn: () => chatService.active(conversationId as string).then((res) => res.data),
    enabled: !!conversationId,
    staleTime: 0,
    gcTime: 0,
    retry: false,
  })
}
