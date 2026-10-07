import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Citation } from '../../../../types'
import {
  buildCitationIndexMap,
  citationSelectionKey,
  segmentAssistantContent,
} from '../../../../utils/assistantContent'

interface Props {
  content: string
  citations?: Citation[]
  retrievedEvidence?: Citation[]
  activeCitationKey?: string | null
  onCitationClick?: (citation: Citation) => void
}

export function AssistantMessageBody({
  content,
  citations,
  retrievedEvidence,
  activeCitationKey,
  onCitationClick,
}: Props) {
  const indexMap = buildCitationIndexMap(citations, retrievedEvidence)
  const segments = segmentAssistantContent(content)

  return (
    <div className="chat-msg__markdown">
      {segments.map((segment, i) => {
        if (segment.type === 'text') {
          if (!segment.value.trim()) return null
          return (
            <ReactMarkdown key={`t-${i}`} remarkPlugins={[remarkGfm]}>
              {segment.value}
            </ReactMarkdown>
          )
        }

        const ref = indexMap.get(segment.index)
        const isValid = ref != null
        const key = isValid ? citationSelectionKey(ref) : `invalid-${segment.index}-${i}`
        const isActive = isValid && activeCitationKey === key

        if (!isValid) {
          return (
            <span key={key} className="chat-msg__cite chat-msg__cite--invalid" title="Citation not found">
              [{segment.index}]
            </span>
          )
        }

        return (
          <button
            key={key}
            type="button"
            className={`chat-msg__cite${isActive ? ' chat-msg__cite--active' : ''}`}
            aria-label={`View source ${segment.index}: ${ref.source_title}`}
            title={`View source ${segment.index}: ${ref.source_title}`}
            onClick={() => onCitationClick?.(ref)}
          >
            [{segment.index}]
          </button>
        )
      })}
    </div>
  )
}
