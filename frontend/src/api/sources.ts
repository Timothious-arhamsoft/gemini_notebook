import { apiClient } from './client'

export interface ApiSource {
  id: string
  notebook_id: string
  source_type: string
  title: string
  file_path: string | null
  content_text: string | null
  token_count: number | null
  status: 'pending' | 'processing' | 'ready' | 'error' | 'failed'
  error_message: string | null
  created_at: string
  updated_at: string
}

export async function uploadSourceApi(notebookId: string, file: File): Promise<ApiSource> {
  const formData = new FormData()
  formData.append('file', file)

  const res = await apiClient.post<ApiSource>(`/notebooks/${notebookId}/sources/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return res.data
}

export async function fetchSourcesApi(notebookId: string): Promise<ApiSource[]> {
  const res = await apiClient.get<ApiSource[]>(`/notebooks/${notebookId}/sources`)
  return res.data
}

export async function deleteSourceApi(notebookId: string, sourceId: string): Promise<void> {
  await apiClient.delete(`/notebooks/${notebookId}/sources/${sourceId}`)
}
