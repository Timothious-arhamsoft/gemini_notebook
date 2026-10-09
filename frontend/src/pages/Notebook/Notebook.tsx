import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { BrandLogo } from '../../components/BrandLogo'
import { notebooksApi } from '../../api/notebooks'
import {
  uploadSourceApi,
  fetchSourcesApi,
  deleteSourceApi,
  fetchSourceStatusApi,
  retrySourceApi,
} from '../../api/sources'
import {
  fetchChatMessagesApi,
  fetchNotebookTokenUsageApi,
  mapApiChatMessage,
  sendChatMessageApi,
} from '../../api/chat'
import { citationSelectionKey } from '../../utils/assistantContent'
import {
  ACTIVE_PROCESSING_STATUSES,
  applyStatusToUpload,
  mapApiSourceToUpload,
} from '../../utils/sourceProcessing'
import { logsForStatusTransition, type PollLogState } from './sourceActivityLog'
import type { GroqUsage, NotebookTokenUsage } from '../../types'
import { WorkspaceHeader } from './components/WorkspaceHeader/WorkspaceHeader'
import { SourcesSidebar } from './components/SourcesSidebar/SourcesSidebar'
import { StudioSidebar } from './components/StudioSidebar/StudioSidebar'
import { ChatMessage } from './components/ChatMessage/ChatMessage'
import { ChatInput } from './components/ChatInput/ChatInput'
import { UploadModal } from './components/UploadModal/UploadModal'
import { Spinner } from '../../components/Spinner'
import type { ChatMessage as ChatMessageType, Citation, Notebook, UploadFile } from '../../types'
import './Notebook.css'
import './components/StudioSidebar/StudioSidebar.css'

const UNTITLED = 'Untitled'

/** Once per notebook id per browser session — survives StrictMode remounts. */
const activityRestoredNotebooks = new Set<string>()

function sourceCountLabel(n: number) {
  return n === 1 ? '1 source' : `${n} sources`
}

