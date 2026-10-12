import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'

import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import type { IBookUploadPayload } from '@/features/library/types/book.types'
import { bookService } from '@/services/book.service'

/** Upload a PDF (new book or attach to `bookId`). Exposes upload `progress` 0–100. */
export function useUploadBook() {
  const queryClient = useQueryClient()
  const [progress, setProgress] = useState(0)

  const mutation = useMutation({
    mutationFn: (payload: IBookUploadPayload) => {
      setProgress(0)
      return bookService.upload(payload, setProgress).then((res) => res.data)
    },
    onSuccess: (book) => {
      queryClient.invalidateQueries({ queryKey: BOOK_KEYS.all })
      queryClient.setQueryData(BOOK_KEYS.detail(book.id), book)
      toast.success(`Uploaded "${book.title}"`, { description: 'Indexing has started. It becomes searchable when the status is Indexed.' })
    },
    onError: (error: Error) => toast.error('Upload failed', { description: error.message }),
  })

  return { ...mutation, progress }
}
