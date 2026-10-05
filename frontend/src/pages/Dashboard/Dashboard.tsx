import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { notebooksApi } from '../../api/notebooks'
import { DashboardHeader } from './components/DashboardHeader/DashboardHeader'
import { NotebookCard } from './components/NotebookCard/NotebookCard'
import { Spinner } from '../../components/Spinner'
import { Button } from '../../components/Button'
import type { Notebook } from '../../types'
import './Dashboard.css'

export function Dashboard() {
  const navigate = useNavigate()
  const [notebooks, setNotebooks] = useState<Notebook[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)

  const load = async () => {
    try {
      const data = await notebooksApi.list()
      setNotebooks(data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  /** Create an Untitled notebook and navigate straight into it */
  const handleNewNotebook = async () => {
    if (creating) return
    setCreating(true)
    try {
      const nb = await notebooksApi.create({ title: 'Untitled', description: '0 sources' })
      navigate(`/notebook/${nb.id}`)
    } catch (err) {
      console.error('Failed to create notebook:', err)
      setCreating(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this notebook and all its sources?')) return
    await notebooksApi.delete(id)
    setNotebooks(prev => prev.filter(n => n.id !== id))
  }

  return (
    <div className="dashboard">
      <DashboardHeader onNewNotebook={handleNewNotebook} />

      <main className="dashboard__main">
        <div className="dashboard__section-header">
          <h2 className="dashboard__section-title">My notebooks</h2>
          <span className="dashboard__count">{notebooks.length}</span>
        </div>

        {loading ? (
          <div className="dashboard__loading"><Spinner size="lg" /></div>
        ) : notebooks.length === 0 ? (
          <div className="dashboard__empty">
            <div className="dashboard__empty-icon" aria-hidden="true">
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <rect x="8" y="6" width="32" height="36" rx="4" stroke="var(--border)" strokeWidth="2" fill="none"/>
                <path d="M16 16h16M16 22h16M16 28h10" stroke="var(--border)" strokeWidth="2" strokeLinecap="round"/>
                <circle cx="36" cy="36" r="8" fill="var(--accent)" opacity="0.15"/>
                <path d="M33 36h6M36 33v6" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <p className="dashboard__empty-title">No notebooks yet</p>
            <p className="dashboard__empty-sub">Create your first notebook to start chatting with your documents</p>
            <Button
              variant="primary"
              onClick={handleNewNotebook}
              loading={creating}
              icon={<svg viewBox="0 0 16 16" fill="currentColor"><path d="M8 1.5a.5.5 0 0 1 .5.5v5.5H14a.5.5 0 0 1 0 1H8.5V14a.5.5 0 0 1-1 0V8.5H2a.5.5 0 0 1 0-1h5.5V2a.5.5 0 0 1 .5-.5Z"/></svg>}
            >
              New notebook
            </Button>
          </div>
        ) : (
          <div className="dashboard__grid">
            {notebooks.map(nb => (
              <NotebookCard key={nb.id} notebook={nb} onDelete={handleDelete} />
            ))}
            <button
              className="notebook-card notebook-card--new"
              onClick={handleNewNotebook}
              disabled={creating}
            >
              <div className="notebook-card__new-icon">
                {creating ? (
                  <Spinner size="sm" />
                ) : (
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                    <path d="M10 3.5a.5.5 0 0 1 .5.5v5.5H16a.5.5 0 0 1 0 1h-5.5V16a.5.5 0 0 1-1 0v-5.5H4a.5.5 0 0 1 0-1h5.5V4a.5.5 0 0 1 .5-.5Z"/>
                  </svg>
                )}
              </div>
              <span>{creating ? 'Creating…' : 'New notebook'}</span>
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
