import { useCallback, useRef, useState } from 'react'
import { Button } from '../../../../components/Button'
import type { UploadFile } from '../../../../types'

const ACCEPTED = { pdf: 'application/pdf', txt: 'text/plain', md: 'text/markdown', docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }
const ACCEPTED_EXT = Object.keys(ACCEPTED).map(e => `.${e}`).join(',')

function getIcon(name: string) {
  const ext = name.split('.').pop()?.toLowerCase() ?? ''
  const colors: Record<string, string> = { pdf: '#f06060', txt: '#9898a8', md: '#6d6aff', docx: '#4da3ff' }
  return { ext: ext.toUpperCase(), color: colors[ext] ?? '#9898a8' }
}

function formatBytes(b: number) {
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`
  return `${(b / 1024 / 1024).toFixed(1)} MB`
}

interface Props {
  uploads: UploadFile[]
  onAdd: (files: File[]) => void
  onRemove: (id: string) => void
}

export function SourceUpload({ uploads, onAdd, onRemove }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)

  const handleFiles = useCallback((files: FileList | null) => {
    if (!files) return
    onAdd(Array.from(files))
  }, [onAdd])

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  return (
    <div className="source-upload">
      {/* Drop zone */}
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
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" className="source-upload__zone-icon">
          <path d="M12 16V8M8 12l4-4 4 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M5 20h14a1 1 0 0 0 1-1V9l-5-5H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1Z" stroke="currentColor" strokeWidth="1.5" fill="none"/>
        </svg>
        <p className="source-upload__zone-text">
          {dragging ? 'Drop files here' : 'Drag & drop or click to upload'}
        </p>
        <p className="source-upload__zone-hint">PDF, TXT, MD, DOCX</p>
      </div>

      <input ref={inputRef} type="file" multiple hidden accept={ACCEPTED_EXT}
        onChange={e => handleFiles(e.target.files)} />

      {/* Upload list */}
      {uploads.length > 0 && (
        <ul className="source-upload__list">
          {uploads.map(u => {
            const { ext, color } = getIcon(u.file.name)
            return (
              <li key={u.id} className="source-upload__item">
                <div className="source-upload__file-icon" style={{ color }}>
                  <span>{ext}</span>
                </div>
                <div className="source-upload__file-info">
                  <span className="source-upload__file-name">{u.file.name}</span>
                  <span className="source-upload__file-size">{formatBytes(u.file.size)}</span>
                  {u.status === 'uploading' && (
                    <div className="source-upload__progress">
                      <div className="source-upload__progress-bar" style={{ width: `${u.progress}%` }} />
                    </div>
                  )}
                </div>
                <div className="source-upload__status">
                  {u.status === 'ready'      && <span className="source-upload__badge source-upload__badge--ready">Ready</span>}
                  {u.status === 'processing' && <span className="source-upload__badge source-upload__badge--processing">Processing…</span>}
                  {u.status === 'uploading'  && <span className="source-upload__badge source-upload__badge--uploading">{u.progress}%</span>}
                  {u.status === 'error'      && <span className="source-upload__badge source-upload__badge--error" title={u.error}>Error</span>}
                </div>
                <button className="source-upload__remove" onClick={() => onRemove(u.id)} aria-label="Remove">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                    <path d="M1 1l10 10M11 1 1 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
                  </svg>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
