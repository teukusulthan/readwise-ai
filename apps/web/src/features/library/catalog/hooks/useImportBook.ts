import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import { bookService } from '@/services/book.service'

export function useImportBook() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (isbn: string) => bookService.importByIsbn(isbn).then((res) => res.data),
    onSuccess: (book) => {
      queryClient.invalidateQueries({ queryKey: BOOK_KEYS.all })
      toast.success(`Imported "${book.title}"`, { description: 'Metadata only — upload a PDF to make it searchable.' })
    },
    onError: (error: Error) => toast.error('Import failed', { description: error.message }),
  })
}
