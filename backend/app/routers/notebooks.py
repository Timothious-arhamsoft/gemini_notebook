import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notebook

router = APIRouter()


# ─── Schemas ───────────────────────────────────────────────
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
def list_notebooks(db: Session = Depends(get_db)):
    """Return all notebooks (auth/filtering wired later)."""
    return db.query(Notebook).order_by(Notebook.updated_at.desc()).all()


@router.post("/", response_model=NotebookResponse, status_code=status.HTTP_201_CREATED)
def create_notebook(payload: NotebookCreate, db: Session = Depends(get_db)):
    """Create a notebook. user_id is stub — replace with auth dep."""
    from app.models import User
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=400, detail="No users exist yet. Register first.")
    nb = Notebook(user_id=user.id, title=payload.title, description=payload.description)
    db.add(nb)
    db.commit()
    db.refresh(nb)
    return nb


@router.get("/{notebook_id}", response_model=NotebookResponse)
def get_notebook(notebook_id: uuid.UUID, db: Session = Depends(get_db)):
    nb = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return nb


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notebook(notebook_id: uuid.UUID, db: Session = Depends(get_db)):
    nb = db.query(Notebook).filter(Notebook.id == notebook_id).first()
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")
    db.delete(nb)
    db.commit()
