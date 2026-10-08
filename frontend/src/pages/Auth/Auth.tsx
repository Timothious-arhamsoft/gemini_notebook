import { useState } from 'react'
import { Link } from 'react-router-dom'
import { BrandLogo } from '../../components/BrandLogo'
import { LoginForm } from './components/LoginForm'
import { RegisterForm } from './components/RegisterForm'
import { useDayNightTheme } from '../../hooks/useDayNightTheme'
import './Auth.css'

export function Auth() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const { isDay, toggleTheme } = useDayNightTheme()

  return (
    <div className={`auth-page ${isDay ? 'auth-page--day' : 'auth-page--night'}`}>
      {/* Back to Home Button */}
      <Link to="/" className="auth-page__back-link" title="Back to Home">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 12H5M12 19l-7-7 7-7" />
        </svg>
        <span>Back to Home</span>
      </Link>

      {/* Day / Night Theme Toggle */}
      <button 
        type="button" 
        className="auth-page__theme-toggle" 
        onClick={toggleTheme}
        title={isDay ? "Switch to Night Mode" : "Switch to Day Mode"}
        aria-label={isDay ? "Switch to Night Mode" : "Switch to Day Mode"}
      >

        {isDay ? (
          <>
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
            <span>Daytime</span>
          </>
        ) : (
          <>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
            <span>Nighttime</span>
          </>
        )}
      </button>

      {/* Aesthetic Animated Background (Day & Night) */}
      <div className="auth-page__bg" aria-hidden="true">
        {/* Sky Ambient Layer */}
        <div className="auth-page__sky-mesh" />
        
        {/* Celestial Body: Sun or Moon */}
        <div className="auth-page__celestial">
          <div className="auth-page__celestial-glow" />
          {!isDay && (
            <>
              <div className="auth-page__moon-crater crater--1" />
              <div className="auth-page__moon-crater crater--2" />
            </>
          )}
        </div>

        {/* Shooting Stars / Sun Rays */}
        {!isDay ? (
          <>
            <div className="auth-page__meteor meteor--1" />
            <div className="auth-page__meteor meteor--2" />
            <div className="auth-page__meteor meteor--3" />
            <div className="auth-page__meteor meteor--4" />

            <div className="auth-page__star star--1" />
            <div className="auth-page__star star--2" />
            <div className="auth-page__star star--3" />
            <div className="auth-page__star star--4" />
            <div className="auth-page__star star--5" />
            <div className="auth-page__star star--6" />
            <div className="auth-page__star star--7" />
            <div className="auth-page__star star--8" />
          </>
        ) : (
          <>
            <div className="auth-page__sun-ray ray--1" />
            <div className="auth-page__sun-ray ray--2" />
            <div className="auth-page__sparkle sparkle--1">✨</div>
            <div className="auth-page__sparkle sparkle--2">✦</div>
          </>
        )}

        {/* Dynamic Vector Clouds */}
        <div className="auth-page__cloud cloud--top-left">
          <svg viewBox="0 0 500 220" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M40 170 C70 100, 160 80, 200 120 C240 60, 350 50, 390 110 C440 80, 510 120, 490 180 C470 210, 50 210, 40 170 Z" fill="url(#cloud-grad-1)"/>
            <defs>
              <linearGradient id="cloud-grad-1" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor={isDay ? "#ffffff" : "#2a45b8"} stopOpacity={isDay ? "0.85" : "0.6"} />
                <stop offset="100%" stopColor={isDay ? "#dbeafe" : "#111a52"} stopOpacity={isDay ? "0.6" : "0.4"} />
              </linearGradient>
            </defs>
          </svg>
        </div>

        <div className="auth-page__cloud cloud--top-right">
          <svg viewBox="0 0 550 240" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M30 190 C70 110, 180 90, 220 130 C280 60, 400 65, 440 130 C490 100, 550 150, 520 200 C480 230, 40 230, 30 190 Z" fill="url(#cloud-grad-2)"/>
            <defs>
              <linearGradient id="cloud-grad-2" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor={isDay ? "#ffffff" : "#3b5fe0"} stopOpacity={isDay ? "0.9" : "0.65"} />
                <stop offset="100%" stopColor={isDay ? "#bfdbfe" : "#16236b"} stopOpacity={isDay ? "0.7" : "0.45"} />
              </linearGradient>
            </defs>
          </svg>
        </div>

        <div className="auth-page__cloud cloud--mid-left">
          <svg viewBox="0 0 450 180" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M20 140 C50 80, 130 70, 170 100 C210 50, 300 50, 340 90 C390 70, 440 110, 420 150 C400 175, 30 175, 20 140 Z" fill="url(#cloud-grad-3)"/>
            <defs>
              <linearGradient id="cloud-grad-3" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor={isDay ? "#f8fafc" : "#253ea3"} stopOpacity={isDay ? "0.75" : "0.5"} />
                <stop offset="100%" stopColor={isDay ? "#93c5fd" : "#0e1644"} stopOpacity={isDay ? "0.5" : "0.3"} />
              </linearGradient>
            </defs>
          </svg>
        </div>

        <div className="auth-page__cloud cloud--bottom-right">
          <svg viewBox="0 0 580 260" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M30 210 C80 120, 200 95, 250 150 C320 65, 450 75, 500 150 C550 120, 600 180, 560 230 C510 260, 40 260, 30 210 Z" fill="url(#cloud-grad-4)"/>
            <defs>
              <linearGradient id="cloud-grad-4" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" stopColor={isDay ? "#ffffff" : "#3254d4"} stopOpacity={isDay ? "0.85" : "0.6"} />
                <stop offset="100%" stopColor={isDay ? "#60a5fa" : "#121c5b"} stopOpacity={isDay ? "0.65" : "0.4"} />
              </linearGradient>
            </defs>
          </svg>
        </div>

        <div className="auth-page__cloud cloud--bottom-left">
          <svg viewBox="0 0 500 220" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M30 170 C70 100, 160 85, 200 130 C250 65, 360 65, 400 120 C450 95, 500 140, 470 190 C440 220, 40 220, 30 170 Z" fill="url(#cloud-grad-5)"/>
            <defs>
              <linearGradient id="cloud-grad-5" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor={isDay ? "#f1f5f9" : "#1e348a"} stopOpacity={isDay ? "0.7" : "0.45"} />
                <stop offset="100%" stopColor={isDay ? "#93c5fd" : "#0b1136"} stopOpacity={isDay ? "0.45" : "0.25"} />
              </linearGradient>
            </defs>
          </svg>
        </div>
      </div>

      <div className="auth-page__card">
        {/* Logo */}
        <div className="auth-page__logo">
          <div className="auth-page__logo-icon">
            <BrandLogo size={32} showText={false} />
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



