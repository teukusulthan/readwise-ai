import { describe, expect, it } from 'vitest'

import { describeSkipReason, formatAuthors, formatBytes, formatPageRange } from './format'

describe('library format helpers', () => {
  it('formats page ranges for citations', () => {
    expect(formatPageRange(null, null)).toBe('')
    expect(formatPageRange(4, 4)).toBe('p. 4')
    expect(formatPageRange(4, null)).toBe('p. 4')
    expect(formatPageRange(4, 6)).toBe('pp. 4–6')
  })

  it('formats authors and sizes', () => {
    expect(formatAuthors([])).toBe('Unknown author')
    expect(formatAuthors(['A', 'B', 'C', 'D', 'E'])).toBe('A, B, C +2')
    expect(formatBytes(1536)).toBe('1.5 KB')
  })

  it('explains skip reasons', () => {
    expect(describeSkipReason('not_found')).toBe('not found')
    expect(describeSkipReason('not_indexed:queued')).toBe('still being indexed')
    expect(describeSkipReason('not_indexed:none')).toBe('metadata only, no text')
  })
})
