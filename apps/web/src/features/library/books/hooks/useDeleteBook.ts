import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import { bookService } from '@/services/book.service'

export function useDeleteBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => bookService.remove(id).then((res) => res.data),
    onSuccess: (result) => {
      queryClient.removeQueries({ queryKey: BOOK_KEYS.detail(result.id) })
      queryClient.invalidateQueries({ queryKey: BOOK_KEYS.all })
      toast.success('Book deleted')
    },
    onError: (error: Error) => toast.error('Could not delete the book', { description: error.message }),
  })
}
