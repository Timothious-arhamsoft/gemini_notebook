import type { ChatMessage as ChatMessageType, Citation } from '../../../../types'
import {
  buildCitationIndexMap,
  citationSelectionKey,
  formatCitationMeta,
  isInsufficientAnswer,
  segmentAssistantContent,
} from '../../../../utils/assistantContent'
import { AssistantMessageBody } from './AssistantMessageBody'

interface Props {
  message: ChatMessageType
  activeCitationKey?: string | null
  onCitationClick?: (citation: Citation) => void
}

/** Prefer persisted citations; recover from markers + retrieved_evidence if needed. */
function resolveSourceList(message: ChatMessageType): Citation[] {
  if (message.citations?.length) return message.citations
  const map = buildCitationIndexMap(undefined, message.retrieved_evidence)
  if (map.size === 0) return []
  const seen = new Set<number>()
  const recovered: Citation[] = []
  for (const part of segmentAssistantContent(message.content)) {
    if (part.type !== 'citation' || seen.has(part.index)) continue
    seen.add(part.index)
    const ref = map.get(part.index)
    if (ref) recovered.push(ref)
  }
  return recovered
}

export function ChatMessage({ message, activeCitationKey, onCitationClick }: Props) {
  const isUser = message.role === 'user'
  const insufficient = !isUser && isInsufficientAnswer(message.content)

  const sourceList = insufficient ? [] : resolveSourceList(message)

  const retrievedCount = message.retrieved_evidence?.length ?? 0

  return (
    <div className={`chat-msg chat-msg--${isUser ? 'user' : 'assistant'}`}>
      <div className="chat-msg__avatar" aria-label={isUser ? 'You' : 'AI'}>
        {isUser ? (
          'U'
        ) : (
          <svg width="14" height="14" viewBox="0 0 28 28" fill="none" aria-hidden="true">
            <rect width="28" height="28" rx="4" fill="var(--accent)" opacity="0.8" />
            <path d="M7 7h8a6 6 0 0 1 0 12H7V7Z" fill="white" opacity="0.9" />
          </svg>
        )}
      </div>

      <div className="chat-msg__body">
        <div className="chat-msg__bubble">
          {isUser ? (
            <p className="chat-msg__plain">{message.content}</p>
          ) : (
            <AssistantMessageBody
              content={message.content}
              citations={message.citations}
              retrievedEvidence={message.retrieved_evidence}
              activeCitationKey={activeCitationKey}
              onCitationClick={onCitationClick}
            />
          )}
        </div>

        {!isUser && insufficient && retrievedCount > 0 && (
          <div className="chat-msg__citations chat-msg__citations--retrieved">
            <p className="chat-msg__citations-label">Retrieved sources</p>
            <p className="chat-msg__retrieved-summary">
              {retrievedCount} source{retrievedCount === 1 ? '' : 's'} were checked
            </p>
          </div>
        )}

        {!isUser && !insufficient && sourceList.length > 0 && (
          <div className="chat-msg__citations">
            <p className="chat-msg__citations-label">Sources</p>
            <ul className="chat-msg__citations-list">
              {sourceList.map((c, i) => {
                const num = c.citation_index ?? i + 1
                const selKey = citationSelectionKey(c)
                const isActive = activeCitationKey === selKey
                const meta = formatCitationMeta(c)
                return (
                  <li key={selKey}>
                    <button
                      type="button"
                      className={`chat-msg__citation-row${isActive ? ' chat-msg__citation-row--active' : ''}`}
                      onClick={() => onCitationClick?.(c)}
                    >
                      <span className="chat-msg__citation-num">[{num}]</span>
                      <span className="chat-msg__citation-body">
                        <span className="chat-msg__citation-title">{c.source_title}</span>
                        {meta ? (
                          <span className="chat-msg__citation-meta"> · {meta}</span>
                        ) : null}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
