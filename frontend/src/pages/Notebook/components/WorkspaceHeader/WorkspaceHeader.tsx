import { useNavigate } from 'react-router-dom'
import { BrandLogo } from '../../../../components/BrandLogo'
import { useAuth } from '../../../../contexts/AuthContext'
import { useDayNightTheme } from '../../../../hooks/useDayNightTheme'

interface Props {
  title: string
  description?: string
  onTitleChange: (t: string) => void
  onTitleBlur?: (t: string) => void
}

export function WorkspaceHeader({ title, description, onTitleChange, onTitleBlur }: Props) {
  const navigate = useNavigate()
  const { logout } = useAuth()
  const { isDay, toggleTheme } = useDayNightTheme()

  return (
    <header className="ws-header">
      <div className="ws-header__left">
        <button className="ws-header__back" onClick={() => navigate('/dashboard')} title="Back to dashboard">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M3.86 8.733a1 1 0 0 1 0-1.466L9.296 1.83A.5.5 0 0 1 10 2.2v11.6a.5.5 0 0 1-.704.37L3.86 8.733Z"/>
          </svg>
        </button>
        <div className="ws-header__logo">
          <BrandLogo size={20} showText={false} />
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
        <button
          type="button"
          className="home__theme-toggle"
          onClick={toggleTheme}
          title={isDay ? "Switch to Night Mode" : "Switch to Day Mode"}
          aria-label={isDay ? "Switch to Night Mode" : "Switch to Day Mode"}
          style={{ padding: '6px', background: 'transparent' }}
        >
          {isDay ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="5"/>
              <line x1="12" y1="1" x2="12" y2="3"/>
              <line x1="12" y1="21" x2="12" y2="23"/>
              <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
              <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
              <line x1="1" y1="12" x2="3" y2="12"/>
              <line x1="21" y1="12" x2="23" y2="12"/>
              <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
              <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          )}
        </button>
        <button className="ws-header__logout" onClick={() => { logout(); navigate('/auth') }}>
          Sign out
        </button>
      </div>
    </header>
  )
}
