import type { Citation } from '../types'

const SOURCE_CITATION_RE = /\[Source\s+(\d+)\]/gi

export const INSUFFICIENT_ANSWER_PHRASE =
  "couldn't find enough information about that in the uploaded sources"

export function isInsufficientAnswer(content: string): boolean {
  return content.toLowerCase().includes(INSUFFICIENT_ANSWER_PHRASE)
}

/** Undo common escaped-markdown artifacts from model output. */
export function normalizeAssistantMarkdown(raw: string): string {
  if (!raw) return ''
  let text = raw.replace(/\\n/g, '\n').replace(/\\t/g, '\t')
  text = text.replace(/\\([\\`*_{}\[\]()#+\-.!|>])/g, '$1')
  return text
}

export type ContentSegment =
  | { type: 'text'; value: string }
  | { type: 'citation'; index: number }

export function segmentAssistantContent(content: string): ContentSegment[] {
  const normalized = normalizeAssistantMarkdown(content)
  const parts: ContentSegment[] = []
  let lastIndex = 0

  for (const match of normalized.matchAll(SOURCE_CITATION_RE)) {
    const start = match.index ?? 0
    if (start > lastIndex) {
      parts.push({ type: 'text', value: normalized.slice(lastIndex, start) })
    }
    parts.push({ type: 'citation', index: Number.parseInt(match[1], 10) })
    lastIndex = start + match[0].length
  }

  if (lastIndex < normalized.length) {
    parts.push({ type: 'text', value: normalized.slice(lastIndex) })
  }

  if (parts.length === 0) {
    parts.push({ type: 'text', value: normalized })
  }

  return parts
}

export function buildCitationIndexMap(
  citations: Citation[] | undefined,
  retrievedEvidence: Citation[] | undefined,
): Map<number, Citation> {
  const map = new Map<number, Citation>()
  for (const ref of [...(citations ?? []), ...(retrievedEvidence ?? [])]) {
    const idx = ref.citation_index
    if (idx != null && !map.has(idx)) {
      map.set(idx, ref)
    }
  }
  return map
}

export function citationSelectionKey(citation: Citation): string {
  if (citation.id) return citation.id
  if (citation.citation_index != null && citation.chunk_id) {
    return `${citation.citation_index}-${citation.chunk_id}`
  }
  if (citation.citation_index != null) {
    return `idx-${citation.citation_index}`
  }
  return `${citation.source_id}-${citation.chunk_index ?? 0}`
}

export function formatCitationMeta(citation: Citation): string {
  const bits: string[] = []
  if (citation.page != null) bits.push(`Page ${citation.page}`)
  if (citation.chunk_index != null) bits.push(`Chunk ${citation.chunk_index}`)
  if (citation.section) bits.push(citation.section)
  return bits.join(' · ')
}
