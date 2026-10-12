/** Pure display helpers for the library domain. */

export function formatAuthors(authors: string[]): string {
  if (!authors.length) return 'Unknown author'
  if (authors.length <= 3) return authors.join(', ')
  return `${authors.slice(0, 3).join(', ')} +${authors.length - 3}`
}

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes && bytes !== 0) return '—'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`
}

/** "p. 4" / "pp. 4–6" / '' when unknown. */
export function formatPageRange(start: number | null, end: number | null): string {
  if (!start) return ''
  if (!end || end === start) return `p. ${start}`
  return `pp. ${start}–${end}`
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

/** Human text for a skipped-book reason from the backend (`not_found`, `not_indexed:<status>`). */
export function describeSkipReason(reason: string): string {
  if (reason === 'not_found') return 'not found'
  if (reason.startsWith('not_indexed:')) {
    const status = reason.split(':')[1]
    if (status === 'none') return 'metadata only, no text'
    if (status === 'queued' || status === 'processing') return 'still being indexed'
    if (status === 'failed') return 'indexing failed'
    return `not indexed (${status})`
  }
  return reason
}
