/** Pure helpers for answers: citation segments and the general-knowledge split. */

export type TAnswerSegment = { type: 'text'; text: string } | { type: 'cite'; n: number }

const CITATION_RE = /\[(\d{1,2})\]/g

/**
 * A line starting with optional Markdown decoration, "general knowledge" (any case) and a REQUIRED
 * colon (backend: service/rag.py GENERAL_HEADING / _GENERAL_RE use the same rule). Text after the
 * colon on the same line belongs to the general part. "General knowledge of ..." never splits.
 * Matches as soon as the colon has streamed in.
 */
const GENERAL_HEADING_RE = /^[ \t>#*_-]*general knowledge[ \t]*[*_]*[ \t]*[:：][*_ \t]*/im

/** `[bookPart, generalPart]`; `generalPart` is null when the answer has no general-knowledge section. */
export function splitGeneralKnowledge(text: string): [string, string | null] {
  const match = GENERAL_HEADING_RE.exec(text)
  if (!match) return [text, null]
  return [text.slice(0, match.index), text.slice(match.index + match[0].length)]
}

/**
 * Split a paragraph into text and `[n]` citation segments.
 * Markers that don't match a known source number stay as literal text.
 */
export function segmentCitations(paragraph: string, sourceNumbers: ReadonlySet<number>): TAnswerSegment[] {
  const segments: TAnswerSegment[] = []
  let last = 0
  for (const match of paragraph.matchAll(CITATION_RE)) {
    const n = Number(match[1])
    if (!sourceNumbers.has(n)) continue
    const index = match.index ?? 0
    if (index > last) segments.push({ type: 'text', text: paragraph.slice(last, index) })
    segments.push({ type: 'cite', n })
    last = index + match[0].length
  }
  if (last < paragraph.length) segments.push({ type: 'text', text: paragraph.slice(last) })
  return segments
}
