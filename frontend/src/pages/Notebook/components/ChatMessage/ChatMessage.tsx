import type { ChatMessage as ChatMessageType, Citation } from '../../../../types'

interface Props {
  message: ChatMessageType
  onCitationClick?: (citation: Citation) => void
}

export function ChatMessage({ message, onCitationClick }: Props) {
  const isUser = message.role === 'user'

  return (
    <div className={`chat-msg chat-msg--${isUser ? 'user' : 'ai'}`}>
      <div className="chat-msg__avatar" aria-label={isUser ? 'You' : 'AI'}>
        {isUser ? 'U' : (
          <svg width="14" height="14" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="4" fill="var(--accent)" opacity="0.8"/>
            <path d="M7 7h8a6 6 0 0 1 0 12H7V7Z" fill="white" opacity="0.9"/>
          </svg>
        )}
      </div>

      <div className="chat-msg__body">
        <p className="chat-msg__content">{message.content}</p>

        {message.citations && message.citations.length > 0 && (
          <div className="chat-msg__citations">
            <p className="chat-msg__citations-label">Sources &amp; Citations</p>
            <div className="chat-msg__citations-list">
              {message.citations.map((c, i) => (
                <div
                  key={i}
                  className="chat-msg__citation"
                  onClick={() => onCitationClick?.(c)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={e => e.key === 'Enter' && onCitationClick?.(c)}
                  title="Click to view highlighted chunk citation in sidebar"
                >
                  <span className="chat-msg__citation-num">{i + 1}</span>
                  <div>
                    <p className="chat-msg__citation-title">{c.source_title}</p>
                    {c.excerpt && <p className="chat-msg__citation-excerpt">"{c.excerpt}"</p>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
