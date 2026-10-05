import { SourceUpload } from '../SourceUpload/SourceUpload'
import type { UploadFile } from '../../../../types'

interface Props {
  uploads: UploadFile[]
  onAdd: (files: File[]) => void
  onRemove: (id: string) => void
  onRetry?: (id: string) => void
  onClose: () => void
}

export function UploadModal({ uploads, onAdd, onRemove, onRetry, onClose }: Props) {
  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal-card modal-card--upload" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-card__header">
          <h2 id="modal-title" className="modal-card__title">Upload Document</h2>
          <button className="modal-card__close" onClick={onClose} aria-label="Close dialog">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="modal-card__body">
          <SourceUpload uploads={uploads} onAdd={onAdd} onRemove={onRemove} onRetry={onRetry} />
        </div>

        {/* Footer */}
        <div className="modal-card__footer">
          <button className="modal-btn modal-btn--secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="modal-btn modal-btn--primary" onClick={onClose}>
            Continue
          </button>
        </div>
      </div>
    </div>
  )
}
