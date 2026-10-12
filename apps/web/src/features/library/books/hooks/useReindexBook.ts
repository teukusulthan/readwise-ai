import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import { bookService } from '@/services/book.service'

export function useReindexBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => bookService.reindex(id).then((res) => res.data),
    onSuccess: (book) => {
      queryClient.setQueryData(BOOK_KEYS.detail(book.id), book)
      queryClient.invalidateQueries({ queryKey: BOOK_KEYS.all })
      toast.success('Re-indexing started')
    },
    onError: (error: Error) => toast.error('Could not start re-indexing', { description: error.message }),
  })
}
