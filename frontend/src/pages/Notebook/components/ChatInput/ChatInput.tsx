import { useRef, useState } from 'react'

interface Props {
  onSend: (text: string) => void
  disabled?: boolean
  loading?: boolean
}

export function ChatInput({ onSend, disabled, loading }: Props) {
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    const trimmed = text.trim()
    if (!trimmed || disabled || loading) return
    onSend(trimmed)
    setText('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
    const el = textareaRef.current
    if (el) { el.style.height = 'auto'; el.style.height = Math.min(el.scrollHeight, 160) + 'px' }
  }

  return (
    <div className="chat-input">
      <div className="chat-input__wrapper">
        <textarea
          ref={textareaRef}
          className="chat-input__textarea"
          placeholder="Ask a question about your sources… (Enter to send, Shift+Enter for new line)"
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={disabled || loading}
          rows={1}
          aria-label="Chat input"
        />
        <button
          className={`chat-input__send ${text.trim() ? 'chat-input__send--active' : ''}`}
          onClick={handleSend}
          disabled={!text.trim() || disabled || loading}
          aria-label="Send message"
        >
          {loading ? (
            <span className="chat-input__spinner" />
          ) : (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M15.854 8.354a.5.5 0 0 0 0-.708l-3.5-3.5a.5.5 0 0 0-.708.708L14.293 7.5H.5a.5.5 0 0 0 0 1h13.793l-2.647 2.646a.5.5 0 0 0 .708.708l3.5-3.5Z"/>
            </svg>
          )}
        </button>
      </div>
      <p className="chat-input__hint">
        AI answers are grounded in your uploaded sources.
      </p>
    </div>
  )
}
