import type { SourceStatusResponse } from '../api/sources'
import type { UploadFile, UploadStatus } from '../types'

export const STALE_PROCESSING_MS = 5 * 60 * 1000

export function isPersistedSourceId(id: string): boolean {
  return !id.startsWith('temp-')
}

export const ACTIVE_PROCESSING_STATUSES = new Set([
  'pending',
  'processing',
  'analyzing',
  'chunking',
  'embedding',
  'uploading',
])

export type DocumentDisplayState =
  | 'uploading'
  | 'analyzing'
  | 'chunking'
  | 'embedding'
  | 'saving'
  | 'ready'
  | 'failed'
  | 'stale'

export function mapBackendStatusToUpload(status: string): UploadStatus {
  if (status === 'completed' || status === 'ready') return 'ready'
  if (status === 'failed' || status === 'error') return 'error'
  return status as UploadStatus
}

export function formatDurationSeconds(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds))
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  const rem = s % 60
  return `${m}:${rem.toString().padStart(2, '0')}`
}

export function formatDurationFromTimings(timings?: Record<string, number> | null): string | null {
  if (!timings?.total_s && timings?.total_s !== 0) return null
  return formatDurationSeconds(timings.total_s)
}

export function elapsedSecondsSince(iso: string | null | undefined, nowMs = Date.now()): number {
  if (!iso) return 0
  const start = new Date(iso).getTime()
  if (Number.isNaN(start)) return 0
  return Math.max(0, Math.floor((nowMs - start) / 1000))
}

export function resolveDocumentDisplayState(
  upload: UploadFile,
  statusRes?: Pick<SourceStatusResponse, 'is_stale' | 'status'> | null,
): DocumentDisplayState {
  if (upload.status === 'uploading') return 'uploading'
  if (upload.status === 'error' || upload.status === 'failed') return 'failed'

  const backendStatus = statusRes?.status ?? upload.status
  if (backendStatus === 'completed' || backendStatus === 'ready' || upload.status === 'ready') {
    return 'ready'
  }

  if (statusRes?.is_stale || isLocallyStale(upload)) return 'stale'

  if (backendStatus === 'analyzing' || upload.status === 'analyzing') return 'analyzing'
  if (backendStatus === 'chunking' || upload.status === 'chunking') return 'chunking'
  if (backendStatus === 'embedding' || upload.status === 'embedding') return 'embedding'
  if (backendStatus === 'processing') return 'analyzing'
  return 'embedding'
}

export function isLocallyStale(upload: UploadFile): boolean {
  if (!ACTIVE_PROCESSING_STATUSES.has(upload.status)) return false
  const startedAt = upload.processing_started_at
  if (!startedAt) return false
  const elapsedMs = elapsedSecondsSince(startedAt) * 1000
  return elapsedMs > STALE_PROCESSING_MS
}

export function statusLabelForDisplay(state: DocumentDisplayState): string {
  switch (state) {
    case 'uploading':
      return 'Uploading…'
    case 'analyzing':
      return 'Analyzing…'
    case 'chunking':
      return 'Preparing chunks…'
    case 'embedding':
      return 'Embedding…'
    case 'saving':
      return 'Saving vectors…'
    case 'ready':
      return 'Ready'
    case 'failed':
      return 'Processing failed'
    case 'stale':
      return 'Taking longer than expected'
    default:
      return 'Processing…'
  }
}

export function applyStatusToUpload(
  upload: UploadFile,
  statusRes: SourceStatusResponse,
): UploadFile {
  const mapped = mapBackendStatusToUpload(statusRes.status)
  return {
    ...upload,
    status: mapped,
    analysis: statusRes.analysis ?? upload.analysis,
    chunk_count: statusRes.chunk_count,
    processing_started_at: statusRes.processing_started_at ?? upload.processing_started_at,
    processing_completed_at: statusRes.processing_completed_at ?? upload.processing_completed_at,
    processing_failed_at: statusRes.processing_failed_at ?? upload.processing_failed_at,
    processing_timings: statusRes.processing_timings ?? upload.processing_timings,
    is_stale: statusRes.is_stale,
    error: statusRes.error_message ?? upload.error,
  }
}

export function mapApiSourceToUpload(s: {
  id: string
  title: string | null
  status: string
  analysis?: UploadFile['analysis']
  content_text?: string | null
  file_size?: number | null
  processing_started_at?: string | null
  processing_completed_at?: string | null
  processing_failed_at?: string | null
  processing_timings?: Record<string, number> | null
  chunk_count?: number | null
  error_message?: string | null
}): UploadFile {
  const isDone = s.status === 'completed' || s.status === 'ready'
  const isErr = s.status === 'error' || s.status === 'failed'
  return {
    id: s.id,
    file: new File([], s.title || 'document'),
    status: isDone ? 'ready' : isErr ? 'error' : mapBackendStatusToUpload(s.status),
    progress: 100,
    analysis: s.analysis ?? null,
    content_text: s.content_text,
    file_size: s.file_size ?? s.analysis?.total_characters ?? 0,
    processing_started_at: s.processing_started_at ?? null,
    processing_completed_at: s.processing_completed_at ?? null,
    processing_failed_at: s.processing_failed_at ?? null,
    processing_timings: s.processing_timings ?? null,
    chunk_count: s.chunk_count ?? undefined,
    error: s.error_message ?? undefined,
  }
}
