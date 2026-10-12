import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useUpdateBook } from '@/features/library/books/hooks/useUpdateBook'
import { bookToFormValues, editBookSchema, formValuesToPayload, type TEditBookFormValues } from '@/features/library/books/schemas/edit-book.schema'
import type { IBook } from '@/features/library/types/book.types'
import { renderIcon } from '@/utils/icon-renderer'

interface EditBookDialogProps {
  book: IBook
}

export function EditBookDialog({ book }: EditBookDialogProps) {
  const [open, setOpen] = useState(false)
  const updateBook = useUpdateBook()
  const form = useForm<TEditBookFormValues>({ resolver: zodResolver(editBookSchema), defaultValues: bookToFormValues(book) })

  const handleOpenChange = (next: boolean) => {
    if (next) {
      form.reset(bookToFormValues(book))
      updateBook.reset()
    }
    setOpen(next)
  }

  const onSubmit = (values: TEditBookFormValues) => {
    updateBook.mutate(formValuesToPayload(book.id, values), {
      onSuccess: () => setOpen(false),
      onError: (error: Error) => {
        // Keep ISBN problems (bad checksum, duplicate -> 409) next to the ISBN input.
        if (/isbn/i.test(error.message)) form.setError('isbn', { type: 'server', message: error.message })
      },
    })
  }

  const serverError = updateBook.error && !form.formState.errors.isbn ? updateBook.error.message : null

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          {renderIcon({ icon: 'pencil-simple' })}
          Edit details
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit book details</DialogTitle>
          <DialogDescription>Fix the catalog metadata. The uploaded document is not changed.</DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <FormField
              control={form.control}
              name="title"
              render={({ field }) => (
                <FormItem className="sm:col-span-2">
                  <FormLabel>Title</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="authors"
              render={({ field }) => (
                <FormItem className="sm:col-span-2">
                  <FormLabel>Authors</FormLabel>
                  <FormControl>
                    <Input placeholder="Comma separated" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="isbn"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>ISBN</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormDescription>Checked by the server.</FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="publishedYear"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Year</FormLabel>
                  <FormControl>
                    <Input inputMode="numeric" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="publisher"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Publisher</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="language"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Language</FormLabel>
                  <FormControl>
                    <Input placeholder="e.g. en" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="subjects"
              render={({ field }) => (
                <FormItem className="sm:col-span-2">
                  <FormLabel>Subjects</FormLabel>
                  <FormControl>
                    <Input placeholder="Comma separated" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="coverUrl"
              render={({ field }) => (
                <FormItem className="sm:col-span-2">
                  <FormLabel>Cover URL</FormLabel>
                  <FormControl>
                    <Input inputMode="url" placeholder="https://" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem className="sm:col-span-2">
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea rows={4} {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            {serverError && (
              <p role="alert" className="text-body-sm text-error-bold sm:col-span-2">
                {serverError}
              </p>
            )}
            <DialogFooter className="sm:col-span-2">
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={updateBook.isPending}>
                {updateBook.isPending ? 'Saving…' : 'Save changes'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
