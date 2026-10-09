
import { BrandLogo } from '../../../../components/BrandLogo'
import type { ChatMessage as ChatMessageType, Citation, GroqUsage } from '../../../../types'
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

function formatTokens(value: number | null | undefined): string {
  return value == null ? '—' : value.toLocaleString()
}

function formatCost(value: number | null | undefined): string {
  return value == null ? 'Unavailable' : `$${value.toFixed(6)}`
}

function formatLatency(value: number | null | undefined): string {
  if (value == null) return '—'
  return value >= 1000 ? `${(value / 1000).toFixed(1)}s` : `${Math.round(value)}ms`
}

function ResponseUsage({ usage }: { usage: GroqUsage }) {
  const inputTokens = usage.input_tokens ?? usage.prompt_tokens
  const outputTokens = usage.output_tokens ?? usage.completion_tokens
  const totalTokens = inputTokens != null && outputTokens != null
    ? inputTokens + outputTokens
    : usage.total_tokens

  return (
    <div className="chat-msg__usage" aria-label="AI response token usage">
      <span className="chat-msg__usage-model">{usage.model || 'AI model'}</span>
      <span>Input: {formatTokens(inputTokens)}</span>
      <span>Output: {formatTokens(outputTokens)}</span>
      <span>Total: {formatTokens(totalTokens)}</span>
      <span>Est. cost: {formatCost(usage.total_cost ?? usage.estimated_cost_usd)}</span>
      <span>Latency: {formatLatency(usage.latency_ms)}</span>
    </div>
  )
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
          <BrandLogo size={32} showText={false} />
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

        {!isUser && message.usage && <ResponseUsage usage={message.usage} />}

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
