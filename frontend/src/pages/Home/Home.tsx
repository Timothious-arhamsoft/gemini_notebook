import { useEffect, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { useDayNightTheme } from '../../hooks/useDayNightTheme'
import './Home.css'

/* ── Slide illustrations (pure CSS mockups) ───────────────── */
function UploadArt() {
  return (
    <div className="home__art-card">
      {[
        { tag: 'PDF', short: false },
        { tag: 'DOCX', short: true },
        { tag: 'MD', short: false },
      ].map((f, i) => (
        <div key={f.tag} className={`home__art-row${i === 2 ? ' home__art-row--dim' : ''}`}>
          <span className="home__art-badge">{f.tag}</span>
          <div className="home__art-lines">
            <span className="home__bar" />
            <span className={`home__bar ${f.short ? 'home__bar--accent' : 'home__bar--short'}`} />
          </div>
        </div>
      ))}
    </div>
  )
}

function AskArt() {
  return (
    <div className="home__art-card">
      <span className="home__art-bubble">What did the report conclude?</span>
      <div className="home__art-lines">
        <span className="home__bar" />
        <span className="home__bar" />
        <span className="home__bar home__bar--short" />
      </div>
      <div className="home__art-chips">
        <span className="home__art-chip">report.pdf · p. 12</span>
        <span className="home__art-chip">notes.md</span>
      </div>
    </div>
  )
}

function PrivateArt() {
  return (
    <div className="home__art-card">
      <div className="home__art-row">
        <span className="home__art-badge" aria-hidden="true">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="4" y="11" width="16" height="10" rx="2" />
            <path d="M8 11V7a4 4 0 0 1 8 0v4" />
          </svg>
        </span>

        <div className="home__art-lines">
          <span className="home__bar" />
          <span className="home__bar home__bar--short" />
        </div>
      </div>

      {['Notebooks', 'Documents', 'Answers'].map(label => (
        <div key={label} className="home__art-row home__art-row--between">
          <span className="home__art-label">{label}</span>
          <span className="home__art-chip">Only you</span>
        </div>
      ))}
    </div>
  )
}

const FEATURES = [
  {
    Art: UploadArt,
    title: 'Upload any document',
    desc: 'PDF, DOCX, TXT, Markdown — drag & drop in seconds.',
  },
  {
    Art: AskArt,
    title: 'Ask anything',
    desc: 'Get precise, cited answers from your uploaded sources only.',
  },
  {
    Art: PrivateArt,
    title: 'Private by default',
    desc: 'Your notebooks and documents are only visible to you.',
  },
]

const AUTOPLAY_DELAY = 2000

export function Home() {
  const { isAuthenticated } = useAuth()
  const { isDay, toggleTheme } = useDayNightTheme()
  const [active, setActive] = useState(0)
  const [paused, setPaused] = useState(false)
  const touchX = useRef<number | null>(null)

  const go = (i: number) => {
    setActive((i + FEATURES.length) % FEATURES.length)
  }

  // Automatic carousel movement
  useEffect(() => {
    if (paused) return

    const timer = window.setInterval(() => {
      setActive(current => (current + 1) % FEATURES.length)
    }, AUTOPLAY_DELAY)

    return () => window.clearInterval(timer)
  }, [paused])

  const onTouchEnd = (e: React.TouchEvent) => {
    if (touchX.current === null) return

    const dx = e.changedTouches[0].clientX - touchX.current
    touchX.current = null

    if (Math.abs(dx) > 50) {
      go(active + (dx < 0 ? 1 : -1))
    }
  }
  const handleHome = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  return (
    <main className={`home ${isDay ? 'home--day' : 'home--night'}`}>
      <nav className="home__nav">
        <div className="home__nav-logo">
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

        <div className="home__nav-links">
          {/* Day / Night Theme Toggle */}
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

          {isAuthenticated ? (
            <Link
              to="/dashboard"
              className="home__nav-btn home__nav-btn--primary"
            >
              Go to Dashboard
            </Link>
          ) : (
            <>
              <Link to="/auth" className="home__nav-btn">
                Sign in
              </Link>

              <Link
                to="/auth"
                className="home__nav-btn home__nav-btn--primary"
              >
                Get started
              </Link>
            </>
          )}
        </div>
      </nav>


      <section className="home__hero">
        <span className="home__eyebrow">
          AI-powered document workspace
        </span>

        <h1>
          Your documents.
          <br />
          One intelligent notebook.
        </h1>

        <p>
          Upload your sources, ask questions, and get answers
          grounded exclusively in your own documents — with citations.
        </p>

        <div className="home__actions">
          <Link
            to={isAuthenticated ? '/dashboard' : '/auth'}
            className="home__primary"
          >
            {isAuthenticated ? 'Open Dashboard' : "Get Started — it's free"}
          </Link>

          {!isAuthenticated && (
            <Link to="/auth" className="home__secondary">
              Sign in
            </Link>
          )}
        </div>
      </section>

      <section
        className="home__features"
        aria-roledescription="carousel"
        aria-label="Features"
        data-paused={paused}
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
        onFocus={() => setPaused(true)}
        onBlur={() => setPaused(false)}
      >
        <div
          className="home__carousel"
          style={{ '--i': active } as CSSProperties}
          onTouchStart={e => {
            touchX.current = e.touches[0].clientX
          }}
          onTouchEnd={onTouchEnd}
        >
          <div className="home__track">
            {FEATURES.map(({ Art, title, desc }, i) => (
              <div
                key={title}
                className={`home__slide${
                  i === active ? ' home__slide--active' : ''
                }`}
                role="group"
                aria-roledescription="slide"
                aria-label={`${i + 1} of ${FEATURES.length}`}
                onClick={() => go(i)}
              >
                <div className="home__slide-art">
                  <Art />
                </div>

                <div className="home__slide-caption">
                  <h3 className="home__slide-title">{title}</h3>
                  <p className="home__slide-desc">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="home__dots">
          {FEATURES.map((f, i) => (
            <button
              key={f.title}
              type="button"
              className={`home__dot${
                i === active ? ' home__dot--active' : ''
              }`}
              aria-label={`Show: ${f.title}`}
              aria-current={i === active}
              onClick={() => go(i)}
            >
              {i === active && <span className="home__dot-fill" />}
            </button>
          ))}
        </div>
      </section>
    </main>
  )
}
