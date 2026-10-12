/** Pure helpers that turn plain-text answers into paragraphs, lists and citation segments. */

export type TAnswerSegment = { type: 'text'; text: string } | { type: 'cite'; n: number }

export type TAnswerBlock = { type: 'p'; text: string } | { type: 'ul' | 'ol'; items: string[] }

const CITATION_RE = /\[(\d{1,2})\]/g

/**
 * Heading line that starts the part of an answer coming from the model's general knowledge
 * (backend: service/rag.py GENERAL_HEADING). Tolerates stray Markdown and a missing colon,
 * and also matches while the heading is still being streamed in full.
 */
const GENERAL_HEADING_RE = /^[ \t>*_#-]*general knowledge\s*[:：]?[*_ \t]*/im

/** `[bookPart, generalPart]`; `generalPart` is null when the answer has no general-knowledge section. */
export function splitGeneralKnowledge(text: string): [string, string | null] {
  const match = GENERAL_HEADING_RE.exec(text)
  if (!match) return [text, null]
  return [text.slice(0, match.index), text.slice(match.index + match[0].length)]
}

/** Every line break starts a new paragraph (models separate paragraphs with one or two newlines). */
export function splitParagraphs(text: string): string[] {
  return text
    .replace(/\r\n?/g, '\n')
    .split(/\n+/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
}

const BULLET_RE = /^[-•*]\s+/
const NUMBERED_RE = /^\d{1,2}[.)]\s+/

/** Group consecutive "- item" / "1. item" lines into lists; everything else is a paragraph. */
export function toBlocks(paragraphs: string[]): TAnswerBlock[] {
  const blocks: TAnswerBlock[] = []
  for (const paragraph of paragraphs) {
    const listType = BULLET_RE.test(paragraph) ? 'ul' : NUMBERED_RE.test(paragraph) ? 'ol' : null
    if (!listType) {
      blocks.push({ type: 'p', text: paragraph })
      continue
    }
    const item = paragraph.replace(listType === 'ul' ? BULLET_RE : NUMBERED_RE, '')
    const previous = blocks[blocks.length - 1]
    if (previous && previous.type === listType) previous.items.push(item)
    else blocks.push({ type: listType, items: [item] })
  }
  return blocks
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
