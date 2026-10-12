import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import type { IBookCreatePayload } from '@/features/library/types/book.types'
import { bookService } from '@/services/book.service'

export function useAddBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: IBookCreatePayload) => bookService.add(payload).then((res) => res.data),
    onSuccess: (book) => {
      queryClient.invalidateQueries({ queryKey: BOOK_KEYS.all })
      toast.success(`Added "${book.title}"`)
    },
    onError: (error: Error) => toast.error('Could not add the book', { description: error.message }),
  })
}
