import { useCallback, useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { notebooksApi } from '../../api/notebooks'
import { WorkspaceHeader } from './components/WorkspaceHeader/WorkspaceHeader'
import { SourcesSidebar } from './components/SourcesSidebar/SourcesSidebar'
import { ChatMessage } from './components/ChatMessage/ChatMessage'
import { ChatInput } from './components/ChatInput/ChatInput'
import { UploadModal } from './components/UploadModal/UploadModal'
import { Spinner } from '../../components/Spinner'
import type { ChatMessage as ChatMessageType, Notebook, UploadFile } from '../../types'
import './Notebook.css'

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

  // Track whether the user has manually set the title
  const userHasRenamedRef = useRef(false)

  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [sending, setSending] = useState(false)

  const chatEndRef = useRef<HTMLDivElement>(null)

  // 1. Fetch notebook details
  useEffect(() => {
    if (!id) return
    setLoading(true)
    notebooksApi.get(id)
      .then(data => {
        setNotebook(data)
        // If notebook was saved with a real name before, mark as user-renamed
        if (data.title && data.title !== UNTITLED) {
          userHasRenamedRef.current = true
        }
        document.title = `${data.title} - NoteGenio`
      })
      .catch(err => {
        console.error('Failed to load notebook:', err)
        setError('Notebook not found or accessible.')
      })
      .finally(() => setLoading(false))
  }, [id])

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
    // Persist description update in background (best-effort)
    notebooksApi.update(id, { description: label }).catch(() => {})
  }, [uploads.length, id]) // eslint-disable-line react-hooks/exhaustive-deps

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  // Handle uploading files
  const handleAddFiles = useCallback((files: File[]) => {
    const newItems: UploadFile[] = files.map(file => ({
      id: Math.random().toString(36).substring(2, 9),
      file,
      status: 'uploading',
      progress: 25,
    }))

    setUploads(prev => {
      const combined = [...prev, ...newItems]

      // Auto-title: if this is the FIRST upload ever AND user hasn't manually renamed
      if (prev.length === 0 && !userHasRenamedRef.current && newItems.length > 0) {
        const firstFileName = newItems[0].file.name.replace(/\.[^/.]+$/, '') // strip extension
        const newTitle = firstFileName || UNTITLED
        setNotebook(nb => {
          if (!nb) return nb
          document.title = `${newTitle} - NoteGenio`
          // Persist in background
          if (id) notebooksApi.update(id, { title: newTitle }).catch(() => {})
          return { ...nb, title: newTitle }
        })
        userHasRenamedRef.current = true
      }

      return combined
    })

    // Simulate progress → processing → ready
    newItems.forEach(item => {
      setTimeout(() => {
        setUploads(prev => prev.map(u => u.id === item.id ? { ...u, progress: 75, status: 'processing' } : u))
      }, 700)

      setTimeout(() => {
        setUploads(prev => prev.map(u => u.id === item.id ? { ...u, progress: 100, status: 'ready' } : u))
      }, 1500)
    })
  }, [id])

  const handleRemoveFile = useCallback((fileId: string) => {
    setUploads(prev => prev.filter(u => u.id !== fileId))
    if (selectedViewFile?.id === fileId) {
      setSelectedViewFile(null)
    }
  }, [selectedViewFile?.id])

  /** Called when user edits the title inline in WorkspaceHeader */
  const handleTitleChange = (newTitle: string) => {
    if (!notebook || !id) return
    userHasRenamedRef.current = true
    setNotebook({ ...notebook, title: newTitle })
    document.title = `${newTitle} - NoteGenio`
  }

  /** Persist title when user finishes editing (blur event) */
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

    // Simulate RAG answer response
    setTimeout(() => {
      const readySources = uploads.filter(u => u.status === 'ready')
      let aiContent = `Based on your uploaded sources, here is what I found regarding "${text}":\n\n`

      if (readySources.length > 0) {
        aiContent += `Key insights extracted from **${readySources[0].file.name}**:\n` +
          `• The documents emphasize core principles and structured execution.\n` +
          `• All relevant references align with your query context.`
      } else {
        aiContent += `No source documents are currently active. Upload PDF, TXT, or MD files in the left sidebar to get grounded answers with direct citations!`
      }

      const aiMsg: ChatMessageType = {
        id: Math.random().toString(36).substring(2, 9),
        notebook_id: id,
        role: 'assistant',
        content: aiContent,
        citations: readySources.length > 0 ? [
          {
            source_id: readySources[0].id,
            source_title: readySources[0].file.name,
            excerpt: 'Relevant excerpt matching your query from the uploaded document context.',
          }
        ] : undefined,
        created_at: new Date().toISOString(),
      }

      setMessages(prev => [...prev, aiMsg])
      setSending(false)
    }, 1200)
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

      {/* 2. Main Workspace Layout */}
      <div className="notebook-workspace__body">
        {/* Left Panel: Sources Sidebar with inline preview */}
        <SourcesSidebar
          uploads={uploads}
          onRemove={handleRemoveFile}
          onOpenUploadModal={() => setShowUploadModal(true)}
          activePreviewFile={selectedViewFile}
          onSelectFile={file => setSelectedViewFile(file)}
        />

        {/* Center Panel: Chat Workspace */}
        <main className="chat-workspace">
          {/* Chat Messages */}
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
                <ChatMessage key={msg.id} message={msg} />
              ))
            )}

            {sending && (
              <div className="chat-workspace__typing">
                <Spinner size="sm" />
                <span>Thinking & analyzing sources…</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat Input */}
          <div className="chat-workspace__input-container">
            <ChatInput
              onSend={handleSendMessage}
              loading={sending}
              disabled={sending}
            />
          </div>
        </main>
      </div>

      {/* 3. Upload Modal Pop-Up */}
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
