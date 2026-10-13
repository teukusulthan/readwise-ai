import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import type { IBatchRow } from '@/features/library/upload/hooks/useBatchUpload'
import { BatchUploadPanel } from './BatchUploadPanel'

const row = (changes: Partial<IBatchRow>): IBatchRow => ({
  id: 'row-1',
  file: new File(['x'], 'a.pdf', { type: 'application/pdf' }),
  title: 'A',
  status: 'pending',
  progress: 0,
  ...changes,
})

function renderPanel(rows: IBatchRow[]) {
  const noop = vi.fn()
  render(
    <Dialog open>
      <DialogContent aria-describedby={undefined}>
        <DialogTitle>Upload</DialogTitle>
        <BatchUploadPanel rows={rows} running onAddFiles={noop} onTitleChange={noop} onRemove={noop} onRetry={noop} onStart={noop} onClose={noop} />
      </DialogContent>
    </Dialog>,
  )
}

describe('BatchUploadPanel', () => {
  it('shows the rate-limit countdown of a waiting row', () => {
    renderPanel([row({ status: 'waiting', waitSeconds: 12 })])
    expect(screen.getByText('Waiting 12s (rate limit)…')).toBeInTheDocument()
    expect(screen.getByLabelText('Title for a.pdf')).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Remove a.pdf' })).toBeEnabled()
  })
})
