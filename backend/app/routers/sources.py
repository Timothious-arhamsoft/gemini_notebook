import json
import logging
import os
import shutil
import uuid
from datetime import datetime
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

from app.database import get_db
from app.models import Notebook, Source, User
from app.rag.ingestion import (
    DocumentIngestionError,
    ingestion_service,
)
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Base storage directory
STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"


# ── Schemas ────────────────────────────────────────────────────
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

    class Config:
        from_attributes = True


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


def _build_source_response(source: Source) -> SourceResponse:
    res = SourceResponse.model_validate(source)
    res.analysis = source.analysis
    if source.file_path and os.path.exists(source.file_path):
        try:
            res.file_size = os.path.getsize(source.file_path)
        except Exception:
            res.file_size = None
    return res


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
    Upload a document file (.pdf, .md, .docx, .txt), parse it with IngestionService,
    and update the Source record lifecycle: UPLOADED -> PROCESSING -> READY (or FAILED).
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
    )
    db.add(source)
    db.commit()
    db.refresh(source)

    analysis_data = None
    # Ingestion / Parsing Step
    try:
        parsed_result = ingestion_service.parse(
            file_path=saved_file_path,
            document_id=source.id,
        )

        extracted_text = parsed_result.get("full_text", "")
        token_count = len(extracted_text.split()) if extracted_text else 0
        analysis_data = parsed_result.get("analysis")

        source.content_text = extracted_text
        source.token_count = token_count
        source.analysis = analysis_data
        source.status = "ready"
        db.commit()
        db.refresh(source)
        logger.info(f"Successfully processed source {source.id} ({source.title})")

    except DocumentIngestionError as die:
        logger.warning(f"Ingestion failed for source {source.id}: {die}")
        source.status = "error"
        source.error_message = str(die)
        db.commit()
        db.refresh(source)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document parsing error: {str(die)}",
        )
    except Exception as exc:
        logger.error(f"Unexpected error parsing source {source.id}: {exc}", exc_info=True)
        source.status = "error"
        source.error_message = str(exc)
        db.commit()
        db.refresh(source)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal ingestion error: {str(exc)}",
        )

    return _build_source_response(source)


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
    return [_build_source_response(s) for s in sources]


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
    return _build_source_response(source)


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
