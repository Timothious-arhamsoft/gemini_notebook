from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Liveness + DB connectivity check."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
