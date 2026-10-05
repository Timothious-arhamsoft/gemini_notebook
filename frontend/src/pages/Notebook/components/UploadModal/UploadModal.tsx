import { useState } from 'react'
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
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const handleAddFiles = (files: File[]) => {
    // Clear previous error message
    setErrorMessage(null)

    const existingNames = new Set(
      uploads.map(upload => upload.file.name.toLowerCase())
    )
    const uniqueFiles: File[] = []
    const addedNames = new Set<string>()
    const duplicateNames: string[] = []

    files.forEach(file => {
      const fileName = file.name.toLowerCase()

      if (existingNames.has(fileName) || addedNames.has(fileName)) {
        duplicateNames.push(file.name)
      } else {
        uniqueFiles.push(file)
        addedNames.add(fileName)
      }
    })

    if (duplicateNames.length > 0) {
      setErrorMessage(
        `Duplicate file${duplicateNames.length > 1 ? 's' : ''} detected: ${duplicateNames.join(
          ', '
        )}. ${duplicateNames.length > 1 ? 'These files have' : 'This file has'} already been added.`
      )
    }

    if (uniqueFiles.length > 0) {
      onAdd(uniqueFiles)
    }
  }

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
          {errorMessage && (
            <div className="modal-card__error" role="alert">
              <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"/>
                <path d="M7.002 11a1 1 0 1 1 2 0 1 1 0 0 1-2 0zM7.1 4.995a.905.905 0 1 1 1.8 0l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 4.995z"/>
              </svg>
              <span>{errorMessage}</span>
              <button
                className="modal-card__error-dismiss"
                onClick={() => setErrorMessage(null)}
                aria-label="Dismiss error"
              >
                ×
              </button>
            </div>
          )}

          <SourceUpload uploads={uploads} onAdd={handleAddFiles} onRemove={onRemove} onRetry={onRetry} />
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