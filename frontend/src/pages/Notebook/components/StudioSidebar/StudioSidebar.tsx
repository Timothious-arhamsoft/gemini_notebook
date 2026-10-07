import { useMemo, useState } from 'react'
import type { Citation, GroqUsage, UploadFile } from '../../../../types'
import type { DocumentAnalysisResult } from '../../../../api/sources'
import { citationSelectionKey, formatCitationMeta } from '../../../../utils/assistantContent'

interface Props {
  activeCitation: Citation | null
  onClearCitation: () => void
  uploads: UploadFile[]
  logs: string[]
  latestAiUsage?: GroqUsage | null
}

type Tone = 'info' | 'success' | 'error'

interface Entry {
  time: string
  message: string
  tone: Tone
  count: number
}

function parseLog(raw: string): Omit<Entry, 'count'> {
  const m = raw.match(/^\[(\d{1,2}:\d{2}:\d{2})\]\s*(.*)$/)
  const time = m ? m[1] : ''
  const message = (m ? m[2] : raw).replace(/^\[SYSTEM\]\s*/i, '')

  let tone: Tone = 'info'
  if (/fail|error|could not|unable/i.test(message)) tone = 'error'
  else if (/ready|loaded|uploaded|complete|success|indexed|saved|analysis|retrieval|generation|response saved/i.test(message)) {
    tone = 'success'
  }

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

function formatModelLabel(model: string | null | undefined): string {
  if (!model) return 'AI model'
  if (model.includes('gpt-oss-120b')) return 'GPT-OSS 120B'
  const short = model.split('/').pop() ?? model
  return short.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function formatCost(usd: number | null | undefined): string {
  if (usd == null) return 'Unavailable'
  if (usd >= 0.01) return `$${usd.toFixed(4)}`
  return `$${usd.toFixed(6)}`
}

function formatLatency(ms: number | null | undefined): string {
  if (ms == null) return '—'
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.round(ms)}ms`
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
      </div>
    </div>
  )
}

function UsagePanel({ usage }: { usage: GroqUsage }) {
  return (
    <div className="studio-sidebar__usage-card">
      <span className="studio-sidebar__eyebrow">AI response</span>
      <p className="studio-sidebar__usage-model">{formatModelLabel(usage.model)}</p>

      <div className="studio-sidebar__usage-grid">
        <span className="studio-sidebar__usage-label">Input</span>
        <span className="studio-sidebar__usage-value">{fmt(usage.prompt_tokens)}</span>

        <span className="studio-sidebar__usage-label">Output</span>
        <span className="studio-sidebar__usage-value">{fmt(usage.completion_tokens)}</span>

        <span className="studio-sidebar__usage-label">Total</span>
        <span className="studio-sidebar__usage-value">{fmt(usage.total_tokens)}</span>

        {usage.cached_tokens != null && usage.cached_tokens > 0 && (
          <>
            <span className="studio-sidebar__usage-label">Cached input</span>
            <span className="studio-sidebar__usage-value">{fmt(usage.cached_tokens)}</span>
          </>
        )}

        <span className="studio-sidebar__usage-label">Est. cost</span>
        <span className="studio-sidebar__usage-value">{formatCost(usage.estimated_cost_usd)}</span>

        {usage.latency_ms != null && (
          <>
            <span className="studio-sidebar__usage-label">Latency</span>
            <span className="studio-sidebar__usage-value">{formatLatency(usage.latency_ms)}</span>
          </>
        )}
      </div>
    </div>
  )
}

export function StudioSidebar({ activeCitation, onClearCitation, uploads, logs, latestAiUsage }: Props) {
  const [showHistory, setShowHistory] = useState(false)
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null)

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

  // Logs are prepended (newest first)
  const latest = entries[0]
  const earlier = entries.slice(1, 1 + HISTORY_LIMIT)

  if (activeCitation) {
    const meta = formatCitationMeta(activeCitation)
    const body = activeCitation.content || activeCitation.excerpt || ''

    return (
      <aside className="studio-sidebar studio-sidebar--evidence">
        <div className="studio-sidebar__header">
          <button type="button" className="studio-sidebar__back-btn" onClick={onClearCitation}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <line x1="19" y1="12" x2="5" y2="12" />
              <polyline points="12 19 5 12 12 5" />
            </svg>
            <span>Back</span>
          </button>
          <h3 className="studio-sidebar__title studio-sidebar__title--inline">Evidence</h3>
        </div>

        <div className="studio-sidebar__content">
          <div className="studio-sidebar__evidence-block">
            <span className="studio-sidebar__eyebrow">Source</span>
            <h3 className="studio-sidebar__citation-source">{activeCitation.source_title}</h3>
            {meta && <p className="studio-sidebar__citation-meta">{meta}</p>}
            {activeCitation.citation_index != null && (
              <p className="studio-sidebar__citation-badge">Citation [{activeCitation.citation_index}]</p>
            )}
          </div>

          <div className="studio-sidebar__divider" />

          <div>
            <span className="studio-sidebar__eyebrow">Retrieved content</span>
            <p className="studio-sidebar__excerpt">
              <mark className="studio-sidebar__highlight">{body}</mark>
            </p>
          </div>

          <div className="studio-sidebar__divider" />

          <div>
            <span className="studio-sidebar__eyebrow">Metadata</span>
            <dl className="studio-sidebar__meta-list">
              <div>
                <dt>Source ID</dt>
                <dd>{activeCitation.source_id}</dd>
              </div>
              {activeCitation.chunk_id && (
                <div>
                  <dt>Chunk ID</dt>
                  <dd>{activeCitation.chunk_id}</dd>
                </div>
              )}
              {activeCitation.page != null && (
                <div>
                  <dt>Page</dt>
                  <dd>{activeCitation.page}</dd>
                </div>
              )}
              {activeCitation.section && (
                <div>
                  <dt>Section</dt>
                  <dd>{activeCitation.section}</dd>
                </div>
              )}
            </dl>
          </div>
        </div>
      </aside>
    )
  }

  return (
    <aside className="studio-sidebar">
      <div className="studio-sidebar__header">
        <h3 className="studio-sidebar__title">Studio</h3>
      </div>

      <div className="studio-sidebar__content">
        {latestAiUsage && (
          <section>
            <UsagePanel usage={latestAiUsage} />
          </section>
        )}

        <section>
          <h4 className="studio-sidebar__section-title">Activity</h4>

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
            <p className="studio-sidebar__empty-text">Nothing yet — upload a document to get started.</p>
          )}

          {earlier.length > 0 && (
            <>
              <button
                type="button"
                className="studio-sidebar__toggle"
                aria-expanded={showHistory}
                onClick={() => setShowHistory(v => !v)}
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

        <section>
          <h4 className="studio-sidebar__section-title">Documents</h4>
          {uploads.length === 0 ? (
            <p className="studio-sidebar__empty-text">No documents uploaded yet.</p>
          ) : (
            <ul className="studio-sidebar__resource-list">
              {uploads.map(u => {
                const isExpanded = expandedDoc === u.id
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

                    {u.analysis && (
                      <button
                        type="button"
                        className="studio-sidebar__analysis-toggle"
                        aria-expanded={isExpanded}
                        onClick={() => setExpandedDoc(isExpanded ? null : u.id)}
                      >
                        <span className="studio-sidebar__analysis-toggle-label">Analysis {isExpanded ? '▲' : '▼'}</span>
                      </button>
                    )}

                    {isExpanded && u.analysis && <AnalysisPanel analysis={u.analysis} />}
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

// Re-export for tests / key helper
export { citationSelectionKey }
