import logging
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notebook, User
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Same base as sources router — DB rows and files are separate concerns
STORAGE_DIR = Path(__file__).resolve().parent.parent.parent / "storage"


# ── Schemas ────────────────────────────────────────────────────
class NotebookCreate(BaseModel):
    title: str = "Untitled Notebook"
    description: str | None = None


class NotebookUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class NotebookResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ─── Routes ────────────────────────────────────────────────

@router.get("/", response_model=list[NotebookResponse])
def list_notebooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return only notebooks belonging to the authenticated user."""
    return (
        db.query(Notebook)
        .filter(Notebook.user_id == current_user.id)
        .order_by(Notebook.updated_at.desc())
        .all()
    )


@router.post(
    "/",
    response_model=NotebookResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_notebook(
    payload: NotebookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a notebook for the authenticated user."""
    nb = Notebook(
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
    )

    db.add(nb)
    db.commit()
    db.refresh(nb)

    return nb


@router.get("/{notebook_id}", response_model=NotebookResponse)
def get_notebook(
    notebook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a notebook only if it belongs to the authenticated user."""
    nb = (
        db.query(Notebook)
        .filter(
            Notebook.id == notebook_id,
            Notebook.user_id == current_user.id,
        )
        .first()
    )

    if not nb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found",
        )

    return nb


@router.patch("/{notebook_id}", response_model=NotebookResponse)
def update_notebook(
    notebook_id: uuid.UUID,
    payload: NotebookUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Partially update a notebook's title and/or description."""
    nb = (
        db.query(Notebook)
        .filter(
            Notebook.id == notebook_id,
            Notebook.user_id == current_user.id,
        )
        .first()
    )

    if not nb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(nb, field, value)

    db.commit()
    db.refresh(nb)

    return nb


@router.delete(
    "/{notebook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_notebook(
    notebook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete notebook DB rows (cascade), then remove storage/notebooks/<id>/."""
    nb = (
        db.query(Notebook)
        .filter(
            Notebook.id == notebook_id,
            Notebook.user_id == current_user.id,
        )
        .first()
    )

    if not nb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notebook not found",
        )

    # 1) DB relationships (sources → chunks, chat messages, notebook)
    db.delete(nb)
    db.commit()

    # 2) Physical storage — separate from DB; cascade does not touch disk
    nb_storage_dir = STORAGE_DIR / "notebooks" / str(notebook_id)
    if nb_storage_dir.is_dir():
        try:
            shutil.rmtree(nb_storage_dir)
        except Exception as e:
            logger.warning(
                "Could not remove notebook storage %s: %s", nb_storage_dir, e
            )