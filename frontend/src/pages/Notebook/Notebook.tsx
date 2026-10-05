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
        document.title = `${data.title} - Gemini Notebook`
      })
      .catch(err => {
        console.error('Failed to load notebook:', err)
        setError('Notebook not found or accessible.')
      })
      .finally(() => setLoading(false))
  }, [id])

  // 2. Set document title on notebook change
  useEffect(() => {
    if (notebook?.title) {
      document.title = `${notebook.title} - Gemini Notebook`
    }
  }, [notebook?.title])

  // 3. Automatically pop up Upload Modal IF no documents added on open
  useEffect(() => {
    if (!loading && notebook && uploads.length === 0 && !hasAutoOpenedModal) {
      setShowUploadModal(true)
      setHasAutoOpenedModal(true)
    }
  }, [loading, notebook, uploads.length, hasAutoOpenedModal])

  // Scroll to bottom when new messages arrive
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

    setUploads(prev => [...prev, ...newItems])

    // Simulate progress -> processing -> ready
    newItems.forEach(item => {
      setTimeout(() => {
        setUploads(prev => prev.map(u => u.id === item.id ? { ...u, progress: 75, status: 'processing' } : u))
      }, 700)

      setTimeout(() => {
        setUploads(prev => prev.map(u => u.id === item.id ? { ...u, progress: 100, status: 'ready' } : u))
      }, 1500)
    })
  }, [])

  const handleRemoveFile = useCallback((fileId: string) => {
    setUploads(prev => prev.filter(u => u.id !== fileId))
    if (selectedViewFile?.id === fileId) {
      setSelectedViewFile(null)
    }
  }, [selectedViewFile?.id])

  const handleTitleChange = (newTitle: string) => {
    if (!notebook) return
    setNotebook({ ...notebook, title: newTitle })
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
        onTitleChange={handleTitleChange}
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
                  <span>Gemini RAG Assistant</span>
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

      {/* 3. Upload Modal Pop-Up (Appears when clicking Add Source or automatically if empty) */}
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
