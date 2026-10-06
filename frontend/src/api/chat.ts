import { apiClient } from './client'
import type { Citation } from '../types'

export interface ApiChatMessage {
  id: string
  notebook_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  citations?: Citation[] | null
  created_at: string
}

export async function fetchChatMessagesApi(notebookId: string): Promise<ApiChatMessage[]> {
  const res = await apiClient.get<ApiChatMessage[]>(`/notebooks/${notebookId}/chat/messages`)
  return res.data
}

export async function sendChatMessageApi(notebookId: string, content: string): Promise<ApiChatMessage[]> {
  const res = await apiClient.post<ApiChatMessage[]>(`/notebooks/${notebookId}/chat/messages`, { content })
  return res.data
}
