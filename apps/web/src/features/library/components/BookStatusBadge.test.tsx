import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { INGESTION_STATUS_META } from '@/features/library/constants/ingestion-status'
import type { TIngestionStatus } from '@/features/library/types/book.types'
import { BookStatusBadge } from './BookStatusBadge'

describe('BookStatusBadge', () => {
  it('marks indexed books as searchable', () => {
    render(<BookStatusBadge status="indexed" />)
    expect(screen.getByText('Indexed (searchable)')).toBeInTheDocument()
  })

  it('marks metadata-only books as not searchable', () => {
    render(<BookStatusBadge status="none" />)
    expect(screen.getByText('Metadata only — not searchable')).toBeInTheDocument()
  })

  it('marks failed ingestion as not searchable with the destructive style', () => {
    const { container } = render(<BookStatusBadge status="failed" />)
    expect(screen.getByText('Indexing failed — not searchable')).toBeInTheDocument()
    expect(container.firstElementChild).toHaveClass('bg-error-light')
  })

  it('never calls a non-indexed status searchable', () => {
    const notIndexed: TIngestionStatus[] = ['none', 'queued', 'processing', 'failed']
    for (const status of notIndexed) {
      expect(INGESTION_STATUS_META[status].label).toMatch(/not searchable/)
    }
    expect(INGESTION_STATUS_META.indexed.label).not.toMatch(/not searchable/)
  })
})
