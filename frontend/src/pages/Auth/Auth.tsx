import { useState } from 'react'
import { LoginForm } from './components/LoginForm'
import { RegisterForm } from './components/RegisterForm'
import './Auth.css'

export function Auth() {
  const [mode, setMode] = useState<'login' | 'register'>('login')

  return (
    <div className="auth-page">
      <div className="auth-page__bg" aria-hidden="true">
        <div className="auth-page__glow" />
      </div>

      <div className="auth-page__card">
        {/* Logo */}
        <div className="auth-page__logo">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="28" height="28" rx="8" fill="var(--accent)" />
            <path d="M8 8h8a6 6 0 0 1 0 12H8V8Z" fill="white" opacity="0.9"/>
            <circle cx="19" cy="20" r="2.5" fill="white" opacity="0.6"/>
          </svg>
          <span className="auth-page__logo-text">NoteGenio</span>
        </div>

        <div className="auth-page__form-wrapper">
          {mode === 'login'
            ? <LoginForm onSwitch={() => setMode('register')} />
            : <RegisterForm onSwitch={() => setMode('login')} />
          }
        </div>
      </div>
    </div>
  )
}
