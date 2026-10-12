import { useRef } from 'react'

import { Button } from '@/components/ui/button'
import { DialogFooter } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { PerfectScrollArea } from '@/components/wrappers/PerfectScrollArea'
import type { IBatchRow, TBatchRowStatus } from '@/features/library/books/hooks/useBatchUpload'
import { renderIcon } from '@/utils/icon-renderer'

const STATUS_LABEL: Record<TBatchRowStatus, string> = {
  pending: 'Pending',
  uploading: 'Uploading',
  queued: 'Queued for indexing',
  error: 'Error',
}

interface BatchUploadPanelProps {
  rows: IBatchRow[]
  running: boolean
  onAddFiles: (files: File[]) => void
  onTitleChange: (id: string, title: string) => void
  onRemove: (id: string) => void
  onStart: () => void
  onClose: () => void
}

/** File picker (multiple, drag-and-drop) plus one editable row per PDF with its upload status. */
export function BatchUploadPanel({ rows, running, onAddFiles, onTitleChange, onRemove, onStart, onClose }: BatchUploadPanelProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const pendingCount = rows.filter((row) => row.status === 'pending').length
  const allDone = rows.length > 0 && !running && pendingCount === 0

  const pick = (list: FileList | null) => {
    if (list?.length) onAddFiles(Array.from(list))
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      <div
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault()
          pick(event.dataTransfer.files)
        }}
        className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border-primary p-4 text-center"
      >
        <p className="text-body-sm text-font-secondary">Drop PDFs here, or choose several at once.</p>
        <Input
          ref={inputRef}
          type="file"
          multiple
          accept="application/pdf,.pdf"
          aria-label="PDF files"
          onChange={(event) => {
            pick(event.target.files)
            event.target.value = ''
          }}
        />
      </div>

      {rows.length > 0 && (
        <div className="relative max-h-72 min-h-0 overflow-hidden">
          <PerfectScrollArea className="max-h-72">
            <ul className="space-y-2 pr-3" aria-label="Files to upload">
              {rows.map((row) => (
                <li key={row.id} className="space-y-1 rounded-md border border-border-primary p-2" data-status={row.status}>
                  <div className="flex items-center gap-2">
                    <Input
                      value={row.title}
                      aria-label={`Title for ${row.file.name}`}
                      disabled={row.status !== 'pending'}
                      onChange={(event) => onTitleChange(row.id, event.target.value)}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label={`Remove ${row.file.name}`}
                      disabled={row.status === 'uploading'}
                      onClick={() => onRemove(row.id)}
                    >
                      {renderIcon({ icon: 'x' })}
                    </Button>
                  </div>
                  <p className="truncate text-body-sm text-font-secondary">{row.file.name}</p>
                  <p className="text-body-sm" aria-live="polite">
                    <span className="font-medium">{STATUS_LABEL[row.status]}</span>
                    {row.status === 'uploading' && <span> {row.progress}%</span>}
                    {row.error && <span className="text-destructive"> — {row.error}</span>}
                  </p>
                </li>
              ))}
            </ul>
          </PerfectScrollArea>
        </div>
      )}

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>
          {allDone ? 'Close' : 'Cancel'}
        </Button>
        <Button type="button" disabled={running || pendingCount === 0} onClick={onStart}>
          {running ? 'Uploading…' : `Upload and index${pendingCount > 1 ? ` (${pendingCount})` : ''}`}
        </Button>
      </DialogFooter>
    </div>
  )
}
