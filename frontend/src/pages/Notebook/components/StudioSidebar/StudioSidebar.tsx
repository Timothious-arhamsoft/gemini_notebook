import React from 'react'
import type { Citation, UploadFile } from '../../../../types'

interface Props {
  activeCitation: Citation | null
  onClearCitation: () => void
  uploads: UploadFile[]
  logs: string[]
}

export function StudioSidebar({
  activeCitation,
  onClearCitation,
  uploads,
  logs,
}: Props) {
  return (
    <aside className="studio-sidebar">
      {activeCitation ? (
        /* CITATION & CHUNK DETAIL VIEW (With Back Button) */
        <div className="studio-sidebar__citation-view">
          <div className="studio-sidebar__header">
            <button
              className="studio-sidebar__back-btn"
              onClick={onClearCitation}
              title="Back to activity logs"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="19" y1="12" x2="5" y2="12"/>
                <polyline points="12 19 5 12 12 5"/>
              </svg>
              <span>Back to Logs</span>
            </button>
          </div>

          <div className="studio-sidebar__citation-body">
            <div className="studio-sidebar__citation-badge">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              <span>Grounded Citation Detail</span>
            </div>

            <h3 className="studio-sidebar__citation-source">{activeCitation.source_title}</h3>

            <div className="studio-sidebar__chunk-box">
              <div className="studio-sidebar__chunk-header">
                <span className="studio-sidebar__chunk-tag">Extracted Chunk Context</span>
              </div>
              <div className="studio-sidebar__chunk-content">
                <mark className="studio-sidebar__highlight">{activeCitation.excerpt}</mark>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* STANDARD STUDIO & INGESTION LOGS VIEW */
        <div className="studio-sidebar__logs-view">
          <div className="studio-sidebar__header">
            <div className="studio-sidebar__title-group">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                <line x1="8" y1="21" x2="16" y2="21"/>
                <line x1="12" y1="17" x2="12" y2="21"/>
              </svg>
              <h3>Studio & Activity Logs</h3>
            </div>
          </div>

          <div className="studio-sidebar__content">
            {/* 1. Document Overview */}
            <div className="studio-sidebar__section">
              <h4 className="studio-sidebar__section-title">Active Resources</h4>
              {uploads.length === 0 ? (
                <p className="studio-sidebar__empty-text">No active documents uploaded yet.</p>
              ) : (
                <div className="studio-sidebar__resource-list">
                  {uploads.map(u => (
                    <div key={u.id} className="studio-sidebar__resource-item">
                      <span className="studio-sidebar__resource-name">{u.file.name}</span>
                      <span className={`studio-sidebar__status-tag studio-sidebar__status-tag--${u.status}`}>
                        {u.status}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 2. Pipeline Logs */}
            <div className="studio-sidebar__section">
              <h4 className="studio-sidebar__section-title">Ingestion & RAG Logs</h4>
              <div className="studio-sidebar__log-console">
                {logs.length === 0 ? (
                  <div className="studio-sidebar__log-entry studio-sidebar__log-entry--info">
                    [SYSTEM] Pipeline ready. Waiting for document upload...
                  </div>
                ) : (
                  logs.map((log, idx) => (
                    <div key={idx} className="studio-sidebar__log-entry">
                      {log}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
