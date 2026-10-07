import logging
import os
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models import Notebook, Source, User, Chunk
from app.rag.pipeline import run_runtime_ingestion_pipeline
from app.rag.retrieval import retrieve_chunks, RetrievedChunk
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Base storage directory
STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"


# ── Schemas ────────────────────────────────────────────────────
class ProcessingTimingsSchema(BaseModel):
    upload_s: Optional[float] = None
    parse_and_analysis_s: Optional[float] = None
    chunking_s: Optional[float] = None
    embedding_s: Optional[float] = None
    embedding_model_load_s: Optional[float] = None
    embedding_encode_s: Optional[float] = None
    database_save_s: Optional[float] = None
    total_s: Optional[float] = None
    chunk_count: Optional[int] = None


class SourceResponse(BaseModel):
    id: uuid.UUID
    notebook_id: uuid.UUID
    source_type: str
    title: Optional[str]
    file_path: Optional[str]
    content_text: Optional[str]
    token_count: Optional[int]
    status: str
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    analysis: Optional[Dict[str, Any]] = None
    file_size: Optional[int] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_failed_at: Optional[datetime] = None
    processing_timings: Optional[Dict[str, Any]] = None
    chunk_count: Optional[int] = None

    class Config:
        from_attributes = True


class SourceStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    error_message: Optional[str] = None
    chunk_count: int = 0
    progress_label: str
    analysis: Optional[Dict[str, Any]] = None
    token_count: Optional[int] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    processing_failed_at: Optional[datetime] = None
    processing_timings: Optional[Dict[str, Any]] = None
    is_stale: bool = False


class RetrieveRequest(BaseModel):
    query: str
    top_k: int = 5


class RetrieveResponse(BaseModel):
    query: str
    top_k: int
    retrieved_chunks: List[RetrievedChunk]
    count: int


# ── Helpers ────────────────────────────────────────────────────
def _verify_notebook_access(
    notebook_id: uuid.UUID, current_user: User, db: Session
) -> Notebook:
    nb = (
        db.query(Notebook)
        .filter(Notebook.id == notebook_id, Notebook.user_id == current_user.id)
        .first()
    )
    if not nb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notebook not found"
        )
    return nb


STALE_PROCESSING_SECONDS = 300  # 5 minutes


def _chunk_count(db: Session, source_id: uuid.UUID) -> int:
    return db.query(Chunk).filter(Chunk.source_id == source_id).count()


def _is_stale_processing(source: Source) -> bool:
    if source.status not in {"pending", "processing", "analyzing", "chunking", "embedding"}:
        return False
    started = source.processing_started_at or source.updated_at or source.created_at
    if not started:
        return False
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    return elapsed > STALE_PROCESSING_SECONDS


def _build_source_response(source: Source, db: Session) -> SourceResponse:
    res = SourceResponse.model_validate(source)
    res.analysis = source.analysis
    res.chunk_count = _chunk_count(db, source.id)
    if source.file_path and os.path.exists(source.file_path):
        try:
            res.file_size = os.path.getsize(source.file_path)
        except Exception:
            res.file_size = None
    return res


def _build_status_response(source: Source, db: Session) -> SourceStatusResponse:
    chunk_count = _chunk_count(db, source.id)
    _PROGRESS_LABELS: dict[str, str] = {
        "pending": "Pending…",
        "processing": "Extracting document…",
        "analyzing": "Analyzing document…",
        "chunking": "Splitting into chunks…",
        "embedding": "Generating embeddings…",
        "ready": "Ready",
        "completed": "Ready",
        "error": "Failed",
        "failed": "Failed",
    }
    return SourceStatusResponse(
        id=source.id,
        status=source.status,
        error_message=source.error_message,
        chunk_count=chunk_count,
        progress_label=_PROGRESS_LABELS.get(source.status, source.status),
        analysis=source.analysis,
        token_count=source.token_count,
        processing_started_at=source.processing_started_at,
        processing_completed_at=source.processing_completed_at,
        processing_failed_at=source.processing_failed_at,
        processing_timings=source.processing_timings,
        is_stale=_is_stale_processing(source),
    )


# ── Background task runner ────────────────────────────────────
def _run_pipeline_in_background(source_id: uuid.UUID) -> None:
    """Runs the ingestion pipeline in a dedicated background thread with its own DB session."""
    db = SessionLocal()
    try:
        run_runtime_ingestion_pipeline(source_id=source_id, db=db)
    except Exception as exc:
        logger.error(f"[Background Pipeline] Unhandled error for source {source_id}: {exc}", exc_info=True)
        try:
            source = db.query(Source).filter(Source.id == source_id).first()
            if source:
                source.status = "failed"
                source.error_message = str(exc)
                source.processing_failed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ── Routes ────────────────────────────────────────────────────
