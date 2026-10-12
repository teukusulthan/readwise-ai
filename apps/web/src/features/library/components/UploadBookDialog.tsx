import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { useUploadBook } from '@/features/library/books/hooks/useUploadBook'
import { uploadSchema, type TUploadFormValues } from '@/features/library/books/schemas/upload.schema'
import { MAX_UPLOAD_MB } from '@/features/library/constants/catalog'
import type { IBook } from '@/features/library/types/book.types'
import { renderIcon } from '@/utils/icon-renderer'

interface UploadBookDialogProps {
  /** Attach the PDF to this existing catalog entry instead of creating a new book. */
  bookId?: string
  triggerLabel?: string
  onUploaded?: (book: IBook) => void
}

export function UploadBookDialog({ bookId, triggerLabel = 'Upload PDF', onUploaded }: UploadBookDialogProps) {
  const [open, setOpen] = useState(false)
  const upload = useUploadBook()
  const form = useForm<TUploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: { file: undefined, title: '' },
  })

  const onSubmit = (values: TUploadFormValues) => {
    if (!values.file) return
    upload.mutate(
      { file: values.file, bookId, title: bookId ? undefined : values.title },
      {
        onSuccess: (book) => {
          form.reset()
          setOpen(false)
          onUploaded?.(book)
        },
      },
    )
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!upload.isPending) setOpen(next)
      }}
    >
      <DialogTrigger asChild>
        <Button>
          {renderIcon({ icon: 'upload-simple' })}
          {triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{bookId ? 'Upload the book PDF' : 'Upload a PDF book'}</DialogTitle>
          <DialogDescription>
            Only upload documents you are allowed to use. Text-based PDFs up to {MAX_UPLOAD_MB} MB; scanned pages without a text layer can&apos;t be indexed.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="grid grid-cols-1 gap-4">
            <FormField
              control={form.control}
              name="file"
              // File inputs are uncontrolled: drop `value`, keep the File via onChange.
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              render={({ field: { onChange, value, ...field } }) => (
                <FormItem>
                  <FormLabel>PDF file</FormLabel>
                  <FormControl>
                    <Input {...field} type="file" accept="application/pdf,.pdf" onChange={(event) => onChange(event.target.files?.[0])} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            {!bookId && (
              <FormField
                control={form.control}
                name="title"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Title (optional)</FormLabel>
                    <FormControl>
                      <Input placeholder="Defaults to the file name" {...field} />
                    </FormControl>
                    <FormDescription>You can edit the catalog details later.</FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
            {upload.isPending && (
              <div className="space-y-1" aria-live="polite">
                <progress
                  value={upload.progress}
                  max={100}
                  aria-label="Upload progress"
                  className="h-2 w-full appearance-none overflow-hidden rounded-full bg-muted [&::-moz-progress-bar]:rounded-full [&::-moz-progress-bar]:bg-primary [&::-webkit-progress-bar]:rounded-full [&::-webkit-progress-bar]:bg-muted [&::-webkit-progress-value]:rounded-full [&::-webkit-progress-value]:bg-primary"
                />
                <p className="text-body-sm text-font-secondary">Uploading… {upload.progress}%</p>
              </div>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" disabled={upload.isPending} onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={upload.isPending}>
                {upload.isPending ? 'Uploading…' : 'Upload and index'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
