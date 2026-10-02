import { Link } from 'react-router-dom'
import './Home.css'

export function Home() {
  return (
    <main className="home">
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
          Upload your sources, ask questions, and explore
          answers grounded in your own documents.
        </p>

        <div className="home__actions">
          <Link to="/register" className="home__primary">
            Get Started
          </Link>

          <Link to="/login" className="home__secondary">
            Sign In
          </Link>
        </div>
      </section>
    </main>
  )
}