@router.post(
    "/{notebook_id}/sources/upload",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_source(
    notebook_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a document file (.pdf, .md, .docx, .txt), save it, create a Source record
    with status 'processing', then launch the full RAG ingestion pipeline in a background
    thread. Returns immediately so the frontend can poll /status for progress.
    """
    _verify_notebook_access(notebook_id, current_user, db)

    file_ext = Path(file.filename).suffix.lower()
    if not file_ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File has no extension.",
        )

    # Prepare storage path
    nb_storage_dir = STORAGE_DIR / "notebooks" / str(notebook_id)
    nb_storage_dir.mkdir(parents=True, exist_ok=True)

    source_id = uuid.uuid4()
    saved_file_name = f"{source_id}_{file.filename}"
    saved_file_path = nb_storage_dir / saved_file_name

    # Save original file to storage
    try:
        with open(saved_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        logger.error(f"Failed to save uploaded file '{file.filename}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {str(e)}",
        )

    # Determine source_type
    source_type = file_ext.lstrip(".")

    # Create initial Source record with status="processing"
    source = Source(
        id=source_id,
        notebook_id=notebook_id,
        source_type=source_type,
        title=file.filename,
        file_path=str(saved_file_path),
        status="processing",
        processing_started_at=datetime.now().astimezone(),
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    # Launch pipeline in background — returns immediately to client
    thread = threading.Thread(
        target=_run_pipeline_in_background,
        args=(source_id,),
        daemon=True,
        name=f"pipeline-{source_id}",
    )
    thread.start()
    logger.info(f"[Upload] Launched background pipeline thread for source {source_id}")

    return _build_source_response(source, db)


@router.get(
    "/{notebook_id}/sources/{source_id}/status",
    response_model=SourceStatusResponse,
)
def get_source_status(
    notebook_id: uuid.UUID,
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lightweight polling endpoint — returns current ingestion status and chunk count."""
    _verify_notebook_access(notebook_id, current_user, db)
    source = (
        db.query(Source)
        .filter(Source.id == source_id, Source.notebook_id == notebook_id)
        .first()
    )
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    return _build_status_response(source, db)


@router.post(
    "/{notebook_id}/sources/{source_id}/retry",
    response_model=SourceStatusResponse,
)
def retry_source_processing(
    notebook_id: uuid.UUID,
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retry ingestion/embedding for a failed or stale source.
    Removes incomplete chunks and re-runs the runtime pipeline idempotently.
    """
    _verify_notebook_access(notebook_id, current_user, db)
    source = (
        db.query(Source)
        .filter(Source.id == source_id, Source.notebook_id == notebook_id)
        .first()
    )
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")

    if source.status in ("completed", "ready"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source is already ready. Delete and re-upload to process again.",
        )

    if source.status in ("pending", "processing", "analyzing", "chunking", "embedding"):
        if not _is_stale_processing(source):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Source is still processing. Retry when failed or stale.",
            )

    db.query(Chunk).filter(Chunk.source_id == source.id).delete()
    source.status = "processing"
    source.error_message = None
    source.processing_started_at = datetime.now().astimezone()
    source.processing_completed_at = None
    source.processing_failed_at = None
    source.processing_timings = None
    db.commit()
    db.refresh(source)

    thread = threading.Thread(
        target=_run_pipeline_in_background,
        args=(source_id,),
        daemon=True,
        name=f"pipeline-retry-{source_id}",
    )
    thread.start()
    logger.info("[Retry] Relaunched pipeline for source %s", source_id)

    return _build_status_response(source, db)


@router.get(
    "/{notebook_id}/sources",
    response_model=List[SourceResponse],
)
def list_sources(
    notebook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all sources associated with a notebook."""
    _verify_notebook_access(notebook_id, current_user, db)
    sources = (
        db.query(Source)
        .filter(Source.notebook_id == notebook_id)
        .order_by(Source.created_at.desc())
        .all()
    )
    return [_build_source_response(s, db) for s in sources]


@router.get(
    "/{notebook_id}/sources/{source_id}",
    response_model=SourceResponse,
)
def get_source(
    notebook_id: uuid.UUID,
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific source for a notebook."""
    _verify_notebook_access(notebook_id, current_user, db)
    source = (
        db.query(Source)
        .filter(Source.id == source_id, Source.notebook_id == notebook_id)
        .first()
    )
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source not found"
        )
    return _build_source_response(source, db)


@router.get(
    "/{notebook_id}/sources/{source_id}/file",
)
def get_source_file(
    notebook_id: uuid.UUID,
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download/stream the raw document file for a source."""
    _verify_notebook_access(notebook_id, current_user, db)
    source = (
        db.query(Source)
        .filter(Source.id == source_id, Source.notebook_id == notebook_id)
        .first()
    )
    if not source or not source.file_path or not os.path.exists(source.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk"
        )

    media_type = "application/pdf" if source.source_type == "pdf" else "application/octet-stream"
    return FileResponse(
        path=source.file_path,
        filename=source.title or "document",
        media_type=media_type,
    )


@router.delete(
    "/{notebook_id}/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_source(
    notebook_id: uuid.UUID,
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a source and its file on disk."""
    _verify_notebook_access(notebook_id, current_user, db)
    source = (
        db.query(Source)
        .filter(Source.id == source_id, Source.notebook_id == notebook_id)
        .first()
    )
    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source not found"
        )

    # Delete storage file
    if source.file_path and os.path.exists(source.file_path):
        try:
            os.remove(source.file_path)
        except Exception as e:
            logger.warning(f"Could not remove file {source.file_path}: {e}")

    db.delete(source)
    db.commit()


@router.post(
    "/{notebook_id}/retrieve",
    response_model=RetrieveResponse,
)
def dev_retrieve_chunks(
    notebook_id: uuid.UUID,
    payload: RetrieveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Development & testing endpoint — embeds query and retrieves top K chunks
    using pgvector cosine similarity, scoped strictly to notebook_id.
    """
    _verify_notebook_access(notebook_id, current_user, db)

    chunks = retrieve_chunks(
        notebook_id=notebook_id,
        query=payload.query,
        db=db,
        top_k=payload.top_k,
    )

    return RetrieveResponse(
        query=payload.query,
        top_k=payload.top_k,
        retrieved_chunks=chunks,
        count=len(chunks),
    )
