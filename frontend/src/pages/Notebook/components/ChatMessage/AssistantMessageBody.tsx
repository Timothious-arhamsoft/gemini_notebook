import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import type { Citation } from '../../../../types'
import {
  buildCitationIndexMap,
  citationSelectionKey,
  parseCitationHref,
  toCitationMarkdown,
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
  const markdown = toCitationMarkdown(content)

  const components: Components = {
    a: ({ href, children }) => {
      const index = parseCitationHref(href)
      if (index == null) {
        return (
          <a href={href} target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        )
      }

      const ref = indexMap.get(index)
      if (ref == null) {
        return (
          <span className="chat-msg__cite chat-msg__cite--invalid" title="Citation not found">
            [{index}]
          </span>
        )
      }

      const isActive = activeCitationKey === citationSelectionKey(ref)

      return (
        <button
          type="button"
          className={`chat-msg__cite${isActive ? ' chat-msg__cite--active' : ''}`}
          aria-label={`View source ${index}: ${ref.source_title}`}
          title={`View source ${index}: ${ref.source_title}`}
          onClick={() => onCitationClick?.(ref)}
        >
          [{index}]
        </button>
      )
    },
  }

  return (
    <div className="chat-msg__markdown">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {markdown}
      </ReactMarkdown>
    </div>
  )
}
