import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../../../contexts/AuthContext'

interface Props {
  title: string
  description?: string
  onTitleChange: (t: string) => void
  onTitleBlur?: (t: string) => void
}

export function WorkspaceHeader({ title, description, onTitleChange, onTitleBlur }: Props) {
  const navigate = useNavigate()
  const { logout } = useAuth()

  return (
    <header className="ws-header">
      <div className="ws-header__left">
        <button className="ws-header__back" onClick={() => navigate('/dashboard')} title="Back to dashboard">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M3.86 8.733a1 1 0 0 1 0-1.466L9.296 1.83A.5.5 0 0 1 10 2.2v11.6a.5.5 0 0 1-.704.37L3.86 8.733Z"/>
          </svg>
        </button>
        <div className="ws-header__logo">
          <svg width="18" height="18" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="var(--accent)" />
            <path d="M8 8h8a6 6 0 0 1 0 12H8V8Z" fill="white" opacity="0.9"/>
          </svg>
        </div>
        <div className="ws-header__title-group">
          <input
            className="ws-header__title"
            value={title}
            onChange={e => onTitleChange(e.target.value)}
            onBlur={e => onTitleBlur?.(e.target.value)}
            placeholder="Untitled"
            aria-label="Notebook title"
          />
          {description !== undefined && (
            <span className="ws-header__description" aria-label="Source count">
              {description}
            </span>
          )}
        </div>
      </div>
      <div className="ws-header__right">
        <button className="ws-header__logout" onClick={() => { logout(); navigate('/auth') }}>
          Sign out
        </button>
      </div>
    </header>
  )
}
