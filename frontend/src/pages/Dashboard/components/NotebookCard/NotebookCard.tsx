import { useNavigate } from 'react-router-dom'
import type { Notebook } from '../../../../types'

function formatDate(iso: string) {
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

export function NotebookCard({ notebook, onDelete }: { notebook: Notebook; onDelete: (id: string) => void }) {
  const navigate = useNavigate()

  return (
    <div className="notebook-card" onClick={() => navigate(`/notebook/${notebook.id}`)} role="button" tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && navigate(`/notebook/${notebook.id}`)}>

      <div className="notebook-card__icon" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
          <rect x="3" y="2" width="14" height="16" rx="2" stroke="currentColor" strokeWidth="1.5" fill="none"/>
          <path d="M7 7h6M7 10h6M7 13h4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
        </svg>
      </div>

      <div className="notebook-card__body">
        <h3 className="notebook-card__title">{notebook.title}</h3>
        {notebook.description && (
          <p className="notebook-card__desc">{notebook.description}</p>
        )}
        <p className="notebook-card__meta">
          Updated {formatDate(notebook.updated_at)}
        </p>
      </div>

      <button className="notebook-card__delete" title="Delete notebook"
        onClick={e => { e.stopPropagation(); onDelete(notebook.id) }}>
        <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
          <path d="M5.5 1.5A1.5 1.5 0 0 1 7 0h2a1.5 1.5 0 0 1 1.5 1.5H13a.5.5 0 0 1 0 1H3a.5.5 0 0 1 0-1h2.5ZM4.5 4a.5.5 0 0 1 .5.5v8a.5.5 0 0 1-1 0v-8a.5.5 0 0 1 .5-.5Zm3.5 0a.5.5 0 0 1 .5.5v8a.5.5 0 0 1-1 0v-8A.5.5 0 0 1 8 4Zm3 .5a.5.5 0 0 0-1 0v8a.5.5 0 0 0 1 0v-8Z"/>
        </svg>
      </button>
    </div>
  )
}
