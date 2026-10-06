import { useMemo, useState } from 'react'
import type { Citation, UploadFile } from '../../../../types'
import type { DocumentAnalysisResult } from '../../../../api/sources'

interface Props {
  activeCitation: Citation | null
  onClearCitation: () => void
  uploads: UploadFile[]
  logs: string[]
}

type Tone = 'info' | 'success' | 'error'

interface Entry {
  time: string
  message: string
  tone: Tone
  count: number
}

/** "[12:57:34] Loaded 2 documents" -> { time: "12:57:34", message: "Loaded 2 documents", tone } */
function parseLog(raw: string): Omit<Entry, 'count'> {
  const m = raw.match(/^\[(\d{1,2}:\d{2}:\d{2})\]\s*(.*)$/)
  const time = m ? m[1] : ''
  const message = (m ? m[2] : raw).replace(/^\[SYSTEM\]\s*/i, '')

  let tone: Tone = 'info'
  if (/fail|error|could not|unable/i.test(message)) tone = 'error'
  else if (/ready|loaded|uploaded|complete|success|indexed|saved|analysis/i.test(message)) tone = 'success'

  return { time, message, tone }
}

const STATUS_LABEL: Record<string, string> = {
  ready: 'Ready',
  completed: 'Ready',
  uploading: 'Uploading…',
  processing: 'Extracting…',
  analyzing: 'Analyzing…',
  chunking: 'Chunking…',
  embedding: 'Embedding…',
  error: 'Failed',
  failed: 'Failed',
}

const HISTORY_LIMIT = 20

function fmt(n: number | null | undefined): string {
  if (n == null) return '—'
  return n.toLocaleString()
}

function AnalysisPanel({ analysis }: { analysis: DocumentAnalysisResult }) {
  if (analysis.error) {
    return (
      <div className="studio-sidebar__analysis-error">
        ⚠ Analysis failed: {analysis.error}
      </div>
    )
  }
  return (
    <div className="studio-sidebar__analysis">
      <div className="studio-sidebar__analysis-grid">
        <span className="studio-sidebar__analysis-label">Characters</span>
        <span className="studio-sidebar__analysis-value">{fmt(analysis.total_characters)}</span>

        <span className="studio-sidebar__analysis-label">Words</span>
        <span className="studio-sidebar__analysis-value">{fmt(analysis.total_words)}</span>

        {analysis.page_count != null && (
          <>
            <span className="studio-sidebar__analysis-label">Pages</span>
            <span className="studio-sidebar__analysis-value">{fmt(analysis.page_count)}</span>
          </>
        )}

        <span className="studio-sidebar__analysis-label">Paragraphs</span>
        <span className="studio-sidebar__analysis-value">{fmt(analysis.paragraph_count)}</span>

        {analysis.heading_count != null && (
          <>
            <span className="studio-sidebar__analysis-label">Headings</span>
            <span className="studio-sidebar__analysis-value">{fmt(analysis.heading_count)}</span>
          </>
        )}

        {analysis.section_count != null && (
          <>
            <span className="studio-sidebar__analysis-label">Sections</span>
            <span className="studio-sidebar__analysis-value">{fmt(analysis.section_count)}</span>
          </>
        )}
      </div>

      <div className="studio-sidebar__analysis-divider" />

      <div className="studio-sidebar__analysis-section-title">Paragraph distribution</div>
      <div className="studio-sidebar__analysis-grid">
        <span className="studio-sidebar__analysis-label">Median</span>
        <span className="studio-sidebar__analysis-value">{fmt(analysis.median_paragraph_chars)}</span>

        <span className="studio-sidebar__analysis-label">P75</span>
        <span className="studio-sidebar__analysis-value">{fmt(analysis.p75_paragraph_chars)}</span>

        <span className="studio-sidebar__analysis-label">P90</span>
        <span className="studio-sidebar__analysis-value">{fmt(analysis.p90_paragraph_chars)}</span>

        <span className="studio-sidebar__analysis-label">P95</span>
        <span className="studio-sidebar__analysis-value">{fmt(analysis.p95_paragraph_chars)}</span>

        <span className="studio-sidebar__analysis-label">Max</span>
        <span className="studio-sidebar__analysis-value">{fmt(analysis.max_paragraph_chars)}</span>
      </div>

      <div className="studio-sidebar__analysis-divider" />

      <div className="studio-sidebar__analysis-recommendation">
        <span className="studio-sidebar__analysis-strategy">Strategy: {analysis.recommended_strategy}</span>
        <span className="studio-sidebar__analysis-chunk">
          Chunk size: <strong>~{fmt(analysis.recommended_chunk_size)} chars</strong>
        </span>
      </div>
    </div>
  )
}

