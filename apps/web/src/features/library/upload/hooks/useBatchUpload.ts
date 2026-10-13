import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useRef, useState } from 'react'

import { MAX_UPLOAD_MB } from '@/features/library/constants/catalog'
import { BOOK_KEYS } from '@/features/library/constants/query-keys'
import type { IBook } from '@/features/library/types/book.types'
import { ApiError } from '@/services/api-error'
import { bookService } from '@/services/book.service'

export type TBatchRowStatus = 'pending' | 'uploading' | 'waiting' | 'queued' | 'error'

export interface IBatchRow {
  id: string
  file: File
  title: string
  status: TBatchRowStatus
  progress: number
  error?: string
  /** True when the failure came from the upload itself (not local validation), so it may be retried. */
  retryable?: boolean
  /** While `waiting`: seconds left before the rate-limited upload is sent again. */
  waitSeconds?: number
  book?: IBook
}

/** Automatic re-sends of one row after a 429; the next 429 marks the row as a (retryable) error. */
export const MAX_RATE_LIMIT_RETRIES = 3
/** Used when a 429 carries no usable `Retry-After`. */
const DEFAULT_RETRY_AFTER_SECONDS = 5
const MAX_RETRY_AFTER_SECONDS = 300

/**
 * Seconds to wait before re-sending, when `error` is a 429 (rate limit or capacity cap); otherwise undefined.
 * `Retry-After` is read as delay-seconds or an HTTP date, clamped to 1..300 s.
 */
export function rateLimitDelaySeconds(error: unknown): number | undefined {
  if (!(error instanceof ApiError) || error.status !== 429) return undefined
  const headers = error.response?.headers as Record<string, unknown> | undefined
  const raw = headers?.['retry-after'] ?? headers?.['Retry-After']
  let seconds = typeof raw === 'number' || (typeof raw === 'string' && raw.trim() !== '') ? Number(raw) : NaN
  if (Number.isNaN(seconds) && typeof raw === 'string') {
    const at = Date.parse(raw)
    if (!Number.isNaN(at)) seconds = (at - Date.now()) / 1000
  }
  if (!Number.isFinite(seconds)) seconds = DEFAULT_RETRY_AFTER_SECONDS
  return Math.min(MAX_RETRY_AFTER_SECONDS, Math.max(1, Math.ceil(seconds)))
}

/** Resolves true after `ms`, or false as soon as `signal` aborts. */
function sleep(ms: number, signal: AbortSignal): Promise<boolean> {
  return new Promise((resolve) => {
    if (signal.aborted) return resolve(false)
    const onAbort = () => {
      clearTimeout(timer)
      resolve(false)
    }
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', onAbort)
      resolve(true)
    }, ms)
    signal.addEventListener('abort', onAbort, { once: true })
  })
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
 * A 429 (upload rate limit, ingestion queue full) is not a failure: the row waits `Retry-After`
 * seconds (`waiting`, counting down) and is re-sent, up to MAX_RATE_LIMIT_RETRIES times. `stop()`,
 * closing the dialog or removing the row cancels the wait and leaves the row pending.
 */
export function useBatchUpload() {
  const queryClient = useQueryClient()
  const [rows, setRows] = useState<IBatchRow[]>([])
  const [running, setRunning] = useState(false)
  const stopRequested = useRef(false)
  const runningRef = useRef(false)
  // Latest rows for the async loop (titles stay editable while earlier rows upload).
  const rowsRef = useRef<IBatchRow[]>([])
  // Aborted by stop() (and on unmount) to cancel a rate-limit wait at once.
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => () => abortRef.current?.abort(), [])

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
    abortRef.current?.abort()
  }, [])

  /** Count down `seconds` on the row; false when stopped or the row was removed meanwhile. */
  const waitForRateLimit = useCallback(
    async (id: string, seconds: number, signal: AbortSignal) => {
      for (let left = seconds; left > 0; left--) {
        patch(id, { status: 'waiting', waitSeconds: left })
        if (!(await sleep(1000, signal))) return false
        if (!rowsRef.current.some((row) => row.id === id)) return false
      }
      return true
    },
    [patch],
  )

  const start = useCallback(async () => {
    if (runningRef.current) return
    runningRef.current = true
    stopRequested.current = false
    const controller = new AbortController()
    abortRef.current = controller
    setRunning(true)
    try {
      for (;;) {
        if (stopRequested.current) break
        const row = rowsRef.current.find((r) => r.status === 'pending' && r.title.trim())
        if (!row) break
        for (let rateLimitRetries = 0; ; rateLimitRetries++) {
          patch(row.id, { status: 'uploading', progress: 0, error: undefined, waitSeconds: undefined })
          try {
            const res = await bookService.upload({ file: row.file, title: row.title.trim() }, (progress) => patch(row.id, { progress }))
            queryClient.setQueryData(BOOK_KEYS.detail(res.data.id), res.data)
            queryClient.invalidateQueries({ queryKey: BOOK_KEYS.all })
            patch(row.id, { status: 'queued', progress: 100, book: res.data })
            break
          } catch (error) {
            const delay = rateLimitDelaySeconds(error)
            if (delay === undefined || rateLimitRetries >= MAX_RATE_LIMIT_RETRIES) {
              patch(row.id, { status: 'error', retryable: true, waitSeconds: undefined, error: error instanceof Error ? error.message : 'Upload failed' })
              break
            }
            if (!(await waitForRateLimit(row.id, delay, controller.signal))) {
              patch(row.id, { status: 'pending', progress: 0, waitSeconds: undefined })
              break
            }
          }
        }
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null
      runningRef.current = false
      setRunning(false)
    }
  }, [patch, queryClient, waitForRateLimit])

  const getRows = useCallback(() => rowsRef.current, [])

  return { rows, getRows, running, addFiles, setTitle, removeRow, retry, reset, start, stop }
}
