import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { bookService } from '@/services/book.service'
import { UploadBookDialog } from './UploadBookDialog'

vi.mock('@/services/book.service', () => ({ bookService: { upload: vi.fn() } }))
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

const upload = vi.mocked(bookService.upload)
const pdf = (name: string) => new File(['x'], name, { type: 'application/pdf' })

function renderDialog(props: Parameters<typeof UploadBookDialog>[0] = {}) {
  render(
    <QueryClientProvider client={new QueryClient()}>
      <UploadBookDialog {...props} />
    </QueryClientProvider>,
  )
  fireEvent.click(screen.getByRole('button', { name: /upload pdf/i }))
}

describe('UploadBookDialog', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows per-row status for a batch, including a 409 duplicate message', async () => {
    upload.mockRejectedValueOnce(new Error("This file was already uploaded as 'Dune' (id 1)."))
    upload.mockResolvedValueOnce({ data: { id: 'b', title: 'b' } } as never)
    renderDialog()
    fireEvent.change(await screen.findByLabelText('PDF files'), { target: { files: [pdf('a.pdf'), pdf('b.pdf')] } })
    expect(screen.getAllByText('Pending')).toHaveLength(2)
    fireEvent.click(screen.getByRole('button', { name: /upload and index/i }))
    expect(await screen.findByText(/already uploaded as 'Dune'/)).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Queued for indexing')).toBeInTheDocument())
    expect(upload.mock.calls.map(([payload]) => payload.title)).toEqual(['a', 'b'])
  })

  it('single file: calls onUploaded and closes', async () => {
    const created = { id: 'x', title: 'x' }
    upload.mockResolvedValueOnce({ data: created } as never)
    const onUploaded = vi.fn()
    renderDialog({ onUploaded })
    fireEvent.change(await screen.findByLabelText('PDF files'), { target: { files: [pdf('x.pdf')] } })
    fireEvent.click(screen.getByRole('button', { name: /upload and index/i }))
    await waitFor(() => expect(onUploaded).toHaveBeenCalledWith(created))
  })

  it('attach flow (bookId) keeps the single-file form', async () => {
    renderDialog({ bookId: 'b1' })
    expect(await screen.findByLabelText('PDF file')).toBeInTheDocument()
    expect(screen.queryByLabelText('PDF files')).not.toBeInTheDocument()
  })

  it('asks for confirmation before closing mid-batch', async () => {
    upload.mockImplementation(() => new Promise(() => {}))
    renderDialog()
    fireEvent.change(await screen.findByLabelText('PDF files'), { target: { files: [pdf('a.pdf'), pdf('b.pdf')] } })
    fireEvent.click(screen.getByRole('button', { name: /upload and index/i }))
    await waitFor(() => expect(screen.getByText('Uploading', { selector: 'span' })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(screen.getByRole('alertdialog')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /keep uploading/i }))
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    fireEvent.click(screen.getByRole('button', { name: /stop and close/i }))
    await waitFor(() => expect(screen.queryByLabelText('PDF files')).not.toBeInTheDocument())
  })

  it('blocks Start while a title is blank and offers Retry on failed rows', async () => {
    upload.mockRejectedValueOnce(new Error('network down'))
    upload.mockResolvedValueOnce({ data: { id: 'a', title: 'a' } } as never)
    renderDialog()
    fireEvent.change(await screen.findByLabelText('PDF files'), { target: { files: [pdf('a.pdf'), pdf('b.pdf')] } })
    fireEvent.change(screen.getByLabelText('Title for a.pdf'), { target: { value: '  ' } })
    expect(screen.getByText(/Enter a title/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /upload and index/i })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Title for a.pdf'), { target: { value: 'A' } })
    upload.mockReset()
    upload.mockRejectedValueOnce(new Error('network down'))
    upload.mockResolvedValueOnce({ data: { id: 'b', title: 'b' } } as never)
    upload.mockResolvedValueOnce({ data: { id: 'a', title: 'A' } } as never)
    fireEvent.click(screen.getByRole('button', { name: /upload and index/i }))
    fireEvent.click(await screen.findByRole('button', { name: 'Retry a.pdf' }))
    await waitFor(() => expect(upload).toHaveBeenCalledTimes(3))
    await waitFor(() => expect(screen.getAllByText('Queued for indexing')).toHaveLength(2))
  })
})
