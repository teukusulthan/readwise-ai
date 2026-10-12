import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { useBatchUpload } from '@/features/library/upload/hooks/useBatchUpload'
import { useUploadBook } from '@/features/library/upload/hooks/useUploadBook'
import { uploadSchema, type TUploadFormValues } from '@/features/library/upload/schemas/upload.schema'
import { MAX_UPLOAD_MB } from '@/features/library/constants/catalog'
import type { IBook } from '@/features/library/types/book.types'
import { BatchUploadPanel } from './BatchUploadPanel'
import { renderIcon } from '@/utils/icon-renderer'

interface UploadBookDialogProps {
  /** Attach the PDF to this existing catalog entry instead of creating a new book. */
  bookId?: string
  triggerLabel?: string
  onUploaded?: (book: IBook) => void
}

export function UploadBookDialog({ bookId, triggerLabel = 'Upload PDF', onUploaded }: UploadBookDialogProps) {
  const [open, setOpen] = useState(false)
  const [confirmClose, setConfirmClose] = useState(false)
  const upload = useUploadBook()
  const batch = useBatchUpload()
  const form = useForm<TUploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: { file: undefined },
  })

  const onSubmit = (values: TUploadFormValues) => {
    if (!values.file) return
    upload.mutate(
      { file: values.file, bookId },
      {
        onSuccess: (book) => {
          form.reset()
          setOpen(false)
          onUploaded?.(book)
        },
      },
    )
  }

  const closeBatch = () => {
    setConfirmClose(false)
    batch.stop()
    setOpen(false)
    batch.reset() // a new batch starts clean; an in-flight file still finishes in the background
  }

  const retryRow = (id: string) => {
    batch.retry(id)
    if (!batch.running) void startBatch()
  }

  const startBatch = async () => {
    const single = batch.rows.length === 1
    await batch.start()
    // Preserve the single-file flow: close and hand the new book to the caller.
    const done = batch.getRows()
    if (single && done[0]?.book) {
      batch.reset()
      setOpen(false)
      onUploaded?.(done[0].book)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (next) return setOpen(true)
        if (bookId) {
          if (!upload.isPending) setOpen(false)
        } else if (batch.running) setConfirmClose(true)
        else closeBatch()
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
          <DialogTitle>{bookId ? 'Upload the book PDF' : 'Upload PDF books'}</DialogTitle>
          <DialogDescription>
            Only upload documents you are allowed to use. Text-based PDFs up to {MAX_UPLOAD_MB} MB; scanned pages without a text layer can&apos;t be indexed.
          </DialogDescription>
        </DialogHeader>
        {!bookId && (
          <>
            <BatchUploadPanel
              rows={batch.rows}
              running={batch.running}
              onAddFiles={batch.addFiles}
              onTitleChange={batch.setTitle}
              onRemove={batch.removeRow}
              onRetry={retryRow}
              onStart={startBatch}
              onClose={() => (batch.running ? setConfirmClose(true) : closeBatch())}
            />
            {confirmClose && (
              <div role="alertdialog" aria-label="Stop uploading?" className="space-y-2 rounded-md border border-border-primary p-3">
                <p className="text-body-sm">
                  Uploads are still running. The file being sent will finish, but the files still waiting will not be uploaded. Close anyway?
                </p>
                <div className="flex justify-end gap-2">
                  <Button type="button" variant="outline" size="xs" onClick={() => setConfirmClose(false)}>
                    Keep uploading
                  </Button>
                  <Button type="button" size="xs" onClick={closeBatch}>
                    Stop and close
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
        {bookId && <Form {...form}>
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
        </Form>}
      </DialogContent>
    </Dialog>
  )
}
