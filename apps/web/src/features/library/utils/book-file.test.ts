import { describe, expect, it } from 'vitest'

import { bookFileUrl } from './book-file'

describe('bookFileUrl', () => {
  it('points at the file endpoint through the API base', () => {
    expect(bookFileUrl('abc-123')).toBe('/api/v1/apps/book/file?id=abc-123')
  })

  it('adds the page fragment for a valid page only', () => {
    expect(bookFileUrl('abc-123', 7)).toBe('/api/v1/apps/book/file?id=abc-123#page=7')
    expect(bookFileUrl('abc-123', null)).not.toContain('#')
    expect(bookFileUrl('abc-123', 0)).not.toContain('#')
  })

  it('encodes the id', () => {
    expect(bookFileUrl('a&b')).toContain('id=a%26b')
  })
})
