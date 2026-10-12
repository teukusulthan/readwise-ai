import { beforeEach, describe, expect, it, vi } from 'vitest'

import { API_ENDPOINTS } from './api-endpoints'
import { apiRequests } from './api-factory.service'
import { bookService } from './book.service'

vi.mock('./api-factory.service', () => ({
  apiRequests: {
    get: vi.fn().mockResolvedValue({ data: null }),
    post: vi.fn().mockResolvedValue({ data: null }),
    delete: vi.fn().mockResolvedValue({ data: null }),
    upload: vi.fn().mockResolvedValue({ data: null }),
  },
}))

describe('bookService', () => {
  beforeEach(() => vi.clearAllMocks())

  it('lists books with POST /book/get-all and the filter body', async () => {
    const params = { search: 'dune', status: ['indexed' as const], page: 2, size: 12 }
    await bookService.getAll(params)
    expect(apiRequests.post).toHaveBeenCalledWith(API_ENDPOINTS.BOOK.GET_ALL, params)
    expect(API_ENDPOINTS.BOOK.GET_ALL).toBe('/apps/book/get-all')
  })

  it('reads and deletes by ?id= query parameter', async () => {
    await bookService.getOne('abc')
    await bookService.remove('abc')
    expect(apiRequests.get).toHaveBeenCalledWith(API_ENDPOINTS.BOOK.GET_ONE, { id: 'abc' })
    expect(apiRequests.delete).toHaveBeenCalledWith(API_ENDPOINTS.BOOK.DELETE, { id: 'abc' })
  })

  it('uploads multipart form data with file, bookId and trimmed title', async () => {
    const file = new File(['%PDF-1.4'], 'book.pdf', { type: 'application/pdf' })
    const onProgress = vi.fn()
    await bookService.upload({ file, bookId: 'b1', title: '  My Book  ' }, onProgress)

    const [url, formData, progress] = vi.mocked(apiRequests.upload).mock.calls[0]
    expect(url).toBe(API_ENDPOINTS.BOOK.UPLOAD)
    expect((formData as FormData).get('file')).toBe(file)
    expect((formData as FormData).get('bookId')).toBe('b1')
    expect((formData as FormData).get('title')).toBe('My Book')
    expect(progress).toBe(onProgress)
  })

  it('omits empty optional upload fields', async () => {
    const file = new File(['%PDF-1.4'], 'book.pdf', { type: 'application/pdf' })
    await bookService.upload({ file, title: '   ' })
    const formData = vi.mocked(apiRequests.upload).mock.calls[0][1] as FormData
    expect(formData.has('bookId')).toBe(false)
    expect(formData.has('title')).toBe(false)
  })

  it('reindexes with the id in the query string and imports by ISBN', async () => {
    await bookService.reindex('a b')
    await bookService.importByIsbn('9780441013593')
    await bookService.lookup('dune')
    expect(apiRequests.post).toHaveBeenCalledWith(`${API_ENDPOINTS.BOOK.REINDEX}?id=a%20b`, null)
    expect(apiRequests.post).toHaveBeenCalledWith(API_ENDPOINTS.BOOK.IMPORT, { isbn: '9780441013593' })
    expect(apiRequests.get).toHaveBeenCalledWith(API_ENDPOINTS.BOOK.LOOKUP, { q: 'dune' })
  })
})
