import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../../../contexts/AuthContext'
import { Button } from '../../../../components/Button'

export function DashboardHeader({ onNewNotebook }: { onNewNotebook: () => void }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  const handleLogout = () => {
    setMenuOpen(false)
    logout()
    navigate('/auth')
  }

  const initials = user?.full_name
    ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.username?.slice(0, 2).toUpperCase() ?? 'U'

  return (
    <header className="dash-header">
      <div className="dash-header__left">
        <div className="dash-header__logo">
          <svg width="22" height="22" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="var(--accent)" />
            <path d="M8 8h8a6 6 0 0 1 0 12H8V8Z" fill="white" opacity="0.9"/>
            <circle cx="19" cy="20" r="2.5" fill="white" opacity="0.6"/>
          </svg>
          <span className="dash-header__logo-text">NoteGenio</span>
        </div>
      </div>

      <div className="dash-header__right">
        <Button
          variant="primary"
          size="sm"
          onClick={onNewNotebook}
          icon={
            <svg viewBox="0 0 16 16" fill="currentColor">
              <path d="M8 1.5a.5.5 0 0 1 .5.5v5.5H14a.5.5 0 0 1 0 1H8.5V14a.5.5 0 0 1-1 0V8.5H2a.5.5 0 0 1 0-1h5.5V2a.5.5 0 0 1 .5-.5Z"/>
            </svg>
          }
        >
          New notebook
        </Button>

        {/* User menu */}
        <div className="dash-header__user" ref={menuRef}>
          <button
            className="dash-header__avatar"
            onClick={() => setMenuOpen(o => !o)}
            aria-label="User menu"
            aria-expanded={menuOpen}
          >
            {initials}
          </button>

          {menuOpen && (
            <>
              {/* Backdrop */}
              <div className="dash-header__backdrop" onClick={() => setMenuOpen(false)} />
              <div className="dash-header__menu">
                <div className="dash-header__menu-user">
                  <span className="dash-header__menu-name">
                    {user?.full_name || user?.username}
                  </span>
                  <span className="dash-header__menu-email">{user?.email}</span>
                </div>
                <div className="dash-header__menu-divider" />
                <button className="dash-header__menu-item dash-header__menu-item--danger" onClick={handleLogout}>
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M6 12.5a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5v-9a.5.5 0 0 0-.5-.5h-8a.5.5 0 0 0-.5.5v2a.5.5 0 0 1-1 0v-2A1.5 1.5 0 0 1 6.5 2h8A1.5 1.5 0 0 1 16 3.5v9a1.5 1.5 0 0 1-1.5 1.5h-8A1.5 1.5 0 0 1 5 12.5v-2a.5.5 0 0 1 1 0v2Z"/>
                    <path d="M.146 8.354a.5.5 0 0 1 0-.708l3-3a.5.5 0 1 1 .708.708L1.707 7.5H10.5a.5.5 0 0 1 0 1H1.707l2.147 2.146a.5.5 0 0 1-.708.708l-3-3Z"/>
                  </svg>
                  Sign out
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