export function NotebookPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [notebook, setNotebook] = useState<Notebook | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [uploads, setUploads] = useState<UploadFile[]>([])
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [hasAutoOpenedModal, setHasAutoOpenedModal] = useState(false)
  const [selectedViewFile, setSelectedViewFile] = useState<UploadFile | null>(null)

  const [logs, setLogs] = useState<string[]>([])
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null)
  const [latestAiUsage, setLatestAiUsage] = useState<GroqUsage | null>(null)
  const [notebookTokenUsage, setNotebookTokenUsage] = useState<NotebookTokenUsage | null>(null)

  const userHasRenamedRef = useRef(false)
  const pollLogStateRef = useRef<Map<string, PollLogState>>(new Map())
  const activePollsRef = useRef<Set<string>>(new Set())

  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [sending, setSending] = useState(false)
  const [activeTab, setActiveTab] = useState<'sources' | 'chat'>('chat')

  const chatEndRef = useRef<HTMLDivElement>(null)

  const addLog = useCallback((message: string) => {
    const timestamp = new Date().toLocaleTimeString([], { hour12: false })
    setLogs(prev => [`[${timestamp}] ${message}`, ...prev])
  }, [])

  const stopPolling = useCallback((sourceId: string) => {
    activePollsRef.current.delete(sourceId)
  }, [])

  const pollSourceUntilDone = useCallback(
    async (notebookId: string, sourceId: string, fileName: string) => {
      if (activePollsRef.current.has(sourceId)) return
      activePollsRef.current.add(sourceId)

      let logState = pollLogStateRef.current.get(sourceId)
      if (!logState) {
        logState = { lastStatus: '', loggedStages: new Set() }
        pollLogStateRef.current.set(sourceId, logState)
      }

      const maxAttempts = 150 // ~5 min at 2s
      try {
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
          if (!activePollsRef.current.has(sourceId)) return

          if (attempt > 0) {
            await new Promise(r => setTimeout(r, 2000))
          }
          if (!activePollsRef.current.has(sourceId)) return

          try {
            const statusRes = await fetchSourceStatusApi(notebookId, sourceId)
            const prevStatus = logState.lastStatus
            const nextStatus = statusRes.status

            setUploads(prev =>
              prev.map(u =>
                u.id === sourceId ? applyStatusToUpload({ ...u, retrying: false }, statusRes) : u,
              ),
            )

            if (nextStatus !== prevStatus) {
              const stageLogs = logsForStatusTransition(
                fileName,
                prevStatus,
                nextStatus,
                statusRes,
                logState,
              )
              stageLogs.forEach(msg => addLog(msg))
            } else {
              logState.lastStatus = nextStatus
            }

            if (
              nextStatus === 'completed' ||
              nextStatus === 'ready' ||
              nextStatus === 'failed' ||
              nextStatus === 'error'
            ) {
              return
            }

            // Stale: keep polling lightly but surface retry via is_stale on uploads
            if (statusRes.is_stale) {
              // Continue until terminal or user retries (retry cancels this poll)
            }
          } catch (err) {
            console.error(`Polling status error for ${fileName}:`, err)
          }
        }
      } finally {
        activePollsRef.current.delete(sourceId)
      }
    },
    [addLog],
  )

  // 1. Fetch notebook, sources & chat history — restore activity once per session
  useEffect(() => {
    if (!id) return
    let cancelled = false
    setLoading(true)
    setError(null)
    setLatestAiUsage(null)
    setNotebookTokenUsage(null)

    Promise.all([
      notebooksApi.get(id),
      fetchSourcesApi(id).catch(() => []),
      fetchChatMessagesApi(id).catch(() => []),
      fetchNotebookTokenUsageApi(id).catch(err => {
        console.error('Failed to load notebook token usage:', err)
        return null
      }),
    ])
      .then(([data, existingSources, existingChatMessages, existingTokenUsage]) => {
        if (cancelled) return

        setNotebook(data)
        setNotebookTokenUsage(existingTokenUsage)
        if (data.title && data.title !== UNTITLED) {
          userHasRenamedRef.current = true
        }
        document.title = `${data.title} - NoteGenio`

        const loadedUploads = existingSources.map(mapApiSourceToUpload)
        setUploads(loadedUploads)

        // Activity restoration: one summary line, once per notebook per session.
        // Do NOT emit per-document "[ANALYSIS] Restored …" (that caused duplicates).
        if (!activityRestoredNotebooks.has(id)) {
          activityRestoredNotebooks.add(id)
          if (existingSources.length > 0) {
            addLog(`Loaded ${existingSources.length} existing document resources`)
          } else {
            addLog('Notebook initialized. No existing sources found.')
          }
        }

        // Resume polling only for sources still processing — never re-ingest Ready docs.
        loadedUploads.forEach(u => {
          if (ACTIVE_PROCESSING_STATUSES.has(u.status) && !u.id.startsWith('temp-')) {
            void pollSourceUntilDone(id, u.id, u.file.name)
          }
        })

        if (existingChatMessages.length > 0) {
          const loadedMessages: ChatMessageType[] = existingChatMessages.map(m =>
            mapApiChatMessage(m),
          )
          setMessages(loadedMessages)
          const lastAssistant = [...loadedMessages].reverse().find(m => m.role === 'assistant')
          if (lastAssistant?.usage) {
            setLatestAiUsage(lastAssistant.usage)
          }
        }
      })
      .catch(err => {
        if (cancelled) return
        console.error('Failed to load notebook:', err)
        setError('Notebook not found or accessible.')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
      // Stop polls belonging to this mount; StrictMode remount starts fresh polls if needed.
      activePollsRef.current.clear()
    }
  }, [id, addLog, pollSourceUntilDone])

  // 2. Sync document.title when notebook title changes
  useEffect(() => {
    if (notebook?.title) {
      document.title = `${notebook.title} - NoteGenio`
    }
  }, [notebook?.title])

  // 3. Auto-open Upload Modal when no sources on first open
  useEffect(() => {
    if (!loading && notebook && uploads.length === 0 && !hasAutoOpenedModal) {
      setShowUploadModal(true)
      setHasAutoOpenedModal(true)
    }
  }, [loading, notebook, uploads.length, hasAutoOpenedModal])

  // 4. Auto-update description to match source count
  useEffect(() => {
    if (!notebook || !id) return
    const label = sourceCountLabel(uploads.length)
    if (notebook.description === label) return
    setNotebook(prev => (prev ? { ...prev, description: label } : prev))
    notebooksApi.update(id, { description: label }).catch(() => {})
  }, [uploads.length, id]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const handleAddFiles = useCallback(
    (files: File[]) => {
      if (!id) return

      const isFirstUpload =
        uploads.length === 0 && notebook?.title === UNTITLED && !userHasRenamedRef.current

      if (isFirstUpload && files.length > 0) {
        const newTitle = files[0].name.replace(/\.[^/.]+$/, '').trim()
        if (newTitle) {
          setNotebook(prev => (prev ? { ...prev, title: newTitle } : prev))
          document.title = `${newTitle} - NoteGenio`
          notebooksApi.update(id, { title: newTitle }).catch(err => {
            console.error('Failed to update notebook title:', err)
          })
        }
      }

      files.forEach(file => {
        const tempId = `temp-${Math.random().toString(36).substring(2, 9)}`

        const newUpload: UploadFile = {
          id: tempId,
          file,
          status: 'uploading',
          progress: 30,
          processing_started_at: new Date().toISOString(),
        }

        setUploads(prev => [...prev, newUpload])
        addLog(`[INGESTION] Uploading ${file.name}…`)

        uploadSourceApi(id, file)
          .then(apiSource => {
            const mapped = mapApiSourceToUpload({
              ...apiSource,
              title: file.name,
            })
            mapped.file = file
            mapped.progress = 50

            setUploads(prev => prev.map(u => (u.id === tempId ? mapped : u)))
            addLog(`[INGESTION] Saved ${file.name}. Starting runtime analysis & ingestion…`)

            pollLogStateRef.current.set(apiSource.id, {
              lastStatus: apiSource.status,
              loggedStages: new Set(),
            })
            void pollSourceUntilDone(id, apiSource.id, file.name)
          })
          .catch(err => {
            console.error(`Upload error for ${file.name}:`, err)
            setUploads(prev =>
              prev.map(u =>
                u.id === tempId
                  ? { ...u, status: 'error', error: err.message, processing_failed_at: new Date().toISOString() }
                  : u,
              ),
            )
            addLog(
              `[ERROR] File upload failed for ${file.name}: ${
                err.response?.data?.detail || err.message
              }`,
            )
          })
      })
    },
    [id, addLog, uploads.length, notebook?.title, pollSourceUntilDone],
  )

  const handleRetrySource = useCallback(
    async (sourceId: string) => {
      if (!id || sourceId.startsWith('temp-')) return

      const upload = uploads.find(u => u.id === sourceId)
      const fileName = upload?.file.name ?? 'document'

      setUploads(prev =>
        prev.map(u =>
          u.id === sourceId
            ? {
                ...u,
                retrying: true,
                status: 'processing',
                is_stale: false,
                error: undefined,
                processing_started_at: new Date().toISOString(),
                processing_completed_at: null,
                processing_failed_at: null,
                processing_timings: null,
              }
            : u,
        ),
      )
      addLog(`[RETRY] Retrying processing for ${fileName}…`)

      stopPolling(sourceId)
      pollLogStateRef.current.set(sourceId, { lastStatus: '', loggedStages: new Set() })

      try {
        const statusRes = await retrySourceApi(id, sourceId)
        setUploads(prev =>
          prev.map(u =>
            u.id === sourceId ? applyStatusToUpload({ ...u, retrying: true }, statusRes) : u,
          ),
        )
        void pollSourceUntilDone(id, sourceId, fileName)
      } catch (err: unknown) {
        const detail =
          (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data
            ?.detail ||
          (err as { message?: string })?.message ||
          'Retry failed'
        setUploads(prev =>
          prev.map(u =>
            u.id === sourceId
              ? { ...u, retrying: false, status: 'error', error: String(detail) }
              : u,
          ),
        )
        addLog(`[ERROR] ${fileName} · Retry failed · ${detail}`)
      }
    },
    [id, uploads, addLog, stopPolling, pollSourceUntilDone],
  )

  const handleRemoveFile = useCallback(
    (fileId: string) => {
      stopPolling(fileId)
      pollLogStateRef.current.delete(fileId)
      if (id) {
        deleteSourceApi(id, fileId).catch(err => console.error('Failed to delete source:', err))
      }
      setUploads(prev => prev.filter(u => u.id !== fileId))
      if (selectedViewFile?.id === fileId) {
        setSelectedViewFile(null)
      }
      addLog(`Resource removed.`)
    },
    [id, selectedViewFile?.id, addLog, stopPolling],
  )

  const handleTitleChange = (newTitle: string) => {
    if (!notebook || !id) return
    userHasRenamedRef.current = true
    setNotebook({ ...notebook, title: newTitle })
    document.title = `${newTitle} - NoteGenio`
  }

  const handleTitleBlur = (finalTitle: string) => {
    if (!id) return
    const trimmed = finalTitle.trim() || UNTITLED
    if (trimmed !== notebook?.title) {
      setNotebook(prev => (prev ? { ...prev, title: trimmed } : prev))
    }
    notebooksApi.update(id, { title: trimmed }).catch(() => {})
  }

  const handleSendMessage = async (text: string) => {
    const trimmed = text.trim()
    if (!trimmed || sending || !id) return

    const tempUserMsg: ChatMessageType = {
      id: Math.random().toString(36).substring(2, 9),
      notebook_id: id,
      role: 'user',
      content: trimmed,
      created_at: new Date().toISOString(),
    }

    setMessages(prev => [...prev, tempUserMsg])
    setSending(true)
    addLog(`[USER QUERY] "${trimmed}"`)

    try {
      const savedMessages = await sendChatMessageApi(id, trimmed)
      const formatted: ChatMessageType[] = savedMessages.map(m => mapApiChatMessage(m))
      const assistantMsg = formatted.find(m => m.role === 'assistant')

      setMessages(prev => {
        const withoutTemp = prev.filter(m => m.id !== tempUserMsg.id)
        return [...withoutTemp, ...formatted]
      })

      if (assistantMsg?.retrieved_evidence?.length) {
        addLog(`[RETRIEVAL] ${assistantMsg.retrieved_evidence.length} relevant chunks retrieved`)
      }
      if (assistantMsg?.citations?.length) {
        addLog(
          `[GENERATION] ${assistantMsg.citations.length} citation${
            assistantMsg.citations.length === 1 ? '' : 's'
          } in answer`,
        )
      }
      if (assistantMsg?.usage) {
        setLatestAiUsage(assistantMsg.usage)
        const total = assistantMsg.usage.total_tokens
        addLog(
          `[GENERATION] Model response complete${
            total != null ? ` · ${total.toLocaleString()} tokens` : ''
          }`,
        )
      } else {
        addLog('[ASSISTANT ANSWER] Response saved to database.')
      }
      try {
        setNotebookTokenUsage(await fetchNotebookTokenUsageApi(id))
      } catch (usageErr) {
        console.error('Failed to refresh notebook token usage:', usageErr)
      }
    } catch (err: unknown) {
      console.error('Failed to send chat message:', err)
      const detail =
        (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data
          ?.detail ||
        (err as { message?: string })?.message ||
        'Unknown error'
      addLog(`[ERROR] Failed to save chat message: ${detail}`)
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return (
      <div className="notebook-loading">
        <Spinner size="lg" />
        <p>Loading notebook workspace…</p>
      </div>
    )
  }

  if (error || !notebook) {
    return (
      <div className="notebook-error">
        <h2>Notebook Not Found</h2>
        <p>{error || 'Unable to load notebook.'}</p>
        <button onClick={() => navigate('/dashboard')} className="button button--primary">
          Return to Dashboard
        </button>
      </div>
    )
  }

  const suggestedQuestions = [
    'Summarize the key points from my uploaded documents.',
    'What are the main takeaways?',
    'Find specific references to my query.',
  ]

  return (
    <div className="notebook-workspace">
      <WorkspaceHeader
        title={notebook.title}
        description={notebook.description ?? sourceCountLabel(uploads.length)}
        tokenUsage={notebookTokenUsage}
        onTitleChange={handleTitleChange}
        onTitleBlur={handleTitleBlur}
      />

      <div className="nb-tabs" role="tablist" aria-label="Notebook sections">
        <button
          role="tab"
          aria-selected={activeTab === 'sources'}
          className={`nb-tabs__tab${activeTab === 'sources' ? ' nb-tabs__tab--active' : ''}`}
          onClick={() => setActiveTab('sources')}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          Sources
          {uploads.length > 0 && <span className="nb-tabs__badge">{uploads.length}</span>}
        </button>

        <button
          role="tab"
          aria-selected={activeTab === 'chat'}
          className={`nb-tabs__tab${activeTab === 'chat' ? ' nb-tabs__tab--active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          Chat
          {messages.length > 0 && <span className="nb-tabs__badge">{messages.length}</span>}
        </button>
      </div>

      <div className="notebook-workspace__body">
        <SourcesSidebar
          uploads={uploads}
          onRemove={handleRemoveFile}
          onRetry={handleRetrySource}
          onOpenUploadModal={() => {
            setShowUploadModal(true)
            setActiveTab('sources')
          }}
          activePreviewFile={selectedViewFile}
          onSelectFile={file => setSelectedViewFile(file)}
          activeTab={activeTab}
        />

        <main className={`chat-workspace${activeTab === 'chat' ? ' chat-workspace--active-tab' : ''}`}>
          <div className="chat-workspace__messages">
            {messages.length === 0 ? (
              <div className="chat-workspace__empty">
                <div className="chat-workspace__empty-badge">
                  <BrandLogo size={32} showText={false} />
                  <span>NoteGenio Assistant</span>
                </div>
                <h2>Chat with your sources</h2>
                <p>
                  Ask questions, summarize documents, or extract key information. Answers are grounded
                  in your uploaded source files.
                </p>

                <div className="chat-workspace__suggestions">
                  <p className="chat-workspace__suggestions-label">Suggested prompts:</p>
                  <div className="chat-workspace__suggestions-list">
                    {suggestedQuestions.map((q, idx) => (
                      <button
                        key={idx}
                        className="chat-workspace__suggestion-chip"
                        onClick={() => handleSendMessage(q)}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              messages.map(msg => (
                <ChatMessage
                  key={msg.id}
                  message={msg}
                  activeCitationKey={activeCitation ? citationSelectionKey(activeCitation) : null}
                  onCitationClick={citation => setActiveCitation(citation)}
                />
              ))
            )}

            {sending && (
              <div className="chat-workspace__typing">
                <Spinner size="sm" />
                <span>Thinking &amp; analyzing sources…</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="chat-workspace__input-container">
            <ChatInput onSend={handleSendMessage} loading={sending} disabled={sending} />
          </div>
        </main>

        <StudioSidebar
          activeCitation={activeCitation}
          onClearCitation={() => setActiveCitation(null)}
          uploads={uploads}
          logs={logs}
          latestAiUsage={latestAiUsage}
          onRetry={handleRetrySource}
        />
      </div>

      {showUploadModal && (
        <UploadModal
          uploads={uploads}
          onAdd={handleAddFiles}
          onRemove={handleRemoveFile}
          onRetry={handleRetrySource}
          onClose={() => setShowUploadModal(false)}
        />
      )}
    </div>
  )
}
