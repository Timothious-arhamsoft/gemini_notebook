import { useEffect, useState } from 'react'
import { getFileTypeConfig, formatFileSize } from '../SourceUpload'
import type { UploadFile } from '../../../../types'

interface Props {
  uploads: UploadFile[]
  onRemove: (id: string) => void
  onOpenUploadModal: () => void
  activePreviewFile?: UploadFile | null
  onSelectFile?: (file: UploadFile | null) => void
  activeTab?: 'sources' | 'chat'
}

export function SourcesSidebar({
  uploads,
  onRemove,
  onOpenUploadModal,
  activePreviewFile: externalPreviewFile,
  onSelectFile,
  activeTab,
}: Props) {
  const [internalPreviewFile, setInternalPreviewFile] = useState<UploadFile | null>(null)
  
  // Support both controlled or uncontrolled preview file state
  const activeFile = externalPreviewFile !== undefined ? externalPreviewFile : internalPreviewFile

  const handleSelect = (file: UploadFile | null) => {
    if (onSelectFile) {
      onSelectFile(file)
    } else {
      setInternalPreviewFile(file)
    }
  }

  // Effect for Object URL & Text reading during inline sidebar preview
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const [textContent, setTextContent] = useState<string | null>(null)

  useEffect(() => {
    if (!activeFile) {
      setObjectUrl(null)
      setTextContent(null)
      return
    }

    const url = URL.createObjectURL(activeFile.file)
    setObjectUrl(url)

    const isText = activeFile.file.type.includes('text') || 
                   activeFile.file.name.endsWith('.txt') || 
                   activeFile.file.name.endsWith('.md')

    if (isText) {
      activeFile.file.text().then(text => setTextContent(text)).catch(() => setTextContent(null))
    } else {
      setTextContent(null)
    }

    return () => {
      URL.revokeObjectURL(url)
    }
  }, [activeFile])

  // 1. INLINE PREVIEW MODE (When a file is selected)
  if (activeFile) {
    const config = getFileTypeConfig(activeFile.file.name)
    const isPdf = activeFile.file.type === 'application/pdf' || activeFile.file.name.toLowerCase().endsWith('.pdf')

    return (
      <aside className={`sources-sidebar sources-sidebar--preview${activeTab === 'sources' ? ' sources-sidebar--active-tab' : ''}`}>
        {/* Inline Preview Header */}
        <div className="sidebar-preview__header">
          <button
            className="sidebar-preview__back-btn"
            onClick={() => handleSelect(null)}
            title="Back to sources list"
            aria-label="Back to sources list"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="19" y1="12" x2="5" y2="12"/>
              <polyline points="12 19 5 12 12 5"/>
            </svg>
          </button>
          
          <div className="sidebar-preview__title-container">
            <span className="sidebar-preview__badge" style={{ color: config.color, borderColor: config.color }}>
              {config.label}
            </span>
            <span className="sidebar-preview__filename" title={activeFile.file.name}>
              {activeFile.file.name}
            </span>
          </div>

          <button
            className="sidebar-preview__close-btn"
            onClick={() => handleSelect(null)}
            title="Close document preview"
            aria-label="Close document preview"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        {/* Inline Preview Body */}
        <div className="sidebar-preview__body">
          {isPdf && objectUrl ? (
            <iframe
              src={objectUrl}
              title={activeFile.file.name}
              className="sidebar-preview__iframe"
            />
          ) : textContent !== null ? (
            <pre className="sidebar-preview__text">{textContent}</pre>
          ) : objectUrl ? (
            <object data={objectUrl} type={activeFile.file.type} className="sidebar-preview__object">
              <div className="sidebar-preview__fallback">
                <p>Preview not available</p>
                <a href={objectUrl} download={activeFile.file.name} className="sources-sidebar__add-btn">
                  Download File
                </a>
              </div>
            </object>
          ) : (
            <div className="sidebar-preview__fallback">Loading preview…</div>
          )}
        </div>
      </aside>
    )
  }

  // 2. ORIGINAL STATE MODE (Header with Add Source button & uploaded docs list)
  return (
    <aside className={`sources-sidebar${activeTab === 'sources' ? ' sources-sidebar--active-tab' : ''}`}>
      {/* Sidebar Header */}
      <div className="sources-sidebar__header">
        <div className="sources-sidebar__header-title">
          <h2 className="sources-sidebar__title">Sources</h2>
          <span className="sources-sidebar__count">{uploads.length}</span>
        </div>
        <button
          className="sources-sidebar__add-btn"
          onClick={onOpenUploadModal}
          title="Add source document"
          aria-label="Add source document"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 1.5a.5.5 0 0 1 .5.5v5.5H14a.5.5 0 0 1 0 1H8.5V14a.5.5 0 0 1-1 0V8.5H2a.5.5 0 0 1 0-1h5.5V2a.5.5 0 0 1 .5-.5Z"/>
          </svg>
          <span>Add source</span>
        </button>
      </div>

      {/* Sources List or Empty State */}
      {uploads.length === 0 ? (
        <div className="sources-sidebar__empty-card">
          <p className="sources-sidebar__empty-title">No sources added yet</p>
        </div>

      ) : (
        <div className="sources-sidebar__list">
          {uploads.map(item => {
            const config = getFileTypeConfig(item.file.name)
            return (
              <div
                key={item.id}
                className="sources-sidebar__item"
                onClick={() => handleSelect(item)}
                role="button"
                tabIndex={0}
                onKeyDown={e => e.key === 'Enter' && handleSelect(item)}
                title="Click to view document in sidebar"
              >
                <div className="sources-sidebar__item-badge" style={{ color: config.color, borderColor: config.color }}>
                  {config.label}
                </div>

                <div className="sources-sidebar__item-info">
                  <span className="sources-sidebar__item-name" title={item.file.name}>
                    {item.file.name}
                  </span>
                  <span className="sources-sidebar__item-size">
                    {formatFileSize(item.file.size)}
                  </span>
                </div>

                <div className="sources-sidebar__item-actions">
                  <button
                    className="sources-sidebar__remove-btn"
                    onClick={e => {
                      e.stopPropagation()
                      onRemove(item.id)
                    }}
                    title="Remove source"
                    aria-label="Remove source"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <polyline points="3 6 5 6 21 6"/>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </aside>
  )
}
