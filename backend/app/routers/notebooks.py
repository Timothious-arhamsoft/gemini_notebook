import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notebook, User
from app.routers.auth import get_current_user
from app.models import Notebook, User
from app.routers.auth import get_current_user

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────
class NotebookCreate(BaseModel):
    title: str = "Untitled Notebook"
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


@router.delete(
    "/{notebook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_notebook(
    notebook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a notebook only if it belongs to the authenticated user."""
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

    db.delete(nb)
    db.commit()