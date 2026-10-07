import type { SourceStatusResponse } from '../../api/sources'

export interface PollLogState {
  lastStatus: string
  loggedStages: Set<string>
}

export function formatTimingSeconds(value?: number | null): string {
  if (value == null) return '—'
  return `${value.toFixed(1)}s`
}

export function buildStageCompleteLog(
  stage: 'analysis' | 'chunking' | 'embedding' | 'complete' | 'failed',
  fileName: string,
  statusRes: SourceStatusResponse,
): string | null {
  const t = statusRes.processing_timings ?? {}

  switch (stage) {
    case 'analysis':
      return `[ANALYSIS] ${fileName} · Completed · ${formatTimingSeconds(t.parse_and_analysis_s)}`
    case 'chunking': {
      const chunks = statusRes.chunk_count || t.chunk_count
      return `[CHUNKING] ${fileName} · Created ${chunks ?? '—'} chunks · ${formatTimingSeconds(t.chunking_s)}`
    }
    case 'embedding':
      return `[EMBEDDING] ${fileName} · Generating embeddings…`
    case 'complete': {
      const total = formatTimingSeconds(t.total_s)
      const embed = formatTimingSeconds(t.embedding_s)
      const chunks = statusRes.chunk_count
      return `[COMPLETE] ${fileName} · ${chunks} embeddings saved · ${embed} · Total ${total}`
    }
    case 'failed':
      return `[ERROR] ${fileName} · Processing failed · ${formatTimingSeconds(t.total_s)}${statusRes.error_message ? ` · ${statusRes.error_message}` : ''}`
    default:
      return null
  }
}

export function logsForStatusTransition(
  fileName: string,
  prevStatus: string,
  nextStatus: string,
  statusRes: SourceStatusResponse,
  state: PollLogState,
): string[] {
  const logs: string[] = []
  if (nextStatus === prevStatus) return logs

  if (nextStatus === 'analyzing' && !state.loggedStages.has('analyzing')) {
    logs.push(`[ANALYSIS] ${fileName} · Analyzing layout and text density…`)
    state.loggedStages.add('analyzing')
  }

  if (nextStatus === 'chunking' && !state.loggedStages.has('chunking')) {
    const rec = statusRes.analysis?.recommended_chunk_size
    logs.push(
      `[CHUNKING] ${fileName} · Splitting into chunks${rec ? ` (~${rec} chars)` : ''}…`,
    )
    state.loggedStages.add('chunking')
  }

  if (nextStatus === 'embedding' && !state.loggedStages.has('embedding')) {
    logs.push(`[EMBEDDING] ${fileName} · Generating embeddings…`)
    state.loggedStages.add('embedding')
  }

  if ((nextStatus === 'completed' || nextStatus === 'ready') && !state.loggedStages.has('complete')) {
    if (statusRes.processing_timings?.parse_and_analysis_s != null) {
      logs.push(
        `[ANALYSIS] ${fileName} · Completed · ${formatTimingSeconds(statusRes.processing_timings.parse_and_analysis_s)}`,
      )
    }
    if (statusRes.processing_timings?.chunking_s != null) {
      logs.push(buildStageCompleteLog('chunking', fileName, statusRes)!)
    }
    if (statusRes.processing_timings?.embedding_s != null) {
      logs.push(
        `[EMBEDDING] ${fileName} · Completed · ${formatTimingSeconds(statusRes.processing_timings.embedding_s)}`,
      )
    }
    if (statusRes.processing_timings?.database_save_s != null) {
      logs.push(
        `[SAVE] ${fileName} · Saved to vector store · ${formatTimingSeconds(statusRes.processing_timings.database_save_s)}`,
      )
    }
    logs.push(buildStageCompleteLog('complete', fileName, statusRes)!)
    state.loggedStages.add('complete')
  }

  if ((nextStatus === 'failed' || nextStatus === 'error') && !state.loggedStages.has('failed')) {
    logs.push(buildStageCompleteLog('failed', fileName, statusRes)!)
    state.loggedStages.add('failed')
  }

  state.lastStatus = nextStatus
  return logs
}
