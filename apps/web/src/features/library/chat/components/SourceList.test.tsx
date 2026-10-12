import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { IAnswerSource } from '@/features/library/chat/types/chat.types'
import { SourceList } from './SourceList'

const source = (overrides: Partial<IAnswerSource>): IAnswerSource => ({
  n: 1,
  bookId: 'book-1',
  bookTitle: 'Book 1',
  headings: [],
  pageStart: 12,
  pageEnd: 14,
  score: 0.7,
  text: 'Passage text',
  cited: true,
  ...overrides,
})

describe('SourceList', () => {
  it('links each source to its PDF at the first cited page, in a new tab', () => {
    render(<SourceList sources={[source({})]} expandAll />)

    const link = screen.getByRole('link', { name: /Open page 12/ })
    expect(link).toHaveAttribute('href', '/api/v1/apps/book/file?id=book-1#page=12')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('hides the link when the source has no page information', () => {
    render(<SourceList sources={[source({ pageStart: null, pageEnd: null })]} expandAll />)

    expect(screen.queryByRole('link', { name: /Open page/ })).not.toBeInTheDocument()
  })
})
