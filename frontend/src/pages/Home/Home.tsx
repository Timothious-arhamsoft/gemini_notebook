import { Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import './Home.css'

export function Home() {
  const { isAuthenticated } = useAuth()

  return (
    <main className="home">
      <nav className="home__nav">
        <div className="home__nav-logo">
          <svg width="22" height="22" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="var(--accent)" />
            <path d="M8 8h8a6 6 0 0 1 0 12H8V8Z" fill="white" opacity="0.9"/>
            <circle cx="19" cy="20" r="2.5" fill="white" opacity="0.6"/>
          </svg>
          <span>Gemini Notebook</span>
        </div>
        <div className="home__nav-links">
          {isAuthenticated ? (
            <Link to="/dashboard" className="home__nav-btn home__nav-btn--primary">
              Go to Dashboard
            </Link>
          ) : (
            <>
              <Link to="/auth" className="home__nav-btn">Sign in</Link>
              <Link to="/auth" className="home__nav-btn home__nav-btn--primary">Get started</Link>
            </>
          )}
        </div>
      </nav>

      <section className="home__hero">
        <span className="home__eyebrow">AI-powered document workspace</span>

        <h1>
          Your documents.<br />
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
            {isAuthenticated ? 'Open Dashboard' : 'Get Started — it\'s free'}
          </Link>
          {!isAuthenticated && (
            <Link to="/auth" className="home__secondary">Sign in</Link>
          )}
        </div>
      </section>

      <section className="home__features">
        {[
          { icon: '📄', title: 'Upload any document', desc: 'PDF, DOCX, TXT, Markdown — drag & drop in seconds.' },
          { icon: '💬', title: 'Ask anything', desc: 'Get precise, cited answers from your uploaded sources only.' },
          { icon: '🔒', title: 'Private by default', desc: 'Your notebooks and documents are only visible to you.' },
        ].map(f => (
          <div key={f.title} className="home__feature-card">
            <span className="home__feature-icon">{f.icon}</span>
            <h3 className="home__feature-title">{f.title}</h3>
            <p className="home__feature-desc">{f.desc}</p>
          </div>
        ))}
      </section>
    </main>
  )
}