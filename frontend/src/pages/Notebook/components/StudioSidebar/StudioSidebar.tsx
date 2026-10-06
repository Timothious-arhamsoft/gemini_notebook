import { useMemo, useState } from 'react'
import type { Citation, UploadFile } from '../../../../types'

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
  else if (/ready|loaded|uploaded|complete|success|indexed|saved/i.test(message)) tone = 'success'

  return { time, message, tone }
}

const STATUS_LABEL: Record<string, string> = {
  ready: 'Ready',
  uploading: 'Uploading…',
  processing: 'Processing…',
  error: 'Failed',
}

const HISTORY_LIMIT = 20

export function StudioSidebar({ activeCitation, onClearCitation, uploads, logs }: Props) {
  const [showHistory, setShowHistory] = useState(false)

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
              {uploads.map((u) => (
                <li key={u.id} className="studio-sidebar__resource-item">
                  <span className="studio-sidebar__resource-name" title={u.file.name}>
                    {u.file.name}
                  </span>
                  <span className={`studio-sidebar__status studio-sidebar__status--${u.status}`}>
                    <span className="studio-sidebar__dot" aria-hidden="true" />
                    {STATUS_LABEL[u.status] ?? u.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </aside>
  )
}