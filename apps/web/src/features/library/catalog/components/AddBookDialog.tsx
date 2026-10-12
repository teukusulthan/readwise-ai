import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'

import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useAddBook } from '@/features/library/catalog/hooks/useAddBook'
import { addBookSchema, type TAddBookFormValues } from '@/features/library/catalog/schemas/add-book.schema'
import { renderIcon } from '@/utils/icon-renderer'

const EMPTY: TAddBookFormValues = { title: '', authors: '', isbn: '', publishedYear: '', description: '' }

export function AddBookDialog() {
  const [open, setOpen] = useState(false)
  const addBook = useAddBook()
  const form = useForm<TAddBookFormValues>({ resolver: zodResolver(addBookSchema), defaultValues: EMPTY })

  const onSubmit = (values: TAddBookFormValues) => {
    addBook.mutate(
      {
        title: values.title,
        authors: values.authors
          .split(',')
          .map((author) => author.trim())
          .filter(Boolean),
        isbn: values.isbn.trim() || undefined,
        publishedYear: values.publishedYear ? Number(values.publishedYear) : undefined,
        description: values.description.trim() || undefined,
        subjects: [],
      },
      {
        onSuccess: () => {
          form.reset(EMPTY)
          setOpen(false)
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline">
          {renderIcon({ icon: 'plus' })}
          Add manually
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add a catalog entry</DialogTitle>
          <DialogDescription>Creates a metadata-only book. Upload its PDF later to make it searchable.</DialogDescription>
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
            <DialogFooter className="sm:col-span-2">
              <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={addBook.isPending}>
                {addBook.isPending ? 'Saving…' : 'Add book'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
