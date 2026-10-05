import { useState } from 'react'
import { Link } from 'react-router-dom'
import { LoginForm } from './components/LoginForm'
import { RegisterForm } from './components/RegisterForm'
import './Auth.css'

export function Auth() {
  const [mode, setMode] = useState<'login' | 'register'>('login')

  return (
    <div className="auth-page">
      {/* Back to Home Button */}
      <Link to="/" className="auth-page__back-link" title="Back to Home">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 12H5M12 19l-7-7 7-7" />
        </svg>
        <span>Back to Home</span>
      </Link>

      {/* Aesthetic Animated Background */}
      <div className="auth-page__bg" aria-hidden="true">
        <div className="auth-page__grid" />
        <div className="auth-page__orb auth-page__orb--1" />
        <div className="auth-page__orb auth-page__orb--2" />
        <div className="auth-page__orb auth-page__orb--3" />
        
        {/* Floating Genie Sparkles */}
        <div className="auth-page__sparkle sparkle--1">✨</div>
        <div className="auth-page__sparkle sparkle--2">✦</div>
        <div className="auth-page__sparkle sparkle--3">✨</div>
        <div className="auth-page__sparkle sparkle--4">✦</div>
      </div>

      <div className="auth-page__card">
        {/* Logo */}
        <div className="auth-page__logo">
          <div className="auth-page__logo-icon">
            <svg width="32" height="32" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="28" height="28" rx="8" fill="var(--accent)" />
              <path d="M8 8h8a6 6 0 0 1 0 12H8V8Z" fill="white" opacity="0.9"/>
              <circle cx="19" cy="20" r="2.5" fill="white" opacity="0.6"/>
            </svg>
          </div>
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


