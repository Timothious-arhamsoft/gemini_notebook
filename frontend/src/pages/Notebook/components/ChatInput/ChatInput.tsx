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
      textareaRef.current.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    setText(value)

    const el = textareaRef.current

    if (el) {
      el.style.height = 'auto'
      el.style.height = `${Math.min(el.scrollHeight, 180)}px`
    }
  }

  const hasText = text.trim().length > 0
  const isDisabled = disabled || loading

  return (
    <div className="chat-input">
      <div
        className={`chat-input__wrapper ${
          hasText ? 'chat-input__wrapper--active' : ''
        }`}
      >
        <textarea
          ref={textareaRef}
          className="chat-input__textarea"
          placeholder="Ask anything about your sources..."
          value={text}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          disabled={isDisabled}
          rows={1}
          aria-label="Ask a question about your sources"
        />

        <div className="chat-input__bottom">
          <span className="chat-input__shortcut">
            <kbd>Enter</kbd>
            <span>to send</span>
            <kbd>Shift</kbd>
            <span>+</span>
            <kbd>Enter</kbd>
            <span>for new line</span>
          </span>

          <button
            type="button"
            className={`chat-input__send ${
              hasText ? 'chat-input__send--active' : ''
            }`}
            onClick={handleSend}
            disabled={!hasText || isDisabled}
            aria-label={loading ? 'Sending message' : 'Send message'}
          >
            {loading ? (
              <span className="chat-input__spinner" aria-hidden="true" />
            ) : (
              <svg
                width="17"
                height="17"
                viewBox="0 0 16 16"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M14.5 1.5 7.25 8.75"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <path
                  d="m14.5 1.5-4.75 12-2.5-4.75L2.5 6.25l12-4.75Z"
                  stroke="currentColor"
                  strokeWidth="1.6"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        </div>
      </div>

      <p className="chat-input__hint">
        Answers are generated from your uploaded sources.
      </p>
    </div>
  )
}
