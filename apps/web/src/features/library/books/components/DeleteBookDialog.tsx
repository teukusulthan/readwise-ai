import { useState } from 'react'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { useDeleteBook } from '@/features/library/books/hooks/useDeleteBook'
import type { IBook } from '@/features/library/types/book.types'
import { renderIcon } from '@/utils/icon-renderer'

interface DeleteBookDialogProps {
  book: IBook
  disabled?: boolean
  onDeleted: () => void
}

export function DeleteBookDialog({ book, disabled, onDeleted }: DeleteBookDialogProps) {
  const [open, setOpen] = useState(false)
  const deleteBook = useDeleteBook()

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" disabled={disabled} title={disabled ? 'Wait until indexing finishes' : undefined}>
          {renderIcon({ icon: 'trash' })}
          Delete
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete “{book.title}”?</DialogTitle>
          <DialogDescription>This removes the catalog entry, the uploaded PDF and all indexed passages. It can&apos;t be undone.</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)} disabled={deleteBook.isPending}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            disabled={deleteBook.isPending}
            onClick={() =>
              deleteBook.mutate(book.id, {
                onSuccess: () => {
                  setOpen(false)
                  onDeleted()
                },
              })
            }
          >
            {deleteBook.isPending ? 'Deleting…' : 'Delete book'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
