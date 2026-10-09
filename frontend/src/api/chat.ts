import { apiClient } from './client'
import type { Citation, GroqUsage, NotebookTokenUsage } from '../types'

export interface ApiChatMessage {
  id: string
  notebook_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  citations?: Citation[] | null
  retrieved_evidence?: Citation[] | null
  usage?: GroqUsage | null
  created_at: string
}

function normalizeCitation(c: Citation): Citation {
  return {
    ...c,
    source_id: String(c.source_id),
    source_title: c.source_title || c.source_name || 'Unknown source',
    excerpt: c.excerpt ?? c.content?.slice(0, 300) ?? '',
  }
}

export function mapApiChatMessage(m: ApiChatMessage) {
  return {
    id: m.id,
    notebook_id: m.notebook_id,
    role: m.role,
    content: m.content,
    citations: m.citations?.map(normalizeCitation) ?? undefined,
    retrieved_evidence: m.retrieved_evidence?.map(normalizeCitation) ?? undefined,
    usage: m.usage ?? undefined,
    created_at: m.created_at,
  }
}

export async function fetchChatMessagesApi(notebookId: string): Promise<ApiChatMessage[]> {
  const res = await apiClient.get<ApiChatMessage[]>(`/notebooks/${notebookId}/chat/messages`)
  return res.data
}

export async function fetchNotebookTokenUsageApi(notebookId: string): Promise<NotebookTokenUsage> {
  const res = await apiClient.get<NotebookTokenUsage>(`/notebooks/${notebookId}/chat/usage`)
  return res.data
}

export async function sendChatMessageApi(notebookId: string, content: string): Promise<ApiChatMessage[]> {
  const res = await apiClient.post<ApiChatMessage[]>(`/notebooks/${notebookId}/chat/messages`, { content })
  return res.data
}
