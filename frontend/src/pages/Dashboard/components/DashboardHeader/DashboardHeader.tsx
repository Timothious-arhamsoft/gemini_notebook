import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../../../contexts/AuthContext'
import { Button } from '../../../../components/Button'

interface DashboardHeaderProps {
  onNewNotebook: () => void
}

export function DashboardHeader({
  onNewNotebook,
}: DashboardHeaderProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const initials = user?.full_name
    ? user.full_name
        .split(' ')
        .filter(Boolean)
        .map((name) => name[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    : user?.username
      ? user.username.slice(0, 2).toUpperCase()
      : 'U'

  const displayName =
    user?.full_name ||
    user?.username ||
    user?.email ||
    'User'

  return (
    <header className="dash-header">
      <div className="dash-header__left">
        <div className="dash-header__logo">
          <svg
            width="22"
            height="22"
            viewBox="0 0 28 28"
            fill="none"
            aria-hidden="true"
          >
            <rect
              width="28"
              height="28"
              rx="8"
              fill="var(--accent)"
            />

            <path
              d="M8 8h8a6 6 0 0 1 0 12H8V8Z"
              fill="white"
              opacity="0.9"
            />

            <circle
              cx="19"
              cy="20"
              r="2.5"
              fill="white"
              opacity="0.6"
            />
          </svg>

          <span className="dash-header__logo-text">
            Gemini Notebook
          </span>
        </div>
      </div>

      <div className="dash-header__right">
        <Button
          variant="primary"
          size="sm"
          onClick={onNewNotebook}
          icon={
            <svg
              viewBox="0 0 16 16"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M8 1.5a.5.5 0 0 1 .5.5v5.5H14a.5.5 0 0 1 0 1H8.5V14a.5.5 0 0 1-1 0V8.5H2a.5.5 0 0 1 0-1h5.5V2a.5.5 0 0 1 .5-.5Z" />
            </svg>
          }
        >
          New notebook
        </Button>

        <div className="dash-header__user">
          <div className="dash-header__user-info">
            <span className="dash-header__user-name">
              {displayName}
            </span>

            {user?.email && (
              <span className="dash-header__user-email">
                {user.email}
              </span>
            )}
          </div>

          <button
            type="button"
            className="dash-header__avatar"
            title={`Sign out ${displayName}`}
            onClick={handleLogout}
            aria-label={`Sign out ${displayName}`}
          >
            {initials}
          </button>
        </div>
      </div>
    </header>
  )
}