import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { renderAsync } from 'docx-preview'
import { getFileTypeConfig, formatFileSize } from '../SourceUpload'
import { apiClient } from '../../../../api/client'
import type { UploadFile } from '../../../../types'
import { DocumentProcessingStatus } from '../DocumentProcessingStatus'

interface Props {
  uploads: UploadFile[]
  onRemove: (id: string) => void
  onRetry?: (id: string) => void
  onOpenUploadModal: () => void
  activePreviewFile?: UploadFile | null
  onSelectFile?: (file: UploadFile | null) => void
  activeTab?: 'sources' | 'chat'
}

export function SourcesSidebar({
  uploads,
  onRemove,
  onRetry,
  onOpenUploadModal,
  activePreviewFile: externalPreviewFile,
  onSelectFile,
  activeTab,
}: Props) {
  const { id: notebookId } = useParams<{ id: string }>()
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

  // Effect for Object URL, Text reading & DOCX blob preview
  const [objectUrl, setObjectUrl] = useState<string | null>(null)
  const [textContent, setTextContent] = useState<string | null>(null)
  const [docxBlob, setDocxBlob] = useState<Blob | null>(null)
  const [docxLoading, setDocxLoading] = useState<boolean>(false)
  const [docxRenderError, setDocxRenderError] = useState<boolean>(false)
  
  const docxContainerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!activeFile) {
      setObjectUrl(null)
      setTextContent(null)
      setDocxBlob(null)
      setDocxLoading(false)
      setDocxRenderError(false)
      return
    }

    const fileNameLower = activeFile.file.name.toLowerCase()
    const isDocx = fileNameLower.endsWith('.docx') || fileNameLower.endsWith('.doc')
    const isPdf = activeFile.file.type === 'application/pdf' || fileNameLower.endsWith('.pdf')
    const isText = activeFile.file.type.includes('text') || 
                   fileNameLower.endsWith('.txt') || 
                   fileNameLower.endsWith('.md')

    let createdBlobUrl: string | null = null

    if (isText) {
      setDocxBlob(null)
      if (activeFile.file.size > 0) {
        activeFile.file.text().then(text => setTextContent(text)).catch(() => setTextContent(activeFile.content_text ?? null))
      } else {
        setTextContent(activeFile.content_text ?? null)
      }
    } else if (isDocx) {
      setTextContent(activeFile.content_text ?? null)
      if (activeFile.file.size > 0) {
        setDocxBlob(activeFile.file)
      } else if (notebookId && activeFile.id) {
        setDocxLoading(true)
        apiClient.get(`/notebooks/${notebookId}/sources/${activeFile.id}/file`, { responseType: 'blob' })
          .then(res => {
            setDocxBlob(res.data)
          })
          .catch(err => {
            console.error('Failed to load docx file blob:', err)
            setDocxRenderError(true)
            setDocxLoading(false)
          })
      }
    } else if (isPdf) {
      setTextContent(activeFile.content_text ?? null)
      setDocxBlob(null)
      if (activeFile.file.size > 0) {
        const url = URL.createObjectURL(activeFile.file)
        createdBlobUrl = url
        setObjectUrl(url)
      } else if (notebookId && activeFile.id) {
        apiClient.get(`/notebooks/${notebookId}/sources/${activeFile.id}/file`, { responseType: 'blob' })
          .then(res => {
            const blobUrl = URL.createObjectURL(res.data)
            createdBlobUrl = blobUrl
            setObjectUrl(blobUrl)
          })
          .catch(err => {
            console.error('Failed to load PDF file blob:', err)
            setObjectUrl(null)
          })
      }
    } else {
      setTextContent(activeFile.content_text ?? null)
      setDocxBlob(null)
    }

    return () => {
      if (createdBlobUrl) {
        URL.revokeObjectURL(createdBlobUrl)
      }
    }
  }, [activeFile, notebookId])

  // Effect to trigger docx-preview renderAsync when container ref and docxBlob are ready
  useEffect(() => {
    const fileNameLower = activeFile?.file.name.toLowerCase() ?? ''
    const isDocx = fileNameLower.endsWith('.docx') || fileNameLower.endsWith('.doc')

    if (isDocx && docxBlob && docxContainerRef.current) {
      setDocxLoading(true)
      setDocxRenderError(false)
      docxContainerRef.current.innerHTML = ''

      renderAsync(docxBlob, docxContainerRef.current, undefined, {
        inWrapper: true,
        ignoreWidth: false,
        ignoreHeight: false,
        breakPages: true,
        experimental: true,
      })
        .then(() => {
          setDocxLoading(false)
        })
        .catch(err => {
          console.error('docx-preview render error:', err)
          setDocxRenderError(true)
          setDocxLoading(false)
        })
    }
  }, [docxBlob, activeFile])

  // 1. INLINE PREVIEW MODE (When a file is selected)
  if (activeFile) {
    const config = getFileTypeConfig(activeFile.file.name)
    const fileNameLower = activeFile.file.name.toLowerCase()
    const isPdf = activeFile.file.type === 'application/pdf' || fileNameLower.endsWith('.pdf')
    const isDocx = fileNameLower.endsWith('.docx') || fileNameLower.endsWith('.doc')
    const displayContent = textContent || activeFile.content_text

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
          ) : isDocx ? (
            <>
              {docxLoading && <div className="sidebar-preview__fallback">Loading formatted document preview...</div>}
              {docxRenderError ? (
                <pre className="sidebar-preview__text">
                  {displayContent || 'No extracted text available for this document.'}
                </pre>
              ) : (
                <div
                  ref={docxContainerRef}
                  className="sidebar-preview__docx"
                  style={{ display: docxLoading ? 'none' : 'block' }}
                />
              )}
            </>
          ) : displayContent ? (
            <pre className="sidebar-preview__text">
              {displayContent}
            </pre>
          ) : objectUrl ? (
            <div className="sidebar-preview__fallback">
              <p>Preview not available directly for this file format.</p>
              <a href={objectUrl} download={activeFile.file.name} className="sources-sidebar__add-btn">
                Download File
              </a>
            </div>
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
                    {formatFileSize(item.file_size ?? item.file.size)}
                  </span>
                  <DocumentProcessingStatus
                    upload={item}
                    onRetry={onRetry}
                    retryDisabled={!!item.retrying}
                    compact
                  />
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