export function StudioSidebar({ activeCitation, onClearCitation, uploads, logs }: Props) {
  const [showHistory, setShowHistory] = useState(false)
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null)

  // Parse logs and collapse consecutive duplicates (oldest -> newest)
  const entries = useMemo(() => {
    const out: Entry[] = []
    for (const raw of logs) {
      const e = parseLog(raw)
      const last = out[out.length - 1]
      if (last && last.message === e.message) {
        last.count += 1
        last.time = e.time || last.time
      } else {
        out.push({ ...e, count: 1 })
      }
    }
    return out
  }, [logs])

  const latest = entries[entries.length - 1]
  const earlier = entries.slice(0, -1).reverse().slice(0, HISTORY_LIMIT)

  /* ── Citation detail ───────────────────────────────────── */
  if (activeCitation) {
    return (
      <aside className="studio-sidebar">
        <div className="studio-sidebar__header">
          <button
            type="button"
            className="studio-sidebar__back-btn"
            onClick={onClearCitation}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            <span>Back</span>
          </button>
        </div>

        <div className="studio-sidebar__content">
          <div>
            <span className="studio-sidebar__eyebrow">Source</span>
            <h3 className="studio-sidebar__citation-source">{activeCitation.source_title}</h3>
          </div>

          <div>
            <span className="studio-sidebar__eyebrow">Excerpt used for the answer</span>
            <p className="studio-sidebar__excerpt">
              <mark className="studio-sidebar__highlight">{activeCitation.excerpt}</mark>
            </p>
          </div>
        </div>
      </aside>
    )
  }

  /* ── Activity view ─────────────────────────────────────── */
  return (
    <aside className="studio-sidebar">
      <div className="studio-sidebar__header">
        <h3 className="studio-sidebar__title">Activity</h3>
      </div>

      <div className="studio-sidebar__content">
        {/* Latest activity */}
        <section>
          <h4 className="studio-sidebar__section-title">Latest</h4>

          {latest ? (
            <div className={`studio-sidebar__latest studio-sidebar__latest--${latest.tone}`}>
              <span className="studio-sidebar__dot" aria-hidden="true" />
              <div className="studio-sidebar__latest-text">
                <p className="studio-sidebar__latest-msg">{latest.message}</p>
                {latest.time && (
                  <span className="studio-sidebar__time">
                    {latest.time}
                    {latest.count > 1 && ` · ×${latest.count}`}
                  </span>
                )}
              </div>
            </div>
          ) : (
            <p className="studio-sidebar__empty-text">
              Nothing yet — upload a document to get started.
            </p>
          )}

          {earlier.length > 0 && (
            <>
              <button
                type="button"
                className="studio-sidebar__toggle"
                aria-expanded={showHistory}
                onClick={() => setShowHistory((v) => !v)}
              >
                {showHistory ? 'Hide earlier activity' : `Show earlier activity (${entries.length - 1})`}
              </button>

              {showHistory && (
                <ol className="studio-sidebar__history">
                  {earlier.map((e, i) => (
                    <li key={`${e.time}-${i}`} className={`studio-sidebar__history-item studio-sidebar__history-item--${e.tone}`}>
                      <span className="studio-sidebar__dot" aria-hidden="true" />
                      <span className="studio-sidebar__history-msg">{e.message}</span>
                      <span className="studio-sidebar__time">
                        {e.time}
                        {e.count > 1 && ` ×${e.count}`}
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </>
          )}
        </section>

        {/* Documents */}
        <section>
          <h4 className="studio-sidebar__section-title">Documents</h4>
          {uploads.length === 0 ? (
            <p className="studio-sidebar__empty-text">No documents uploaded yet.</p>
          ) : (
            <ul className="studio-sidebar__resource-list">
              {uploads.map((u) => {
                const isExpanded = expandedDoc === u.id
                const hasAnalysis = u.analysis && !u.analysis.error
                const analysisFailed = u.analysis?.error

                return (
                  <li key={u.id} className="studio-sidebar__resource-item">
                    <div className="studio-sidebar__resource-row">
                      <span className="studio-sidebar__resource-name" title={u.file.name}>
                        {u.file.name}
                      </span>
                      <span className={`studio-sidebar__status studio-sidebar__status--${u.status}`}>
                        <span className="studio-sidebar__dot" aria-hidden="true" />
                        {STATUS_LABEL[u.status] ?? u.status}
                      </span>
                    </div>

                    {/* Show analysis toggle when analysis is available */}
                    {u.analysis && (
                      <button
                        type="button"
                        className="studio-sidebar__analysis-toggle"
                        aria-expanded={isExpanded}
                        onClick={() => setExpandedDoc(isExpanded ? null : u.id)}
                      >
                        {analysisFailed ? (
                          <span className="studio-sidebar__analysis-toggle-label studio-sidebar__analysis-toggle-label--error">
                            ⚠ Analysis error
                          </span>
                        ) : (
                          <span className="studio-sidebar__analysis-toggle-label">
                            📊 Analysis {isExpanded ? '▲' : '▼'}
                          </span>
                        )}
                        {hasAnalysis && !isExpanded && (
                          <span className="studio-sidebar__analysis-peek">
                            ~{u.analysis!.recommended_chunk_size} chars
                          </span>
                        )}
                      </button>
                    )}

                    {isExpanded && u.analysis && (
                      <AnalysisPanel analysis={u.analysis} />
                    )}
                  </li>
                )
              })}
            </ul>
          )}
        </section>
      </div>
    </aside>
  )
}