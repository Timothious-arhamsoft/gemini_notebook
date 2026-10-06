import { apiClient } from './client'

export interface DocumentAnalysisResult {
  filename: string
  file_type: string
  total_characters: number
  total_words: number
  paragraph_count: number
  avg_paragraph_chars: number | null
  median_paragraph_chars: number | null
  min_paragraph_chars: number | null
  max_paragraph_chars: number | null
  p75_paragraph_chars: number | null
  p90_paragraph_chars: number | null
  p95_paragraph_chars: number | null
  page_count: number | null
  avg_page_chars: number | null
  median_page_chars: number | null
  min_page_chars: number | null
  max_page_chars: number | null
  heading_count: number | null
  section_count: number | null
  table_count: number | null
  recommended_strategy: string
  recommended_chunk_size: number
  error?: string
}

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
  analysis?: DocumentAnalysisResult | null
  file_size?: number | null
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

export function getSourceFileUrl(notebookId: string, sourceId: string): string {
  return `/api/v1/notebooks/${notebookId}/sources/${sourceId}/file`
}
