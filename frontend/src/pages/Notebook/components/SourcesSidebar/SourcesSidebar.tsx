import type { UploadFile } from '../../../../types'
import { SourceUpload } from '../SourceUpload/SourceUpload'

interface Props {
  uploads: UploadFile[]
  onAdd: (files: File[]) => void
  onRemove: (id: string) => void
}

export function SourcesSidebar({ uploads, onAdd, onRemove }: Props) {
  return (
    <aside className="sources-sidebar">
      <div className="sources-sidebar__header">
        <h2 className="sources-sidebar__title">Sources</h2>
        <span className="sources-sidebar__count">{uploads.length}</span>
      </div>

      {uploads.length === 0 && (
        <p className="sources-sidebar__empty">
          Add sources to ground the AI's answers in your documents.
        </p>
      )}

      <SourceUpload uploads={uploads} onAdd={onAdd} onRemove={onRemove} />
    </aside>
  )
}
