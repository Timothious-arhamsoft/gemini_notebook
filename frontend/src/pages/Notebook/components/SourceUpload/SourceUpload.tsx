import { useCallback, useRef, useState } from 'react'
import type { UploadFile } from '../../../../types'

export interface FileTypeConfig {
  extension: string
  mimeType: string
  label: string
  color: string
}

export const SUPPORTED_FILE_TYPES: Record<string, FileTypeConfig> = {
  pdf:  { extension: 'pdf',  mimeType: 'application/pdf', label: 'PDF', color: '#f06060' },
  txt:  { extension: 'txt',  mimeType: 'text/plain', label: 'TXT', color: '#9898a8' },
  md:   { extension: 'md',   mimeType: 'text/markdown', label: 'MD', color: '#6d6aff' },
  docx: { extension: 'docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', label: 'DOCX', color: '#4da3ff' },
}

const ACCEPTED_EXTENSIONS = Object.keys(SUPPORTED_FILE_TYPES).map(ext => `.${ext}`).join(',')

export function getFileTypeConfig(fileName: string): FileTypeConfig {
  const ext = fileName.split('.').pop()?.toLowerCase() ?? ''
  if (SUPPORTED_FILE_TYPES[ext]) {
    return SUPPORTED_FILE_TYPES[ext]
  }
  return {
    extension: ext || 'doc',
    mimeType: 'application/octet-stream',
    label: (ext || 'DOC').toUpperCase(),
    color: '#9898a8',
  }
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}


interface Props {
  uploads: UploadFile[]
  onAdd: (files: File[]) => void
  onRemove: (id: string) => void
  onRetry?: (id: string) => void
}

export function SourceUpload({ uploads, onAdd, onRemove, onRetry }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files || files.length === 0) return
    onAdd(Array.from(files))
  }, [onAdd])

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  return (
    <div className="source-upload">
      {/* Drag & Drop Zone */}
      <div
        className={`source-upload__zone ${dragging ? 'source-upload__zone--active' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && inputRef.current?.click()}
      >
        <div className="source-upload__icon-box">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="12" y1="18" x2="12" y2="12"/>
            <polyline points="9 15 12 12 15 15"/>
          </svg>
        </div>
        <p className="source-upload__prompt">
          Drag and Drop or <span className="source-upload__link">Click to upload</span>
        </p>
        <p className="source-upload__subtext">
          Supported formats: PDF, TXT, MD, DOCX. Max Size: 25MB
        </p>
      </div>

      {/* Hidden File Picker Input */}
      <input
        ref={inputRef}
        type="file"
        multiple
        hidden
        accept={ACCEPTED_EXTENSIONS}
        onChange={e => handleFiles(e.target.files)}
      />

      {/* File Item List */}
      {uploads.length > 0 && (
        <div className="source-upload__list">
          {uploads.map(item => (
            <div key={item.id} className={`source-upload__card ${item.status === 'error' ? 'source-upload__card--error' : ''}`}>
              <div className="source-upload__card-main">
                <div className="source-upload__card-info">
                  <span className="source-upload__filename">{item.file.name}</span>
                  <span className="source-upload__filesize">{formatFileSize(item.file.size)}</span>
                  {item.status === 'error' && (
                    <span className="source-upload__error-msg">Upload Failed</span>
                  )}
                </div>

                <div className="source-upload__card-actions">
                  {item.status === 'error' && onRetry && (
                    <button
                      className="source-upload__action-btn"
                      onClick={() => onRetry(item.id)}
                      title="Retry upload"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="23 4 23 10 17 10"/>
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                      </svg>
                    </button>
                  )}

                  {item.status === 'uploading' ? (
                    <button
                      className="source-upload__action-btn"
                      onClick={() => onRemove(item.id)}
                      title="Cancel upload"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="18" y1="6" x2="6" y2="18"/>
                        <line x1="6" y1="6" x2="18" y2="18"/>
                      </svg>
                    </button>
                  ) : (
                    <button
                      className="source-upload__action-btn"
                      onClick={() => onRemove(item.id)}
                      title="Remove file"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                      </svg>
                    </button>
                  )}
                </div>
              </div>

              {/* Live progress line for uploading state */}
              {item.status === 'uploading' && (
                <div className="source-upload__progress-track">
                  <div
                    className="source-upload__progress-fill"
                    style={{ width: `${item.progress}%` }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
