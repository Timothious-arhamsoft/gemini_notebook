import { useState } from 'react'
import { Button } from '../../../../components/Button'
import type { CreateNotebookPayload } from '../../../../types'

interface Props {
  onConfirm: (payload: CreateNotebookPayload) => Promise<void>
  onClose: () => void
}

export function CreateNotebookModal({ onConfirm, onClose }: Props) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    setLoading(true)
    try {
      await onConfirm({ title: title.trim(), description: description.trim() || undefined })
      onClose()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true">
      <div className="modal-card" onClick={e => e.stopPropagation()}>
        <div className="modal-card__header">
          <h2 className="modal-card__title">New notebook</h2>
          <button className="modal-card__close" onClick={onClose} aria-label="Close">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor">
              <path d="M1 1l12 12M13 1 1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-card__body">
            <label className="modal-card__label">
              Title <span className="modal-card__required">*</span>
              <input className="modal-card__input" type="text" placeholder="My Research Notebook"
                value={title} onChange={e => setTitle(e.target.value)} autoFocus required maxLength={200} />
            </label>
            <label className="modal-card__label">
              Description <span className="modal-card__optional">(optional)</span>
              <input className="modal-card__input" type="text" placeholder="What is this notebook about?"
                value={description} onChange={e => setDescription(e.target.value)} maxLength={500} />
            </label>
          </div>
          <div className="modal-card__footer">
            <Button variant="secondary" type="button" onClick={onClose}>Cancel</Button>
            <Button variant="primary" type="submit" loading={loading} disabled={!title.trim()}>Create</Button>
          </div>
        </form>
      </div>
    </div>
  )
}
