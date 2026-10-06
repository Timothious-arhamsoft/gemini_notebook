// ── Auth ─────────────────────────────────────────────────────
export interface User {
  id: string
  email: string
  username: string
  full_name: string | null
  is_active: boolean
  is_verified: boolean
  created_at: string
}

export interface AuthTokens {
  access_token: string
  token_type: string
}

export interface LoginPayload {
  email: string
  password: string
}

export interface RegisterPayload {
  email: string
  username: string
  full_name?: string
  password: string
}

// ── Notebooks ────────────────────────────────────────────────
export interface Notebook {
  id: string
  user_id: string
  title: string
  description: string | null
  created_at: string
  updated_at: string
  source_count?: number
}

export interface CreateNotebookPayload {
  title: string
  description?: string
}

// ── Sources ──────────────────────────────────────────────────
export type SourceType = 'pdf' | 'txt' | 'md' | 'docx' | 'url' | 'youtube' | 'pasted_text'
export type SourceStatus = 'pending' | 'processing' | 'ready' | 'error'

export interface Source {
  id: string
  notebook_id: string
  source_type: SourceType
  title: string | null
  file_path: string | null
  raw_url: string | null
  content_text: string | null
  token_count: number | null
  status: SourceStatus
  error_message: string | null
  created_at: string
  updated_at: string
}

// ── Upload state (frontend-only) ─────────────────────────────
export type UploadStatus = 'idle' | 'uploading' | 'processing' | 'ready' | 'error'

export interface UploadFile {
  id: string           // local temp id
  file: File
  status: UploadStatus
  progress: number
  error?: string
  analysis?: import('../api/sources').DocumentAnalysisResult | null
  content_text?: string | null
  file_size?: number | null
}

// ── Chat ─────────────────────────────────────────────────────
export type MessageRole = 'user' | 'assistant' | 'system'

export interface Citation {
  source_id: string
  source_title: string
  excerpt: string
}

export interface ChatMessage {
  id: string
  notebook_id: string
  role: MessageRole
  content: string
  citations?: Citation[]
  created_at: string
}

// ── API response wrappers ────────────────────────────────────
export interface ApiError {
  detail: string
}
