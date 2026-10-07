import { useEffect, useState } from 'react'
import { elapsedSecondsSince } from '../utils/sourceProcessing'

/** Live elapsed seconds from a backend processing_started_at timestamp. */
export function useProcessingElapsed(
  processingStartedAt: string | null | undefined,
  active: boolean,
): number {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (!processingStartedAt || !active) {
      setElapsed(0)
      return
    }

    const tick = () => setElapsed(elapsedSecondsSince(processingStartedAt))
    tick()
    const id = window.setInterval(tick, 1000)
    return () => window.clearInterval(id)
  }, [processingStartedAt, active])

  return elapsed
}
