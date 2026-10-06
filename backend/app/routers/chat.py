import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatMessage, Notebook, Source, User
from app.rag.generation import run_rag_pipeline
from app.routers.auth import get_current_user
from app.routers.sources import _verify_notebook_access

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────
class CitationSchema(BaseModel):
    source_id: Optional[uuid.UUID] = None
    source_title: Optional[str] = None
    excerpt: Optional[str] = None


class ChatMessageCreate(BaseModel):
    content: str


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    notebook_id: uuid.UUID
    role: str
    content: str
    citations: Optional[List[CitationSchema]] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── Helpers ────────────────────────────────────────────────────
def _to_chat_response(msg: ChatMessage) -> ChatMessageResponse:
    citations = None
    if msg.source_refs and isinstance(msg.source_refs, list):
        citations = [CitationSchema(**ref) for ref in msg.source_refs]

    return ChatMessageResponse(
        id=msg.id,
        notebook_id=msg.notebook_id,
        role=msg.role,
        content=msg.content,
        citations=citations,
        created_at=msg.created_at,
    )


# ── Routes ────────────────────────────────────────────────────
@router.get(
    "/{notebook_id}/chat/messages",
    response_model=List[ChatMessageResponse],
)
def list_chat_messages(
    notebook_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all chat messages for a notebook in chronological order."""
    _verify_notebook_access(notebook_id, current_user, db)

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.notebook_id == notebook_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [_to_chat_response(m) for m in messages]


@router.post(
    "/{notebook_id}/chat/messages",
    response_model=List[ChatMessageResponse],
    status_code=status.HTTP_201_CREATED,
)
def create_chat_message(
    notebook_id: uuid.UUID,
    payload: ChatMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Save user message, generate assistant response based on notebook sources,
    persist both messages to the database, and return them.
    """
    _verify_notebook_access(notebook_id, current_user, db)

    text = payload.content.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty.",
        )

    # 1. Save user message
    user_msg = ChatMessage(
        id=uuid.uuid4(),
        notebook_id=notebook_id,
        role="user",
        content=text,
    )
    db.add(user_msg)

    # 2. Execute RAG pipeline: query -> BGE embedding -> pgvector retrieval -> context builder -> Groq LLM
    rag_result = run_rag_pipeline(
        notebook_id=notebook_id,
        query=text,
        db=db,
        top_k=5,
    )

    ai_content = rag_result.get("answer", "No response generated.")
    citation_refs = rag_result.get("sources") or None

    # 3. Save assistant response
    assistant_msg = ChatMessage(
        id=uuid.uuid4(),
        notebook_id=notebook_id,
        role="assistant",
        content=ai_content,
        source_refs=citation_refs,
    )
    db.add(assistant_msg)

    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return [_to_chat_response(user_msg), _to_chat_response(assistant_msg)]
