import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../../../contexts/AuthContext'
import { Button } from '../../../../components/Button'
import { useDayNightTheme } from '../../../../hooks/useDayNightTheme'

interface DashboardHeaderProps {
  onNewNotebook: () => void
}

export function DashboardHeader({ onNewNotebook }: DashboardHeaderProps) {
  const { user, logout } = useAuth()
  const { isDay, toggleTheme } = useDayNightTheme()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  const userRef = useRef<HTMLDivElement>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const signOutRef = useRef<HTMLButtonElement>(null)

  // Close on outside click or Escape; move focus into the menu when it opens
  useEffect(() => {
    if (!menuOpen) return

    signOutRef.current?.focus()

    const onMouseDown = (e: MouseEvent) => {
      if (!userRef.current?.contains(e.target as Node)) setMenuOpen(false)
    }
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMenuOpen(false)
        triggerRef.current?.focus()
      }
    }

    document.addEventListener('mousedown', onMouseDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onMouseDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [menuOpen])

  const handleLogout = () => {
    setMenuOpen(false)
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

  const displayName = user?.full_name || user?.username || user?.email || 'User'
  const handleHome = () => {
    navigate('/')
  }
  return (
    <header className="dash-header">
      <div className="dash-header__left">
        <div className="dash-header__logo">
          <button
            type="button"
            className="dash-header__logo"
            onClick={handleHome}
            aria-label="Go to home page"
          >
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
              NoteGenio
            </span>
          </button>
        </div>
      </div>

      <div className="dash-header__right">
        <button
          type="button"
          className="home__theme-toggle"
          onClick={toggleTheme}
          title={isDay ? "Switch to Night Mode" : "Switch to Day Mode"}
          aria-label={isDay ? "Switch to Night Mode" : "Switch to Day Mode"}
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

        <Button
          variant="primary"
          size="sm"
          onClick={onNewNotebook}
          icon={
            <svg viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path d="M8 1.5a.5.5 0 0 1 .5.5v5.5H14a.5.5 0 0 1 0 1H8.5V14a.5.5 0 0 1-1 0V8.5H2a.5.5 0 0 1 0-1h5.5V2a.5.5 0 0 1 .5-.5Z" />
            </svg>
          }
        >
          New notebook
        </Button>

        <div className="dash-header__user" ref={userRef}>
          {/* Opens the menu — it does NOT sign out */}
          <button
            ref={triggerRef}
            type="button"
            className={`dash-header__trigger${menuOpen ? ' is-open' : ''}`}
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="Account menu"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
          >
            <span className="dash-header__user-name">{displayName}</span>
            <span className="dash-header__avatar" aria-hidden="true">{initials}</span>
            <svg
              className="dash-header__chevron"
              width="14"
              height="14"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="m4 6 4 4 4-4" />
            </svg>
          </button>

          {menuOpen && (
            <div className="dash-header__menu" role="menu" aria-label="Account">
              <div className="dash-header__menu-profile">
                <span className="dash-header__avatar dash-header__avatar--lg" aria-hidden="true">
                  {initials}
                </span>
                <div className="dash-header__menu-id">
                  <span className="dash-header__menu-name">{displayName}</span>
                  {user?.email && (
                    <span className="dash-header__menu-email">{user.email}</span>
                  )}
                </div>
              </div>

              <div className="dash-header__menu-divider" role="separator" />

              <button
                ref={signOutRef}
                type="button"
                role="menuitem"
                className="dash-header__menu-item dash-header__menu-item--danger"
                onClick={handleLogout}
              >
                <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                  <path d="M6 12.5a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-8a.5.5 0 0 0-.5.5v2a.5.5 0 0 1-1 0v-2A1.5 1.5 0 0 1 6.5 2h8A1.5 1.5 0 0 1 16 3.5v9a1.5 1.5 0 0 1-1.5 1.5h-8A1.5 1.5 0 0 1 5 12.5v-2a.5.5 0 0 1 1 0v2Z" />
                  <path d="M.146 8.354a.5.5 0 0 1 0-.708l3-3a.5.5 0 1 1 .708.708L1.707 7.5H10.5a.5.5 0 0 1 0 1H1.707l2.147 2.146a.5.5 0 0 1-.708.708l-3-3Z" />
                </svg>
                <span>Sign out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}