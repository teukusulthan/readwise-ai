import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useRef, useState } from 'react'

import { MAX_UPLOAD_MB } from '@/features/library/constants/catalog'
import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import type { IBook } from '@/features/library/types/book.types'
import { bookService } from '@/services/book.service'

export type TBatchRowStatus = 'pending' | 'uploading' | 'queued' | 'error'

export interface IBatchRow {
  id: string
  file: File
  title: string
  status: TBatchRowStatus
  progress: number
  error?: string
  /** True when the failure came from the upload itself (not local validation), so it may be retried. */
  retryable?: boolean
  book?: IBook
}

/** "Dune_Messiah.pdf" -> "Dune Messiah". */
export function titleFromFileName(name: string): string {
  const derived = name
    .replace(/\.pdf$/i, '')
    .replace(/[_]+/g, ' ')
    .trim()
  return derived || name.trim()
}

export const BLANK_TITLE_ERROR = 'Enter a title'

export const hasBlankTitle = (row: Pick<IBatchRow, 'status' | 'title'>) => row.status === 'pending' && !row.title.trim()

function validate(file: File): string | undefined {
  if (!file.name.toLowerCase().endsWith('.pdf')) return 'Only .pdf files are supported'
  if (file.size > MAX_UPLOAD_MB * 1024 * 1024) return `The file must be ${MAX_UPLOAD_MB} MB or smaller`
  return undefined
}

let nextId = 0

/**
 * Upload several PDFs as separate `POST /book/upload` calls, strictly one after another.
 * Rows already uploaded (queued) or failed are never retried by `start()`; `stop()` leaves the
 * in-flight file to finish and keeps the remaining rows pending.
 */
export function useBatchUpload() {
  const queryClient = useQueryClient()
  const [rows, setRows] = useState<IBatchRow[]>([])
  const [running, setRunning] = useState(false)
  const stopRequested = useRef(false)
  const runningRef = useRef(false)
  // Latest rows for the async loop (titles stay editable while earlier rows upload).
  const rowsRef = useRef<IBatchRow[]>([])

  const commit = useCallback((next: IBatchRow[]) => {
    rowsRef.current = next
    setRows(next)
  }, [])

  const patch = useCallback(
    (id: string, changes: Partial<IBatchRow>) => commit(rowsRef.current.map((row) => (row.id === id ? { ...row, ...changes } : row))),
    [commit],
  )

  const addFiles = useCallback(
    (files: File[]) => {
      const added = files.map<IBatchRow>((file) => {
        const error = validate(file)
        return { id: `row-${nextId++}`, file, title: titleFromFileName(file.name), status: error ? 'error' : 'pending', progress: 0, error }
      })
      commit([...rowsRef.current, ...added])
    },
    [commit],
  )

  const setTitle = useCallback((id: string, title: string) => patch(id, { title }), [patch])

  const removeRow = useCallback(
    (id: string) => commit(rowsRef.current.filter((row) => row.id !== id || row.status === 'uploading')),
    [commit],
  )

  /** Re-queue a row whose upload failed. Local validation failures and queued rows are left alone. */
  const retry = useCallback(
    (id: string) => {
      const row = rowsRef.current.find((r) => r.id === id)
      if (row?.status === 'error' && row.retryable) patch(id, { status: 'pending', progress: 0, error: undefined, retryable: false })
    },
    [patch],
  )

  const reset = useCallback(() => commit([]), [commit])

  const stop = useCallback(() => {
    stopRequested.current = true
  }, [])

  const start = useCallback(async () => {
    if (runningRef.current) return
    runningRef.current = true
    stopRequested.current = false
    setRunning(true)
    try {
      for (;;) {
        if (stopRequested.current) break
        const row = rowsRef.current.find((r) => r.status === 'pending' && r.title.trim())
        if (!row) break
        patch(row.id, { status: 'uploading', progress: 0, error: undefined })
        try {
          const res = await bookService.upload({ file: row.file, title: row.title.trim() }, (progress) => patch(row.id, { progress }))
          queryClient.setQueryData(BOOK_KEYS.detail(res.data.id), res.data)
          queryClient.invalidateQueries({ queryKey: BOOK_KEYS.all })
          patch(row.id, { status: 'queued', progress: 100, book: res.data })
        } catch (error) {
          patch(row.id, { status: 'error', retryable: true, error: error instanceof Error ? error.message : 'Upload failed' })
        }
      }
    } finally {
      runningRef.current = false
      setRunning(false)
    }
  }, [patch, queryClient])

  const getRows = useCallback(() => rowsRef.current, [])

  return { rows, getRows, running, addFiles, setTitle, removeRow, retry, reset, start, stop }
}
