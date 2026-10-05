import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { notebooksApi } from '../../api/notebooks'
import { uploadSourceApi, fetchSourcesApi, deleteSourceApi } from '../../api/sources'
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

/** Derive singular/plural source count label */
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

  // Track activity logs for the right sidebar studio
  const [logs, setLogs] = useState<string[]>([])
  // Active citation detail view
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null)

  // Track whether the user has manually set the title
  const userHasRenamedRef = useRef(false)

  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [sending, setSending] = useState(false)
  const [activeTab, setActiveTab] = useState<'sources' | 'chat'>('chat')

  const chatEndRef = useRef<HTMLDivElement>(null)

  const addLog = useCallback((message: string) => {
    const timestamp = new Date().toLocaleTimeString([], { hour12: false })
    setLogs(prev => [`[${timestamp}] ${message}`, ...prev])
  }, [])

  // 1. Fetch notebook & sources details
  useEffect(() => {
    if (!id) return
    setLoading(true)

    Promise.all([
      notebooksApi.get(id),
      fetchSourcesApi(id).catch(() => []),
    ])
      .then(([data, existingSources]) => {
        setNotebook(data)
        if (data.title && data.title !== UNTITLED) {
          userHasRenamedRef.current = true
        }
        document.title = `${data.title} - NoteGenio`

        if (existingSources.length > 0) {
          const loadedUploads: UploadFile[] = existingSources.map(s => ({
            id: s.id,
            file: new File([], s.title || 'document'),
            status: s.status === 'ready' ? 'ready' : s.status === 'error' || s.status === 'failed' ? 'error' : 'processing',
            progress: 100,
          }))
          setUploads(loadedUploads)
          addLog(`Loaded ${existingSources.length} existing document resources from database.`)
        } else {
          addLog('Notebook initialized. No existing sources found.')
        }
      })
      .catch(err => {
        console.error('Failed to load notebook:', err)
        setError('Notebook not found or accessible.')
      })
      .finally(() => setLoading(false))
  }, [id, addLog])

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
    setNotebook(prev => prev ? { ...prev, description: label } : prev)
    notebooksApi.update(id, { description: label }).catch(() => {})
  }, [uploads.length, id]) // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  // Handle uploading files via FastAPI backend
  const handleAddFiles = useCallback((files: File[]) => {
    if (!id) return

    files.forEach(file => {
      const tempId = Math.random().toString(36).substring(2, 9)
      const newUpload: UploadFile = {
        id: tempId,
        file,
        status: 'uploading',
        progress: 30,
      }

      setUploads(prev => [...prev, newUpload])
      addLog(`[INGESTION] Uploading ${file.name}...`)

      uploadSourceApi(id, file)
        .then(apiSource => {
          setUploads(prev => prev.map(u => u.id === tempId ? {
            id: apiSource.id,
            file,
            status: apiSource.status === 'ready' ? 'ready' : 'error',
            progress: 100,
          } : u))
          addLog(`[SUCCESS] IngestionService parsed ${file.name} (Status: ${apiSource.status}, Tokens: ${apiSource.token_count || 0})`)
        })
        .catch(err => {
          console.error(`Ingestion error for ${file.name}:`, err)
          setUploads(prev => prev.map(u => u.id === tempId ? { ...u, status: 'error', error: err.message } : u))
          addLog(`[ERROR] Document ingestion failed for ${file.name}: ${err.response?.data?.detail || err.message}`)
        })
    })
  }, [id, addLog])

  const handleRemoveFile = useCallback((fileId: string) => {
    if (id) {
      deleteSourceApi(id, fileId).catch(err => console.error('Failed to delete source:', err))
    }
    setUploads(prev => prev.filter(u => u.id !== fileId))
    if (selectedViewFile?.id === fileId) {
      setSelectedViewFile(null)
    }
    addLog(`Resource ${fileId} removed.`)
  }, [id, selectedViewFile?.id, addLog])

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
      setNotebook(prev => prev ? { ...prev, title: trimmed } : prev)
    }
    notebooksApi.update(id, { title: trimmed }).catch(() => {})
  }

  // Handle sending chat message
  const handleSendMessage = async (text: string) => {
    if (!text.trim() || sending || !id) return

    const userMsg: ChatMessageType = {
      id: Math.random().toString(36).substring(2, 9),
      notebook_id: id,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMsg])
    setSending(true)
    addLog(`[USER QUERY] "${text}"`)

    setTimeout(() => {
      const readySources = uploads.filter(u => u.status === 'ready')
      let aiContent = `Based on your uploaded sources, here is what I found regarding "${text}":\n\n`

      if (readySources.length > 0) {
        aiContent += `Key insights extracted from **${readySources[0].file.name}**:\n` +
          `• The document content was successfully processed by the IngestionService.\n` +
          `• Click the citation below to inspect the highlighted chunk extract in the right sidebar studio.`
      } else {
        aiContent += `No source documents are currently active. Upload PDF, TXT, or MD files in the left sidebar to get grounded answers with direct citations!`
      }

      const citationObj: Citation | undefined = readySources.length > 0 ? {
        source_id: readySources[0].id,
        source_title: readySources[0].file.name,
        excerpt: `Direct extracted excerpt matching "${text}" from document ${readySources[0].file.name}.`,
      } : undefined

      const aiMsg: ChatMessageType = {
        id: Math.random().toString(36).substring(2, 9),
        notebook_id: id,
        role: 'assistant',
        content: aiContent,
        citations: citationObj ? [citationObj] : undefined,
        created_at: new Date().toISOString(),
      }

      setMessages(prev => [...prev, aiMsg])
      setSending(false)
      addLog(`[ASSISTANT ANSWER] Generated response with ${citationObj ? '1 citation' : '0 citations'}.`)
    }, 1000)
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
    "Summarize the key points from my uploaded documents.",
    "What are the main takeaways?",
    "Find specific references to my query.",
  ]

  return (
    <div className="notebook-workspace">
      {/* 1. Header */}
      <WorkspaceHeader
        title={notebook.title}
        description={notebook.description ?? sourceCountLabel(uploads.length)}
        onTitleChange={handleTitleChange}
        onTitleBlur={handleTitleBlur}
      />

      {/* 2. Mobile Tab Bar */}
      <div className="nb-tabs" role="tablist" aria-label="Notebook sections">
        <button
          role="tab"
          aria-selected={activeTab === 'sources'}
          className={`nb-tabs__tab${activeTab === 'sources' ? ' nb-tabs__tab--active' : ''}`}
          onClick={() => setActiveTab('sources')}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
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
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
          Chat
          {messages.length > 0 && <span className="nb-tabs__badge">{messages.length}</span>}
        </button>
      </div>

      {/* 3. Main Workspace Layout */}
      <div className="notebook-workspace__body">
        {/* Left Panel: Sources Sidebar */}
        <SourcesSidebar
          uploads={uploads}
          onRemove={handleRemoveFile}
          onOpenUploadModal={() => { setShowUploadModal(true); setActiveTab('sources') }}
          activePreviewFile={selectedViewFile}
          onSelectFile={file => setSelectedViewFile(file)}
          activeTab={activeTab}
        />

        {/* Center Panel: Chat Workspace */}
        <main className={`chat-workspace${activeTab === 'chat' ? ' chat-workspace--active-tab' : ''}`}>
          <div className="chat-workspace__messages">
            {messages.length === 0 ? (
              <div className="chat-workspace__empty">
                <div className="chat-workspace__empty-badge">
                  <svg width="24" height="24" viewBox="0 0 28 28" fill="none">
                    <rect width="28" height="28" rx="8" fill="var(--accent)" />
                    <path d="M8 8h8a6 6 0 0 1 0 12H8V8Z" fill="white" opacity="0.9"/>
                  </svg>
                  <span>NoteGenio Assistant</span>
                </div>
                <h2>Chat with your sources</h2>
                <p>
                  Ask questions, summarize documents, or extract key information.
                  Answers are grounded in your uploaded source files.
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
            <ChatInput
              onSend={handleSendMessage}
              loading={sending}
              disabled={sending}
            />
          </div>
        </main>

        {/* Right Panel: Studio & Citation Sidebar */}
        <StudioSidebar
          activeCitation={activeCitation}
          onClearCitation={() => setActiveCitation(null)}
          uploads={uploads}
          logs={logs}
        />
      </div>

      {/* 4. Upload Modal */}
      {showUploadModal && (
        <UploadModal
          uploads={uploads}
          onAdd={handleAddFiles}
          onRemove={handleRemoveFile}
          onClose={() => setShowUploadModal(false)}
        />
      )}
    </div>
  )
}
