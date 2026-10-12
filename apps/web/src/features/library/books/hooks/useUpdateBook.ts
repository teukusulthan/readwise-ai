import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import type { IBookUpdatePayload } from '@/features/library/types/book.types'
import { bookService } from '@/services/book.service'

/** Errors are not toasted here: the edit dialog shows the server message inline next to the form. */
export function useUpdateBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (payload: IBookUpdatePayload) => bookService.update(payload).then((res) => res.data),
    onSuccess: (book) => {
      queryClient.invalidateQueries({ queryKey: BOOK_KEYS.detail(book.id) })
      queryClient.invalidateQueries({ queryKey: BOOK_KEYS.all })
      toast.success(`Saved "${book.title}"`)
    },
  })
}
