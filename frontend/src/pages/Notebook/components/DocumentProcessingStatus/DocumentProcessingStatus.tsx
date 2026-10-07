import { useProcessingElapsed } from '../../../../hooks/useProcessingElapsed'
import type { UploadFile } from '../../../../types'
import {
  formatDurationFromTimings,
  formatDurationSeconds,
  isPersistedSourceId,
  resolveDocumentDisplayState,
  statusLabelForDisplay,
} from '../../../../utils/sourceProcessing'

interface Props {
  upload: UploadFile
  onRetry?: (sourceId: string) => void
  retryDisabled?: boolean
  compact?: boolean
}

export function DocumentProcessingStatus({ upload, onRetry, retryDisabled, compact }: Props) {
  const displayState = resolveDocumentDisplayState(upload)
  const isActive =
    displayState === 'uploading' ||
    displayState === 'analyzing' ||
    displayState === 'chunking' ||
    displayState === 'embedding' ||
    displayState === 'saving'

  const elapsed = useProcessingElapsed(upload.processing_started_at, isActive)
  const label = statusLabelForDisplay(displayState)

  const completedDuration =
    formatDurationFromTimings(upload.processing_timings) ??
    (upload.processing_started_at && upload.processing_completed_at
      ? formatDurationSeconds(
          Math.floor(
            (new Date(upload.processing_completed_at).getTime() -
              new Date(upload.processing_started_at).getTime()) /
              1000,
          ),
        )
      : null)

  const showRetry =
    (displayState === 'failed' || displayState === 'stale') &&
    onRetry &&
    isPersistedSourceId(upload.id)

  let statusText = label
  if (displayState === 'ready' && completedDuration) {
    statusText = `Ready · ${completedDuration}`
  } else if (isActive && elapsed > 0) {
    statusText = `${label.replace('…', '')}… ${formatDurationSeconds(elapsed)}`
  }

  return (
    <div className={`doc-status doc-status--${displayState}${compact ? ' doc-status--compact' : ''}`}>
      <span className="doc-status__dot" aria-hidden="true" />
      <span className="doc-status__text">{statusText}</span>
      {showRetry && (
        <button
          type="button"
          className="doc-status__retry"
          title="Retry processing"
          aria-label={`Retry processing for ${upload.file.name}`}
          disabled={retryDisabled}
          onClick={e => {
            e.stopPropagation()
            onRetry?.(upload.id)
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <polyline points="23 4 23 10 17 10" />
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
          </svg>
        </button>
      )}
    </div>
  )
}
